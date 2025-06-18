import datetime

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty
from datasources.snr import SNR

MENU_ENTRY = 'Zlecenie w Centrum i SNR'
REQUIRE_ROLE = 'C-ROZL'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    VBox(
        InfoText(
            text='''Proszę wybrać laboratorium, numer i datę rejestracji zlecenia, aby sprawdzić informację o tym zleceniu w systemie Centrum oraz SNR. 
                Jeśli nie znasz numeru zlecenia, a znasz kod kreskowy - numer i datę możesz sprawdzić w raporcie "Przebieg pracy".'''),
        LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', pokaz_nieaktywne=True),
        HBox(
            VBox(TextInput(field='numerzl', title='Numer i data zlecenia', desc_title='Numer zlecenia')),
            DateInput(field='datazl', desc_title='Data zlecenia', default='PZM')
        )
    )
))

SQL_CENTRUM_ZLEC = """
    select z.*, o.symbol as zleceniodawca_symbol, o.nazwa as zleceniodawca_nazwa, pl.symbol as platnik_symbol,
        pl.nazwa as platnik_nazwa, coalesce(l.nazwisko, '') || ' ' || coalesce(l.imiona, '') as lekarz,
        coalesce(p.nazwisko, '') || ' ' || coalesce(p.imiona, '') as pacjent,
        tz.symbol as typzlecenia_symbol, tz.nazwa as typzlecenia_nazwa,
        pa.symbol as powodanulowania_symbol,
        pa.nazwa as powodanulowania_nazwa,
        pr.nazwisko as rejestratorka,
        kan.symbol as kanal_symbol, kan.nazwa as kanal_nazwa,
        st.symbol as status_symbol, st.nazwa as status_nazwa,
        rej.symbol as rejestracja_symbol, rej.nazwa as rejestracja_nazwa
    from zlecenia z 
        left join oddzialy o on o.id=z.oddzial
        left join platnicy pl on pl.id=z.platnik
        left join lekarze l on l.id=z.lekarz
        left join pacjenci p on p.id=z.pacjent
        left join typyzlecen tz on tz.id=z.typzlecenia
        left join powodyanulowania pa on pa.id=z.powodanulowania
        left join pracownicy pr on pr.id=z.pracownikodrejestracji
        left join kanaly kan on kan.id=pr.kanalinternetowy
        left join statusypacjentow st on st.id=z.statuspacjenta
        left join rejestracje rej on rej.id=z.rejestracja
    where z.datarejestracji=? and z.numer=?
"""

SQL_CENTRUM_WYK = """
    select w.*, b.symbol as badanie_symbol, b.nazwa as badanie_nazwa, pw.symbol as platnik_symbol, m.symbol as material_symbol, m.nazwa as material_nazwa,
        pr.nazwisko as pc_nazwa, pa.symbol as pa_symbol, pa.nazwa as pa_nazwa, bw.symbol as bw_symbol, bw.nazwa as bw_nazwa
    from wykonania w 
        left join badania b on b.id=w.badanie
        left join materialy m on m.id=w.material
        left join pracownicy pr on pr.id=w.pc
        left join platnicy pw on pw.id=w.platnik
        left join powodyanulowania pa on pa.id=w.powodanulowania
        left join bledywykonania bw on bw.id=w.bladwykonania
    where w.zlecenie=?
    order by b.kolejnosc, m.kolejnosc
"""

SQL_SNR = """
    select w.*, u.identyfikatorwrejestrze as umowa_ident, c.symbol as cennik_symbol, c.nazwa as cennik_nazwa,
        rozl.identyfikatorwrejestrze as rozl_ident, rozl.datarozliczenia as rozl_data, fv.numer as fv_numer, fv.datadokumentu as fv_data,
        plw.nazwa as plw_nazwa, plw.nip as plw_nip, plw.hs->'umowa' as plw_umowa,
        plf.nazwa as plf_nazwa, plf.nip as plf_nip, plf.hs->'umowa' as plf_umowa,
        plr.nazwa as plr_nazwa, plr.nip as plr_nip, plr.hs->'umowa' as plr_umowa
    from wykonania w 
    left join umowy u on u.id=w.umowa
    left join cenniki c on c.id=w.cennik
    left join pozycjerozliczen pz on pz.id=w.pozycjerozliczen
    left join rozliczenia rozl on rozl.id=pz.rozliczenie
    left join faktury fv on fv.id=rozl.faktura
    left join platnicy plw on plw.id=w.platnik
    left join platnicy plf on plf.id=fv.platnik
    left join platnicy plr on plr.id=rozl.platnik
    where w.laboratorium=%s and w.zlecenie=%s
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'centrum',
        'priority': 0,
        'target': params['laboratorium'],
        'params': params,
        'function': 'zbierz_centrum_i_snr'
    }
    report.create_task(task)
    report.save()
    return report


def formatuj_czas(czas):
    if czas is None:
        return '---'
    else:
        if isinstance(czas, str):
            return czas[:12]
        elif isinstance(czas, datetime.datetime):
            return czas.strftime('%Y-%m-%d %H:%M')
        else:
            return czas.strftime('%Y-%m-%d')


def wiersz_wykonania(row):
    if row['pakiet'] is not None:
        row['badanie_symbol'] = "\u00a0\u00a0\u00a0\u00a0-\u00a0" + row['badanie_symbol']

    godziny = """Rejestracja: %s
                 Pobranie: %s
                 Dystrybucja: %s
                 Wykonanie: %s
                 Zatwierdzenie: %s"""
    godziny %= tuple(
        [formatuj_czas(row[fld]) for fld in 'godzinarejestracji godzina dystrybucja wykonane zatwierdzone'.split(' ')])
    ost_zm = "%s\n%s" % (formatuj_czas(row['dc']), row['pc_nazwa'])
    uwagi = []
    if row['platne'] != 1:
        uwagi.append('bezpłatne')
    if row['anulowane'] is not None:
        uwagi.append('anulowane %s: %s - %s' % (row['anulowane'], row['pa_symbol'], row['pa_nazwa']))
    if row['bladwykonania'] is not None:
        uwagi.append('zabłędowane: %s - %s' % (row['bw_symbol'], row['bw_nazwa']))
    if row['cena'] is not None:
        uwagi.append('cena: %f' % row['cena'])
    return [
        row['badanie_symbol'],
        row['material_symbol'],
        row['platnik_symbol'],
        row['kodkreskowy'],
        godziny,
        formatuj_czas(row['rozliczone']),
        ost_zm,
        '; '.join(uwagi)
    ]


def wiersz_wykonania_snr(row, system):
    if row['pakiet'] is not None:
        row['badanie'] = "\u00a0\u00a0\u00a0\u00a0-\u00a0" + row['badanie']
    uwagi = []
    if row['wspolczynnikpakietowydlaplatnika'] != 1.0 and row['wspolczynnikpakietowydlaplatnika'] is not None:
        uwagi.append('współczynnik pakietowy dla płatnika: %f' % row['wspolczynnikpakietowydlaplatnika'])
    if row['umowa'] is None:
        if row['cennik'] is None:
            uwagi.append('poza umową i cennikiem')
        else:
            uwagi.append('cennik: %s' % row['cennik_symbol'])
    else:
        uwagi.append('umowa: %s' % row['umowa_ident'])
    if row['bezplatne']:
        uwagi.append('bezpłatne')
    wykon = row['wykonanie'].split('^')
    if wykon[1].strip() != system.strip():
        uwagi.append('zlecone z: %s' % wykon[1])

    return [
        row['badanie'],
        row['material'],
        '%s (%s, %s)' % (row['plw_nazwa'] or '', row['plw_nip'] or '', row['plw_umowa'] or ''),
        row['cenadlaplatnika'],
        row['nettodlaplatnika'],
        "%s\n%s" % (row['statusprzeliczenia'], formatuj_czas(row['godzinaprzeliczenia'])),
        "%s\n%s" % (row['statusrozliczenia'], formatuj_czas(row['godzinarozliczenia'])),
        '; '.join(uwagi),
    ]


def dane_zlecenia_centrum(zlec):
    res = [
        {'title': 'Nr / data rejestracji', 'value': '%d / %s' % (zlec['numer'], zlec['datarejestracji'])},
        {'title': 'Id / System : SysId', 'value': '%d / %s : %d' % (zlec['id'], zlec['system'], zlec['sysid'])},
        {'title': 'Kod kreskowy', 'value': zlec['kodkreskowy']},
        {'title': 'Typ zlecenia', 'value': '%s - %s' % (zlec['typzlecenia_symbol'], zlec['typzlecenia_nazwa'])},
        {'title': 'Zleceniodawca', 'value': '%s - %s' % (zlec['zleceniodawca_symbol'], zlec['zleceniodawca_nazwa'])},
        {'title': 'Płatnik', 'value': '%s - %s' % (zlec['platnik_symbol'], zlec['platnik_nazwa'])},
        {'title': 'Rejestracja', 'value': '%s - %s' % (zlec['rejestracja_symbol'], zlec['rejestracja_nazwa'])},
        {'title': 'Pacjent', 'value': zlec['pacjent']},
        {'title': 'Lekarz', 'value': zlec['lekarz']},
        {'title': 'Pracownik od rejestracji', 'value': zlec['rejestratorka']},
    ]
    if zlec['kanal_symbol'] is not None:
        res.append({'title': 'Kanał internetowy', 'value': '%s - %s' % (zlec['kanal_symbol'], zlec['kanal_nazwa'])})
    if zlec['status_symbol'] is not None:
        res.append({'title': 'Status pacjenta', 'value': '%s - %s' % (zlec['status_symbol'], zlec['status_nazwa'])})
    if zlec['anulowane'] is not None:
        res.append({'title': 'Anulowane', 'value': '%s / %s' % (zlec['anulowane'], zlec['powodanulowania_symbol'])})
    if zlec['zewnetrznyidentyfikator'] is not None:
        res.append({'title': 'Zewnętrzny identyfikator', 'value': zlec['zewnetrznyidentyfikator']})
    # res.append({'title': 'dane', 'value': repr(zlec)})
    return res


def zbierz_centrum_i_snr(task_params):
    params = task_params['params']
    with get_centrum_connection(task_params['target']) as conn:
        res = conn.raport_slownikowy(SQL_CENTRUM_ZLEC, [params['datazl'], params['numerzl']])
    if len(res) == 0:
        return
    zlec = res[0]
    id_snr = '%d^%s' % (zlec['sysid'], zlec['system'].strip())
    with get_centrum_connection(task_params['target']) as conn:
        wykonania = conn.raport_slownikowy(SQL_CENTRUM_WYK, [zlec['id']])
    skladowe = {}
    for row in wykonania:
        if row['pakiet'] is not None:
            if row['pakiet'] not in skladowe:
                skladowe[row['pakiet']] = []
            skladowe[row['pakiet']].append(row)
    dane_wykonan = []
    for row in wykonania:
        if row['pakiet'] is None:
            dane_wykonan.append(wiersz_wykonania(row))
            if row['id'] in skladowe:
                for skl in skladowe[row['id']]:
                    dane_wykonan.append(wiersz_wykonania(skl))
    with SNR() as snr:
        dane_snr = snr.dict_select(SQL_SNR, [task_params['target'], id_snr])

    wykonania_snr = []
    skladowe_snr = {}
    rozliczenia = {}
    faktury = {}
    platnicy_faktur = {}
    platnicy_rozliczen = {}
    for row in dane_snr:
        if row['pakiet'] is not None:
            if row['pakiet'] not in skladowe_snr:
                skladowe_snr[row['pakiet']] = []
            skladowe_snr[row['pakiet']].append(row)
        symbol = row['badanie']
        if row['material'] is not None:
            symbol += ':' + row['material']
        if row['rozl_ident'] is not None:
            rozl = '%s z dnia %s' % (row['rozl_ident'], formatuj_czas(row['rozl_data']))
            platnicy_rozliczen[rozl] = row['plr_nazwa']
            if rozl not in rozliczenia:
                rozliczenia[rozl] = []
            rozliczenia[rozl].append(symbol)
        if row['fv_numer'] is not None:
            fv = '%s z dnia %s' % (row['fv_numer'], formatuj_czas(row['fv_data']))
            platnicy_faktur[fv] = row['plf_nazwa']
            if fv not in faktury:
                faktury[fv] = []
            faktury[fv].append(symbol)
    for row in dane_snr:
        if row['pakiet'] is not None:
            continue
        wykonania_snr.append(wiersz_wykonania_snr(row, task_params['target']))
        if row['id'] in skladowe_snr:
            for skl in skladowe_snr[row['id']]:
                wykonania_snr.append(wiersz_wykonania_snr(skl, task_params['target']))

    res_zlecenie = {
        'type': 'vertTable',
        'title': 'Centrum - zlecenie',
        'data': dane_zlecenia_centrum(zlec),
    }
    res_wykonania = {
        'type': 'table',
        'title': 'Centrum - wykonania',
        'header': 'Badanie,Materiał,Płatnik,Kod kreskowy,Godziny,Data rozl.,Ost. zmiana,Uwagi'.split(','),
        'data': dane_wykonan,
    }
    res_wykonania_snr = {
        'type': 'table',
        'title': 'SNR - wykonania',
        'header': 'Badanie,Materiał,Płatnik,Cena dla płatnika,Netto dla płatnika,Przeliczenie,Rozliczenie,Uwagi'.split(','),
        'data': prepare_for_json(wykonania_snr),
    }
    zapisy_rozliczeniowe = []
    for nr, badania in rozliczenia.items():
        zapisy_rozliczeniowe.append(['ROZL', nr, ', '.join(badania), platnicy_rozliczen[nr]])
    for nr, badania in faktury.items():
        zapisy_rozliczeniowe.append(['FV', nr, ', '.join(badania), platnicy_faktur[nr]])
    res_rozl_snr = {
        'type': 'table',
        'title': 'SNR - rozliczenia i faktury',
        'header': 'Typ zapisu,Numer,Badania,Płatnik'.split(','),
        'data': zapisy_rozliczeniowe,
    }
    return [res_zlecenie, res_wykonania, res_wykonania_snr, res_rozl_snr]
