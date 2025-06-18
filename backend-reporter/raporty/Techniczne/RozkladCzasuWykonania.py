import datetime

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch
from helpers.helpers import group_by_first_cols
from helpers.strings import db_escape_string
from helpers.validators import validate_date_range, validate_symbol
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, Kalendarz, empty, list_from_space_separated

MENU_ENTRY = 'Rozkład czasu wykonania'

REQUIRE_ROLE = ['L-KIER', 'C-FIN', 'C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='''Rozkład czasu wykonania badań wg podanych kryteriów. Raport wg dat rejestracji.
                Jeśli badania mają podane czasy maksymalne to będzie też przedstawiony rozkład względem tego czasu.
                Wykresy rozkładów będą generowane tylko przy braku podziałów.'''),
    DateInput(field='oddnia', title='Data początkowa', default='-7D'),
    DateInput(field='dodnia', title='Data końcowa', default='-1D'),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    TextInput(field='f_badania', title='Filtr badań (symbole)'),
    TextInput(field='f_metody', title='Filtr metod (symbole)'),
    TextInput(field='f_pracownie', title='Filtr pracowni (symbole)'),
    TextInput(field='f_typyzlecen', title='Filtr typy zleceń (symbole)'),
    Switch(field='p_badania', title='Podział na badania'),
    Switch(field='p_metody', title='Podział na metody'),
    Switch(field='p_pracownie', title='Podział na pracownie'),
    Switch(field='p_typyzlecen', title='Podział na typ zlecenia'),

))

SQL_WEW = """
    select pr.symbol as pracownia, m.symbol as metoda, bad.symbol as badanie, tz.symbol as typzlecenia,
        bad.czasmaksymalny, datediff(hour, w.dystrybucja, w.zatwierdzone) as czaswykonania, 
        case when bad.czasmaksymalny is not null and bad.czasmaksymalny > 0 then
            cast((100 * datediff(hour, w.dystrybucja, w.zatwierdzone) / bad.czasmaksymalny) as int)
        else null end as procczasmaks,
        count(w.id) as ilosc
    from wykonania w 
    left join pracownie pr on pr.id=w.pracownia
    left join metody m on m.id=w.metoda
    left join badania bad on bad.id=w.badanie
    left join zlecenia zl on zl.id=w.zlecenie
    left join typyzlecen tz on tz.id=zl.typzlecenia
    where w.zatwierdzone is not null 
    and w.zatwierdzone between ? and ?
    and w.dystrybucja is not null and w.bladwykonania is not null
    and $WARUNEK_WEW$
    group by 1,2,3,4,5,6,7
"""


def transform_to_pg(sql):
    sql = sql.replace('datediff(hour, w.dystrybucja, w.zatwierdzone)',
                      'floor((EXTRACT(EPOCH FROM w.zatwierdzone) - EXTRACT(EPOCH FROM w.dystrybucja))/3600)')
    sql = sql.replace('?', '%s')
    return sql


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    validate_date_range(params['oddnia'], params['dodnia'], 31)
    ile_filtrow = 0
    for fld in ('f_badania', 'f_metody', 'f_pracownie', 'f_typyzlecen'):
        params[fld] = list_from_space_separated(params[fld], upper=True, also_comma=True, also_semicolon=True,
                                                unique=True)
        for sym in params[fld]:
            validate_symbol(sym)
            ile_filtrow += 1
    if ile_filtrow == 0:
        raise ValidationError("Ustaw jakiś filtr")
    if ile_filtrow > 50:
        raise ValidationError("Za dużo filtrów")
    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_wykonania'
    }
    report.create_task(task)
    report.save()
    return report


def raport_wykonania(task_params):
    params = task_params['params']
    lab = task_params['target']
    res = []
    oddnia = params['oddnia']
    dodnia = params['dodnia']
    warunki_wew = []
    for param, col in {
        'f_badania': 'bad.symbol',
        'f_metody': 'm.symbol',
        'f_pracownie': 'pr.symbol',
        'f_typyzlecen': 'tz.symbol',
    }.items():
        if params[param] is not None and len(params[param]) > 0:
            warunki_wew.append('%s in (%s)' % (
                col, ', '.join(["'%s'" % db_escape_string(sym) for sym in params[param]])
            ))
    sql_wew = SQL_WEW.replace('$WARUNEK_WEW$', ' and '.join(warunki_wew))
    sql_params = [params['oddnia'], params['dodnia']]
    kolumny_zew = []
    ile_podzialow = 0
    order_by = []
    for param, col in {
        'p_badania': 'a.badanie',
        'p_metody': 'a.metoda',
        'p_pracownie': 'a.pracownia',
        'p_typyzlecen': 'a.typzlecenia as "typ zlecenia"',
    }.items():
        if params[param]:
            ile_podzialow += 1
            kolumny_zew.append(col)
            order_by.append(str(ile_podzialow))
    order_by.append('a.czaswykonania')
    kolumny_zew += ['a.czasmaksymalny as "Czas maksymalny"', 'a.czaswykonania as "Czas wykonania"',
                    'a.procczasmaks as "proc czasu maks"', 'sum(a.ilosc) as ilosc']
    sql = "select %s from (%s) a %s order by %s"
    sql %= (', '.join(kolumny_zew), sql_wew, group_by_first_cols(len(kolumny_zew)-1), ', '.join(order_by))
    sql_pg = transform_to_pg(sql)
    with get_centrum_connection(lab, fresh=True) as conn:
        print(sql_pg)
        cols, rows = conn.raport_z_kolumnami(sql, sql_params, sql_pg=sql_pg)

    if ile_podzialow == 0:
        data_czasy = []
        data_procenty = []
        for row in sorted(rows, key=lambda r: r[1]):
            data_czasy.append([row[1], row[3]])
        for row in sorted([row for row in rows if row[2] is not None], key=lambda r: r[2]):
            data_procenty.append([row[2], row[3]])
        res.append({
            'type': 'diagram',
            'subtype': 'bars',
            'title': 'Rozkład czasu wykonania',
            'x_axis_title': 'Czas wykonania [godz]',
            'y_axis_title': 'Ilość badań',
            'data': data_czasy,
        })
        res.append({
            'type': 'diagram',
            'subtype': 'bars',
            'title': 'Rozkład czasu wykonania względem czasu maksymalnego',
            'x_axis_title': 'Czas wykonania jako % czasu maks',
            'y_axis_title': 'Ilość badań',
            'data': data_procenty,
        })
    res.append({
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows),
    })
    return res