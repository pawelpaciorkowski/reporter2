from dialog import Dialog, VBox,  InfoText, DateInput, ValidationError
from tasks import TaskGroup, Task
from pprint import pprint
from helpers import prepare_for_json
from datasources.sklep import SklepDatasource
from helpers.validators import validate_date_range
from raporty.Rozliczeniowe.zestawieniaSklep.utils.Query import QueryData
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportData import ReportDzienny
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportTitle import DailyTitleGenerator
MENU_ENTRY = 'Zestawienie dzienne - PDF, HTML'

LAUNCH_DIALOG = Dialog(title='', panel=VBox(
    InfoText(text='''Zestawienie zawiera listę zamówień wraz z ich szczegółami.
    Zestawienie w formacie HTML oraz PDF uwzględnia zamówienia opłacone oraz
nieopłacone.'''),
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

SQL = """
select
    co.order_number,
    from_unixtime(co.created) as data_zam,
    datediff(from_unixtime(co.created), '2015-11-14') as nr_zes,
    JSON_EXTRACT(nfj.field_json_value, '$.mpk') as mpk,
    JSON_EXTRACT(nfj.field_json_value, '$.marcel') as symbol,
    JSON_EXTRACT(nfj.field_json_value, '$.street') as street,
    JSON_EXTRACT(nfj.field_json_value, '$.streetType.short') as street_type,
    JSON_EXTRACT(nfj.field_json_value, '$.city.name') as city,
    coffw.field_for_whom_value as 'for_whom',
    cofiir.field_is_invoice_required_value as 'vat_invoice',
    cpfd.name as 'promotion_code',
    co.total_price__number as 'sum',

    co.payment_gateway as 'payment',
    if (coi.type != 'imported' ,coi.title, cprodfd.title) as 'title',
    if(coi.type != 'imported', cpfs.field_symbol_value, cpfs2.field_symbol_value) as 'test_symbol',

    coi.quantity as 'quantity',
    cpc.code as 'discount_code',
    cpfd.name as 'voucher',
    coi.total_price__number as 'item_price',

    # extra service for non imported orders -> adds missing UPIEL
    if(coi.purchased_entity IS NOT NULL AND coi.purchased_entity != 0, cpfs3.field_symbol_value, null) as extra_service,
    CONCAT(cpfs3.field_symbol_value, '_', substring_index(cpvfd.sku, '_', -1)) AS symbol_sku,
    (select price__number from commerce_product_variation_field_data where sku = symbol_sku) as extra_wartosc,
    (select count(price__number) from commerce_product_variation_field_data where sku = symbol_sku) as extra_ilosc,
    (select title from commerce_product_variation_field_data where sku = symbol_sku) as extra_title,

    # patient/form data
    coffn.field_first_name_value  as 'patient_name',
    cofln.field_last_name_value as 'patient_surname',
    cofp.field_phone_value as 'patient_telephone',
    cofpl.field_pesel_value as 'patient_pesel',
    co.mail as 'mail',

    # user account fields
    ufn.field_name_value as 'name',
    ufs.field_surname_value as 'surname',
    ufpi.field_personal_id_value as 'pesel',
    ufpn.field_phone_number_value as 'telephone',
    ufd.name as 'user_email',

    # billing fields
    pa.address_given_name as 'vat_name',
    pa.address_family_name as 'vat_surname',
    pa.address_organization as 'vat_name_company',
    pa.address_address_line1 as 'vat_street',
    pa.address_postal_code as 'vat_postcode',
    pa.address_locality as 'vat_city',
    ptn.tax_number_value as 'vat_nip',
    pa.bundle as 'vat_type'
    
from commerce_order co
         left join commerce_order__field_collection_point_api cofcpa on cofcpa.entity_id = co.order_id
         left join node__field_json nfj on nfj.entity_id = cofcpa.field_collection_point_api_target_id
         left join commerce_order__field_first_name coffn on coffn.entity_id = co.order_id
         left join commerce_order__field_last_name cofln on cofln.entity_id = co.order_id
         left join commerce_order__field_phone cofp on cofp.entity_id = co.order_id
         left join commerce_order__field_pesel cofpl on cofpl.entity_id = co.order_id
         left join commerce_order__field_for_whom coffw on coffw.entity_id = co.order_id
         left join commerce_order__field_is_invoice_required cofiir on cofiir.entity_id = co.order_id

         left join commerce_promotion_usage cpu on cpu.order_id = co.order_id
         left join commerce_promotion_field_data cpfd on cpfd.promotion_id = cpu.promotion_id
         left join commerce_order_item coi on coi.order_id = co.order_id
         left join commerce_product__variations cpv ON cpv.variations_target_id = coi.purchased_entity
         left join commerce_product cp ON cpv.entity_id = cp.product_id
         left join commerce_product__field_symbol cpfs ON cpfs.entity_id = cp.product_id
         left join alaboratoria_db.commerce_order_item__field_examination coife on coife.entity_id = coi.order_item_id
         left join commerce_product__field_symbol cpfs2 ON cpfs2.entity_id = coife.field_examination_target_id
         left join alaboratoria_db.commerce_product_field_data cprodfd on cprodfd.product_id = coife.field_examination_target_id

         left join alaboratoria_db.commerce_product__field_requiredservices cpfrt on cpfrt.entity_id = cp.product_id
         LEFT JOIN commerce_product__field_symbol cpfs3 ON cpfs3.entity_id = cpfrt.field_requiredservices_target_id
         LEFT JOIN commerce_product_variation_field_data cpvfd ON cpv.variations_target_id = cpvfd.variation_id

         left join commerce_promotion_coupon cpc on cpc.promotion_id = cpu.coupon_id
         left join profile__address pa on pa.entity_id = co.billing_profile__target_id
         left join profile__tax_number ptn on ptn.entity_id = pa.entity_id 
         left join user__field_name ufn on ufn.entity_id = co.uid
         left join user__field_surname ufs on ufs.entity_id = co.uid
         left join user__field_personal_id ufpi on ufpi.entity_id = co.uid
         left join user__field_phone_number ufpn on ufpn.entity_id = co.uid
         left join users_field_data ufd on ufd.uid = co.uid

where date(from_unixtime(co.created)) between %s and %s
and co.order_number is not null
{{PAID}}
"""


def get_sql(sql_type):
    if sql_type == 'paid':
        return SQL.replace('{{PAID}}',
                            " and co.checkout_step = 'complete' and co.state = 'completed' ")
    if sql_type == 'unpaid':
        return SQL.replace('{{PAID}}',
                            " and co.checkout_step != 'complete' and co.state = 'completed' ")
    raise ValueError('Niepoprawn typ zapytania')


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

    data_paid = QueryData(
        db=SklepDatasource(),
        query=get_sql('paid'),
        query_params=task_params['params'])

    data_unpaid = QueryData(
        db=SklepDatasource(),
        query=get_sql('unpaid'),
        query_params=task_params['params'])

    report_data_paid = ReportDzienny(
        query_data=data_paid,
        title_generator=DailyTitleGenerator())

    report_data_unpaid = ReportDzienny(
        query_data=data_unpaid,
        title_generator=DailyTitleGenerator())

    display_report_data_paid = {
        'type': 'table',
        'title': report_data_paid.title,
        'header': HEADERS,
        'data': prepare_for_json(report_data_paid.report_rows()),
    }

    display_report_data_unpaid = {
        'type': 'table',
        'title': 'Nieopłacone',
        'header': HEADERS,
        'data': prepare_for_json(report_data_unpaid.report_rows()),
    }

    display_report_summary = {
        'type': 'table',
        'title': 'Podsumowanie (TYLKO OPŁACONE)',
        'header': ['Punkt Pobrań', 'MPK punktu pobrań', 'Suma netto'],
        'data': prepare_for_json(report_data_paid.summary_rows()),
    }

    return {
        'results': [
            display_report_data_paid,
            display_report_data_unpaid,
            display_report_summary],
        'actions': ['pdf'],
        'errors': [],
        'progress': 1
    }
