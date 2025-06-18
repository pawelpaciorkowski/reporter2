import json
from datasources.mop import MopDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty, get_snr_connection
from datasources.reporter import ReporterDatasource
from tasks.db import redis_conn

MENU_ENTRY = 'Raport Dietetycy'

REQUIRE_ROLE = ['C-FIN', 'C-CS', 'C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport zarejestrowanych badań dla DOBRY DIETETYK/FIT DIETETYK'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 90)
    laby = []
    rep = ReporterDatasource()
    for row in rep.dict_select("""select symbol from laboratoria where aktywne and wewnetrzne"""):
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
                o.nazwa as ZLEC, 
                p.Nazwisko as PANA, p.Imiona as PAIM,
                b.nazwa AS BAD,
                z.DATAREJESTRACJI As DATA, z.numer AS NR,
                w.cena as CENA
            from wykonania w
                left outer join zlecenia z on z.id =w.ZLECENIE
                left outer join pacjenci p on p.id=z.PACJENT
                left outer join Oddzialy o on o.id=z.oddzial	
                left outer join badania b on b.id =w.BADANIE    
                left outer join grupybadan gb on gb.id = b.grupa
                left outer join Taryfy T on w.taryfa = T.id
            where w.DATAREJESTRACJI between ? and ? and T.symbol = 'X-GOTOW' and o.nazwa like '%DIETETYK%' and o.symbol like '%ADD%'
            and W.Platne = 1 and W.Anulowane is Null  and (GB.Symbol != 'TECHNIC' or GB.Symbol is null) and b.pakiet = '0'
            order by z.DATAREJESTRACJI, z.numer, o.nazwa, b.nazwa
        """
        cols, rows = conn.raport_z_kolumnami(sql, [params['dataod'], params['datado']])
    res = []
    for row in rows:
        res.append(row)
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
        'header': 'Nazwa Poradni,Nazwisko pacjenta,Imię pacjenta,Badanie,Numer zlecenia,Data zlecenia,Wartość'.split(','),
        'data': wiersze,
    })
    res['progress'] = task_group.progress
    return res


