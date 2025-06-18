import time

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError, Switch
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty, odpiotrkuj

MENU_ENTRY = 'Powtórzone kody zleceń'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Raport zwraca zlecenia z powtarzającymi się kodami kreskowymi zarejestrowane we wskazanym okresie.
        Brane pod uwagę jest 9 pierwszych cyfr kodu, podane kody są uzupełnione o 0 na końcu.
        Raport nie bierze pod uwagę kodów kreskowych wykonań."""),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', pokaz_nieaktywne=True),
    DateInput(field='dataod', title='Data początkowa', default='-7D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
))

SQL = """
    select left(kodkreskowy, 9) || '0' as "Kod kreskowy", count(id) as "Ilość zleceń",
        list(
            datarejestracji || ' / ' || case when numer is not null then numer else 'BRAK NR' end
        , ', ') as "Zlecenia"
    from zlecenia where datarejestracji between ? and ?
    group by 1
    having count(id) > 1
    order by 1
"""

SQL_PG = """
    select left(kodkreskowy, 9) || '0' as "Kod kreskowy", count(id) as "Ilość zleceń",
        array_to_string(array_agg(
            cast(datarejestracji as varchar) || ' / ' || case when numer is not null then cast(numer as varchar) else 'BRAK NR' end
        ), ', ') as "Zlecenia"
    from zlecenia where datarejestracji between %s and %s
    group by 1
    having count(id) > 1
    order by 1
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 31)
    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_lab'
    }
    report.create_task(task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']
    system = task_params['target']
    oddnia = params['dataod']
    dodnia = params['datado']
    with get_centrum_connection(system) as conn:
        cols, rows = conn.raport_z_kolumnami(SQL, [oddnia, dodnia], sql_pg=SQL_PG)
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows),
    }
