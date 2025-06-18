from datasources.snrkonf import SNRKonf
from datasources.kakl import karta_klienta
from datasources.mop import MopDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, LabSearch, \
    Select, Radio, ValidationError
from helpers import get_centrum_connection, prepare_for_json, obejdz_slownik
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from raporty.info._hl7ctl import ZlaczkiLabu
from tasks.db import redis_conn
import json

MENU_ENTRY = 'Laboratoriach'

REQUIRE_ROLE = ['C-CS', 'C-ROZL', 'C-PP']

HELP = """
Informacje o laboratorium pochodzą z Systemu Nadzoru Rozliczeń
"""

LAUNCH_DIALOG = Dialog(title="Wszystko o laboratorium", panel=VBox(
    InfoText(text="Informacje o laboratorium z różnych systemów"),
    LabSearch(field='lab', title='Laboratorium', width='600px'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'snr',
        'priority': 0,
        'params': params,
        'function': 'raport_snr'
    }
    report.create_task(task)
    task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'function': 'raport_hl7ctl'
    }
    report.create_task(task)
    report.save()
    return report


def raport_snr(task_params):
    params = task_params['params']
    snr = SNRKonf()
    dane_snr = snr.dict_select("""
        select *, hs->'adres' as adres, hs->'mpk' as mpk from laboratoria
        where symbol=%s
    """, [params['lab']])[0]
    params['dane_snr'] = dane_snr

    dane = [
        {'title': 'Symbol', 'value': dane_snr['symbol']},
        {'title': 'Nazwa', 'value': dane_snr['nazwa']},
        {'title': 'Adres', 'value': dane_snr['adres']},
        {'title': 'MPK', 'value': dane_snr['mpk']},
        {'title': 'VPN', 'value': dane_snr['vpn']},
    ]

    return {
        'title': 'Dane laboratorium z SNR',
        'type': 'vertTable',
        'data': dane,
    }

def raport_hl7ctl(task_params):
    params = task_params['params']
    zk = ZlaczkiLabu(params['lab'])
    return zk.html()
