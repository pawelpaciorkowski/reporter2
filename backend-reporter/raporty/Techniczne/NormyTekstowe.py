import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from outlib.xlsx_standalone import RaportXlsxStandalone
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none, list_from_space_separated
from helpers.validators import validate_symbol

MENU_ENTRY = 'Normy Tekstowe'

SQL = """
    select 
    trim(b.symbol) as badanie,
    trim(m.symbol) as metoda,
    trim(ap.symbol) as aparat,
    trim(par.symbol) as parametr,
    trim(par.wyrazenie) as wyrazenie,
    n.opis, n.DLUGIOPIS

    from normy n

    left join parametry par on par.id=n.PARAMETR
    left join metody m on m.id=par.METODA
    left join aparaty ap on ap.id=m.APARAT
    left join badania b on b.id=m.badanie

    where b.symbol in ($BADANIA$)
    and ((coalesce(n.OPISAUTOMATYCZNY, 0)=0 and n.opis is not null and n.opis <> '') or (n.DLUGIOPIS is not null and n.DLUGIOPIS <> ''))
    and n.del=0 and par.del=0 and m.del=0 and b.del=0 and coalesce(m.nieczynna, 0)=0
    order by 1,2,3,4,5
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="""Normy tekstowe i opisowe dla aktywnych metod. Wpisz symbole badań oddzielone spacjami, dla których mają być pobrane dane."""),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria', pracownie_domyslne=True),
    TextInput(field='badania', title='Badania'),
    Switch(field='zakladki', title='Badania w zakładkach (excel)'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    params['badania'] = list_from_space_separated(params['badania'], upper=True, also_comma=True, also_semicolon=True,
                                                  unique=True)
    if len(params['badania']) == 0:
        raise ValidationError("Nie podano żadnego badania")
    for bad in params['badania']:
        validate_symbol(bad)
    for lab in params['laboratoria']:
        lab_task = {
            'type': 'centrum',
            'priority': 0,
            'timeout': 60,
            'target': lab,
            'params': params,
            'function': 'raport_lab',
        }
        report.create_task(lab_task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']
    sql = SQL
    sql = sql.replace('$BADANIA$', ','.join(["'%s'" % bad for bad in params['badania']]))
    with get_centrum_connection(task_params['target'], load_config=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sql)
    res = []
    for row in rows:
        res.append([task_params['target']] + row)
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
    wiersze_badan = {}
    bledy_polaczen = []
    excel = False
    for job_id, params, status, result in task_group.get_tasks_results():
        if params['params']['zakladki']:
            excel = True
        if status == 'finished' and result is not None:
            wiersze += result
            for wiersz in result:
                bad = wiersz[1]
                if bad not in wiersze_badan:
                    wiersze_badan[bad] = []
                wiersze_badan[bad].append([wiersz[0]] + wiersz[2:])
        if status == 'failed':
            bledy_polaczen.append(params['target'])
    if len(bledy_polaczen) > 0:
        res['errors'].append('%s - błąd połączenia' % ', '.join(bledy_polaczen))
    if not excel:
        res['results'].append({
            'type': 'table',
            'header': 'Laboratorium,Badanie,Metoda,Aparat,Parametr,Opis,Długi opis'.split(','),
            'data': prepare_for_json(wiersze)
        })
    if excel and task_group.progress == 1.0:
        xlsx = RaportXlsxStandalone()
        for badanie, wiersze in wiersze_badan.items():
            xlsx.add_sheet(badanie)
            xlsx.set_columns('Laboratorium,Metoda,Aparat,Parametr,Wyrażenie,Opis,Długi opis'.split(','))
            xlsx.add_rows(wiersze)
        res['results'].append({
            'type': 'download',
            'content': base64.b64encode(xlsx.render_as_bytes()).decode(),
            'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'filename': 'normy_tekstowe_%s.xlsx' % datetime.datetime.now().strftime('%Y-%m-%d'),
        })
    res['progress'] = task_group.progress
    return res
