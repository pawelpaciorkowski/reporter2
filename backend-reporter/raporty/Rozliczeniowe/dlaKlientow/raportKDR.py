import json
from datasources.mop import MopDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty, get_snr_connection
from datasources.reporter import ReporterDatasource
from tasks.db import redis_conn

MENU_ENTRY = 'Karta dużej rodziny'

REQUIRE_ROLE = ['C-CS', 'C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport z ilości zleceń i badań zarejestrowanych ze zniżką dla posiadaczy Karty dużej rodziny (15%KDR)'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 96)
    laby = []
    rep = ReporterDatasource()
    for row in rep.dict_select("""select symbol from laboratoria where aktywne and adres is not null"""):
        if row['symbol'] not in laby:
            laby.append(row['symbol'])
    for lab in laby:
        task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'raport_lab'
        }
        report.create_task(task)
    report.save()
    return report


def raport_lab(task_params):
    lab = task_params['target']
    params = task_params['params']
    with get_centrum_connection(lab) as conn:
        sql = """
            select
                count(distinct z.id) as IleZlecen,
                count(w.id) as IleWykonan
            from Zlecenia Z
                left join Wykonania W on W.Zlecenie = Z.ID
                left join StatusyPacjentow SP on SP.id = Z.StatusPacjenta
                left join Badania B on B.id = W.Badanie
                left join GrupyBadan GB on GB.id=B.Grupa
            where
                Z.DataRejestracji between ? and ? and SP.Symbol='15%KDR' and 
                W.Platne = 1 and W.Anulowane is Null and GB.Symbol <> 'TECHNIC'
        """
        cols, rows = conn.raport_z_kolumnami(sql, [params['dataod'], params['datado']])
    res = []
    for row in rows:
        res.append([lab] + row)
    return prepare_for_json(res)


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
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            for wiersz in result:
                wiersze.append(wiersz)
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])
    res['results'].append({
        'type': 'table',
        'header': 'Laboratorium;Ilość zleceń;Ilość badań'.split(';'),
        'data': wiersze,
    })
    res['progress'] = task_group.progress
    return res
