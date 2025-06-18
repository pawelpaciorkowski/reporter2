from dialog import Dialog, VBox,  InfoText, DateInput
from tasks import TaskGroup
from helpers import prepare_for_json
from datasources.sklep import SklepDatasource
from helpers.validators import validate_date_range
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportData import ReportPoKlientach
from raporty.Rozliczeniowe.zestawieniaSklep.utils.Query import QueryData
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportTitle import MonthlyTitleGenerator
from pprint import pprint

MENU_ENTRY = 'Zestawienie po klientach'

LAUNCH_DIALOG = Dialog(title='', panel=VBox(
    InfoText(text='''Zestawienie zawiera listę pacjentów którzy złożyli zamówienie we wskazanym okresie
wraz ze szczegółami zamówień.
Pod uwagę brane są tylko zamówienia opłacone.'''),
    DateInput(field='dataod', title='Data od', default='T'),
    DateInput(field='datado', title='Data do', default='T'),
))

REPORT_HEADERS = [
    [{'title': 'ID', 'rowspan': 2},
     {'title': 'Imię Nazwisko', 'rowspan': 2},
     {'title': 'Wartość sumaryczna brutto', 'rowspan': 2},
     {'title': 'Zamówienia', 'rowspan': 2}],
]

ORDER_HEADERS = [
    'Numer',
    'Brutto',
    'Data',
    'Kod rabatowy',
    'Ilość'
]

# SQL = """
# select
#     ufai.field_alab_id_value as user_id,
#     co.order_number,
#     ufn.field_name_value as name,
#     ufs.field_surname_value as surname,
#     coi.total_price__number as price,
#     from_unixtime(co.created) as 'create_date',
#     coi.order_item_id,
#     coi.quantity,
#     coi.total_price__number,
#     coi.unit_price__number
#
#
# from user__field_name ufn
# left join user__field_alab_id ufai on ufai.entity_id = ufn.entity_id
# left join user__field_surname ufs on ufn.entity_id = ufs.entity_id
# left join commerce_order co on co.uid = ufn.entity_id
# left join commerce_order_item coi on co.order_id = coi.order_id
# where
#     from_unixtime(co.completed) is not null
#     and co.state = 'completed' and co.checkout_step = 'complete'
#     and from_unixtime(co.completed) between
#         concat(%s, " 00:00:00")
#         and concat(%s, " 23:59:59")
#     and order_number is not null
# order by ufai.field_alab_id_value
# """

SQL = """

select
    ufai.field_alab_id_value as user_id,
    co.order_number,
    ufn.field_name_value as name,
    ufs.field_surname_value as surname,
    coi.total_price__number as price,
    from_unixtime(co.created) as 'create_date',
    coi.order_item_id,
    coi.quantity,
    coi.total_price__number,
    coi.unit_price__number,
    coi.type,
    cpc.code as 'discount_code',
    cpfd.name as 'voucher',
    # extra service for non imported orders -> adds missing UPIEL
    if(coi.purchased_entity IS NOT NULL AND coi.purchased_entity != 0, cpfs3.field_symbol_value, null) as extra_service,
    CONCAT(cpfs3.field_symbol_value, '_', substring_index(cpvfd.sku, '_', -1)) AS symbol_sku,
    (select price__number from commerce_product_variation_field_data where sku = symbol_sku) as extra_wartosc,
    (select count(price__number) from commerce_product_variation_field_data where sku = symbol_sku) as extra_ilosc,
    (select title from commerce_product_variation_field_data where sku = symbol_sku) as extra_title

from user__field_name ufn
left join user__field_alab_id ufai on ufai.entity_id = ufn.entity_id
left join user__field_surname ufs on ufn.entity_id = ufs.entity_id
left join commerce_order co on co.uid = ufn.entity_id
left join commerce_order_item coi on co.order_id = coi.order_id

left join commerce_product__variations cpv ON cpv.variations_target_id = coi.purchased_entity
left join commerce_product cp ON cpv.entity_id = cp.product_id
left join commerce_product__field_symbol cpfs ON cpfs.entity_id = cp.product_id


left join alaboratoria_db.commerce_product__field_requiredservices cpfrt on cpfrt.entity_id = cp.product_id
LEFT JOIN commerce_product__field_symbol cpfs3 ON cpfs3.entity_id = cpfrt.field_requiredservices_target_id
LEFT JOIN commerce_product_variation_field_data cpvfd ON cpv.variations_target_id = cpvfd.variation_id

 left join commerce_promotion_usage cpu on cpu.order_id = co.order_id
 left join commerce_promotion_field_data cpfd on cpfd.promotion_id = cpu.promotion_id
 left join commerce_promotion_coupon cpc on cpc.promotion_id = cpu.coupon_id
where
    from_unixtime(co.completed) is not null
    and co.state = 'completed' and co.checkout_step = 'complete'
    and from_unixtime(co.completed) between
        concat(%s, " 00:00:00")
        and concat(%s, " 23:59:59")
    and order_number is not null
order by user_id
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

    data = QueryData(
        db=SklepDatasource(),
        query=SQL,
        query_params=task_params['params'])

    report_data = ReportPoKlientach(
        query_data=data,
        title_generator=MonthlyTitleGenerator())

    report_rows = report_data.report_rows()
    try:
        max_columns = max(len(user) for user in report_rows)
    except ValueError:
        max_columns = 0
    max_orders = (max_columns - len(ReportPoKlientach.USER_FIELDS)) / len(ReportPoKlientach.SINGLE_ORDER_FIELDS)
    headers = REPORT_HEADERS
    order_headers = []
    for i in range(int(max_orders)):
        headers[0].append({'title': f'Zamówienie {i+1}', 'rowspan': 1, 'colspan': len(ORDER_HEADERS)})
        for h in ORDER_HEADERS:
            order_headers.append({'title': h, 'rowspan': 1, 'colspan': 1})
    headers.append(order_headers)
    display_report_data = {
        'type': 'table',
        'title': report_data.title,
        'header': headers,
        'data': prepare_for_json(report_rows),
    }

    return {
        'results': [display_report_data],
        'actions': ['xlsx'],
        'errors': [],
        'progress': 1
    }
