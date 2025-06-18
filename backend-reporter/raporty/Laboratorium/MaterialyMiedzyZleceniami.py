import time

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError, Switch
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty, odpiotrkuj, Kalendarz

MENU_ENTRY = 'Materiały między zleceniami'

ADD_TO_ROLE = ['L-PRAC']

NEWS = [
    ("2024-11-06", """
        Nowy raport umożliwiający znalezienie materiałów od tego samego pacjenta do różnych zleceń w przypadku, kiedy
        jeden materiał jest przyjęty, a inny nie. Raport wykonywany dla zleceń z dnia bieżącego lub bieżącego i poprzedniego.
    """)
]

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text='''Raport ze zleceń zarejestrowanych dziś lub dziś i wczoraj.
        Zwracane są zlecenia z materiałami nieprzyjętymi, jeśli dla pacjentów o tych samych numerach PESEL istnieją 
        te same materiały przyjęte w innych zleceniach.
        Raport działa tylko z baz Postgres'''),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', tylko_postgres=True),
    Switch(field='wczorajsze', title='Uwzględnij zlecenia wczorajsze')
))

SQL = """
    select trim(pac.pesel) as pesel, count(distinct z.id) as ile_zlecen, array_to_string(array_agg(z.id),',') as id_zlecen,
        array_to_string(array_agg(distinct (
            case when w.dystrybucja is not null then trim(m.symbol) || ':' || w.kodkreskowy else null end
        )), ',') as przyjete,
        array_to_string(array_agg(distinct (
            case when w.dystrybucja is null then trim(m.symbol) || ':' || z.kodkreskowy else null end
        )), ',') as nieprzyjete
    from zlecenia z 
    left join pacjenci pac on pac.id=z.pacjent 
    left join wykonania w on w.zlecenie=z.id
    left join materialy m on m.id=w.material
    where z.godzinarejestracji > %s and pac.pesel  is not null and length(trim(pac.pesel)) = 11
    and m.grupa not in (select id from grupymaterialow where symbol in ('HISTOPA', 'INNE', 'MIKROBI', 'PODLOZA', 'SEROLOG', 'TECHNIC'))
    group by 1 
    having count(distinct z.id) > 1
    order by 2 desc
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if empty(params['laboratorium']):
        raise ValidationError("Nie wybrano laboratorium")
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
    kal = Kalendarz()
    od_kiedy = kal.data('-1D') if params['wczorajsze'] else kal.data('TODAY')
    with get_centrum_connection(task_params['target']) as conn:
        rows = conn.raport_slownikowy(SQL, [od_kiedy], sql_pg=SQL)
    res = []
    for row in rows:
        pesel = row['pesel']
        pesel = pesel[:2] + '...' + pesel[-3:]
        mat_p = {}
        for val in row['przyjete'].split(','):
            if ':' not in val:
                continue
            [mat, kod] = val.split(':')
            if mat not in mat_p:
                mat_p[mat] = []
            mat_p[mat].append(kod)
        for val in row['nieprzyjete'].split(','):
            if ':' not in val:
                continue
            [mat, kod] = val.split(':')
            if mat in mat_p:
                res.append([
                    pesel, "%s: %s" % (mat, ', '.join(mat_p[mat])),
                           "%s: %s" % (mat, kod)
                ])
    return {
        'type': 'table',
        'header': 'Pacjent,Materiał przyjęty,Materiał nieprzyjęty do zleceń'.split(','),
        'data': res,
    }
