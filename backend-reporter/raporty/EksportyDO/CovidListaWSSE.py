import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from helpers.validators import validate_date_range
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none, divide_chunks
from datasources.nocka import NockaDatasource

MENU_ENTRY = 'Covid - lista dla WSSE'

REQUIRE_ROLE = ['C-ADM']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Eksport dla wsse - wg dat zatwierdzenia."""),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    DateInput(field='data', title='Data zatwierdzenia', default='-1D'),

))

"""

- tak w takiej sytuacji dodatkowa kolumna na adres będzie jak najbardziej wskazana;

- raport powinien być generowany na podstawie dat zatwierdzenia;

- dla wszystkich prób (NFZ + komercja);

- tylko dla badania 2019COV,

- wartość genORF1ab z parametru o symbolu ORF1, genN z parametru N – tak dokładnie,

- filtrowanie: wszystkie dodatnie (najlepiej spełniające warunek dla parametrów ORF1 i/lub N poniżej < 30)


select par.symbol, y.WYNIKTEKSTOWY, y.WYNIKLICZBOWY, w.POLOZENIEX, w.POLOZENIEY, sta.SYMBOL, sta.NAZWA
from wykonania w
left join zlecenia z on z.id=w.ZLECENIE
left join wyniki y on y.WYKONANIE=w.id
left join parametry par on par.id=y.parametr
left join STATYWY sta on sta.id=w.STATYW



where w.zlecenie=21000847

-- genORF1ab   22,950
-- genN: 22,126
-- plus kolumna położenie: D937 — 6 — 8
-- genS 

"""

SQL = """
select 
    w.id, z.datarejestracji, w.kodkreskowy, z.kodkreskowy as zl_kodkreskowy, w.ZATWIERDZONE, mat.nazwa as material, 
    pac.imiona, pac.nazwisko, trim(pl.symbol) as plec, pac.pesel, pac.dataurodzenia, pac.adres,
    trim(par.symbol) as parametr, y.WYNIKTEKSTOWY, y.WYNIKLICZBOWY, w.POLOZENIEX, w.POLOZENIEY, sta.NAZWA as statyw

from wykonania w
left join badania bad on bad.id=w.badanie
left join zlecenia z on z.id=w.ZLECENIE
left join wyniki y on y.WYKONANIE=w.id
left join parametry par on par.id=y.parametr
left join STATYWY sta on sta.id=w.STATYW
left join materialy mat on mat.id=w.material
left join pacjenci pac on pac.id=z.pacjent
left join plci pl on pl.id=pac.plec

where w.zatwierdzone between ? and ? and w.badanie in (select id from badania where symbol in ('2019COV', 'VIPCOVP', 'SLCOVP'))
and w.anulowane is null and w.bladwykonania is null
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    lb_task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_lista_wynikow',
        'timeout': 2000,
    }
    report.create_task(lb_task)
    report.save()
    return report


def raport_lista_wynikow(task_params):
    params = task_params['params']
    sql = SQL
    sql_params = [
        params['data'], str(params['data']) + ' 23:59:59'
    ]
    res = []
    wykonania = {}
    noc = NockaDatasource()
    nazwa_lab = ''
    for row in noc.dict_select("select nazwa from ewp_laboratoria where alab_symbol=%s", [task_params['target']]):
        nazwa_lab = row['nazwa']
    with get_centrum_connection(task_params['target']) as conn:
        rows = conn.raport_slownikowy(sql, sql_params)

    for row in rows:
        if row['id'] not in wykonania:
            wyk = {}
            for k, v in row.items():
                if k not in ('parametr', 'wyniktekstowy', 'wynikliczbowy'):
                    wyk[k] = v
            wykonania[row['id']] = wyk
        wynik = row['wynikliczbowy'] or row['wyniktekstowy']
        wykonania[row['id']]['wynik_%s' % row['parametr']] = wynik
    lp = 0
    kody = {}
    for id, wyk in wykonania.items():
        try:
            wyn_orf1 = float(str(wyk['wynik_ORF1']).replace(',', '.'))
        except:
            wyn_orf1 = None
        try:
            wyn_n = float(str(wyk['wynik_N']).replace(',', '.'))
        except:
            wyn_n = None
        try:
            wyn_s = float(str(wyk['wynik_S']).replace(',', '.'))
        except:
            wyn_s = None
        wyn_tekst = wyk.get('wynik_2019COV') or wyk.get('wynik_WYNIK') or wyk.get('wynik_SLCOVP') or wyk.get('wynik_VIPCOVP')
        if (wyn_orf1 is not None and wyn_orf1 < 30) or (wyn_n is not None and wyn_n < 30):
            lp += 1
            wiek = None
            if wyk['dataurodzenia'] is not None:
                wiek = int((wyk['datarejestracji'] - wyk['dataurodzenia']).total_seconds() / (3600 * 24 * 365.25))
            for fld in ('kodkreskowy', 'zl_kodkreskowy'):
                kod = wyk[fld]
                if kod is not None:
                    kod = kod.replace('=', '')[:9]
                    if kod not in kody:
                        kody[kod] = lp
            try:
                polozenie = '%s-%d-%d' % (wyk['statyw'], wyk['polozeniey'], wyk['polozeniex'])
            except:
                polozenie = wyk['statyw']
            wiersz = [
                lp, polozenie, wyk['kodkreskowy'],
                wyn_orf1, wyn_n, wyn_s, wyk['zatwierdzone'], wyk['material'],
                wyk['imiona'], wyk['nazwisko'], wiek, wyk['plec'], wyk['pesel'],
                nazwa_lab, '', '', '', '',
                wyk['adres'], wyn_tekst
            ]
            res.append(wiersz)
    print('Zebrane centrum')
    if len(kody.keys()) > 0:
        chunks = list(divide_chunks(kody.keys(), 200))
        for chunk_no, chunk in enumerate(chunks):
            print('nocka chunk', chunk_no, '/', len(chunks))
            sql = "select id_zlectest, o_pesel, z_nr_probki_laboratorium, z_data_wyniku, id_osoba_ewp, miejscowosc, kod_wojew, kod_powiat from wykonania_ewp where "
            sql_params = []
            where = []
            for kod in chunk:
                where.append('z_nr_probki_laboratorium like %s')
                sql_params.append(kod+'%')
            sql += " or ".join(where)
            for row in noc.dict_select(sql, sql_params):
                kod = row['z_nr_probki_laboratorium'][:9]
                lp = kody[kod]
                wiersz = res[lp-1]
                pesel = wiersz[11]
                if pesel is None or pesel.strip() == row['o_pesel'].strip():
                    wiersz[13] = row['id_osoba_ewp']
                    wiersz[14] = row['id_zlectest']
                    wiersz[15] = '%s%s' % (row['kod_wojew'], row['kod_powiat'])
                    wiersz[16] = row['miejscowosc']
    return {
        'type': 'table',
        'header': 'Lp,Pozycja,Nr próbki,genORF1ab,genN,genS,Data uzyskania wyniku,Rodzaj materiału,Imię,Nazwisko,Wiek,Płeć,PESEL,Nazwa laboratorium,ID osoby z EWP,Nr zlecenia w EWP,Powiat,Miejscowość zamieszkania,Adres,Wynik'.split(','),
        'data': prepare_for_json(res)
    }

"""

Lp.	pozycja na płytce	nr próbki	Wartość Ct wykrywanego genu 1	Wartość CE2:Q33t wykrywanego genu 2
	data uzyskania wyniku	rodzaj materiału	imię	 nazwisko	wiek	płeć	PESEL	
	nazwa laboratorium oryginalnego	ID osoby z EWP	Nr zlecenia w EWP	powiat	miejscowość zamieszkania

"""