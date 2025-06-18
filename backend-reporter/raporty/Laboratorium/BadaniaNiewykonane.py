import time

import config
from datasources.postgres import PostgresDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError, Switch
from helpers.strings import db_escape_string
from helpers.validators import validate_date_range, validate_symbol
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty, odpiotrkuj, list_from_space_separated

MENU_ENTRY = 'Badania niewykonane'

ADD_TO_ROLE = ['L-PRAC']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Zestawienie badań niewykonanych. Ze względów wydajnościowych zostanie zwróconych maksymalnie 5000 pozycji,
        w przypadku dużej ilości badań zastosuj filtry. W pola filtrów można wpisywać symbole, oddzielone spacjami lub przecinkami.
        Domyślnie raport tylko dla próbek po dystrybucji - wg dat przyjęcia."""),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', pokaz_nieaktywne=True),
    TextInput(field='badania', title='Tylko badania'),
    TextInput(field='pracownie', title='Tylko pracownie'),
    TextInput(field='aparaty', title='Tylko aparaty'),
    TextInput(field='platnicy', title='Tylko płatnicy'),
    TextInput(field='zleceniodawcy', title='Tylko zleceniodawcy'),
    DateInput(field='dataod', title='Data od', default='-31D'),
    DateInput(field='datado', title='Data do', default='T'),
    Switch(field='przeterminowane', title='Tylko przeterminowane'),
    Switch(field='wgrejestracji', title='Wg dat rejestracji, a nie dystrybucji'),
    Switch(field='nieprzyjete', title='Uwzględnij nieprzyjęte'),
    Switch(field='pacjent', title='Pokaż dane pacjenta'),
    Switch(field='notatki', title='Miejsce na notatki (PDF)'),
))

WARUNEK_PRZETERMINOWANIA_FB = 'W.DataRejestracji + (cast(bad.czasmaksymalny as decimal(18,6))/cast(24 as decimal(18,6))) < \'NOW\''
WARUNEK_PRZETERMINOWANIA_PG = 'W.DataRejestracji + cast((cast(bad.czasmaksymalny as decimal(18,6))/cast(24 as decimal(18,6))) as integer) < \'NOW\''

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError('Nie wybrano laboratorium')
    if not params['wgrejestracji'] and params['nieprzyjete']:
        raise ValidationError('Nie można zrobić raportu wg dat przyjęcia materiału z uwzględnieniem nieprzyjętych.')
    validate_date_range(params['dataod'], params['datado'], 180)
    for fld in ('badania', 'pracownie', 'aparaty', 'platnicy', 'zleceniodawcy'):
        if not empty(fld):
            params[fld] = list_from_space_separated(params[fld], upper=True, also_comma=True, also_semicolon=True, unique=True)
            for symbol in params[fld]:
                validate_symbol(symbol)
        else:
            params[fld] = None
    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_lab'
    }
    report.create_task(task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']
    system = task_params['target']
    sql_params = [params['dataod'], params['datado']]
    columns = ['coalesce(w.kodkreskowy, z.kodkreskowy) as kodkreskowy',
               'coalesce(w.godzinarejestracji, cast(w.datarejestracji as timestamp)) as godzinarejestracji',
               'w.dystrybucja',
               'z.numer', 'z.datarejestracji',
               'trim(pl.symbol) as platnik', 'trim(o.symbol) as zleceniodawca',
               'trim(bad.symbol) as badanie', 'trim(mat.symbol) as material',
               'trim(pr.symbol) as pracownia', 'trim(ap.symbol) as aparat',
               '''
               case when w.statyw is not null then
                   trim(st.symbol) || '-' || cast(w.polozeniey as varchar(10)) || '-' || cast(w.polozeniex as varchar(10))
               else null end as polozenie
               ''',
               'bad.Czasmaksymalny']
    tables = ['wykonania w', 'zlecenia z on z.id=w.zlecenie', 'platnicy pl on pl.id=z.platnik', 'oddzialy o on o.id=z.oddzial',
              'badania bad on bad.id=w.badanie', 'materialy mat on mat.id=w.material',
              'pracownie pr on pr.id=w.pracownia', 'aparaty ap on ap.id=w.aparat',
              'statywy st on st.id=w.statyw']
    if params['pacjent']:
        columns.append('''
            trim(coalesce(pac.nazwisko, '') || ' ' || coalesce(pac.imiona, '') || ' ' || coalesce(pac.pesel, '')) as pacjent
        ''')
        tables.append('pacjenci pac on pac.id=z.pacjent')
    where = ['W.pozamknieciu = 0', 'w.zatwierdzone is null', 'w.anulowane is null']
    if params['wgrejestracji']:
        where.append('w.godzinarejestracji between ? and ?')
    else:
        where.append('w.dystrybucja between ? and ?')
    if not params['nieprzyjete']:
        where.append('w.dystrybucja is not null')
    if params['przeterminowane']:
        where.append('''
            bad.czasmaksymalny is not null and $WARUNEK_PRZETERMINOWANIA$
        ''')
    if params['badania'] is not None and len(params['badania']) > 0:
        where.append('bad.symbol in (%s)' % ', '.join(["'%s'" % db_escape_string(symbol) for symbol in params['badania']]))
    if params['pracownie'] is not None and len(params['pracownie']) > 0:
        where.append('pr.symbol in (%s)' % ', '.join(["'%s'" % db_escape_string(symbol) for symbol in params['pracownie']]))
    if params['aparaty'] is not None and len(params['aparaty']) > 0:
        where.append('ap.symbol in (%s)' % ', '.join(["'%s'" % db_escape_string(symbol) for symbol in params['aparaty']]))
    if params['platnicy'] is not None and len(params['platnicy']) > 0:
        where.append('pl.symbol in (%s)' % ', '.join(["'%s'" % db_escape_string(symbol) for symbol in params['platnicy']]))
    if params['zleceniodawcy'] is not None and len(params['zleceniodawcy']) > 0:
        where.append('o.symbol in (%s)' % ', '.join(["'%s'" % db_escape_string(symbol) for symbol in params['zleceniodawcy']]))
    sql = 'select ' + ', '.join(columns) + ' from ' + ' left join '.join(tables)
    sql += ' where ' + ' and '.join(where) + ' order by w.id limit 5000'
    sql_pg = sql.replace('?', '%s')
    sql = sql.replace('$WARUNEK_PRZETERMINOWANIA$', WARUNEK_PRZETERMINOWANIA_FB)
    sql_pg = sql_pg.replace('$WARUNEK_PRZETERMINOWANIA$', WARUNEK_PRZETERMINOWANIA_PG)
    sql = sql.replace('limit 5000', '').replace('select ', 'select first 5000 ')
    print(sql)
    with get_centrum_connection(system) as conn:
        rows = conn.raport_slownikowy(sql, sql_params, sql_pg=sql_pg)
    res = []
    if len(rows) == 5000:
        res.append({
            'type': 'warning', 'text': 'Znaleziono powyżej 5000 pasujących badań - użyj filtrów.'
        })
    header = ['Kod kreskowy', 'Zlecenie', 'Płatnik/zleceniodawca', 'Przyjęte']
    if params['pacjent']:
        header.append('Pacjent')
    header += ['Badanie: Materiał', 'Pracownia / aparat', 'Położenie']
    if params['notatki']:
        header.append('Notatki')
    res_rows = []
    kody_bez_polozenia = []
    for row in rows:
        if row['polozenie'] is None and row['kodkreskowy'] is not None and len(row['kodkreskowy']) > 9:
            kod = row['kodkreskowy'].strip().replace('=', '')
            if kod not in kody_bez_polozenia:
                kody_bez_polozenia.append(kod)
    dodatkowe_polozenie = {}
    db_sortery = PostgresDatasource(dsn=config.Config.DATABASE_REPUBLIKA.replace('dbname=republika', 'dbname=logstream'))
    if len(kody_bez_polozenia) > 0:
        for row in db_sortery.dict_select("""
            select pl.lab, pl.name as sorter, bo.barcode as kod, bo.description as zdarzenie
            from barcode_occurrences bo
            left join places pl on pl.id=bo.place_id
            where bo.barcode in %s
            order by bo.ts
        """, [tuple(kody_bez_polozenia)]):
            kod = row['kod']
            opis = '%s %s - %s' % (row['lab'], row['sorter'], row['zdarzenie'])
            if kod not in dodatkowe_polozenie:
                dodatkowe_polozenie[kod] = []
            dodatkowe_polozenie[kod].append(opis)
            if len(dodatkowe_polozenie[kod]) > 2:
                dodatkowe_polozenie[kod] = dodatkowe_polozenie[kod][-2:]
    for row in rows:
        kod = row['kodkreskowy'].strip().replace('=', '')
        res_row = [
            row['kodkreskowy'], '%s / %s' % (str(row['datarejestracji']), str(row['numer'])),
            '%s / %s' % (str(row['platnik']), str(row['zleceniodawca'])),
            row['dystrybucja'],
        ]
        if params['pacjent']:
            res_row.append(row['pacjent'])
        res_row.append('%s: %s' % (str(row['badanie']), str(row['material'])))
        res_row.append('%s / %s' % (str(row['pracownia']), str(row['aparat'])))
        if row['polozenie'] is not None:
            polozenie = row['polozenie']
        else:
            polozenie = dodatkowe_polozenie.get(kod)
            if polozenie is not None:
                polozenie = '; '.join(polozenie)
        res_row.append(polozenie)
        if params['notatki']:
            res_row.append('')
        res_rows.append(res_row)
    res.append({
        'type': 'table',
        'header': header,
        'data': prepare_for_json(res_rows)
    })
    return res
# APARAT

# Kod Paskowy/ Kod Kreskowy
#
#
# Data
#
#
# Numer Dzienny
#
#
# Zleceniodawca
#
#
# Pacjent
#
#
# Materiał
#
#
# Badanie
#
#
# Położenie
# notatki

