from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from tasks.db import redis_conn
from datasources.mop import MopDatasource
import json
import datetime

MENU_ENTRY = 'Zlecenia internetowe spoza PP'
REQUIRE_ROLE = 'C-ADM'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="Raport przedstawia internetowe kanały dostępu, z których były zlecenia, a nie ma ich w bazie punktów pobrań"),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa', default='-7D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano laboratorium")
    validate_date_range(params['dataod'], params['datado'], 90 if len(params['laboratoria']) else 31)
    report = TaskGroup(__PLUGIN__, params)
    for lab in params['laboratoria']:
        task = {
            'type': 'centrum',
            'target': lab,
            'priority': 1,
            'params': params,
            'function': 'zbierz_lab'
        }
        report.create_task(task)
    task = {
        'type': 'mop',
        'priority': 1,
        'params': params,
        'function': 'zbierz_mop'
    }
    report.create_task(task)
    report.save()
    return report


def zbierz_lab(task_params):
    params = task_params['params']
    with get_centrum_connection(task_params['target']) as conn:
        _, rows = conn.raport_z_kolumnami("""
            select count(z.id), k.symbol, k.nazwa, pr.logowanie, pr.nazwisko
            from zlecenia z
            left join pracownicy pr on pr.id=z.PRACOWNIKODREJESTRACJI -- tak samo może być pracownikodanulowania
            left join KANALY k on k.id=pr.KANALINTERNETOWY
            where z.DATAREJESTRACJI between ? and ?
            and k.id is not null
            group by 2, 3, 4, 5
            order by 2, 3
        """, [params['dataod'], params['datado']])
        return rows


def zbierz_mop(task_params):
    params = task_params['params']
    res = redis_conn.get('mop:aktywne_pp')
    if res is not None:
        res = json.loads(res.decode())
    else:
        mop = MopDatasource()
        mop_res = mop.get_data('api/v2/collection-point')
        res = []
        for pp in mop_res:
            try:
                rpp = {
                    'symbol': pp['marcel'],
                    'lab': pp.get('laboratory', {}).get('symbol', {}),
                    'active': pp['isActive'],
                }
                res.append(rpp)
            except:
                pass
        redis_conn.set('mop:aktywne_pp', json.dumps(res), ex=3600)
    return res


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': ['xlsx', 'pdf']
    }
    dane_zlecenia = {}
    dane_punkty = {}
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            if params['function'] == 'zbierz_lab':
                dane_zlecenia[params['target']] = result
            elif params['function'] == 'zbierz_mop':
                for row in result:
                    dane_punkty[row['symbol'].strip()] = row
        elif status == 'failed' and params['function'] == 'zbierz_lab':
            res['errors'].append("%s - błąd połączenia" % params['target'])
    if len(dane_punkty) > 0:
        wynik = []
        for lab, ilosci in dane_zlecenia.items():
            if lab == 'KOPERNI':
                lab = 'KOPERNIKA'
            # count(z.id), k.symbol, k.nazwa, pr.logowanie, pr.nazwisko
            for row in ilosci:
                kanal = row[1].strip()
                problem = None
                if kanal in dane_punkty:
                    if not dane_punkty[kanal]["active"]:
                        problem = "Punkt pobrań istnieje w bazie ale jest nieaktywny"
                    elif dane_punkty[kanal]['lab'].strip() != lab.strip():
                        problem = "Punkt pobrań istnieje w bazie, ale pod laboratorium %s" % dane_punkty[kanal]['lab']
                else:
                    problem = "Brak kanału w bazie punktów pobrań"
                if problem is not None:
                    wynik.append([lab, kanal, row[2], row[4], row[0], problem])
        res['results'].append({
            'type': 'table',
            'header': 'Laboratorium,Kanał,Nazwa,Pracownik,Ilość zleceń,Problem'.split(','),
            'data': prepare_for_json(wynik)
        })
    res['progress'] = task_group.progress
    return res
