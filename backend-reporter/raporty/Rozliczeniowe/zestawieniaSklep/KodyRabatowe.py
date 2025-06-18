from dialog import Dialog, VBox,  InfoText, DateInput, KuponSelector, Switch, \
    ValidationError
from tasks import TaskGroup
from helpers import prepare_for_json
from helpers.validators import validate_date_range
from datasources.sklep import SklepDatasource
from raporty.Rozliczeniowe.zestawieniaSklep.utils.Query import QueryData
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportData import \
    ReportPromotionCodes
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportTitle import \
    PromotionCodesTitle


MENU_ENTRY = 'Kody rabatowe'

LAUNCH_DIALOG = Dialog(title='', panel=VBox(
    InfoText(text='''Lista kodów rabatowych 
    Filtrowanie danych po zakresie dat jest jedyni wykorzystywane 
    przy zaznaczonej opcji 'Tylko kody wykorzystane' '''),
    KuponSelector(field="kupony", multiselect=True, title='Kupony'),
    DateInput(field='dataod', title='Data od', default='T'),
    DateInput(field='datado', title='Data do', default='T'),
    Switch(field="used", title="Tylko kody wykorzystane"),
))

REPORT_HEADERS = [
    'Kod rabatowy',
    'Status',
    'Aktywne od',
    'Aktywne do',
    'Promocja',
    'ID zamówienia',
    'Numer Zamówienia',
    'Kto wykorzystał',
    'Data wykorzystania'
]

SQL = """
select
       cpc.code,
       cpc.status,
       cpc.start_date,
       cpc.end_date,
       cpfd.name,
       cpu.mail,
       co.mail,
       co.order_id,
       co.order_number,
       from_unixtime(co.created) as 'usage',
       if(ufn.field_name_value is not null,
           concat(ufn.field_name_value, ' ', ufs.field_surname_value ),
          concat(coffn.field_first_name_value, ' ', cofln.field_last_name_value)
       ) as user,
       from_unixtime(co.created) as use_date
from commerce_promotion_coupon cpc
left join commerce_promotion_field_data cpfd on cpfd.promotion_id = cpc.promotion_id
left join commerce_promotion_usage cpu on cpc.id = cpu.coupon_id
left join commerce_order co on co.order_id = cpu.order_id
left join alaboratoria_db.user__field_name ufn on ufn.entity_id = co.uid
left join alaboratoria_db.user__field_surname ufs on ufs.entity_id = co.uid
left join commerce_order__field_first_name coffn on coffn.entity_id = co.order_id
left join commerce_order__field_last_name cofln on cofln.entity_id = co.order_id
where
    cpc.promotion_id in ( {IDS} )
    {only_used}
order by order_id desc
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)

    if len(params['kupony']) == 0:
        raise ValidationError("Nie wybrano żadnego kuponu")
    validate_date_range(params['dataod'], params['datado'], max_days=31)

    task = {
        'type': 'hbz',
        'priority': 1,
        'params': params,
        'function': 'raport_sklep'
    }
    report.create_task(task)
    report.save()
    return report


def prepare_sql(task_params):
    sql = handle_only_used(task_params['params'])
    sql = sql.replace('{IDS}', ', '.join(
        [' %s ' for id in task_params['params']['kupony']]))
    return sql


def prepare_params(task_params):
    new_params = task_params['params']['kupony']

    if task_params['params']['used']:
        new_params.append(task_params['params']['dataod'])
        new_params.append(task_params['params']['datado'])
    return new_params


def handle_only_used(params):
    if params['used']:
        return SQL.replace(
            '{only_used}',
            "  and co.created is not null and from_unixtime(co.created) between concat( %s , ' 00:00:00') and concat( %s , ' 23:59:59') ")
    return SQL.replace('{only_used}', '')


def raport_sklep(task_params):
    sql = prepare_sql(task_params)
    params = prepare_params(task_params)

    data = QueryData(
        db=SklepDatasource(),
        query=sql,
        query_params=params)

    report_data = ReportPromotionCodes(
        query_data=data,
        title_generator=PromotionCodesTitle())

    display_report_data = {
        'type': 'table',
        'title': report_data.title,
        'header': REPORT_HEADERS,
        'data': prepare_for_json(report_data.report_rows()),
    }

    return {
        'results': [display_report_data],
        'actions': [],
        'errors': [],
        'progress': 1
    }
