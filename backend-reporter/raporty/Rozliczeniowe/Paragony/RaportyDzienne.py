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

MENU_ENTRY = 'Raporty dzienne'

REQUIRE_ROLE = ['C-ROZL']

# TODO: dorobić tu mpki ze skarbca,
# TODO: raport offline korelujący dane z raportów ze sprzedaży z systemów: w kanale na gotówki w icentrum + gotówki z offline

SQL = """
    select 
        rr.collection_point as "Punkt pobrań",
        rp.serial_number as "Drukarka",
        rr.report_ts as "Godzina raportu",
        rr.liczba_paragonow as "Liczba paragonów",
        rr.liczba_anulowanych as "Liczba anulowanych",
        rr.liczba_zmian_w_bazie_towarowej as "Liczba zmian w bazie towarowej",
        rr.kwota_anulacji as "Kwota anulacji",
        rr.totalizer_a as "Totalizer A",
        rr.totalizer_b as "Totalizer B",
        rr.totalizer_c as "Totalizer C",
        rr.totalizer_d as "Totalizer D",
        rr.totalizer_e as "Totalizer E",
        rr.totalizer_f as "Totalizer F",
        rr.totalizer_g as "Totalizer G"
    from receipt_reports rr
    left join receipt_printers rp on rp.id=rr.printer_id
    where rr.collection_point in %s and rr.report_ts between %s and %s
    order by rr.collection_point, rr.report_ts
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raporty dzienne z drukarek fiskalnych - zbierane aplikacją PPAlab Offline'),
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
    cols, src_rows = ups.select(SQL, [tuple(cp_symbols), params['dataod'], params['datado'] + ' 23:59:59'])
    rows = []
    for row in src_rows:
        row = list(row)
        # row[0] = laby_punktow[row[1]]
        # row[2] = nazwy_punktow[row[1]]
        rows.append(row)
    rep = ReportXlsx({'results': [{
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows),
        'params': prepare_for_json(params)
    }]})
    fn = 'raporty_fiskalne_dobowe_%s.xlsx' % datetime.datetime.now().strftime('%Y%m%d_%H%M')
    return {
        'type': 'download',
        'content': base64.b64encode(rep.render_as_bytes()).decode(),
        'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'filename': fn,
    }
