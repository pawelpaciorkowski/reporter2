from datasources.nocka import NockaDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, NumberInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
import datetime

MENU_ENTRY = 'Statystyka osad-rozmaz'

ADD_TO_ROLE = ['L-PRAC']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="""Raport dla Angeliki"""),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Zatwierdzone od', default='PZM'),
    DateInput(field='datado', title='Zatwierdzone od', default='KZM')
))

SQL = """
    select wp.lab as "Laboratorium", wp.badanie "Symbol Badania",
    case when wp.blad_wykonania is null then '' else wp.blad_wykonania end as "Błąd wykonania",
    case when wp.blad_wykonania is null then 'Wykonane poprawnie' else wp.blad_wykonania_nazwa end as "Błąd nazwa",
    count(wp.lab_wykonanie_godz_zatw) as "Liczba"
    from wykonania_pelne wp
    where wp.badanie in ('MOCZ', 'OSAD', 'MORF', 'ROZMAZ')
    and wp.lab in %s
    and wp.lab_wykonanie_godz_zatw between %s and %s
    and wp.pracownia not like 'X-%%'
    and wp.lab_techniczne_lub_kontrola is false
    group by wp.lab , wp.badanie, wp.blad_wykonania, wp.blad_wykonania_nazwa
    order by wp.lab, wp.badanie, wp.blad_wykonania
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)
    params['datado'] += ' 23:59:59'
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'noc',
        'priority': 1,
        'params': params,
        'function': 'raport_nocka'
    }
    report.create_task(task)
    report.save()
    return report

def raport_nocka(task_params):
    params = task_params['params']
    sql_params = [
        tuple(params['laboratoria']), params['dataod'], params['datado']
    ]
    nocka = NockaDatasource()
    cols, rows = nocka.select(SQL, sql_params)
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows),
    }