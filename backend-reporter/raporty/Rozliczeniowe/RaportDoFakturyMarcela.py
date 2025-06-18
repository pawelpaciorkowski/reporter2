from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection
from datasources.snr import SNR
from datasources.hbz import HBZ
from api.common import get_db
from decimal import Decimal
MENU_ENTRY = 'Raport Do Faktury Marcela'

REQUIRE_ROLE = ['C-FIN', 'C-CS']
# REQUIRE_ROLE = 'ADMIN'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Liczba Zarejestrowanych badań, nie anulowanych, z pominięciem pakietów'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa', default='-7D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
))

sqlDH = """
        select 
            count(W.id) as ILOSC 
        from Wykonania W 
            left outer join Badania B on B.Id = W.Badanie 
            left outer join GrupyBadan GB on GB.Id = B.Grupa 
            left outer join RodzajeBadan RB on RB.Id = B.Rodzaj 
        where
            W.Datarejestracji  between ? and ?
            and W.Anulowane is null 
            and B.Pakiet = 0
            and (RB.Symbol not in ('DZIALAN', 'PODLOZE', 'OBSERW') or RB.Symbol is null)
"""

def start_report(params):
    laboratoria = []
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)
    for lab in params['laboratoria']:
        lab_task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'zbierz_lab',
        }
        report.create_task(lab_task)
    report.save()
    return report

def zbierz_lab(task_params):
    params = task_params['params']
    oddnia = params['dataod']
    dodnia = params['datado']
    res = []
    sql = sqlDH
    sql_params = [oddnia, dodnia]
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
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
    wartoscSuma = 0
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            for row in result:
                wiersze.append(row)

        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])

    suma = ['W Sumie']
    for wiersz in wiersze:
        wartoscSuma = wartoscSuma + wiersz[1]
    
    suma.append(wartoscSuma)

    wiersze.append(suma)


    res['progress'] = task_group.progress
    res['results'].append(
            {
                'type': 'table',
                'title': 'Liczba Zarejestrowanych badań, nie anulowanych, z pominięciem pakietów',
                'header': 'Baza,Liczba badań'.split(','),
                'data': wiersze
            })
    return res