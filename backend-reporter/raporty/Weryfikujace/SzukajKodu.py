import requests

import config
from datasources.nocka import NockaDatasource
from datasources.mkurier import MKurierDatasource
from datasources.alabserwis import AlabSerwisDatasource
from datasources.postgres import PostgresDatasource
# from datasources.snr import SNR
from datasources.snrkonf import SNRKonf as SNR
from datasources.ppalab_upstream import PPAlabUpstreamDatasource
from datasources.reporter import ReporterExtraDatasource
from datasources.republika import RepublikaDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty

MENU_ENTRY = 'Szukaj kodu'

ADD_TO_ROLE = ['L-REJ', 'L-PRAC', 'R-DYR', 'R-PM']

SQL_CDC = "select array_to_string(array_agg(symbol order by symbol), ', ') as symbole from laboratoria where not del and aktywne  and hs->'cdc'='True'"

LABY_CDC = "brak danych"

try:
    snr = SNR()
    for row in snr.dict_select(SQL_CDC):
        LABY_CDC = row['symbole']
except:
    pass

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Proszę podać kod kreskowy. Szukanie w:'
             '\n - bazie raportowej - stan na koniec poprzedniego dnia'
             '\n - listach roboczych w laboratoriach - stan synchronizowany w miarę możliwości co godzinę'
             '\n - bazie mKurier'
             '\n - bazie dostaw i wydań kodów kreskowych'
             '\n - logach alabserwis'
             '\n - zleceniach z aplikacji Paragon Offline (po odzyskaniu łączności)'
             '\n - serwisie Republika (a.k.a. "pośrednik zleceń", testowe uruchomienie w ' + LABY_CDC + ')'
                                                                                                        '\n - logach sorterów (testowe uruchomienie w lab Zawodzie)'),
    # LabSelector(multiselect=True, selectall=True, field='laboratoria', title='Laboratoria',
    #             pokaz_nieaktywne=True),
    TextInput(field='kodkreskowy', title='Kod kreskowy', helper='min 9 cyfr', autofocus=True,
              validate=lambda x: len(x) >= 9, textarea=True),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    # raise ValidationError("Raport tymczasowo niedostępny")
    if empty(params['kodkreskowy']) or len(params['kodkreskowy']) < 9:
        raise ValidationError('Podaj co najmniej 9 cyfr kodu kreskowego')
    params['kodkreskowy'] = params['kodkreskowy'].replace('=', ' ').replace('\n', ' ').strip()
    if ' ' in params['kodkreskowy']:
        raise ValidationError('Tylko jeden kod!')

    task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'function': 'raport_nocka',
    }
    report.create_task(task)
    task = {
        'type': 'mop',
        'priority': 1,
        'params': params,
        'function': 'raport_listyrobocze',
    }
    report.create_task(task)
    task = {
        'type': 'ick',
        'priority': 0,
        'params': params,
        'function': 'raport_mkurier',
    }
    report.create_task(task)
    task = {
        'type': 'mop',
        'priority': 0,
        'params': params,
        'function': 'raport_alabserwis',
    }
    report.create_task(task)
    task = {
        'type': 'ick',
        'priority': 0,
        'params': params,
        'function': 'raport_ekstra',
    }
    report.create_task(task)
    task = {
        'type': 'snr',
        'priority': 0,
        'params': params,
        'function': 'raport_alabserwis_api',
    }
    report.create_task(task)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport_republika',
    }
    report.create_task(task)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport_sortery',
    }
    report.create_task(task)
    task = {
        'type': 'snr',
        'priority': 0,
        'params': params,
        'function': 'raport_offline',
    }
    report.create_task(task)
    report.save()
    return report


def raport_nocka(task_params):
    params = task_params['params']
    # TODO: laboratoria
    db = NockaDatasource()
    cols, rows = db.select("""select
        lab, lab_kodkreskowy as "kod wyk", lab_zlecenie_kodkreskowy as "kod zl",
        cast(lab_zlecenie_nr as varchar) || ' / ' || cast(lab_zlecenie_data as varchar) as "nr/data",
        zleceniodawca || ' - ' || zleceniodawca_nazwa as zleceniodawca,
        kanal as "kan. intern.",
        platnik_zlecenia || '  - ' || platnik_zlecenia_nazwa as "pł zlecenia",
        platnik_wykonania || '  - ' || platnik_wykonania_nazwa as "pł wykonania",
        typ_zlecenia as "Typ zl.",
        lab_pacjent_data_urodzenia as "data ur.",
        array_to_string(array_agg(badanie || ':' || material), ', ') as badania,
        pracownia,
        blad_wykonania || ' - ' || blad_wykonania_nazwa as "błąd",
        powod_anulowania || ' - ' || powod_anulowania_nazwa as "powód anul.",
        date_trunc('minute', lab_wykonanie_godz_rejestracji) as "godz. rej.",
        date_trunc('minute', lab_wykonanie_godz_pobrania) as "godz. pobr.",
        date_trunc('minute', lab_wykonanie_godz_dystrybucji) as "godz. przyj.",
        date_trunc('minute', lab_wykonanie_godz_zatw) as "godz. zatw.",
        date_trunc('minute', lab_wykonanie_godz_anulowania) as "godz. anul.",
        date_trunc('minute', lab_wykonanie_godz_wydruku) as "godz wydr."
        from wykonania_pelne 
        where left(lab_kodkreskowy, 9)=%s or left(lab_zlecenie_kodkreskowy, 9)=%s 
        group by 1,2,3,4,5,6,7,8,9,10,12,13,14,15,16,17,18,19,20""",
                           [params['kodkreskowy'][:9], params['kodkreskowy'][:9]])
    return [{
        'title': 'Baza raportowa nocka',
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    }]


def raport_listyrobocze(task_params):
    params = task_params['params']
    # TODO: laboratoria
    db = NockaDatasource()
    cols, rows = db.select("""select
        lab as "Laboratorium", bad_symbol as "Badanie", bad_nazwa as "Badanie nazwa",
        material as "Materiał", pr_symbol as "Pracownia", pr_nazwa as "Pracownia nazwa",
        ap_symbol as "Aparat", ap_nazwa as "Aparat nazwa",
        kodkreskowy as "Kod kreskowy", zl_kodkreskowy as "Kod zlecenia",
        numer as "Numer", datarejestracji as "Data zlecenia",
        zl_symbol as "Zleceniodawca", zl_nazwa as "Zlec. nazwa",
        pl_symbol as "Płatnik", pl_nazwa as "Pł. nazwa",
        dystrybucja as "Godzina przyjęcia",
        wyslanezlecenie as "Wysłane międzylab.",
        czasmaksymalny as "Czas maks"
        from listyrobocze 
        where left(kodkreskowy, 9)=%s or left(zl_kodkreskowy, 9)=%s """,
                           [params['kodkreskowy'][:9], params['kodkreskowy'][:9]])
    return [{
        'title': 'Listy robocze w laboratoriach',
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    }]


def raport_mkurier(task_params):
    params = task_params['params']
    db = MKurierDatasource()
    kod = params['kodkreskowy'][:9]
    kody = tuple(['%s%d' % (kod, i) for i in range(10)])
    cols, rows = db.select("""
        select 
            pr.kod as "Kod próbki", 
            pkt.nazwa || ' ' || pkt.ulica as "Punkt odbioru", 
            lab.nazwa || ' ' || lab.ulica as "Laboratorium",
            pr.data_utworzenia as "Data utworzenia próbki", pr.data_weryfikacji as "Data weryfikacji próbki",
            dost.kod_pojemnika as "Kod pojemnika", dost.data_skanowania_punktu_odbioru as "Data pkt. odbioru",
            dost.data_skanowania_pojemnika as "Data skan pojemnika", dost.data_zdania_transportu as "Data zdania transportu",
            dost.data_weryfikacji as "Data weryfikacji dostawy",
            array_to_string(array_agg(tz.nazwa || ' - ' || cast(dzd.data_utworzenia as varchar)), '; ') as "Zdarzenia"
        from pub.probki pr
        left join pub.dostawy dost on dost.id=pr.id_dostawy
        left join adm.punkty_odbioru pkt on pkt.id=dost.id_punktu
        left join adm.laboratoria lab on lab.id=pkt.id_laboratorium
        left join pub.dostawy_zdarzenia dzd on dzd.id_dostawy=dost.id
        left join adm.dostawy_typy_zdarzen tz on tz.id=dzd.id_typu
        where pr.kod in %s
        group by 1,2,3,4,5,6,7,8,9,10

    """, [kody])

    return [{
        'title': 'mKurier',
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    }]


def raport_alabserwis(task_params):
    # TODO: czasy z serwisu są zwracane jako UTC, przesunąć
    """
    jak nie działa (error 502) to trzeba wejść na 10.1.1.85
    # su - deploy
    $ pm2 resurrect
    """
    params = task_params['params']
    db = AlabSerwisDatasource()
    kod = params['kodkreskowy'][:9]
    cols, rows = db.select("""
        select D.sygnatura as "Dokument", D.data as "Data dokumentu",
                Kont.nazwa as "Kontrahent",
               MZ.nazwa as "Magazyn źródłowy",
               MD.nazwa as "Magazyn docelowy",
               concat(convert(dp.banderolaOd, char(64)),  ' - ', convert(dp.banderolaDo, char(64))) as "Zakres kodów",
               dp.typBanderola as "Typ kodów"
        from DokPoz dp
        left join Dokument D on dp.idDokument = D.idDokument
        left join Magazyn MZ on MZ.id=D.idMagazynZrodlowy
        left join Magazyn MD on MD.id=D.idMagazynDocelowy
        left join Kontrahent Kont on Kont.id=D.idKontrahent
        left join TypyDok TD on TD.id=D.idTypDok
        
        where dp.banderolaOd <= %s and dp.banderolaDo >= %s
        order by D.idDokument, dp.idDokPoz
    """, [kod, kod])  # wywalona kolumna D.uwagi, przed Kont.nazwa
    return [{
        'title': 'Przyjęcia i wydania kodów kreskowych',
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    }]


def raport_offline(task_params):
    params = task_params['params']
    kod = params['kodkreskowy'][:9]
    ups = PPAlabUpstreamDatasource()
    cols, rows = ups.select("""
        select collection_point as "Punkt pobrań", order_data->>'zleceniodawca' as "Zleceniodawca", 
            created_at as "Utworzono", order_data->>'kodkreskowy' as "Kod zlecenia",
            order_data->'badania' as "Badania", order_data->>'datapobrania' as "Data pobrania"
        from orders
        where left(order_data->>'kodkreskowy', 9)=%s
    """, [kod])
    if len(rows) == 0:
        return []
    res_rows = []
    for row in rows:
        row = list(row)
        row[4] = ', '.join([bad['badanie'] for bad in row[4]])
        res_rows.append(row)
    return [{
        'type': 'table',
        'title': 'Paragon offline',
        'header': cols,
        'data': prepare_for_json(res_rows)
    }]


def formatuj_znalezione(dane):
    res_txt = []
    res_html = []
    if dane is not None:
        for k, v in dane.items():
            res_txt.append('%s: %s' % (k, v))
            res_html.append('<strong>%s:</strong> %s' % (k, v))
    return {
        'html': '<br />'.join(res_html),
        'value': '\n'.join(res_txt)
    }


def raport_ekstra(task_params):
    params = task_params['params']
    kody = [params['kodkreskowy']]
    db = ReporterExtraDatasource()
    sql = """select p.kod as "Kod kreskowy", o.created_at as "Zapisany", o.created_by as "Zapisany przez", 
            o.description as "Komentarz", p.znalezione as "Znalezione"
        from worekkodow_pozycja p 
        left join worekkodow_operacja o on o.id=p.operacja
        where p.kod in %s"""
    sql_params = [tuple(kody)]
    lefts_sql = []
    lefts_sql_params = []
    for kod in kody:
        left = kod[:9]
        if left not in lefts_sql_params:
            lefts_sql.append('left(p.kod, 9)=%s')
            lefts_sql_params.append(left)
    if len(lefts_sql_params) > 0:
        sql += ' or (' + ' or '.join(lefts_sql) + ')'
        sql_params += lefts_sql_params
    cols, rows = db.select(sql, sql_params)
    cols.append("Dokładne dopasowanie")
    res = []
    for row in rows:
        row = list(row)
        row[-1] = formatuj_znalezione(row[-1])
        if row[0] in kody:
            row.append('T')
        else:
            row.append('')
        res.append(row)
    if len(res) > 0:
        return {
            'title': 'Kody do wyjaśnienia',
            'type': 'table',
            'header': cols,
            'data': prepare_for_json(res),
        }
    else:
        return None


def raport_alabserwis_api(task_params):
    params = task_params['params']
    url = f"http://2.0.205.185:8085/api/find?value={params['kodkreskowy']}&pageNumber=1"
    res = []
    for row in requests.get(url).json():
        res.append([
            (row.get('data') or '').replace('T', ' ').split('.')[0],
            row.get('login'),
            row.get('opis')
        ])
    if len(res) > 0:
        return {
            'title': 'Logi alabserwis',
            'type': 'table',
            'header': 'Czas,Login,Opis'.split(','),
            'data': prepare_for_json(res)
        }
    else:
        return None


def raport_republika(task_params):
    params = task_params['params']
    rep = RepublikaDatasource()
    res = []
    for id_zlec in rep.orders_for_barcode(params['kodkreskowy']):
        zlec = rep.get_order(id_zlec)
        if zlec is not None:
            res.append({
                'title': 'Republika - %s' % zlec['events'][0]['src'],
                'type': 'republika',
                'data': prepare_for_json(zlec)
            })
    return res


def raport_sortery(task_params):
    params = task_params['params']
    db = PostgresDatasource(dsn=config.Config.DATABASE_REPUBLIKA.replace('dbname=republika', 'dbname=logstream'))  # XXX
    kod = params['kodkreskowy']
    kod9 = kod[:9]
    SQL = """
        select pl.lab, pl.name as sorter, bo.barcode as kod, bo.ts as czas, bo.description as zdarzenie
        from barcode_occurrences bo
        left join places pl on pl.id=bo.place_id
        where left(bo.barcode, 9)=%s
        order by bo.ts
    """
    cols, rows = db.select(SQL, [kod9])
    if len(rows) == 0:
        return []
    res_rows = []
    for row in rows:
        row = list(row)
        if row[2] == kod:
            row[2] = {
                'background': '#aaffaa',
                'value': kod,
            }
        res_rows.append(row)
    return {
        'title': 'Sortery',
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(res_rows),
    }
