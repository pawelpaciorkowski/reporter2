from datasources.snrkonf import SNRKonf
from datasources.kakl import karta_klienta
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, PlatnikSearch, \
    Select, Radio, ValidationError
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from raporty.info._hl7ctl import ZlaczkiKlienta

MENU_ENTRY = 'Płatnikach'

REQUIRE_ROLE = ['C-CS', 'C-ROZL', 'C-PP']

LAUNCH_DIALOG = Dialog(title="Wszystko o płatniku", panel=VBox(
    InfoText(text="Informacje o płatnikach z różnych systemów"),
    PlatnikSearch(field='platnik', title='Płatnik', width='600px'),
))

HELP = """
Informacje o płatnikach pochodzą z następujących systemów (jeśli są dostępne):

- SNR - wyszukiwanie płatników, podstawowe dane

- Karty Klienta ("Django") - szczegółowe informacje wprowadzone przez przedstawicieli

- Monitoring HL7 - aktualny stan połączeń z klientem

"""


def start_report(params, user_labs_available):
    params = LAUNCH_DIALOG.load_params(params)
    params['labs_available'] = user_labs_available
    if params['platnik'] is None:
        raise ValidationError("Nie wybrano płatnika")
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'snr',
        'priority': 0,
        'params': params,
        'function': 'raport_snrkonf'
    }
    report.create_task(task)
    task = {
        'type': 'hbz',
        'priority': 1,
        'params': params,
        'function': 'raport_kakl'
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


def raport_snrkonf(task_params):
    params = task_params['params']
    snr = SNRKonf()
    dane_snr = snr.dict_select("""
        select kl.nazwa, kl.nip, kl.hs->'adres' as adres, kl.hs->'umowa' as umowa,
        coalesce(prz.imiona, '') || ' ' || coalesce(prz.nazwisko, '') as przedstawiciel, c.nazwa as cegla, kl.del,
        array_agg(kwl.laboratorium || ':' || kwl.symbol) as symbole_w_labach
        from platnicy kl
        left join platnicywlaboratoriach kwl on kwl.platnik=kl.id and not kwl.del
        left join pracownicy prz on prz.id=kl.hs->'przedstawiciel'
        left join cegly c on c.id=kl.hs->'cegla'
        where kl.id=%s
        group by 1, 2, 3, 4, 5, 6, 7
    """, [params['platnik']])[0]
    params['dane_snr'] = dane_snr

    dane = [
        {'title': 'Nazwa', 'value': dane_snr['nazwa']},
        {'title': 'Adres', 'value': dane_snr['adres']},
        {'title': 'NIP', 'value': dane_snr['nip']},
        {'title': 'Nr K', 'value': dane_snr['umowa']},
        {'title': 'Symbole w laboratoriach', 'value': ', '.join(dane_snr['symbole_w_labach'])},
        {'title': 'Przedstawiciel', 'value': dane_snr['przedstawiciel']},
    ]

    if dane_snr['del']:
        dane.append({'title': '', 'value': 'Płatnik skasowany!'})

    return {
        'title': 'Dane klienta z SNR',
        'type': 'vertTable',
        'data': dane,
    }

# TODO: przykładowy klient z kartą klienta: CZADAX
def raport_kakl(task_params):
    params = task_params['params']
    kakl = karta_klienta(platnik=params['platnik'])
    if kakl is None:
        return None
    return {
        'title': 'Karta Klienta',
        'type': 'html',
        'html': kakl,
    }


def raport_hl7ctl(task_params):
    params = task_params['params']
    zk = ZlaczkiKlienta(params['platnik'], params['labs_available'])
    return zk.html()

    # if res is not None:
    #     return {
    #         'type': 'html',
    #         'html': res
    #     }


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': [
            'pdf',
        ]
    }
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            # TODO: tu być może sprawdzenie czy ktoś ma mieć dostęp (chociaż lepiej przy odpalaniu)
            res['results'].append(result)
    res['progress'] = task_group.progress
    return res
