import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from helpers.validators import validate_date_range, validate_symbol
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none, list_from_space_separated

MENU_ENTRY = 'Wyniki badań'

REQUIRE_ROLE = ['C-ADM']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Eksport wyników dla wybranych badań/pracowni/zleceniodawców.
        Maksymalnie wyeksportować można 5000 wyników, jeśli nie łapią się wszystkie potrzebne, trzeba zawęzić zakres eksportu.
        W polach filtrujących można wpisać symbole oddzielone spacjami."""),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    TextInput(field='zleceniodawca', title='Zleceniodawcy'),
    TextInput(field='badanie', title='Badania'),
    TextInput(field='parametr', title='Parametry'),
    TextInput(field='pracownia', title='Pracownie'),
    TextInput(field='aparat', title='Aparaty'),
    HBox(
        VBox(
            DateInput(field='dataod', title='Data początkowa', default='-1D'),
            DateInput(field='datado', title='Data końcowa', default='-1D'),
        ),
        Radio(field="rodzajdat", values={
            'rej': 'Rejestracji',
            'zatw': 'Zatwierdzenia',
        }, default='rej'),
    ),
))

SQL = """
select first 5000 z.datarejestracji as "Data rej.", z.numer as "Numer", z.KodKreskowy as "Kod Kreskowy", 
pp.symbol as "Zleceniodawca", (P.Nazwisko || ' ' || P.Imiona) as "Pacjent", p.DATAURODZENIA as "Data urodzenia", p.PESEL as "PESEL",
trim(plc.symbol) as "Płeć", wiekpacjenta(z.datarejestracji, p.dataurodzenia, null, null) as "Wiek",
B.Symbol as "Badanie",
pa.symbol as "Parametr",
WY.wyniktekstowy as "Wynik",
WY.opis as "Opis wyniku",
AP.Symbol as "Aparat",
PZ.Nazwisko as "Pracownik zatw.",
W.DC as "Ost. zmiana bad.",
W.Zatwierdzone as "Data zatw."
$KOLEJNOSC_SELECTA$
left join Oddzialy PP on PP.id = Z.oddzial
left join Platnicy PL on PL.id = W.Platnik
left join wyniki WY on WY.wykonanie = W.id
left join badania B on B.id = W.Badanie
left join parametry PA on pa.id =wy.PARAMETR
left join pacjenci P on P.id = Z.pacjent
left join plci plc on plc.id=p.plec
left join aparaty ap on ap.id = w.aparat
left join pracownicy pz on pz.id = w.pracownikodzatwierdzenia
where
$WHERE$ and W.BladWykonania is null and W.anulowane is null and wy.WYNIKTEKSTOWY is not null and wy.ukryty = '0' and z.PACJENT is not null
order by z.datarejestracji, z.numer, b.kolejnosc, pa.kolejnosc
"""

SQL_KOLEJNOSC_WYKONANIA = " from Wykonania W left join Zlecenia Z on Z.id = W.zlecenie "
SQL_KOLEJNOSC_ZLECENIA = " from Zlecenia Z left join Wykonania W on Z.id = W.zlecenie "


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 31)
    ile_filtrow = 0
    for fld in ('zleceniodawca', 'badanie', 'parametr', 'pracownia', 'aparat'):
        params[fld] = list_from_space_separated(params[fld], upper=True, also_comma=True, also_semicolon=True,
                                                unique=True)
        for sym in params[fld]:
            validate_symbol(sym)
        if len(params[fld]) > 0:
            ile_filtrow += 1
        if len(params[fld]) > 30:
            raise ValidationError("Podaj max 30 symboli do filtrowania.")
    if ile_filtrow == 0:
        raise ValidationError("Nie podano żadnego warunku filtrowania")
    if len(params['badanie']) == 0 and len(params['parametr']) > 0:
        raise ValidationError("Nie można filtrować po parametrach bez filtrowania po badaniach!")
    lb_task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_lista_wynikow',
    }
    report.create_task(lb_task)
    report.save()
    return report


def raport_lista_wynikow(task_params):
    res = []
    params = task_params['params']
    sql = SQL
    where = []
    sql_params = []
    if params['rodzajdat'] == 'rej':
        sql = SQL.replace('$KOLEJNOSC_SELECTA$', SQL_KOLEJNOSC_ZLECENIA)
        where.append('z.datarejestracji between ? and ?')
        sql_params += [params['dataod'], params['datado']]
    elif params['rodzajdat'] == 'zatw':
        sql = SQL.replace('$KOLEJNOSC_SELECTA$', SQL_KOLEJNOSC_WYKONANIA)
        where.append('w.zatwierdzone between ? and ?')
        sql_params += [params['dataod'], str(params['datado']) + ' 23:59:59']
    else:
        raise ValidationError(params['rodzajdat'])
    with get_centrum_connection(task_params['target']) as conn:
        if len(params['zleceniodawca']) > 0:
            cols, rows = conn.raport_z_kolumnami("select id from oddzialy where symbol in  (%s)" % ', '.join("'%s'" % s for s in params['zleceniodawca']))
            if len(rows) == 0:
                return {
                    'type': 'info',
                    'text': 'Nie znaleziono żadnego zleceniodawcy'
                }
            where.append('z.oddzial in (%s)' % ','.join([str(row[0]) for row in rows]))
        if len(params['pracownia']) > 0:
            cols, rows = conn.raport_z_kolumnami("select id from pracownie where symbol in  (%s)" % ', '.join("'%s'" % s for s in params['pracownia']))
            if len(rows) == 0:
                return {
                    'type': 'info',
                    'text': 'Nie znaleziono żadnej pracowni'
                }
            where.append('w.pracownia in (%s)' % ','.join([str(row[0]) for row in rows]))
        if len(params['aparat']) > 0:
            cols, rows = conn.raport_z_kolumnami("select id from aparaty where symbol in  (%s)" % ', '.join("'%s'" % s for s in params['aparat']))
            if len(rows) == 0:
                return {
                    'type': 'info',
                    'text': 'Nie znaleziono żadnego aparatu'
                }
            where.append('w.aparat in (%s)' % ','.join([str(row[0]) for row in rows]))
        if len(params['badanie']) > 0:
            cols, rows = conn.raport_z_kolumnami("select id from badania where symbol in (%s)" % ', '.join("'%s'" % s for s in params['badanie']))
            if len(rows) == 0:
                return {
                    'type': 'info',
                    'text': 'Nie znaleziono żadnego badania'
                }
            id_badan = ','.join([str(row[0]) for row in rows])
            where.append('w.badanie in (%s)' % id_badan)
            if len(params['parametr']) > 0:
                cols, rows = conn.raport_z_kolumnami(
                    "select id from parametry where metoda in (select id from metody where badanie in (%s)) and symbol in (%s)" % (id_badan, ', '.join("'%s'" % s for s in params['parametr'])))
                if len(rows) == 0:
                    return {
                        'type': 'info',
                        'text': 'Nie znaleziono żadnego parametru'
                    }
                where.append('wy.parametr in (%s)' % ','.join([str(row[0]) for row in rows]))
        sql = sql.replace('$WHERE$', ' and '.join(where))
        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
        res.append({
            'type': 'table',
            'header': cols,
            'data': prepare_for_json(rows)
        })
        return res
