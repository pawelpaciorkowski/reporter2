from dialog import Dialog, VBox,  InfoText, DateInput, ValidationError, Radio
from tasks import TaskGroup, Task
from outlib.xlsx import ReportXlsx
from helpers import prepare_for_json
from datasources.sklep import SklepDatasource
from helpers.validators import validate_date_range
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportData import ReportPoBadaniachIPakietach
from raporty.Rozliczeniowe.zestawieniaSklep.utils.Query import TestAndExamineQueryData
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportTitle import TestAndBundleTitle


MENU_ENTRY = 'Zestawienie po badaniach i pakietach'

PRODUCT_TYPE = {
    'all': 'Badania i pakiety',
    'laboratorytest': 'Tylko badania',
    'bundle': 'Tylko pakiety',
}

LAUNCH_DIALOG = Dialog(title='', panel=VBox(
    InfoText(text='''
    Zestawienie zawiera listę badań i pakietów wraz z informacją na jaką wartość złożono na nie zamówienia.
    Pod uwagę brane są tylko zamówienia opłacone.
    '''),
    DateInput(field='dataod', title='Data od', default='T'),
    DateInput(field='datado', title='Data do', default='T'),
    Radio(field="product_type", values=PRODUCT_TYPE, default='all'),
))

REPORT_HEADERS = [
    'Symbol',
    'Badanie/Pakiet'
]

SQL = """
select
    cpfd.title as title,
    cpfs.field_symbol_value as symbol,
    sum(coi.total_price__number) as suma
from commerce_order co
left join commerce_order_item coi on co.order_id = coi.order_id
LEFT JOIN commerce_order_item__field_examination coife ON coi.order_item_id = coife.entity_id
LEFT JOIN commerce_product cp ON coife.field_examination_target_id = cp.product_id
left join commerce_product_field_data cpfd on cp.product_id = cpfd.product_id
left join commerce_product__field_symbol cpfs on cpfs.entity_id = cpfd.product_id
where
    from_unixtime(co.completed) is not null
    and co.state = 'completed' and co.checkout_step = 'complete'
    and from_unixtime(co.completed) between 
        concat(%s, " 00:00:00")  
        and concat(%s, " 23:59:59")
  {{product_type}}
group by
    cpfd.title,
    cpfs.field_symbol_value
"""


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
    params = task_params['params']
    sql = query_filters(SQL, params)
    params['product_type'] = PRODUCT_TYPE[params['product_type']]
    data = TestAndExamineQueryData(
        db=SklepDatasource(),
        query=sql,
        query_params=params)

    report_data = ReportPoBadaniachIPakietach(
        query_data=data,
        title_generator=TestAndBundleTitle())

    display_report_data = {
        'type': 'table',
        'title': report_data.title,
        'header': appended_headers(params),
        'data': prepare_for_json(report_data.report_rows())
    }

    return {
        'results': [display_report_data],
        'actions': ['csv'],
        'errors': [],
        'progress': 1
    }


def appended_headers(params):
    headers = REPORT_HEADERS
    headers.append(generate_range_col_title(params))
    return headers


def generate_range_col_title(params):
    return f'{params["dataod"]} - {params["datado"]}'


def query_filters(sql, params):
    if params['product_type'] == 'all':
        sql = sql.replace('{{product_type}}', '')

    if params['product_type'] == 'bundle':
        where = " and cp.type = 'bundle' "
        sql = sql.replace('{{product_type}}', where)

    if params['product_type'] == 'laboratorytest':
        where = " and cp.type = 'laboratorytest' "
        sql = sql.replace('{{product_type}}', where)
    return sql
