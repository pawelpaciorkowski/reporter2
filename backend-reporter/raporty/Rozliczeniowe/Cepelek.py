from pprint import pprint

from dialog import Dialog, VBox, InfoText, DateInput, TextInput
from helpers.validators import validate_date_range
from tasks import TaskGroup
from helpers import prepare_for_json, get_centrum_connection
from datasources.snr import SNR

MENU_ENTRY = 'Cepelek'

REQUIRE_ROLE = ['C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Cepelek'),
    # DateInput(field='dataod', title='Data początkowa', default='2024-04-01'),
    # DateInput(field='datado', title='Data końcowa', default='2024-04-04'),
    TextInput(field='nr_rozliczenia', title='Numer rozliczenia', default=''),
))
SQL_SNR = """
select 
	 w.datarejestracji
	, w.pozycjerozliczen
	, w.hs->'numer' as "numer_zlecenia"
	, w.hs->'obcykodkreskowyzlecenia' as "numer_zewnetrzny"
	, w.hs-> 'zleceniodawcazlecenia' as "punk_pobrania_symbol"
	, z.nazwa as "punkt_pobrania_nazwa"
	--grupa punktu ponran symbol
	--grupa punktu ponran nazwa
	, p.symbole
	, p.nazwa
	--grupa platnikow symbol
	--grupa platnikow nazwa
	, w.hs->'pacjencinumer' as " pacjent_id"
	, w.hs->'pacjencinazwisko' as "pacjent_nazwisko"
	, w.hs->'pacjenciimiona' as "pacjent_imiona"
	, w.hs->'pacjencipesel' as "pacjent_pesel"
	, w.hs->'pacjencidataurodzenia' as "pacjent_dataurodzenia"
	, w.hs->'pacjenciplec' as "pacjent_plec"
	--pacjenct historia choroby
	--pacjent status pacjenta symobl
	--pacjent status pacjenta nazwa
	-- lekarz id
	, w.hs->'lekarzeimiona' as "lekarz_imiona"
	, w.hs->'lekarzenazwisko' as "lekarz_nazwisko"
	, w.hs->'lekarzenumer' as "lekarz_numer"
	, w.badanie
	, b.nazwa as "badanie_nazwa"
	-- badanie idc
	-- badanie grupa symbol
	--bdanie grupa nazwa
	, m.symbol
	, m.nazwa as "material_nazwa"
	, w.cenadlaplatnika 
	, w.bezplatne 
	, w.jestpakietem 
	, w.hs->'godzinapobrania' as "godzina_pobrania"
	, w.hs->'kodkreskowy' as "kodkreskowy"
	, w.zlecenie 
	 from rozliczenia r
	left join pozycjerozliczen p2 on p2.rozliczenie = r.id
	left join wykonania w on w.id = p2.wykonanie 
	left join zleceniodawcy z on z.id = w.zleceniodawca 
	left join platnicy p on p.id = w.platnik
	left join badania b on b.symbol = w.badanie 
	left join materialy m on m.symbol = w.material 
where 
w.platnik = 'ALAB.1.820099452'
and r.identyfikatorwrejestrze = %s

"""

CEPELEK_SQL = """
select id, komentarz from zlecenia 
where id in %s
"""

ZLECENIODAWCY_SQL = """
select symbole, nazwa from zleceniodawcy
where symbole like any(%s)
"""

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    # validate_date_range(params['dataod'], params['datado'], 31)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'zbierz_snr'
    }
    report.create_task(task)
    report.save()
    return report


def zbierz_komentarze_centrum(ids):
    with get_centrum_connection('CEPELEK', fresh=True) as conn:
        komentarze_centrum = conn.raport_slownikowy(CEPELEK_SQL, [tuple(ids),])
    komentarze_by_id = {row["id"]: row['komentarz'] for row in komentarze_centrum}
    komentarze = {'%'+r['komentarz']+'%' for r in komentarze_centrum}
    return komentarze, komentarze_by_id

def zbierz_zleceniodawcow_snr(snr, comments):
    data = snr.dict_select(ZLECENIODAWCY_SQL, [comments, ])
    zleceniodwacy = {}
    for row in data:
        for symbol in row['symbole'].split(' '):
            if not zleceniodwacy.get(symbol):
                zleceniodwacy[symbol] = row['nazwa']
    return zleceniodwacy


def dodaj_centrum_id(rows):
    ids = set()
    for row in rows:
        centrum_id = row['zlecenie'].split('^')[0]
        row['centrum_id'] = centrum_id
        ids.add(centrum_id)
    return rows, ids


def dodaj_zleceniodawcow(rows, zleceniodawcy, komentarze_by_id):
    for row in rows:
        row['komentarz'] = komentarze_by_id.get(int(row['centrum_id']))
        row['zleceniodawca_symbol'] = row['komentarz']
        row['zleceniodawca_nazwa'] = zleceniodawcy.get(row['komentarz'])
    return rows


def wynik(cols, res):
    if not res:
        return {
            'type': 'info',
            'title': 'Brak danych',
            'text': 'Brak danych'
        }

    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(res)
    }


def zbierz_snr(task_params):
    params = task_params['params']
    snr = SNR()
    sql = SQL_SNR
    sql_params = []
    sql_params.append(params['nr_rozliczenia'])
    # sql_params += [params['dataod'], params['datado']]
    rows = snr.dict_select(sql, sql_params)
    print(rows, sql_params)
    if not rows:
        return wynik([], [])

    cols = []
    res = []

    rows, ids = dodaj_centrum_id(rows)
    komentarze, komentarze_by_id = zbierz_komentarze_centrum(ids)
    zleceniodawcy = zbierz_zleceniodawcow_snr(snr, list(komentarze))
    rows = dodaj_zleceniodawcow(rows, zleceniodawcy, komentarze_by_id)

    for row in rows:
        if not cols:
            cols = [r for r in row]
        res.append([row[r] for r in row])
    pprint(res[-10:])

    return wynik(cols, res)

