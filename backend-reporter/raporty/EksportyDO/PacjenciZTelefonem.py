import base64
import datetime
import re

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from helpers.validators import validate_date_range, validate_symbol
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none, empty, \
    list_from_space_separated

MENU_ENTRY = 'Pacjenci z telefonem'

REQUIRE_ROLE = ['C-ADM']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Szukanie pacjentów z podanym numerem telefonu"""),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    TextInput(field='telefon', title='Telefon (9 cyfr)'),
))

SQL = """
select pac.id, pac.nazwisko, pac.imiona, pac.pesel,pac.telefon,
list(cast(zl.numer as varchar(10)) || '/' || cast(zl.datarejestracji as varchar(32)), ', ') as zlecenia
from pacjenci pac
left join zlecenia zl on zl.pacjent=pac.id
where pac.telefon like ?
group by 1,2,3,4,5
"""

SQL_PG = """
select pac.id, pac.nazwisko, pac.imiona, pac.pesel,pac.telefon,
array_to_string(array_agg(cast(zl.numer as varchar) || '/' || cast(zl.datarejestracji as varchar)), ', ') as zlecenia
from pacjenci pac
left join zlecenia zl on zl.pacjent=pac.id
where pac.telefon like %s
group by 1,2,3,4,5
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Wybierz laboratorium")
    if not re.match('^[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]$', params['telefon']):
        raise ValidationError("Podaj numer telefonu jako 9 cyfr bez dodatkowych znaków")
    params['telefon_pattern'] = '%' + '%'.join(params['telefon']) + '%'
    for lab in params['laboratoria']:
        lb_task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'raport_lab',
        }
        report.create_task(lb_task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']
    with get_centrum_connection(task_params['target']) as conn:
        print(SQL, params['telefon_pattern'])
        cols, rows = conn.raport_z_kolumnami(SQL, sql_pg=SQL_PG, params=[params['telefon_pattern']])
        res_rows = []
        for row in rows:
            tel = row[4]
            if params['telefon'] in "".join(re.findall('\d+', tel)):
                res_rows.append(row)
        if len(res_rows) > 0:
            return {
                'title': task_params['target'],
                'type': 'table',
                'header': cols,
                'data': prepare_for_json(res_rows)
            }
        else:
            return {
                'type': 'info',
                'text': '%s - nie znaleziono' % task_params['target']
            }