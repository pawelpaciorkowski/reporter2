
from pprint import pprint
from dialog import Dialog, VBox, LabSelector, InfoText, DateInput, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup
from helpers import prepare_for_json  # get_centrum_connection
from datasources.nocka import NockaDatasource

MENU_ENTRY = 'Alab w domu'

REQUIRE_ROLE = ['C-CS']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Alab w domu'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa', default='-7D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
))

SQL = """
select
	lab_system "Lab",
	lab_zlecenie as "Zlecenie"
from wykonania_pelne wp
	where wp.badanie  = 'UPIELMP'
	and wp.lab_zlecenie_data between %s and %s
    and wp.lab_system in %s
"""

SQL_2 = """
	select 
    wp.lab_zlecenie_data as "Data zlecenia",
    wp.lab_zlecenie as "Zlecenie",
    pacjent_plec_nazwa as "Płeć",
	DATE_PART('year', wp.lab_zlecenie_data ::date) - DATE_PART('year', wp.lab_pacjent_data_urodzenia ::date) as "Wiek",
	wp.lab_pacjent_data_urodzenia as "Data urodzenia",
    string_agg(wp.badanie, ', ') as "Badania"
	from wykonania_pelne wp
	where wp.lab_zlecenie in %s
	and wp.lab_zlecenie_data between %s and %s
	and wp.lab_system  = %s
    group by 1,2,3,4,5
"""

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)

    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")

    validate_date_range(params['dataod'], params['datado'], 93)
    dane_nocka = zbierz_nocka(params)
    if not dane_nocka:
        raise ValidationError('Brak danych')
    labs_and_ids = get_lab_and_ids(dane_nocka)
    for lab in labs_and_ids:
        params_2 = {
            'lab': lab,
            'od': params['dataod'],
            'do': params['datado'],
            'ids': labs_and_ids[lab]['ids']}

        lab_task = {
            'type': 'noc',
            'priority': 1,
            'params': params_2,
            'function': 'zbierz_lab',
        }
        report.create_task(lab_task)
    report.save()
    return report


def zbierz_nocka(task_params):
    ds = NockaDatasource()
    params = task_params
    result = ds.dict_select(SQL, (params['dataod'], params['datado'], tuple(params['laboratoria'])))
    return result

def get_lab_and_ids(dane):
    result = {}
    for d in dane:
        lab = d['Lab']
        if not lab in result:
            result[lab] = {}
            result[lab]['ids'] = []
        result[lab]['ids'].append(d['Zlecenie'])
    return result

def zbierz_lab(params):
    new_params = params['params']
    ds = NockaDatasource()
    result = ds.select(SQL_2, (tuple(new_params['ids']), new_params['od'], new_params['do'], new_params['lab']))
    return {
        'type': 'table',
        'title': new_params['lab'],
        'header': result[0],
        'data': prepare_for_json(result[1])
    }


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'header': ['1','2','3'],
        'actions': ['xlsx']
    }

    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            res['results'].append(result)

    res['progress'] = task_group.progress
    return res
