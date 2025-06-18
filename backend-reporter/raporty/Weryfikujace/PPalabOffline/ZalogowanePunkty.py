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

MENU_ENTRY = 'Zalogowane punkty'

REQUIRE_ROLE = ['L-PP', 'C-ROZL']

SQL = """
select a.sender_cn as "Punkt", msg.created_at as "Ostatnio widziany", (msg::json)->>'version' as "Wersja aplikacji",
    (msg::json)->'printerInfo'->>'nr_seryjny' as "Drukarka numer", 
    (msg::json)->'printerInfo'->>'wersja' as "Drukarka model" 
from (
    select sender_cn, max(id) as last_id from messages where topic='login.status' and msg is not null group by 1 order by 1
) as a
left join messages msg on msg.id=a.last_id
where a.sender_cn in %s
order by a.sender_cn
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Informacja o ostatnich logowaniach/uruchomieniach aplikacji PPAlab Offline'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
))



def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
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
    cols, src_rows = ups.select(SQL, [tuple(cp_symbols)])
    rows = []
    for row in src_rows:
        row = list(row)
        rows.append(row)
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows),
        'params': prepare_for_json(params)
    }
