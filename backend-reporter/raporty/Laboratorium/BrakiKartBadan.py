from datasources.bic import BiCDatasource
import time

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError, Switch
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty, odpiotrkuj, Kalendarz

MENU_ENTRY = 'Braki w kartach badań'

NEWS = [
    ("2025-01-01", """
        Nowy raport sprawdzający braki w kartach badań wykonywanych lokalnie i definicjach centralnych.
    """)
]

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    Switch(field='centralne', title='Sprawdź definicje centralne zamiast laboratoriów')
))

SQL_LABY = """
    select distinct spl.symbol as badanie, cl.symbol as laboratorium, spl.method as metoda, 
    (length(coalesce(st1.value, '') || coalesce(st11.value, '')) = 0) as "brak info: metoda",
    (length(coalesce(st2.value, '') || coalesce(st12.value, '')) = 0) as "brak info: pobrany materiał",
    (length(coalesce(st3.value, '') || coalesce(st13.value, '')) = 0) as "brak info: material do badan",
    (length(coalesce(st4.value, '') || coalesce(st14.value, '')) = 0) as "brak info: warunki pobrania",
    (length(coalesce(st5.value, '') || coalesce(st15.value, '')) = 0) as "brak info: stabilnosc",
    (length(coalesce(st6.value, '') || coalesce(st16.value, '')) = 0) as "brak info: transport",
    (st7.value is null or st7.value ='') as "brak info czas oczekiwania"
    from config_labs cl
    left join service_performance_location spl on cl.symbol=spl.lab
    left join services s on  s.symbol=spl.symbol
    left join service_tags st1 on st1.symbol=s.symbol and st1.name=cl.symbol||':info_method'
    left join service_tags st2 on st2.symbol=s.symbol and st2.name=cl.symbol||':info_collected_material'
    left join service_tags st3 on st3.symbol=s.symbol and st3.name=cl.symbol||':info_tested_material'
    left join service_tags st4 on st4.symbol=s.symbol and st4.name=cl.symbol||':info_collection_conditions'
    left join service_tags st5 on st5.symbol=s.symbol and st5.name=cl.symbol||':info_stability'
    left join service_tags st6 on st6.symbol=s.symbol and st6.name=cl.symbol||':info_transport_conditions'
    left join service_tags st7 on st7.symbol=s.symbol and st7.name=cl.symbol||':centrum_result_in_hours'
    left join service_tags st12 on st12.symbol=s.symbol and st12.name='info_collected_material'
    left join service_tags st11 on st11.symbol=s.symbol and st11.name='info_method'
    left join service_tags st14 on st14.symbol=s.symbol and st14.name='info_collection_conditions'
    left join service_tags st13 on st13.symbol=s.symbol and st13.name='info_tested_material'
    left join service_tags st15 on st15.symbol=s.symbol and st15.name='info_stability'
    left join service_tags st16 on st16.symbol=s.symbol and st16.name='info_transport_conditions'
    where
        cl.is_active
        and s.is_lab_editable and s.is_bundle is false
        and spl.lab=spl.dest_lab
        and spl.method is not null
        and ((length(coalesce(st1.value, '') || coalesce(st11.value, '')) = 0)
            or (length(coalesce(st2.value, '') || coalesce(st12.value, '')) = 0)
            or (length(coalesce(st3.value, '') || coalesce(st13.value, '')) = 0)
            or (length(coalesce(st4.value, '') || coalesce(st14.value, '')) = 0)
            or (length(coalesce(st5.value, '') || coalesce(st15.value, '')) = 0)
            or (length(coalesce(st6.value, '') || coalesce(st16.value, '')) = 0)
            or (st7.value is null or length(st7.value)=0))
        and spl.lab in %s
    order by spl.symbol ;
"""

SQL_CENTRALNE = """
    select distinct s.symbol,
    st1.value is null or st1.value='' as "brak info: przygotowanie pacjenta",
    st2.value is null or st2.value='' as "brak info: pobrany materiał",
    st3.value is null or st3.value='' as "brak info: materiał do badan",
    st4.value is null or st4.value='' as "warunki pobrania",
    st5.value is null or st5.value='' as "przygotowanie materiału",
    st6.value is null or st6.value='' as "brak info:stabilność",
    st7.value is null or st7.value='' as "brak info: metoda "
    from services s
    left join service_tags st on s.symbol=st.symbol
    left join service_tags st1 on s.symbol=st1.symbol and st1.name ='patient_preparation'
    left join service_tags st2 on s.symbol=st2.symbol and st2.name ='info_collected_material'
    left join service_tags st3 on s.symbol=st3.symbol and st3.name ='info_tested_material'
    left join service_tags st4 on s.symbol=st4.symbol and st4.name ='info_collection_conditions'
    left join service_tags st5 on s.symbol=st5.symbol and st5.name ='info_preparation'
    left join service_tags st6 on s.symbol=st6.symbol and st6.name ='info_stability'
    left join service_tags st7 on s.symbol=st7.symbol and st7.name ='info_metod'
    where
        not s.is_lab_editable  and not s.is_bundle and (
            (st1.value is null or length(st1.value)=0)
         or (st2.value is null or length(st2.value)=0)
         or (st3.value is null or length(st3.value)=0)
         or (st4.value is null or length(st4.value)=0)
         or (st5.value is null or length(st5.value)=0)
         or (st6.value is null or length(st6.value)=0)
         or (st7.value is null or length(st7.value)=0)	
        )
    ;
"""

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0 and not params['centralne']:
        raise ValidationError("Nie wybrano laboratorium")
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport_bic'
    }
    report.create_task(task)
    report.save()
    return report


def raport_bic(task_params):
    params = task_params['params']
    bic = BiCDatasource()
    if params['centralne']:
        cols, rows = bic.select(SQL_CENTRALNE, [tuple(params['laboratoria'])])
        res_rows = []
        for row in rows:
            res_row = list(row[:1])
            for val in row[1:]:
                res_row.append('T' if val else '')
            res_rows.append(res_row)
    else:
        cols, rows = bic.select(SQL_LABY, [tuple(params['laboratoria'])])
        res_rows = []
        for row in rows:
            res_row = list(row[:3])
            for val in row[3:]:
                res_row.append('T' if val else '')
            res_rows.append(res_row)
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(res_rows),
    }