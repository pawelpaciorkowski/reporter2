from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json, divide_chunks, empty, get_and_cache
from helpers.validators import validate_date_range, validate_symbol
from datasources.postgres import PostgresDatasource
from config import Config
from tasks import TaskGroup

MENU_ENTRY = 'ErLab'


LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    TabbedView(field='tab', desc_title='Typ raportu', children=[
        Tab(title='Problemy', default=True, value='problemy',
            panel=VBox(
                DateInput(field='dataod', title='Data początkowa', default='-7D'),
                DateInput(field='datado', title='Data końcowa', default='T'),
            )
        ),
        Tab(title='Status zlecenia', value='zlecenie',
            panel=VBox(
                TextInput(field='erlab_id', title='ID zlecenia ErLab'),
            )
        )
    ]),
))

SQL_PROBLEMY = """
	select min(p.created_at) as "Pierwsze wystąpienie", 
	max(p.created_at) as "Ostatnie wystąpienie",
	(problem::jsonb)->>'problem' as problem, count(distinct order_id) as ilosc,
	array_to_string(array_agg(o.erlab_id), ', ') as zlecenia_erlab 
	from problems p 
	left join orders o on o.id=p.order_id 
	where p.created_at between  %s and %s
	group by 3
"""

SQL_ZLECENIE = """
    select o.*,
        (select array_to_string(array_agg(cast(p.created_at as varchar) || ': ' || ((p.problem::jsonb)->>'problem')), '\n') 
            from problems p where p.order_id=o.id) as problems
    from orders o
    where o.erlab_id=%s
"""

SQL_WYNIKI = """
    select response_type, hl7_fn, erlab_data_encoded, erlab_response, created_at, sent_at
    from responses
    where order_id=%s
    order by id 
"""

def erlab_db():
    return PostgresDatasource(Config.DATABASE_ERLAB)

def start_report(params):
    report = TaskGroup(__PLUGIN__, params)
    if params['tab'] == 'problemy':
        validate_date_range(params['dataod'], params['datado'], 31)
        task = {
            'type': 'ick',
            'priority': 1,
            'params': params,
            'function': 'raport_problemy'
        }
        report.create_task(task)
    elif params['tab'] == 'zlecenie':
        if empty(params.get('erlab_id')):
            raise ValidationError("Puste id zlecenia")
        task = {
            'type': 'ick',
            'priority': 1,
            'params': params,
            'function': 'raport_zlecenie'
        }
        report.create_task(task)
    else:
        raise ValidationError(params['tab'])
    report.save()
    return report


def raport_problemy(task_params):
    params = task_params['params']
    db = erlab_db()
    cols, rows = db.select(SQL_PROBLEMY, [params['dataod'], params['datado'] + ' 23:59:59'])
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows),
    }


def raport_zlecenie(task_params):
    params = task_params['params']
    db = erlab_db()
    cols, rows = db.select(SQL_ZLECENIE, [params['erlab_id']])
    res = []
    if len(rows) == 0:
        return {'type': 'error', 'text': 'Nie znaleziono zlecenia o podanym id'}
    if len(rows) > 1:
        return {'type': 'error', 'text': 'Znaleziono więcej niż jedno zlecenie ??????'}
    order = rows[0]



    raw_table = {
        'type': 'table',
        'title': 'Zlecenie',
        'header': cols,
        'data': prepare_for_json(rows),
    }
    res.append(raw_table)
    cols, rows = db.select(SQL_WYNIKI, [order[0]])
    res.append({
        'type': 'table',
        'title': 'Wyniki / odpowiedzi',
        'header': cols,
        'data': prepare_for_json(rows),
    })
    return res