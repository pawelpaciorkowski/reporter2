from datasources.bic import BiCDatasource
from datasources.snrkonf import SNRKonf
from datasources.kakl import karta_klienta
from datasources.mop import MopDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, PunktPobranSearch, \
    Select, Radio, ValidationError
from helpers import get_centrum_connection, prepare_for_json, obejdz_slownik
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from raporty.info._hl7ctl import ZlaczkiKlienta
from tasks.db import redis_conn
import json

MENU_ENTRY = 'Punktach Pobrań'

REQUIRE_ROLE = ['C-CS', 'C-PP', 'C-ROZL']


def odswiez_liste_punktow():
    mop = MopDatasource()
    _ = mop.get_cached_data('api/v2/collection-point')


LAUNCH_DIALOG = Dialog(title="Wszystko o punkcie pobrań", on_show=odswiez_liste_punktow, panel=VBox(
    InfoText(text="Informacje o punkcie pobrań z różnych systemów"),
    PunktPobranSearch(field='punkt', title='Punkt pobrań', width='600px'),
))


def start_report(params, user_labs_available):
    params = LAUNCH_DIALOG.load_params(params)
    params['labs_available'] = user_labs_available
    if params['punkt'] is None:
        raise ValidationError("Nie wybrano punktu pobrań")
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'mop',
        'priority': 1,
        'params': params,
        'function': 'raport_mop'
    }
    report.create_task(task)
    report.save()
    return report


def raport_mop(task_params):
    params = task_params['params']
    mop = MopDatasource()
    bic = BiCDatasource()
    punkty = mop.get_cached_data('api/v2/collection-point')
    punkt = None
    for elem in punkty:
        if elem.get('marcel') == params['punkt']:
            punkt = elem
    if punkt is None:
        return None
    dane = [
        ('Symbol', 'marcel'),
        ('Nazwa', 'name'),
        ('Adres', 'city.postalCode city.name street'),
        ('Laboratorium', 'laboratory.symbol - laboratory.name'),
        ('MPK', 'mpk'),
        ('Kontakt', 'email phone'),
    ]

    res = []

    for title, path in dane:
        value = obejdz_slownik(punkt, path)
        if value is not None:
            res.append({'title': title, 'value': value})
    for row in bic.dict_select("""
        select ccp.is_active, spl.snr_id, spl.symbol, spl.snr_symbol, spl.snr_name
        from config_collection_points ccp 
        left join service_price_lists spl on spl.id=ccp.price_list_id 
        where ccp.symbol=%s
    """, [punkt['marcel']]):
        if row['symbol'] is not None:
            value = '%s (%s, %s)' % (row['symbol'], row['snr_symbol'], row['snr_name'])
        else:
            value = 'Brak informacji o cenniku w BiC!!!'
        res.append({
            'title': 'Cennik',
            'value': value,
        })

    return {
        'title': 'Dane punktu pobrań w serwisach Skarbiec i BiC',
        'type': 'vertTable',
        'data': res,
    }
