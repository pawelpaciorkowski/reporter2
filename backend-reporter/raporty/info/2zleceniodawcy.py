from datasources.snrkonf import SNRKonf
from datasources.kakl import karta_klienta
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, ZleceniodawcaSearch, \
    Select, Radio, ValidationError
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from raporty.info._hl7ctl import ZlaczkiKlienta

MENU_ENTRY = 'Zleceniodawcach'

REQUIRE_ROLE = ['C-CS', 'C-ROZL', 'C-PP']

LAUNCH_DIALOG = Dialog(title="Wszystko o zleceniodawcy", panel=VBox(
    InfoText(text="Informacje o zleceniodawcy z różnych systemów"),
    ZleceniodawcaSearch(field='zleceniodawca', title='Zleceniodawca', width='600px'),
))

def start_report(params, user_labs_available):
    params = LAUNCH_DIALOG.load_params(params)
    params['labs_available'] = user_labs_available
    if params['zleceniodawca'] is None:
        raise ValidationError("Nie wybrano zleceniodawcy")
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'snr',
        'priority': 0,
        'params': params,
        'function': 'raport_snrkonf'
    }
    report.create_task(task)
    # task = {
    #     'type': 'hbz',
    #     'priority': 1,
    #     'params': params,
    #     'function': 'raport_kakl'
    # }
    # report.create_task(task)
    # task = {
    #     'type': 'ick',
    #     'priority': 1,
    #     'params': params,
    #     'function': 'raport_hl7ctl'
    # }
    # report.create_task(task)
    report.save()
    return report


def raport_snrkonf(task_params):
    params = task_params['params']
    snr = SNRKonf()
    dane_snr = snr.dict_select("""
        select zl.nazwa, zl.hs->'adres' as adres,
            pl.nazwa as nazwa_platnika, pl.id as id_platnika,
            array_agg(zwl.laboratorium || ':' || zwl.symbol) as symbole_w_labach,
            zl.hs->'identzestgot' as identzestgot
        from zleceniodawcy zl
        left join platnicy pl on pl.id=zl.platnik
        left join zleceniodawcywlaboratoriach zwl on zwl.zleceniodawca=zl.id
        where zl.id=%s
        group by 1, 2, 3, 4, 6
    """, [params['zleceniodawca']])[0]
    params['dane_snr'] = dane_snr

    dane = [
        {'title': 'Płatnik', 'value': dane_snr['nazwa_platnika']},
        {'title': 'Nazwa', 'value': dane_snr['nazwa']},
        {'title': 'Adres', 'value': dane_snr['adres']},
        {'title': 'Symbole w laboratoriach', 'value': ', '.join(dane_snr['symbole_w_labach'])},
        {'title': 'Identyfikator do zestawień gotówkowych', 'value': dane_snr['identzestgot']},
    ]

    return {
        'title': 'Dane zleceniodawcy z SNR',
        'type': 'vertTable',
        'data': dane,
    }