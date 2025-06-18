import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from helpers.validators import validate_date_range, validate_symbol
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none, empty, \
    list_from_space_separated

MENU_ENTRY = 'Wyniki dla zleceniodawcy'

REQUIRE_ROLE = ['C-ADM']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Eksport wyników jednego badania dla pojedynczego zleceniodawcy - wg dat zatwierdzenia."""),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    TextInput(field='platnik', title='Płatnik (symbol)'),
    TextInput(field='zleceniodawca', title='Zleceniodawca (symbol)'),
    TextInput(field='badania', title='Badania (symbole oddzielone spacją)'),
    TextInput(field='parametr', title='Parametr (symbol, opcjonalnie)'),
    DateInput(field='dataod', title='Data początkowa', default='-1D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),

))

SQL = """
select z.datarejestracji, z.KodKreskowy as "Kod Kreskowy", pp.symbol as "Zleceniodawca",
(P.Nazwisko || ' ' || P.Imiona) as "Pacjent", p.DATAURODZENIA as "Data urodzenia", p.PESEL as "PESEL",
W.Godzina as "Pobrane",
W.Zatwierdzone as "Zatwierdzone",
B.Symbol as "Badanie",
pa.symbol as "Parametr",
WY.wyniktekstowy as "Wynik",
WY.opis as "Opis wyniku"
from Wykonania W
join Zlecenia Z on Z.id = W.zlecenie
join Oddzialy PP on PP.id = Z.oddzial
join Platnicy PL on PL.id = W.Platnik
join wyniki WY on WY.wykonanie = W.id
join badania B on B.id = W.Badanie
join parametry PA on pa.id =wy.PARAMETR
left outer join pacjenci P on P.id = Z.pacjent
where
w.zatwierdzone between ? and ? and pp.symbol=? and z.PACJENT is not null
and B.symbol in ($BADANIA$) and W.BladWykonania is null and W.anulowane is null and wy.WYNIKTEKSTOWY is not null and wy.ukryty = '0'
order by z.datarejestracji
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if empty(params['platnik']) and empty(params['zleceniodawca']):
        raise ValidationError("Podaj symbol zleceniodawcy lub płatnika")
    if not empty(params['zleceniodawca']) and not empty(params['platnik']):
        raise ValidationError("Podaj albo symbol płatnika albo zleceniodawcy!")
    params['badania'] = list_from_space_separated(params['badania'], upper=True, also_comma=True, unique=True)
    if len(params['badania']) == 0:
        raise ValidationError("Podaj symbol badania")
    if len(params['badania']) > 50:
        raise ValidationError("Max 50 badań")
    if len(params['badania']) == 1 and not empty(params['zleceniodawca']):
        validate_date_range(params['dataod'], params['datado'], 366)
    else:
        validate_date_range(params['dataod'], params['datado'], 31)
    for bad in params['badania']:
        validate_symbol(bad)
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
    params = task_params['params']
    sql = SQL.replace('$BADANIA$', ','.join("'%s'" % bad for bad in params['badania']))
    if empty(params['zleceniodawca']):
        sql = sql.replace('pp.symbol=?', 'w.platnik=(select id from platnicy where symbol=? and del=0)')
        sql_params = [
            params['dataod'], str(params['datado']) + ' 23:59:59',
            params['platnik']
        ]
    else:
        sql_params = [
            params['dataod'], str(params['datado']) + ' 23:59:59',
            params['zleceniodawca']
        ]
    if params.get('parametr') not in (None, ''):
        sql = sql.replace('W.BladWykonania is null', 'PA.symbol = ? and W.BladWykonania is null')
        sql_params.append(params['parametr'])
    with get_centrum_connection(task_params['target']) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
        return {
            'type': 'table',
            'header': cols,
            'data': prepare_for_json(rows)
        }
