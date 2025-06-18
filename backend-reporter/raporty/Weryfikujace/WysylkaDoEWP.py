import datetime

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty
from datasources.korona import KoronaDatasource
from datasources.nocka import NockaDatasource

MENU_ENTRY = 'Wysyłka do EWP'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    VBox(
        InfoText(
            text='''Raport sprawdzający fakt wysyłki wyniku do EWP i ślady tego wydarzenia w różnych miejscach'''),
        HBox(
            VBox(TextInput(field='kodkreskowy', title='Kod kreskowy')),
        )
    )
))

SQL_WYKONANIA = """
    select system as "Lab", kodkreskowy as "Kod wykonania", zl_kodkreskowy as "Kod zlecenia",
        godzinapobrania as "Pobranie", dystrybucja as "Dystrybucja", zatwierdzone as "Zatwierdzone",
        wydrukowane as "Wydrukowane", badanie as "Badanie", wynik as "Wynik", zleceniodawca as "Zleceniodawca",
        lab_last_sync_at as "Sync. lab.",
        invalid_reason as "Nieprawidłowe dane", case when to_send then 'TAK' else 'NIE' end as "Wys.na.bież.",
        do_not_send_reason as "Powód nie-wys.",	ewp_sent_at as "Pierwsza wysyłka"
    from wykonania_biezace_ewp where kodkreskowy like %s or zl_kodkreskowy like %s
"""

SQL_LOG = """
    select system as "Lab", ewp_id as "ID zlec. z EWP", kodkreskowy as "Kod kreskowy",
        created_at as "Pierwsze wystąpienie", ewp_ftp_log_seen_at as "Ostatnie wystąpienie",
        ewp_ftp_log_ng_at as "Odp. EWP BŁĄD", autokorekta_at as "Autokorekta", ewp_ftp_log_ok_at as "Odp. EWP OK",
        log_text as "Log"
    from wyniki_ewp_log where kodkreskowy9=%s
"""

SQL_ZRZUT = """
    select id_zlectest, z_probka_data_pobrania, z_data_dostarczenia_laboratorium, z_data_wyniku, z_wynik_opis, status_zlecenia,
        z_nr_probki_laboratorium, laboratorium_id, id_osoba_ewp, kod_wojew, kod_powiat, kod_gmina, kod_miejscowosci, miejscowosc,
        kod_pocztowy, kod_miejscowosci
    from wykonania_ewp where z_nr_probki_laboratorium like %s
"""

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    kodkreskowy = params['kodkreskowy'].strip()
    if len(kodkreskowy) < 9 or len(kodkreskowy) > 10:
        raise ValidationError('Podaj 10-cyfrowy kod kreskowy (może być bez ostatniej cyfry)')
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': {'kodkreskowy': kodkreskowy},
        'function': 'zbierz_noc'
    }
    report.create_task(task)
    report.save()
    return report


def zbierz_noc(task_params):
    kodkreskowy = task_params['params']['kodkreskowy']
    res = []
    kod9 = kodkreskowy[:9]
    kod9like = kod9 + '%'
    noc = NockaDatasource()
    cols, rows = noc.select(SQL_WYKONANIA, [kod9like, kod9like])
    res.append({
        'type': 'table',
        'title': 'Wykonania z labów',
        'header': cols,
        'data': prepare_for_json(rows),
    })
    cols, rows = noc.select(SQL_LOG, [kod9])
    res.append({
        'type': 'table',
        'title': 'Log komunikacji z EWP (przesyłki XML)',
        'header': cols,
        'data': prepare_for_json(rows),
    })
    cols, rows = noc.select(SQL_ZRZUT, [kod9like])
    res.append({
        'type': 'table',
        'title': 'Zrzut codzienny z EWP',
        'header': cols,
        'data': prepare_for_json(rows),
    })
    return res

