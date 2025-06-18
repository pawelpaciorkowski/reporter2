import base64
import json

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, Kalendarz
from datasources.bic import BiCDatasource
from datasources.ppalab_upstream import PPAlabUpstreamDatasource
from api.common import get_db
from decimal import Decimal
import datetime

MENU_ENTRY = 'Zlecenia i paragony'

REQUIRE_ROLE = ['L-PP', 'C-ROZL']

SQL = """
    select sender_cn as "Punkt pobrań",
        sum(case when topic='upload.orders' then 1 else 0 end) as "Ilość zleceń",
        sum(case when topic='upload.orders' and (msg::json)->>'zleceniodawca_is_cash'='true' then 1 else 0 end) as "Ilość płatnych pacjent",
        sum(case when topic='upload.receipts' then 1 else 0 end) as "Ilość paragonów"
    from messages 
    where topic in ('upload.orders', 'upload.receipts')
    and sender_cn in %s and created_at between %s and %s
    group by sender_cn
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Liczba zleceń i paragonów z aplikacji PPAlab Offline. Uwaga - raport wykonywany wg dat otrzymania komunikatów, a nie wystawienia zleceń/paragonów!'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa', default='-1D'),
    DateInput(field='datado', title='Data końcowa', default='T'),
))



def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)
    lab_task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'function': 'zbierz',
    }
    report.create_task(lab_task)
    report.save()
    return report


def zbierz(task_params):
    params = task_params['params']
    bic = BiCDatasource()
    ups = PPAlabUpstreamDatasource()
    collection_points = bic.get_collection_points_for_labs(params['laboratoria'])
    cp_symbols = []
    laby_punktow = {}
    nazwy_punktow = {}
    for lab, punkty in collection_points.items():
        for symbol, nazwa in punkty.items():
            laby_punktow[symbol] = lab
            nazwy_punktow[symbol] = nazwa
            cp_symbols.append(symbol)
    cols, src_rows = ups.select(SQL, [tuple(cp_symbols), params['dataod'], params['datado'] + ' 23:59:59'])
    rows = []
    for row in src_rows:
        row = list(row)
        if row[2] != row[3]:
            row[3] = {
                'value': row[3],
                'background': '#ff0000',
            }
        rows.append(row)
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows),
        'params': prepare_for_json(params)
    }