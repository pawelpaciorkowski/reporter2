import datetime

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty
from datasources.snr import SNR

MENU_ENTRY = 'Szukaj pozycji faktury'
# REQUIRE_ROLE = 'C-ROZL'


SQL = """
    select f.numer, f.odbiorca, pwl.symbol as platnik, pl.nazwa as platnik_nazwa, pl.nip, 
    zwl.symbol as zleceniodawca, zl.nazwa as zleceniodawca_nazwa,
    f.opis, pr.nazwa as "Pozycja rozliczenia", pr.netto,
    w.badanie, w.material, w.analizator, 
    w.laboratorium, (w.hs->'numer') || ' / ' || (w.datarejestracji) as zlecenie, w.hs->'kodkreskowy' as "Kod kreskowy",
    coalesce(w.hs->'pacjencinazwisko', '') || ' ' || coalesce(w.hs->'pacjenciimiona', '') || ' ' || coalesce(w.hs->'pacjencipesel', ' ') as pacjent,
    coalesce(w.hs->'lekarzenazwisko', '') || ' ' || coalesce(w.hs->'lekarzeimiona', '') as lekarz,
    w.wykonanie
    
    from faktury f 
    left join rozliczenia r on r.faktura=f.id
    left join pozycjerozliczen pr on pr.rozliczenie=r.id
    left join wykonania w on w.id=pr.wykonanie
    left join platnicy pl on pl.id=f.platnik
    left join zleceniodawcy zl on zl.id=w.zleceniodawca
    left join platnicywlaboratoriach pwl on pwl.platnik=pl.id and pwl.laboratorium=w.laboratorium and not pwl.del
    left join zleceniodawcywlaboratoriach zwl on zwl.zleceniodawca=zl.id and zwl.laboratorium=w.laboratorium and not zwl.del
    
    
    where f.numer=%s
    and ( w.hs->'$POLE$nazwisko' ilike %s or w.hs->'$POLE$imiona' like %s )
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    VBox(
        InfoText(
            text='''Podaj numer faktury i nazwisko pacjenta lub lekarza żeby znaleźć odpowiadające im pozycje zestawień do faktury.
            W nazwiskach nie jest istotna wielkość liter, ale jest istotne podanie pełnego nazwiska i polskich znaków tak jak wystąpiły na zestawieniu.
            Uwaga - raport wykonywany jest z danych wykonań replikowanych z labów do SNR. Jeśli lekarz lub pacjent zostali zmienieni po wydaniu faktury i zestawienia i dane te zostały zgrane do SNR to wykonania nie zostaną znalezione.'''),
        TextInput(field='numerfv', title='Numer faktury'),
        TextInput(field='pacjent', title='Nazwisko pacjenta'),
        TextInput(field='lekarz', title='Nazwisko lekarza'),
    )
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if empty(params['numerfv']):
        raise ValidationError("Podaj numer faktury")
    params['numerfv'] = params['numerfv'].strip()
    if not empty(params['pacjent']):
        params['pole'] = 'pacjenci'
        params['szukaj'] = params['pacjent'].strip()
    elif not empty(params['lekarz']):
        params['pole'] = 'lekarze'
        params['szukaj'] = params['lekarz'].strip()
    else:
        raise ValidationError("Podaj nazwisko pacjenta lub lekarza")
    report.create_task({
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport_snr',
    })
    report.save()
    return report


def raport_snr(task_params):
    params = task_params['params']
    snr = SNR()
    sql = SQL.replace('$POLE$', params['pole'])
    cols, rows = snr.select(sql, [params['numerfv'], params['szukaj'], params['szukaj']])
    if len(rows) == 0:
        if len(snr.dict_select("select id from faktury where numer=%s", [params['numerfv']])) > 0:
            return {'type': 'warning',
                    'text': 'Znaleziono fakturę o podanym numerze, ale nie znaleziono pasującego nazwiska.'}
        else:
            return {'type': 'error', 'text': 'Nie znaleziono faktury o podanym numerze :('}
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    }
