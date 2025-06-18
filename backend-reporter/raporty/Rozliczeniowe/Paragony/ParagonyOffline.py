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

MENU_ENTRY = 'Paragony offline'

REQUIRE_ROLE = ['C-ROZL']

SQL = """
    select '' as "Lab", r.collection_point as "Punkt pobrań",
        '' as "Punkt pobrań nazwa", r.receipt_date as "Data paragonu",
        r.receipt_number as "Numer paragonu",
        '' as "-", r.tax_id as "NIP", r.payment_form as "Forma płatności",
        ri.vat_name as "VAT", array_to_string(array_agg(ri.title), ',') as "Badania",
        sum(ri.value) as "Wartość"
    from receipts r
    left join receipt_items ri on ri.receipt_id=r.id
    where r.collection_point in %s and r.receipt_date between %s and %s
    group by 1, 2, 3, 4, 5, 6, 7, 8, 9
    order by 2, 3, 4
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Paragony wystawione z aplikacji PPAlab Offline'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
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
    cols, src_rows = ups.select(SQL, [tuple(cp_symbols), params['dataod'], params['datado']])
    rows = []
    for row in src_rows:
        row = list(row)
        row[0] = laby_punktow[row[1]]
        row[2] = nazwy_punktow[row[1]]
        rows.append(row)
    rep = ReportXlsx({'results': [{
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows),
        'params': prepare_for_json(params)
    }]})
    fn = 'paragony_offline_%s.xlsx' % datetime.datetime.now().strftime('%Y%m%d_%H%M')
    return {
        'type': 'download',
        'content': base64.b64encode(rep.render_as_bytes()).decode(),
        'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'filename': fn,
    }
