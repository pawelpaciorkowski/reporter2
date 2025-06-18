import datetime

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty
from datasources.korona import KoronaDatasource

MENU_ENTRY = 'Zlecenie z EWP'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    VBox(
        InfoText(
            text='''Raport sprawdzający czy konkretne zlecenie spłynęło do nas z EWP i czy zostało zarejestrowane w zlecaczce.
                Wyszukiwanie po dowolnych polach z EWP lub kodzie kreskowym i peselu z zarejestrowanego zlecenia. Zwracane max 20 wierszy.'''),
        HBox(
            VBox(TextInput(field='szukaj', title='Szukaj', desc_title='Pesel, kod kreskowy lub ID z EWP')),
        )
    )
))

SQL = """
    (select wo.waiting_order_id as "EWP id", wo.created_at as "Wczytane z EWP",
        (wo.data::json)->>'Miasto z pliku' as "EWP miasto",
        (wo.data::json)->>'Pesel' as "PESEL EWP",
        case when (wo.is_active and wo.order_id is null) then 'TAK' else 'NIE' end as "Dostępne do wyszukania",
        o.created_at as "Rejestracja w zlecaczce",
        o.sent_at as "Wysłane ze zlecaczki do labu",
        ord.symbol as "Zleceniodawca",
        lr.symbol as "Lab rejestracji",
        lw.symbol as "Lab wykonania",
        pr.username as "Pracownik wysyłający",
        o.patient_pesel as "PESEL rejestracji",
        o.barcode as "Kod kreskowy rej.",
        o.collected_at as "Godzina pobrania"
    
    from zlecenia_waitingorder wo
        left join zlecenia_order o on o.id=wo.order_id
        left join zlecenia_orderer ord on ord.id=o.orderer_id
        left join zlecenia_laboratory lr on lr.id=o.registration_lab_id
        left join zlecenia_laboratory lw on lw.id=o.dest_lab_id
        left join zlecenia_user pr on pr.id=o.sent_by_id
    where wo.waiting_order_type='EWP' 
        and (wo.data like %s or wo.waiting_order_id=%s or o.patient_pesel=%s or o.barcode=%s or o.barcode like %s)
    
    order by wo.created_at limit 20)
    union
    (
    select 'RĘCZNIE' as "EWP id", null as "Wczytane z EWP",
        null as "EWP miasto",
        null as "PESEL EWP",
        null as "Dostępne do wyszukania",
        o.created_at as "Rejestracja w zlecaczce",
        o.sent_at as "Wysłane ze zlecaczki do labu",
        ord.symbol as "Zleceniodawca",
        lr.symbol as "Lab rejestracji",
        lw.symbol as "Lab wykonania",
        pr.username as "Pracownik wysyłający",
        o.patient_pesel as "PESEL rejestracji",
        o.barcode as "Kod kreskowy rej.",
        o.collected_at as "Godzina pobrania"
    
    from zlecenia_order o
        left join zlecenia_orderer ord on ord.id=o.orderer_id
        left join zlecenia_laboratory lr on lr.id=o.registration_lab_id
        left join zlecenia_laboratory lw on lw.id=o.dest_lab_id
        left join zlecenia_user pr on pr.id=o.sent_by_id
    where (o.patient_pesel=%s or o.barcode=%s or o.barcode like %s)
        and not exists (select wo.id from zlecenia_waitingorder wo where wo.order_id=o.id)
    
    order by o.created_at limit 20
    )
"""

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if len(params['szukaj'].strip()) < 4:
        raise ValidationError('Zbyt krótki tekst wyszukiwania')
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'zbierz_korona'
    }
    report.create_task(task)
    report.save()
    return report


def zbierz_korona(task_params):
    params = task_params['params']
    szukaj = params['szukaj'].strip()
    szukajp = '%' + szukaj + '%'
    szukajk = szukaj[:9] + '%'
    korona = KoronaDatasource()
    cols, rows = korona.select(SQL, [szukajp, szukaj, szukaj, szukaj, szukajk, szukaj, szukaj, szukajk])
    return [
        {
            'type': 'table',
            'header': cols,
            'data': prepare_for_json(rows),
        }
    ]

"""
zestawienie z nocki:

select we.laboratorium_id, we.status_zlecenia, el.alab_symbol, el.nazwa, count(we.id_zlectest)
from wykonania_ewp we
right outer join ewp_laboratoria el on we.laboratorium_id=(el.id_wojewodztwo || '_' || el.id)
where el.id is null or el.alab_symbol is not null
group by 1, 2, 3, 4
order by status_zlecenia, alab_symbol

"""