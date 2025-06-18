from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, NumberInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json, empty
from helpers.validators import validate_date_range, validate_symbol
from tasks import TaskGroup, Task
import datetime

MENU_ENTRY = "Kody przyjęte w dniu"

ADD_TO_ROLE = ['L-PRAC']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    DateInput(field='data', title='Data', default='-1D'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if empty(params['laboratorium']) or empty(params['data']):
        raise ValidationError("Wypełnij wszystkie pola")
    report = TaskGroup(__PLUGIN__, params)
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

SQL = """
    select w.kodkreskowy as "Kod kreskowy", cast(w.godzinarejestracji as date) as "zarejestrowane", trim(o.symbol) as zleceniodawca, o.nazwa as "zleceniodawca nazwa",
    list(trim(b.symbol), ', ') as badania, 
        trim(mat.symbol) as material, w.dystrybucja as "Przyjęte"
    from wykonania w 
    left join materialy mat on mat.id=w.material
    left join badania b on b.id=w.badanie
    left join zlecenia zl on zl.id=w.zlecenie
    left join typyzlecen tz on tz.id=zl.typzlecenia
    left join oddzialy o on o.id=zl.oddzial
    where w.dystrybucja between ? and ? and w.kodkreskowy is not null and w.kodkreskowy <> ''
    and tz.symbol not in ('K', 'KZ', 'KW') and length(w.kodkreskowy) >= 10
    group by 1, 2, 3, 4, 6, 7
"""

SQL_PG = """
    select w.kodkreskowy as "Kod kreskowy", cast(w.godzinarejestracji as date) as "zarejestrowane", trim(o.symbol) as zleceniodawca, o.nazwa as "zleceniodawca nazwa", 
        array_to_string(array_agg(trim(b.symbol)), ', ') as badania, trim(mat.symbol) as material, w.dystrybucja as "Przyjęte"
    from wykonania w 
    left join materialy mat on mat.id=w.material
    left join badania b on b.id=w.badanie
    left join zlecenia zl on zl.id=w.zlecenie
    left join typyzlecen tz on tz.id=zl.typzlecenia
    left join oddzialy o on o.id=zl.oddzial
    where w.dystrybucja between %s and %s and w.kodkreskowy is not null and w.kodkreskowy <> ''
    and tz.symbol not in ('K', 'KZ', 'KW') and length(w.kodkreskowy) >= 10
    group by 1, 2, 3, 4, 6, 7
"""

def raport_lab(task_params):
    params = task_params['params']
    sql_params = [params['data'], params['data'] + ' 23:59:59']
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(SQL, sql_params, sql_pg=SQL_PG)
    return ({
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    })
