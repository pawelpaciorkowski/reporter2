import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, \
    TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch, Select
from helpers.validators import validate_date_range
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, empty
from helpers.connections import get_centra, get_db_engine, \
    get_centrum_connection
import re

MENU_ENTRY = 'Raport z obsługi badań'

CACHE_TIMEOUT = 7200

RE_SYMBOL = re.compile('^[A-Z_0-9]+$')

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Raport z wykonanych badań w laboratoriów."""),
    LabSelector(field='laboratoria', title='Laboratoria', pokaz_nieaktywne=True),
    DateInput(field='dataod', title='Data początkowa', default='-1D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
    TextInput(field='badania', title='Filtr badań (symbole oddzielone spacją)'),
    TextInput(field='platnik', title='Filtr płatnika (symbol)'),
    TextInput(field='zleceniodawca', title='Filtr zleceniodawcy (symbol)'),
    TextInput(field='typzlecenia', title='Filtr typu zlecenia (symbol)'),
    TextInput(field='pracownia', title='Filtr pracowni (symbol)'),
    Switch(field='kanaly', title='Pokaż kanały rejestracji'),
    Switch(field='materialy', title='Pokaż materialy'),
    Switch(field='pracownie', title='Pokaż pracownie'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    if params['dataod'] is None:
        raise ValidationError("Nie podano daty początkowej raportu")
    if params['datado'] is None:
        raise ValidationError("Nie podano daty końcowej raportu")
    if not empty(params['platnik']):
        validate_date_range(params['dataod'], params['datado'], 31)
    else:
        validate_date_range(params['dataod'], params['datado'], 7)
    lab_task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratoria'],
        'params': params,
        'function': 'raport_lab',
    }
    report.create_task(lab_task)
    report.save()
    return report


def get_db(lab):
    centra = get_centra(lab)
    return get_db_engine(centra)


def add_czasy(db, sql):
    sql_czasy_fb = """
    cast (((w.dystrybucja - w.GodzinaRejestracji) * 24 * 60) as decimal(18,0)) as rejprzyj,
    cast (((w.zatwierdzone - w.GodzinaRejestracji) * 24 * 60) as decimal(18,0)) as rejzatw,
    cast (((w.zatwierdzone - w.Godzina) * 24 * 60) as decimal(18,0)) as pobrzatw,
    cast (((w.zatwierdzone - w.Dystrybucja) * 24 * 60) as decimal(18,0)) as przyjzatw,
    cast (((w.wydrukowane - w.GodzinaRejestracji) * 24 * 60) as decimal(18,0)) as rejwydr,
    cast (((w.wydrukowane - w.Godzina) * 24 * 60) as decimal(18,0)) as pobrwydr,
    cast (((w.wydrukowane - w.Dystrybucja) * 24 * 60) as decimal(18,0)) as przyjwydr,
    cast (((w.godzinarejestracji - w.Godzina) * 24 * 60) as decimal(18,0)) as pobrrej
    """
    sql_czasy_postgres = """
    cast (((extract(epoch from w.dystrybucja) - extract(epoch from w.GodzinaRejestracji)) / 60) as decimal(18,0)) as rejprzyj,
    cast (((extract(epoch from w.zatwierdzone) -extract(epoch from w.GodzinaRejestracji)) / 60) as decimal(18,0)) as rejzatw,
    cast (((extract(epoch from w.zatwierdzone) -extract(epoch from w.Godzina)) / 60) as decimal(18,0)) as pobrzatw,
    cast (((extract(epoch from w.zatwierdzone) -extract(epoch from w.Dystrybucja)) / 60) as decimal(18,0)) as przyjzatw,
    cast (((extract(epoch from w.wydrukowane) - extract(epoch from w.GodzinaRejestracji)) / 60) as decimal(18,0)) as rejwydr,
    cast (((extract(epoch from w.wydrukowane) - extract(epoch from w.Godzina)) / 60) as decimal(18,0)) as pobrwydr,
    cast (((extract(epoch from w.wydrukowane) - extract(epoch from w.Dystrybucja)) / 60) as decimal(18,0)) as przyjwydr,
    cast (((extract(epoch from w.GodzinaRejestracji) - extract(epoch from w.Godzina)) / 60) as decimal(18,0)) as pobrrej
    """
    if db == 'postgres':
        return sql % sql_czasy_postgres

    if db == 'firebird':
        return sql % sql_czasy_fb
    raise ValueError('Nieobsługiwany typ bazy')


def raport_lab(task_params):
    params = task_params['params']
    lab = task_params['target']
    db_engine = get_db(task_params['target'])
    wiersze = []
    header = 'Symbol zleceniodawcy,Data rejestracji,Numer zlecenia,Kod kreskowy,Typ zlecenia,Symbol badania,Błąd,Anulowanie,Godz.rej.Badania,Pobranie,Przyjęcie materiału,Data wykonania,Data zatwierdzenia,Data wydrukowania,Rej.-Przyj. (min),Rej.-Zatw. (min),Pobr.-Zatw. (min),Przyj.-Zatw. (min),Rej.-Wydr. (min),Pobr.-Wydr. (min),Przyj.-Wydr. (min),Pobr.-Rej. (min)'.split(',')

    sql = """
        select
            o.SYMBOL,
            z.DATAREJESTRACJI,
            z.NUMER,
            coalesce(w.kodkreskowy, z.kodkreskowy) as kodkreskowy,
            tz.SYMBOL,
            b.SYMBOL,
            bl.symbol,
            pa.symbol,
            w.GodzinaRejestracji,
            w.Godzina,
            w.DYSTRYBUCJA,
            w.WYKONANE,
            w.ZATWIERDZONE,
            w.WYDRUKOWANE,
            %s
        from wykonania w
            left join ZLECENIA z on z.id = w.ZLECENIE
            left join BADANIA b on b.id = w.BADANIE
            left join platnicy pl on pl.id=w.platnik
            left join TYPYZLECEN tz on tz.id = z.TYPZLECENIA
            left join ODDZIALY o on o.id = z.ODDZIAL
            left join bledywykonania bl on bl.id=w.bladwykonania
            left join powodyanulowania pa on pa.id=w.powodanulowania
        where $WHERE$
        order by z.DATAREJESTRACJI, z.NUMER
        """
    sql = add_czasy(db_engine, sql)
    if params['pracownie']:
        sql = sql.replace('o.SYMBOL', 'o.SYMBOL, prac.symbol')
        sql = sql.replace('left join ZLECENIA z on z.id = w.ZLECENIE', '''
            left join ZLECENIA z on z.id = w.ZLECENIE
            left join PRACOWNIE prac on prac.id=w.pracownia
        ''')
        header.insert(1, 'Pracownia')
    if params['kanaly']:
        sql = sql.replace('o.SYMBOL', 'o.SYMBOL, kan.symbol')
        sql = sql.replace('left join ZLECENIA z on z.id = w.ZLECENIE', '''
            left join ZLECENIA z on z.id = w.ZLECENIE
            left join PRACOWNICY PR on pr.id=w.pracownikodrejestracji
            left join kanaly kan on kan.id=pr.kanalinternetowy
        ''')
        header.insert(1, 'Symbol kanału')
    if params['materialy']:
        sql = sql.replace('o.SYMBOL', 'o.SYMBOL, mat.symbol')
        sql = sql.replace('left join ZLECENIA z on z.id = w.ZLECENIE', '''
            left join ZLECENIA z on z.id = w.ZLECENIE
            left join MATERIALY mat on mat.id=w.material
        ''')
        header.insert(1, 'Materiał')
    sql_parameters = [params['dataod'], params['datado']]
    where = ['w.DATAREJESTRACJI between ? and ?', "tz.SYMBOL not in ('K')"]
    if params['typzlecenia'] is not None and params['typzlecenia'] != '':
        where.append('tz.symbol=?')
        sql_parameters.append(params['typzlecenia'])
    if params['platnik'] is not None and params['platnik'] != '':
        where.append('pl.symbol=?')
        sql_parameters.append(params['platnik'])
    if params['zleceniodawca'] is not None and params['zleceniodawca'] != '':
        where.append('o.symbol=?')
        sql_parameters.append(params['zleceniodawca'])
    if params['pracownia'] is not None and params['pracownia'] != '':
        where.append('w.pracownia in (select id from pracownie where symbol=?)')
        sql_parameters.append(params['pracownia'])
    if params['badania'] is not None:
        badania = []
        for w in params['badania'].upper().replace(',', ' ').split(' '):
            w = w.strip()
            if RE_SYMBOL.match(w):
                badania.append(w)
        if len(badania) > 0:
            where.append('b.symbol in (%s)' % ', '.join(["'%s'" % s for s in badania]))
    sql = sql.replace('$WHERE$', ' and '.join(where))
    with get_centrum_connection(lab) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_parameters )

        for row in rows:
            wiersze.append(prepare_for_json(row))

    if len(wiersze) == 0:
        return {
            'title': lab,
            'type': 'info',
            'text': '%s  - Brak danych' % lab
        }
    else:
        return {
            'type': 'table',
            'title': lab,
            'header': header,
            'data': wiersze
        }
