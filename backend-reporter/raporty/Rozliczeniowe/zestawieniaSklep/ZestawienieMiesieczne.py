from dialog import Dialog, VBox,  InfoText, DateInput
from tasks import TaskGroup
from helpers import prepare_for_json
from datasources.sklep import SklepDatasource
from helpers.validators import validate_date_range
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportData import ReportMiesieczny
from raporty.Rozliczeniowe.zestawieniaSklep.utils.Query import QueryData
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportTitle import MonthlyTitleGenerator


MENU_ENTRY = 'Zestawienie po punktach pobrań'

LAUNCH_DIALOG = Dialog(title='', panel=VBox(
    InfoText(text='''Zestawienie zawiera listę punktów pobrań wraz z informacją o wartości zamówionych wnich badań.
        Pod uwagę brane są tylko zamówienia opłacone.'''),
    DateInput(field='dataod', title='Data od', default='T'),
    DateInput(field='datado', title='Data do', default='T'),
))

REPORT_HEADERS = [
    'Punkt pobrań_MPK',
    'Punkt pobrań_nazwa',
    'Suma z Cen netto',
    'Suma z Stawka VAT',
    'Suma z Cena brutto',
    'Suma'
]

SQL = """
select
    JSON_EXTRACT(nfj.field_json_value, '$.mpk') as mpk,
    JSON_EXTRACT(nfj.field_json_value, '$.marcel') as symbol,
    JSON_EXTRACT(nfj.field_json_value, '$.street') as street,
    JSON_EXTRACT(nfj.field_json_value, '$.streetType.short') as street_type,
    JSON_EXTRACT(nfj.field_json_value, '$.city.name') as city,
    sum(co.total_price__number) as suma_cen
from commerce_order co
left join commerce_order__field_collection_point_api cofcpa on cofcpa.entity_id = co.order_id
left join node__field_json nfj on nfj.entity_id = cofcpa.field_collection_point_api_target_id
where
    from_unixtime(co.completed) is not null
    and co.state = 'completed' and co.checkout_step = 'complete'
    and from_unixtime(co.completed) between 
        concat(%s, " 00:00:00")  
        and concat(%s, " 23:59:59")
group by mpk, symbol, street, street_type, city"""


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

    report_data = ReportMiesieczny(
        query_data=data,
        title_generator=MonthlyTitleGenerator())

    display_report_data = {
        'type': 'table',
        'title': report_data.title,
        'header': REPORT_HEADERS,
        'data': prepare_for_json(report_data.report_rows()),
    }

    return {
        'results': [display_report_data],
        'actions': ['xlsx', 'pdf', 'csv'],
        'errors': [],
        'progress': 1
    }
