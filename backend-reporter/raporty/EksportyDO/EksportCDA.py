import copy
import re
import os
import shutil
import base64
import datetime
import time

# TODO: przy sprawdzaniu czy były kody sprawdzać też kody wykonań a nie tylko zleceń
# przykład LUBLINC listopad 2022 kod 5863358210

from datasources.reporter import ReporterDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from helpers.crystal_ball.marcel_servers import katalog_wydrukow, sciezka_wydruku
from helpers.validators import validate_date_range, validate_symbol
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none, divide_chunks, random_path, \
    copy_from_remote, ZIP, simple_password, empty

MENU_ENTRY = 'Eksport wyników CDA'

REQUIRE_ROLE = ['C-ADM']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Eksport wyników z plikami CDA wg kodów zleceń i dat wygenerowania sprawozdań.
        Eksport szuka dokładnie pasujących kodów zleceń i wykonań. Jeśli podane są kody niepasujące ani do zleceń ani wykonań
        (np klient zbiera sobie inne kody z kartonika niż rejestruje) trzeba zaznaczyć opcję "Sprawdź inne kody z rodzin",
        ale wyszukiwanie będzie znacząco wolniejsze. Nie używaj tej opcji bez potrzeby."""),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', pokaz_nieaktywne=True),
    TextInput(field='kody', title='Kody kreskowe zleceń (w nowych liniach)', textarea=True),
    Switch(field='innekody', title='Sprawdź inne kody z rodzin'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='T'),
    TextInput(field='oddzial', title='Pojedynczy zleceniodawca (symbol)'),
    TextInput(field='prefix_cda', title='Prefiks plików CDA'),
    TextInput(field='rozsz_cda', title='Rozszerzenie plików CDA')
))

KOD_RE = re.compile('^[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]$')

SQL_CENTRUM_ID_ZLECEN = """
select distinct zlecenie from 
    (select zlecenie from wykonania where kodkreskowy in ($KODY$) and del=0 and anulowane is null
    union select id as zlecenie from zlecenia where kodkreskowy in ($KODY$) and del=0 and anulowane is null) as a 
"""

SQL_CENTRUM_DANE = """
SELECT z.id as zlecenie, r.GODZINAREJESTRACJI, b.SYMBOL as "symbol badania", b.NAZWA as "nazwa badania", 
    pr.SYMBOL as "symbol parametru", pr.NAZWA as "nazwa parametru", m.SYMBOL as "Materiał", 
    w.WYNIKLICZBOWY, w.WYNIKTEKSTOWY, w.FLAGANORMY, w.FLAGAKRYTYCZNYCH, 
    o.SYMBOL as "symbol zleceniodawcy", o.NAZWA as "nazwa zleceniodawcy",
    p.NAZWISKO as "nazwisko pacjenta", p.IMIONA as "imiona pzcjenta", p.PESEL, 
    p.adres, p.telefon,
    r.KODKRESKOWY, r.PODPISANE, 
    z.datarejestracji as zl_data_rejestracji, z.numer as zl_numer,
    trim(bl.symbol) as "błąd wykonania"
from ZLECENIA Z
LEFT JOIN WYKONANIA r on r.zlecenie=z.id
left join wyniki w on w.wykonanie=r.id
LEFT JOIN BADANIA b ON r.BADANIE = b.ID
LEFT JOIN ODDZIALY o ON z.ODDZIAL = o.ID
LEFT JOIN MATERIALY m ON r.MATERIAL = m.ID
LEFT JOIN PACJENCI p ON r.PACJENT = p.ID
LEFT JOIN PARAMETRY pr on w.PARAMETR = pr.ID
left join bledywykonania bl on bl.id=r.bladwykonania
WHERE z.id in ($ZLECENIA$) and r.ANULOWANE is NULL and r.DEL = 0 and r.MATERIAL is NOT NULL and w.ukryty=0
"""

SQL_CENTRUM_PLIKI = """
SELECT wwz.zlecenie as zlecenie,
    list(wwz.plik) as pliki
from wydrukicdawzleceniach wwz
WHERE wwz.zlecenie in ($ZLECENIA$) and wwz.parent_del is null and wwz.podpisany=1 and wwz.dc between ? and ?
group by 1
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 2*365)
    if params['kody'] is None:
        raise ValidationError("Podaj kody kreskowe")
    linie = [kod.strip() for kod in params['kody'].replace('\r\n', '\n').replace('=', '').split('\n')]
    kody = []
    for linia in linie:
        if linia == '':
            continue
        if not KOD_RE.match(linia):
            raise ValidationError("Nieprawidłowy kod: %s" % linia)
        if linia not in kody:
            kody.append(linia)
    if len(kody) == 0:
        raise ValidationError("Podaj kody kreskowe")
    if len(kody) > 1000:
        raise ValidationError("Max 1000 kodów")
    if params['innekody'] and len(kody) > 1000:
        raise ValidationError("Przy zaznaczonej opcji sprawdź inne kody max 100 kodów")
    if not empty(params['oddzial']):
        validate_symbol(params['oddzial'])
    else:
        params['oddzial'] = None
    for fld in ('prefix_cda', 'rozsz_cda'):
        if empty(params[fld]):
            params[fld] = None
        else:
            params[fld] = os.path.basename(params[fld])
    tmp_dir = random_path('eksport_cda_')
    os.makedirs(tmp_dir, 0o755)
    os.makedirs(os.path.join(tmp_dir, 'wyniki'))
    adres = None
    baza_pg = None
    rep = ReporterDatasource()
    for row in rep.dict_select("select * from laboratoria where symbol=%s", [params['laboratorium']]):
        adres = row['adres_fresh']
        baza_pg = row['baza_pg']
    if adres is None:
        raise ValidationError("Brak adresu serwera dla %s" % params['laboratorium'])
    for chunk in divide_chunks(kody, 30):
        lb_task = {
            'type': 'centrum',
            'priority': 1,
            'target': params['laboratorium'],
            'params': {
                'adres': adres,
                'baza_pg': baza_pg,
                'tmp_dir': tmp_dir,
                'kody': chunk,
                'kodywszystkie': kody,
                'innekody': params['innekody'],
                'dataod': params['dataod'],
                'datado': params['datado'],
                'oddzial': params['oddzial'],
                'prefix_cda': params['prefix_cda'],
                'rozsz_cda': params['rozsz_cda'],
            },
            'function': 'raport_pobierz',
        }
        report.create_task(lb_task)
    report.save()
    return report


def raport_pobierz(task_params):
    params = task_params['params']
    # print(params)
    sql = SQL_CENTRUM_ID_ZLECEN
    kody = params['kody']
    if params['innekody']:
        for kod in copy.copy(kody):
            for digit in range(10):
                nkod = "%s%d" % (kod[:9], digit)
                if nkod not in kody:
                    kody.append(nkod)
    sql = sql.replace('$KODY$', ','.join(["'%s'" % kod for kod in kody]))
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        _, rows = conn.raport_z_kolumnami(sql)
        id_zlecen = [row[0] for row in rows]
        # print(sql, id_zlecen)
        if len(id_zlecen) == 0:
            return None
        sql_dane = SQL_CENTRUM_DANE
        sql_dane = sql_dane.replace('$ZLECENIA$', ','.join([str(id) for id in id_zlecen]))
        sql_pliki = SQL_CENTRUM_PLIKI
        sql_pliki = sql_pliki.replace('$ZLECENIA$', ','.join([str(id) for id in id_zlecen]))
        if params['baza_pg']:
            sql_pliki = sql_pliki.replace("list(wwz.plik)", "array_to_string(array_agg(wwz.plik), ',')")
        time_start = time.time()
        cols, rows = conn.raport_z_kolumnami(sql_dane)
        time_end = time.time()
        # print("Dane - zajęło %ds" % (time_end - time_start))
        time_start = time.time()
        pliki_zlecen = {}
        # print(sql_pliki)
        for row in conn.raport_slownikowy(sql_pliki, [params['dataod'], str(params['datado']) + ' 23:59:59']):
            pliki_zlecen[row['zlecenie']] = [plik.strip() for plik in row['pliki'].split(',') if plik != ''] if row[
                                                                                                                    'pliki'] is not None else []
        time_end = time.time()
        # print("Pliki - zajęło %ds" % (time_end - time_start))
        byly_zlecenia = set()
        res_rows = []
        for row in rows:
            zlecenie = row[0]
            oddzial = (row[11] or '').strip()
            if params['oddzial'] is not None and params['oddzial'] != oddzial:
                continue
            pliki = pliki_zlecen.get(zlecenie, [])
            row.append(','.join(pliki))
            res_rows.append(row)
            if zlecenie in byly_zlecenia:
                continue
            [data, numer] = row[20:22]
            if numer is None:
                continue
            byly_zlecenia.add(zlecenie)
            for plik in pliki:
                pelna_sciezka = sciezka_wydruku(task_params['target'], data, numer, plik)
                local_path = os.path.basename(pelna_sciezka)
                if not empty(params['prefix_cda']):
                    local_path = params['prefix_cda'] + local_path
                if not empty(params['rozsz_cda']):
                    rozsz = params['rozsz_cda']
                    if rozsz[0] != '.':
                        rozsz = '.' + rozsz
                    local_path = local_path[:-4] + rozsz
                local_path = os.path.join(params['tmp_dir'], 'wyniki', local_path)
                copy_from_remote(params['adres'], pelna_sciezka, local_path)
    return cols + ['pliki'], prepare_for_json(res_rows)


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': []
    }

    naglowek = None
    wiersze = []
    start_params = None

    for job_id, params, status, result in task_group.get_tasks_results():
        if start_params is None:
            start_params = params['params']
        if status == 'finished' and result is not None:
            cols, rows = result
            if naglowek is None:
                naglowek = cols
            for row in rows:
                wiersze.append(prepare_for_json(row))
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])

    res['progress'] = task_group.progress

    zleceniodawcy = []
    kody = []
    zlecenia_bez_plikow = []
    kody_bez_plikow = {}
    ile_wykonan = {}
    ile_bledow = {}
    for wiersz in wiersze:
        id_zlec = wiersz[0]
        zlec = wiersz[11]
        kod = wiersz[18]
        blad = wiersz[22]
        pliki = wiersz[23]
        if id_zlec not in ile_wykonan:
            ile_wykonan[id_zlec] = 0
            ile_bledow[id_zlec] = 0
        ile_wykonan[id_zlec] += 1
        if blad is not None and str(blad) != '':
            ile_bledow[id_zlec] += 1
        if zlec not in zleceniodawcy and zlec is not None:
            zleceniodawcy.append(zlec)
        if kod is not None and kod != '':
            kod = kod[:9]
            if kod not in kody:
                kody.append(kod)
        if pliki is None or pliki.strip() == '':
            if id_zlec not in zlecenia_bez_plikow:
                zlecenia_bez_plikow.append(id_zlec)

                info_kod = wiersz[18]
                if info_kod is None:
                    try:
                        info_kod = '%s / %d' % (str(wiersz[20]), wiersz[21])
                    except:
                        pass
                if info_kod is None:
                    info_kod = str(id_zlec)
                if id_zlec not in kody_bez_plikow or len(kody_bez_plikow[id_zlec]) != 10:
                    kody_bez_plikow[id_zlec] = info_kod

    if len(zleceniodawcy) > 0:
        res['results'].append({
            'type': 'info',
            'text': 'Eksport obejmuje zlecenia od zleceniodawców: %s' % ', '.join(zleceniodawcy)
        })
    if len(zlecenia_bez_plikow) > 0:
        zbp_bledy = []
        zbp_ok = []
        for id_zlec in zlecenia_bez_plikow:
            zl_info = kody_bez_plikow[id_zlec]
            if ile_wykonan[id_zlec] == ile_bledow[id_zlec]:
                zbp_bledy.append(zl_info)
            else:
                zl_info += ' (%d/%d błędów)' % (ile_bledow[id_zlec], ile_wykonan[id_zlec])
                zbp_ok.append(zl_info)
        if len(zbp_bledy) > 0:
            res['results'].append({
                'type': 'info', 'text': 'Dla %d zleceń w całości zabłędowanych nie ma plików CDA: %s' % (len(zbp_bledy), ', '.join(zbp_bledy))
            })
        if len(zbp_ok) > 0:
            res['results'].append({
                'type': 'warning', 'text': 'Dla %d zleceń niezabłędowanych nie ma plików CDA: %s' % (
                len(zbp_ok), ', '.join(zbp_ok))
            })
    if task_group.progress == 1.0:
        kody_bez_zlecen = []
        for kod in start_params['kodywszystkie']:
            if kod[:9] not in kody:
                kody_bez_zlecen.append(kod)
        if len(kody_bez_zlecen) > 0:
            res['results'].append({
                'type': 'warning',
                'text': 'Dla kodów %s nie znaleziono żadnych zleceń!' % ', '.join(kody_bez_zlecen)
            })
        if naglowek is not None:
            password = simple_password(letters_count=12, digits_count=2)
            res['results'].append({
                'type': 'info',
                'text': 'Hasło do zipa: %s' % password
            })
            zip_file = ZIP()
            zip_file.set_password(password)
            rep = ReportXlsx({'results': [{
                'type': 'table',
                'header': naglowek,
                'data': prepare_for_json(wiersze)
            }]})
            rep_fn = os.path.join(start_params['tmp_dir'], 'dane_centrum.xlsx')
            rep.render_to_file(rep_fn)
            if os.path.exists(rep_fn):
                zip_file.add_file(rep_fn)
            zip_file.add_file(os.path.join(start_params['tmp_dir'], 'wyniki'))
            res['results'].append({
                'type': 'download',
                'content': base64.b64encode(zip_file.save_as_bytes()).decode(),
                'content_type': 'application/zip',
                'filename': 'eksport_cda_%s.zip' % datetime.datetime.now().strftime('%Y-%m-%d'),
            })
            shutil.rmtree(start_params['tmp_dir'])
        else:
            res['errors'].append('Nic nie znaleziono')
    return res
