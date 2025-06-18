from datasources.bic import BiCDatasource
from datasources.centrum import CentrumWzorcowa
from datasources.snr import SNR
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json, divide_chunks, empty, get_and_cache
from helpers.validators import validate_date_range, validate_symbol
from datasources.snrkonf import SNRKonf
from datasources.helper import HelperDb
from datasources.synchronizator import SynchronizatorDatasource
from tasks import TaskGroup, Task
import datetime
from helpers.connections import get_centra, get_db_engine

MENU_ENTRY = 'Płatnicy międzylaboratoryjni'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""
Raport pobiera dane z SNR i porównuje je z danymi wyliczanymi przez Nowy Synchronizator.
Zawiera informacje o:
Płatnikach z innych laborat. w wybranym laboratorium
Płatnikach wybranego laboratorium w innych laboratoriach.
 
Dodatkowo dla wybranego labu podana jest ilość zleceniodawców w bazie dla wyliczonego symbolu płatnika.
Oznaczenia kolorów:
- żółty - oznacza niezgodność niekrytyczną na poziomie wyliczeń: brak przyporządkowanego płatnika międzylaboratoryjnego w danym laboratorium, niezgodna ilość wyliczonych zleceniodawców przez Synchronizator w stosunku do ilości zleceniodawców w SNR.
- czerwony - oznacza niezgodność na poziomie danych wejściowych zawartych w SNR niezbędnych do procesów wyliczanych w nowym synchronizatorze: brak zdefiniowanego pre-/post- fiksu dla laboratorium.
    """),
    LabSelector(field='lab', title='Laboratorium', multiselect=False),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport_snr'
    }
    report.create_task(task)
    # task = {
    #     'type': 'ick',
    #     'priority': 1,
    #     'params': params,
    #     'function': 'raport_synchro'
    # }
    # report.create_task(task)
    report.save()
    return report


def ilosci_zleceniodawcow_sync(lab, platnicy):
    synchronizator = SynchronizatorDatasource()
    res = {}
    for row in synchronizator.dict_select("""
        select lab, dane->>'platnik' as platnik, count(id) as ilosc,
        sum(case when lab_id is not null then 1 else 0 end) as ilosc_sync
        from slownik_lab where slownik='oddzialy' and not lab_del
        and dane->>'platnik' in %s
        group by 1, 2
    """, [tuple(platnicy)]):
        lab = row['lab']
        if lab not in res:
            res[lab] = {}
        res[lab][row['platnik']] = (row['ilosc'], row['ilosc_sync'])
    return res


def raport_snr(task_params):
    params = task_params['params']
    lab = params['lab']
    wiersz_lab = None
    wiersze_pozostale = {}
    snr = SNR()
    ilosci_oddzialow_w_lab = {}
    with get_centrum_connection(lab) as conn:
        for row in conn.raport_slownikowy("""
            select trim(pl.symbol) as platnik, count(o.id) as ilosc
            from oddzialy o 
            left join platnicy pl on pl.id=o.platnik 
            where o.del=0
            group by 1
        """):
            ilosci_oddzialow_w_lab[row['platnik']] = row['ilosc']

    symbole_platnikow_wszysktie = set()
    for row in snr.dict_select("""
        select
        symbol, nazwa, vpn, coalesce(hs->'wykluczsync', 'False')='True' as wykluczsync,
        coalesce(hs->'cdc', 'False')='True' as cdc, coalesce(hs->'nowesk', 'False')='True' as nowesk,
        trim(coalesce(hs->'symbolplatnika', '')) as postfix,
        trim(coalesce(hs->'przedrosteksymbolu', '')) as prefix,
        hs->'centrumrozliczeniowe' as centrumrozliczeniowe,
        trim(coalesce(hs->'miejscowosc', '')) as miejscowosc,
        (select count(id) from zleceniodawcywlaboratoriach zwl where zwl.laboratorium=laboratoria.symbol and not zwl.del) as ile_zleceniodawcow
        from laboratoria where aktywne and not del
    """):
        symbol = row['symbol'][:7]
        if symbol == lab:
            wiersz_lab = row
        else:
            wiersze_pozostale[symbol] = row
    res = []
    if wiersz_lab is None:
        return {'type': 'error', 'text': 'Nie znaleziono konfiguracji labu w SNR!'}
    if empty(wiersz_lab['prefix']):
        return {'type': 'error', 'text': 'Brak prefiksu laboratorium'}
    if empty(wiersz_lab['postfix']):
        return {'type': 'error', 'text': 'Brak części wspólnej symbolu laboratorium'}

    for row in wiersze_pozostale.values():
        if not empty(row['prefix']):
            symbole_platnikow_wszysktie.add(row['prefix'] + wiersz_lab['postfix'])
        if not empty(row['postfix']):
            symbole_platnikow_wszysktie.add(wiersz_lab['prefix'] + row['postfix'])

    pwl = {}
    for row in snr.dict_select("""
        select pwl.symbol, pwl.laboratorium, pl.nazwa, pwl.hs->'grupa' as grupa
        from platnicywlaboratoriach pwl
        left join platnicy pl on pl.id=pwl.platnik
        where pwl.symbol in %s and not pwl.del
    """, [tuple(symbole_platnikow_wszysktie)]):
        labp = row['laboratorium'][:7]
        if labp not in pwl:
            pwl[labp] = {}
        pwl[labp][row['symbol']] = row

    zleceniodawcy_sync = get_and_cache(f'miedzylab_ile_zleceniodawcow_sync_{lab}',
                                       lambda: ilosci_zleceniodawcow_sync(lab, symbole_platnikow_wszysktie),
                                       timeout=3600)

    res.append({
        'type': 'vertTable',
        'title': f'Laboratorium {lab}',
        'data': prepare_for_json([
            {'title': 'Nazwa', 'value': wiersz_lab['nazwa']},
            {'title': 'Centrum rozliczeniowe', 'value': wiersz_lab['centrumrozliczeniowe']},
            {'title': 'Prefiks', 'value': wiersz_lab['prefix']},
            {'title': 'Część wspólna symbolu', 'value': wiersz_lab['postfix']},
        ]),
    })

    wiersze_wchodzace = []
    for symbol in sorted(wiersze_pozostale.keys()):
        row = wiersze_pozostale[symbol]
        nazwa = grupa = ile_do_synchro = ile_platnika_w_labie = None
        if not empty(row['postfix']):
            platnik = wiersz_lab['prefix'] + row['postfix']
            ile_platnika_w_labie = ilosci_oddzialow_w_lab.get(platnik)
            if platnik in pwl.get(lab, {}):
                row_platnik = pwl[lab][platnik]
                nazwa = row_platnik['nazwa']
                grupa = row_platnik['grupa']
                if platnik in zleceniodawcy_sync.get(lab, {}):
                    ilosc, ilosc_sync = zleceniodawcy_sync[lab][platnik]
                    if ilosc == 0:
                        kolor = '#ff0000'
                    elif ilosc > ilosc_sync or ilosc != row['ile_zleceniodawcow']:
                        kolor = '#ffff00'
                    else:
                        kolor = '#ffffff'
                    if ilosc == ilosc_sync:
                        ilosc_opis = str(ilosc)
                    else:
                        ilosc_opis = f'{ilosc_sync} / {ilosc}'
                    ile_do_synchro = {'background': kolor, 'value': ilosc_opis}
            else:
                platnik = {'background': '#ffff00', 'value': platnik}
        else:
            platnik = {'background': '#ff0000', 'value': 'Brak postfiksa'}

        wiersze_wchodzace.append([symbol, platnik, nazwa, grupa, row['ile_zleceniodawcow'], ile_do_synchro, ile_platnika_w_labie])
    res.append({
        'type': 'table',
        'title': f'Płatnicy innych labów w {lab}',
        'header': 'Lab,Oczekiwany symbol,Płatnik w laboratorium,Grupa płatnika,Zleceniodawcy w lab,Zleceniodawcy synchro,Zleceniodawcy płatnika w bazie'.split(
            ','),
        'data': prepare_for_json(wiersze_wchodzace),
    })

    wiersze_wychodzace = []
    for symbol in sorted(wiersze_pozostale.keys()):
        row = wiersze_pozostale[symbol]
        nazwa = grupa = ile_do_synchro = None
        if not empty(row['prefix']):
            platnik = row['prefix'] + wiersz_lab['postfix']
            if platnik in pwl.get(symbol, {}):
                row_platnik = pwl[symbol][platnik]
                nazwa = row_platnik['nazwa']
                grupa = row_platnik['grupa']
                if platnik in zleceniodawcy_sync.get(symbol, {}):
                    ilosc, ilosc_sync = zleceniodawcy_sync[symbol][platnik]
                    if ilosc == 0:
                        kolor = '#ff0000'
                    elif ilosc > ilosc_sync or ilosc != wiersz_lab['ile_zleceniodawcow']:
                        kolor = '#ffff00'
                    else:
                        kolor = '#ffffff'
                    if ilosc == ilosc_sync:
                        ilosc_opis = str(ilosc)
                    else:
                        ilosc_opis = f'{ilosc_sync} / {ilosc}'
                    ile_do_synchro = {'background': kolor, 'value': ilosc_opis}
            else:
                platnik = {'background': '#ffff00', 'value': platnik}
        else:
            platnik = {'background': '#ff0000', 'value': 'Brak prefiksa'}
        wiersze_wychodzace.append([symbol, platnik, nazwa, grupa, ile_do_synchro])

    res.append({
        'type': 'table',
        'title': f'Płatnik {lab} ({wiersz_lab["ile_zleceniodawcow"]} zleceniodawców) w innych labach',
        'header': 'Lab,Oczekiwany symbol,Płatnik w laboratorium,Grupa płatnika,Zleceniodawcy synchro'.split(','),
        'data': prepare_for_json(wiersze_wychodzace),
    })

    return res

# def raport_synchro(task_params):
#     params = task_params['params']
#
