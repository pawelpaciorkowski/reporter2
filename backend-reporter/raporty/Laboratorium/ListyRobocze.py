from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, NumberInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range, validate_symbol
from tasks import TaskGroup, Task
import datetime

MENU_ENTRY = "Listy robocze"

ADD_TO_ROLE = ['L-PRAC']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="""Raport przedstawia listy robocze utworzone w laboratorium w konkretnej pracowni.
Aby zobaczyć spis list istniejących w Centrum: wybierz laboratorium i wpisz symbol pracowni.
Aby zobaczyć szczegóły listy roboczej: wybierz datę wykonania listy i wpisz jej numer. Wskazaną listę można wyeksportować do pliku excel."""),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    TextInput(field="symbol", title="Symbol pracowni"),
    DateInput(field="data", title="Data wykonania", default="T"),
    NumberInput(field='numer', title='Numer listy'),
))

SQL_ALL = """
    SELECT  lr.datawykonania as data_wykonania_listy , lr.NUMER as nr_listy, trim(a.SYMBOL) as aparat, trim(prac.symbol) AS pracownia, count(p.id) as ilosc_pozycji
    FROM LISTYROBOCZE lr
    LEFT JOIN PRACOWNIE prac
    ON PRAC.ID = lr.PRACOWNIA
    LEFT JOIN APARATY a
    ON a.ID = lr.APARAT
    left join wykonanianalistach wl
    on wl.listarobocza = lr.id
    left join pozycjenalistach p
    on p.id = wl.pozycjanaliscie
    WHERE a.symbol NOT LIKE ('X-%') AND prac.SYMBOL = ?
    group by 1,2,3,4
    order by lr.datawykonania, lr.numer
"""

SQL_SINGLE = """
    SELECT p.identyfikator as KOD_PROBKI, trim(p.opis)  AS symbol_badania, trim(a.SYMBOL) as aparat, trim(prac.symbol) AS pracownia ,lr.datawykonania as dataw_wykonania_listy ,  lr.NUMER as nr_listy, p.pozycja as pozycja_na_liscie
    FROM LISTYROBOCZE lr
    LEFT JOIN PRACOWNIE prac
    ON PRAC.ID = lr.PRACOWNIA
    LEFT JOIN APARATY a
    ON a.ID = lr.APARAT
    left join wykonanianalistach wl
    on wl.listarobocza = lr.id
    left join pozycjenalistach p
    on p.id = wl.pozycjanaliscie
    WHERE a.symbol NOT LIKE ('X-%') AND prac.SYMBOL =? and lr.datawykonania = ? and lr.numer = ?
    order by lr.datautworzenia, lr.numer, p.pozycja
"""

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    if params['numer'] is None:
        params['tryb'] = 'all'
    else:
        try:
            params['numer'] = int(params['numer'])
            params['tryb'] = 'single'
        except:
            raise ValidationError("Nieprawidłowy numer")
    validate_symbol(params['symbol'])
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_pojedynczy'
    }
    report.create_task(task)
    report.save()
    return report


def raport_pojedynczy(task_params):
    params = task_params['params']
    if params['tryb'] == 'single':
        sql = SQL_SINGLE
        sql_params = [params['symbol'], params['data'], params['numer']]
    else:
        sql = SQL_ALL
        sql_params = [params['symbol']]
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_params, sql_pg=sql.replace('%', '%%').replace('?', '%s'))
    return [{
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    }]
