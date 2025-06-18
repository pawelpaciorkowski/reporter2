from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError
from tasks import TaskGroup, Task
from helpers import prepare_for_json, generate_barcode_img_tag, get_centrum_connection
from datasources.ick import IccDatasource
import random
import string

MENU_ENTRY = 'Zablokuj odbiór wyników'
REQUIRE_ROLE = ['C-ADM']

SQL_KODY_PESELU = """
    select distinct zl.numer, zl.datarejestracji, zl.kodkreskowy as kod_zl, w.kodkreskowy as kod_wyk
    from pacjenci pac
    left join zlecenia zl on zl.pacjent=pac.id
    left join wykonania w on w.zlecenie=zl.id
    where pac.pesel=?
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    TabbedView(field='tab', children=[
        Tab(title='Wg kodu', value='kod', panel=VBox(
            InfoText(text='Blokada odbioru wyników wg kodu kreskowego na stronie internetowej i w nowych wynikomatach'),
            TextInput(field="kod", title="Kod kreskowy")
        )),
        Tab(title='Wg PESELu', value='pesel', panel=VBox(
            InfoText(
                text='Blokada odbioru wyników na stronie internetowej i w nowych wynikomatach. UWAGA, obecnie blokada'
                     ' działa na podstawie kodów kreskowych. Uruchomienie raportu zbierze aktualnie istniejące kody'
                     ' z wybranych laboratoriów'
                     ' dla podanego nru PESEL i je zablokuje. PESEL zostanie również zapisany jako zablokowany,'
                     ' ale obecnie taka blokada nie działa.'),
            TextInput(field="pesel", title="PESEL"),
            LabSelector(multiselect=True, selectall=True, field='laboratoria', title='Laboratoria')
        )),
    ]),
))


def start_report(params, user_login):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['tab'] == 'kod':
        if params['kod'] is None or len(params['kod']) not in (9, 10):
            raise ValidationError('Podaj 10-cyfrowy kod kreskowy lub pierwsze 9 cyfr kodu')
        params['kod'] = params['kod'][:9]
        task = {
            'type': 'ick',
            'priority': 1,
            'params': params,
            'user': user_login,
            'function': 'zablokuj_kod'
        }
        report.create_task(task)
    elif params['tab'] == 'pesel':
        if params['pesel'] is None or len(params['pesel']) != 11:
            raise ValidationError('Podaj 11-znakowy nr pesel')
        if len(params['laboratoria']) == 0:
            raise ValidationError("Nie wybrano żadnego laboratorium")
        for lab in params['laboratoria']:
            task = {
                'type': 'centrum',
                'priority': 1,
                'target': lab,
                'params': params,
                'user': user_login,
                'function': 'zbierz_kody'
            }
            report.create_task(task)
    else:
        raise ValidationError('Nieprawidłowy wybór')
    report.save()
    return report


def zablokuj_kod(task_params):
    params = task_params['params']
    user = task_params['user']
    icc = IccDatasource(read_write=True)
    res = {
        'errors': [],
        'results': [],
        'actions': [],
    }
    for row in icc.dict_select("select * from kody_zablokowane where kodkreskowy=%s", [params['kod']]):
        res['errors'].append('Kod już zablokowany %s przez %s @ %s' % (str(row['dc']), row['login'], row['system']))
    if len(res['errors']) == 0:
        icc.insert('kody_zablokowane', {
            'kodkreskowy': params['kod'],
            'dc': 'NOW',
            'system': 'Reporter',
            'login': user
        })
        icc.commit()
        res['results'].append({
            'type': 'info', 'text': 'Zablokowano'
        })
    return res


def zbierz_kody(task_params):
    params = task_params['params']
    user = task_params['user']
    res = []
    with get_centrum_connection(task_params['target']) as conn:
        cols, rows = conn.raport_z_kolumnami(SQL_KODY_PESELU, [params['pesel']])
        for row in rows:
            res.append([user, task_params['target']] + row)
    return res


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': ['xlsx']
    }
    wiersze = []
    kody = []
    user = None
    pesel = None
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            if isinstance(result, list):
                for row in result:
                    if user is None:
                        user = row[0]
                    wiersze.append(row[1:])
                    for val in (row[4], row[5]):
                        if val is not None and len(val) >= 9:
                            val = val.replace('=', '').strip()[:9]
                            if val not in kody:
                                kody.append(val)
            else:
                res['results'].append(result)
            if 'pesel' in params['params']:
                pesel = params['params']['pesel']
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])
    res['progress'] = task_group.progress
    if len(wiersze) > 0:
        res['results'].append({
            'type': 'table',
            'title': 'Kody do zablokowania',
            'header': 'Laboratorium,Nr,Data,Kod zlecenia,Kod wykonania'.split(','),
            'data': prepare_for_json(wiersze)
        })
        if res['progress'] == 1.0:
            zablokowane = []
            icc = IccDatasource(read_write=True)
            for kod in kody:
                ok = True
                for row in icc.dict_select("select * from kody_zablokowane where kodkreskowy=%s", [kod]):
                    ok = False
                    res['errors'].append(
                        'Kod już zablokowany %s przez %s @ %s' % (str(row['dc']), row['login'], row['system']))
                if ok:
                    icc.insert('kody_zablokowane', {
                        'kodkreskowy': kod,
                        'dc': 'NOW',
                        'system': 'Reporter',
                        'login': user
                    })
                    zablokowane.append(kod)
                if pesel is not None:
                    ok = True
                    for row in icc.dict_select("select * from pesele_zablokowane where pesel=%s", [pesel]):
                        ok = False
                    if ok:
                        icc.insert('pesele_zablokowane', {
                            'pesel': pesel,
                            'dc': 'NOW',
                            'system': 'Reporter',
                            'login': user
                        })
            icc.commit()
            res['results'].insert(0, {
                'type': 'info',
                'text': 'Zablokowano kody: %s' % ', '.join(zablokowane)
            })
    return res
