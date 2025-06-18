import base64
from dialog import Dialog, VBox,  InfoText, DateInput, ValidationError
from tasks import TaskGroup, Task
from pprint import pprint
from helpers import prepare_for_json
from datasources.sklep import SklepDatasource
from outlib.xlsx import ReportXlsx
from helpers.validators import validate_date_range
from raporty.Rozliczeniowe.zestawieniaSklep.utils.Query import QueryData
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportData import ReportDzienny
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportTitle import DailyTitleGenerator
from raporty.Rozliczeniowe.zestawieniaSklep.ZestawienieDzienne import get_sql
MENU_ENTRY = 'Zestawienie dzienne - XLSX'

LAUNCH_DIALOG = Dialog(title='', panel=VBox(
    InfoText(text='''Zestawienie zawiera listę zamówień wraz z ich szczegółami.
    Zestawienie w formacie CSV oraz XLSX uwzględnia wyłącznie zamówienia
opłacone.'''),
    DateInput(field='dataod', title='Data od', default='T'),
    DateInput(field='datado', title='Data do', default='T'),
))

HEADERS = [
    'Nr zam.',
    'Nr zes.',
    'MPK punk pobrań',
    'Punk pobrań',
    'Zamawiający',
    'Dla kogo',
    'Suma brutto zam.',
    'Faktura VAT',
    'Płatność nazwa',
    'Wpisany kod rabatowy',
    'Symbol',
    'Nazwa',
    'Ilość',
    'Cena brutto'
]

SQL = get_sql('paid')


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)

    validate_date_range(params['dataod'], params['datado'], 366)

    task = {
        'type': 'hbz',
        'priority': 1,
        'params': params,
        'function': 'raport_sklep'
    }
    report.create_task(task)
    report.save()
    return report


def raport_sklep(task_params):

    data = QueryData(
        db=SklepDatasource(),
        query=SQL,
        query_params=task_params['params'])

    report_data = ReportDzienny(
        query_data=data,
        title_generator=DailyTitleGenerator())

    # display_report_data = {
    #     'type': 'table',
    #     'title': report_data.title,
    #     'header': HEADERS,
    #     'data': prepare_for_json(report_data.report_rows_no_merge()),
    # }

    rep = ReportXlsx({'results': [{
        'type': 'table',
        'header': HEADERS,
        'data': prepare_for_json(report_data.report_rows_no_merge()),
    }]})
    results = []
    results.append({
        'type': 'download',
        'content': base64.b64encode(rep.render_as_bytes()).decode(),
        'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'filename': f'{report_data.title}.xlsx',
    })
    return {
        'results': results,
        'progress': '',
        'actions': [],
        'errors': '',
    }
    # return {
    #     # 'results': [],
    #     'results': [display_report_data],
    #     'actions': ['xlsx', 'csv'],
    #     'errors': [],
    #     'progress': 1
    # }
