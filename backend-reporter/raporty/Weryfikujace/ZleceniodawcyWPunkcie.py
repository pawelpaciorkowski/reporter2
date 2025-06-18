from datasources.nocka import NockaDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range, validate_symbol
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty
from api_access_client import ApiAccessManager
from datasources.bic import BiCDatasource

MENU_ENTRY = 'Zleceniodawcy w punkcie'

LAUNCH_DIALOG = Dialog(title='Lista zleceniodawców dostępnych w punkcie pobrań', panel=VBox(
    InfoText(
        text='''Proszę podać symbol punktu
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
    bic = BiCDatasource()
    cols, rows = bic.select("""
        select cpowk.lab, cpo.zleceniodawca, cpo.zleceniodawca_nazwa, cpo.platnik 
        from config_ppalab_oddzialywkanalach cpowk
        left join config_ppalab_kanaly cpk on cpk.kanal=cpowk.kanal 
        left join config_ppalab_oddzialy cpo on cpo.zleceniodawca=cpowk.zleceniodawca 
        where cpowk.kanal=%s
    """, [params['symbol']])
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows),
    }
