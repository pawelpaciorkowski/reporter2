from config import Config
from datasources.postgres import PostgresDatasource
from dialog import (
    Dialog,
    Panel,
    HBox,
    VBox,
    TextInput,
    LabSelector,
    TabbedView,
    Tab,
    InfoText,
    DateInput,
    Switch,
    ValidationError,
)
from helpers.validators import validate_date_range, validate_symbol
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection
from datasources.snr import SNR
from datasources.hbz import HBZ
from api.common import get_db
from decimal import Decimal

MENU_ENTRY = "Ile zleceń z HL7"

SQL = """
    select la.data::date as data, la.opis as akcja, count(la.log_akcja_id) as ilosc
    from log_akcja la 
    left join log_logowanie ll on ll.log_logowanie_id=la.log_logowanie_id 
    left join uzytkownicy u on u.uzytkownik_id=ll.uzytkownik_id 
    left join laboratorium l on l.laboratorium_id=u.laboratorium_id 
    where la.data between %s and %s
	and u.symbol_pp = %s
	and la.opis like 'zapisano plik:%%'
	group by 1, 2
	order by 1, 2
"""

LAUNCH_DIALOG = Dialog(
    title=MENU_ENTRY,
    panel=VBox(
        InfoText(
            text="Ile zleceń w podanym zakresie dat przyjął punkt pobrań przez system dystrybucji zleceń HL7?"
        ),
        TextInput(field="symbol", title="Symbol PP"),
        DateInput(field="dataod", title="Data początkowa", default="-7D"),
        DateInput(field="datado", title="Data końcowa", default="-1D"),
    ),
)


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_symbol(params['symbol'])
    validate_date_range(params['dataod'], params['datado'], max_days=31)
    task = {
        "type": "ick",
        "priority": 1,
        "params": params,
        "function": "raport",
    }
    report.create_task(task)
    report.save()
    return report


def raport(task_params):
    params = task_params['params']
    db = PostgresDatasource(Config.DATABASE_WOREK)
    cols, rows = db.select(SQL, [params['dataod'], params['datado'] + ' 23:59:59', params['symbol']])
    return {
        'type': 'table', 'header': cols, 'data': prepare_for_json(rows)
    }
