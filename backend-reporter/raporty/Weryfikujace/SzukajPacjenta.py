import requests
from datasources.nocka import NockaDatasource
from datasources.mkurier import MKurierDatasource
from datasources.alabserwis import AlabSerwisDatasource
from datasources.reporter import ReporterExtraDatasource
from datasources.wyniki_stats import WynikiStats
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range, validate_pesel
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty

from helpers.strings import ident_pacjenta_sw_gellert

MENU_ENTRY = 'Szukaj pacjenta'
REQUIRE_ROLE = ['C-CS']
ADD_TO_ROLE = ['R-MDO', 'C-CS']

SQL_BADANIA = """
    select distinct system, datarejestracji, numer, platnik, zleceniodawca, array_to_string(array_agg(distinct badanie), ', ') as badania
    from wyniki where pacjent=%s
    group by 1, 2, 3, 4, 5
    order by 2, 3, 1
"""

SQL_DATY = """
    select min(results_date) as min_date, max(results_date) as max_date
    from (
        select results_date, count(system) from log_zgrywanie where success 
        group by 1
        having count(system) > 50
    ) a
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="""Raport wyszukuje pacjenta po hashu z danych osobowych w bazie statystycznej wyników (tzw baza św. Gellerta).
                UWAGA! Baza obejmuje ograniczony okres, z których ma zebrane dane. Aktualny zakres zostanie zwrócony razem z wynikami raportu.
                UWAGA! Wyszukiwanie ma charakter przybliżony. W przypadku innego sposobu zapisu danych przy rejestracji zlecenia mogą nie zostać znalezione (w przypadku pacjenta z PESEL brana jest pod uwagę pierwsza litera imienia, w przypadku daty urodzenia - imiona i nazwisko, w ujednoliconym formacie). Z minimalnym prawdopodobieństwem mogą zostać również zwrócone informacje o innych pacjentach."""),
    TextInput(field='nazwisko', title='Nazwisko'),
    TextInput(field='imiona', title='Imiona'),
    TextInput(field='pesel', title='PESEL'),
    DateInput(field='dataur', title='lub data urodzenia'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if empty(params['nazwisko']) or empty(params['imiona']):
        raise ValidationError('Podaj nazwisko i imiona')
    if empty(params['pesel']) and empty(params['dataur']):
        raise ValidationError('Podaj PESEL lub datę ur.')
    if not empty(params['pesel']) and not empty(params['dataur']):
        raise ValidationError('Podaj PESEL lub datę ur.')
    if not empty(params['pesel']):
        params['pesel'] = validate_pesel(params['pesel'])
    task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'function': 'raport_sw_gellert',
    }
    report.create_task(task)
    report.save()
    return report


def raport_sw_gellert(task_params):
    params = task_params['params']
    pacjent = ident_pacjenta_sw_gellert(params['nazwisko'], params['imiona'], params['pesel'], params['dataur'])
    db = WynikiStats()
    res = []
    for row in db.dict_select(SQL_DATY):
        res.append({
            'type': 'warning',
            'text': 'Baza statystyczna wyników obejmuje okres od %s do %s' % (row['min_date'], row['max_date'])
        })
    cols, rows = db.select(SQL_BADANIA, [pacjent])
    if len(rows) > 0:
        res.append({
            'type': 'table',
            'header': cols,
            'data': prepare_for_json(rows)
        })
    else:
        res.append({
            'type': 'error',
            'text': 'Nie znaleziono badań zarejestrowanych na takiego pacjenta',
        })
    return res
