from datasources.nocka import NockaDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range, validate_symbol
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty
from api_access_client import ApiAccessManager

MENU_ENTRY = 'Zleceniodawca w punktach'

LAUNCH_DIALOG = Dialog(title='Dostępność zleceniodawcy w punktach pobrań', panel=VBox(
    InfoText(
        text='''Proszę podać część wspólną symbolu zleceniodawcy (bez prefiksu labu).
            Dostępność jest sprawdzana w konfiguracji dla aplikacji PPOffline - aktualizowanej raz na dobę.'''),
    TextInput(field='symbol', title='Symbol (bez prefiksu labu)'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if empty(params['symbol']) or len(params['symbol']) < 2:
        raise ValidationError('Za krótki symbol')
    validate_symbol(params['symbol'])
    task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'function': 'raport',
    }
    report.create_task(task)
    report.save()
    return report


def raport(task_params):
    params = task_params['params']
    access_manager = ApiAccessManager()
    api = access_manager['ppalab-centrala']
    resp = api.get_json('external/zleceniodawcaWPunktach/%s' % params['symbol'])
    return {
        'type': 'table',
        'header': resp['cols'],
        'data': resp['rows'],
    }
