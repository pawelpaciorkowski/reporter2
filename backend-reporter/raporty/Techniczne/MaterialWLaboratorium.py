import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch, Select
from helpers.validators import validate_date_range
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none, empty

MENU_ENTRY = 'Materiał w laboratorium'

ADD_TO_ROLE = ['L-PRAC']

CACHE_TIMEOUT = 7200

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    TextInput(field='material', title="Symbol materiału"),
))

SQL_MATERIAL = """
    select m.symbol, m.dc, m.nazwa, m.nazwaalternatywna, m.kod, 
    case when gm.id is not null then gm.symbol || ' - ' || gm.nazwa else null end as grupa,
    m.osobnezlecenie 
    from materialy m
    left join grupymaterialow gm on gm.id=m.grupa where m.symbol=? and m.del=0
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if empty(params['material']):
        raise ValidationError("Podaj symbol materiału")
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego labu")
    params['material'] = params['material'].upper().strip()
    report = TaskGroup(__PLUGIN__, params)
    for lab in params['laboratoria']:
        lab_task = {
            'type': 'centrum',
            'priority': 0,
            'target': lab,
            'params': params,
            'function': 'raport_lab',
        }
        report.create_task(lab_task)
    report.save()
    return report


TYTULY_POL = {
    'dc': 'Ost. zmiana',
    'osobnezlecenie': 'Materiał wymaga rejestracji w osobnym zleceniu',
}


def wartosc_pola(fld, val):
    return val


def raport_lab(task_params):
    params = task_params['params']
    symbol = params['material']
    lab = task_params['target']
    res = []
    with get_centrum_connection(lab) as conn:
        cols, rows = conn.raport_z_kolumnami(SQL_MATERIAL, [symbol])
        if len(rows) == 0:
            return {
                'type': 'error',
                'text': 'Nie znaleziono badania o podanym symbolu',
            }
        else:
            header = [TYTULY_POL.get(col, col) for col in cols]
            res.append({
                'title': lab,
                'type': 'table',
                'header': header,
                'data': prepare_for_json(rows)
            })

    return res
