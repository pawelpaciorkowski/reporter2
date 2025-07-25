from dialog import Dialog, VBox, InfoText
from datasources.bic import BiCDatasource
from helpers import prepare_for_json
from tasks import TaskGroup

MENU_ENTRY = 'Przygotowania do badań SKLEP'

REQUIRE_ROLE = ['C-FIN']

SQL = """
with f as (
select s.symbol,
    MAX(value) FILTER (WHERE st.name = 'name_cms') AS name_cms,
    MAX(value) FILTER (WHERE st.name = 'short_description_cms') AS short_description_cms,
    MAX(value) FILTER (WHERE st.name = 'long_description_cms') AS long_description_cms,
    MAX(value) FILTER (WHERE st.name = 'patient_preparation') AS patient_preparation,
    unnest(string_to_array(MAX(value) FILTER (WHERE st.name = 'patient_preparation'), '|')) as preparation_symbol
from services s
left join service_tags st on st.symbol = s.symbol 
where
    (s.is_visible_site or s.is_visible_shop) 
    and st.name in ('short_description_cms', 'long_description_cms', 'name_cms', 'patient_preparation')
group by 1
order by 1
)
select f.*, d.value as "preparation_value" from f
JOIN dictionaries d on d.symbol = f.preparation_symbol
order by 1
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="""Przygotawania do badań dla sklepu internetowgo z BIC """),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    main_task = {
        'type': 'noc',
        'priority': 1,
        'params': params,
        'function': 'zbierz',
    }
    report.create_task(main_task)
    report.save()
    return report


def zbierz(task_params):
    ds = BiCDatasource()
    header = 'Symbol, Nazwa CMS, Krótki opis CMS, Długi opis CMS, Przygotawania pacjenta, Symbol przygotowania, Przygotowanie'.split(',')
    cols, rows = ds.select(SQL)
    return {
        'type': 'table',
        'header': header,
        'data': prepare_for_json(rows),
    }
