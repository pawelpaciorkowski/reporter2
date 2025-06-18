from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, NumberInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json, list_from_space_separated
from helpers.validators import validate_date_range, validate_symbol
from tasks import TaskGroup, Task
import datetime

SQL = """
    select z.datarejestracji as data, z.numer, coalesce(w.kodkreskowy, z.kodkreskowy) as "kod kreskowy",
        trim(pl.symbol) as platnik, trim(o.symbol) as zleceniodawca, o.nazwa as "zleceniodawca nazwa", 
        coalesce(l.nazwisko, '') || ' ' || coalesce (l.imiona, '') || ' ' || coalesce(l.telefony, '') as lekarz,
        coalesce(pac.nazwisko, '') || ' ' || coalesce (pac.imiona, '') || ' ' || coalesce(pac.pesel, '') || ' tel. ' || coalesce(pac.telefon , '') as pacjent,
        bad.symbol as badanie, bad.nazwa as "badanie nazwa",
        par.symbol as parametr, 
        w.zatwierdzone,
        y.wyniktekstowy as wynik, y.opis as "wynik opis", 
        case when y.normatekstowa='tabelka' then '' else y.normatekstowa end as norma,
        substring(z.opis from position('$&' in z.opis)+2) as "notatka wewnętrzna"
    from 
    wykonania w
    left join wyniki y on y.wykonanie=w.id 
    left join zlecenia z on z.id=w.zlecenie
    left join oddzialy o on o.id=z.oddzial 
    left join lekarze l on l.id=z.lekarz
    left join pacjenci pac on pac.id=z.pacjent
    left join badania bad on bad.id=w.badanie
    left join parametry par on par.id=y.parametr 
    left join typyzlecen tz on tz.id=z.typzlecenia
    left join platnicy pl on pl.id=z.platnik
    where 
    w.zatwierdzone between ? and ?
    and y.flagakrytycznych is not null and y.flagakrytycznych  != 0 and y.ukryty=0
    and (tz.symbol not in ('K', 'KZ', 'KW') or tz.id is null)
    and (pl.id is null or pl.symbol not like '%KONT%')
    order by w.zatwierdzone 
"""

ZAGRAZAJACE_ZYCIU = [
    'UREA', 'TROPIHS', 'GLU', 'NA', 'K', 'CL', 'P', 'CA', 'GLUKO-M', 'KREA', 'AMYL', 'ALT', 'AST', 'LIPAZA', 'CK',
    'BIL-T', 'MORF.WBC', 'MORF.RBC', 'MORF.HGB', 'MORF.HCT', 'MORF.PLT', 'FIBR', 'APTT', 'PT', 'D-DIMER', 'WIT-DTO',
    'DIGOKS', 'LIT', 'WALPRO', 'TSH'
]

ZAGRAZAJACE_BADANIA = []
ZAGRAZAJACE_PARAMETRY = {}
OPIS_ZAGRAZAJACE = None

if len(ZAGRAZAJACE_BADANIA) == 0:
    for v in ZAGRAZAJACE_ZYCIU:
        if '.' in v:
            [bad, par] = v.split('.')
        else:
            bad = v
            par = None
        if bad not in ZAGRAZAJACE_BADANIA:
            ZAGRAZAJACE_BADANIA.append(bad)
        if par is not None:
            if bad not in ZAGRAZAJACE_PARAMETRY:
                ZAGRAZAJACE_PARAMETRY[bad] = []
            ZAGRAZAJACE_PARAMETRY[bad].append(par)
    opis = []
    for bad in ZAGRAZAJACE_BADANIA:
        bad_opis = bad
        if bad in ZAGRAZAJACE_PARAMETRY:
            bad_opis += ' (tylko parametry %s)' % ', '.join(ZAGRAZAJACE_PARAMETRY[bad])
        opis.append(bad_opis)
    OPIS_ZAGRAZAJACE = ', '.join(opis)

MENU_ENTRY = "Wyniki krytyczne"

ADD_TO_ROLE = ['L-PRAC']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text=f"""Raport przedstawia wyniki krytyczne zatwierdzone w podanym przedziale dat, z notatkami wewnętrznymi.
        Domyślnie raport obejmuje tylko wyniki zagrażające życiu - badania {OPIS_ZAGRAZAJACE}.
        Aby dostać listę wszystkich wyników krytycznych należy zaznaczyć "wszystkie parametry".
        W pole "Symbole VIP" można wpisać symbole płatników lub zleceniodawców, którzy mają być traktowani priorytetowo (na górze tabelki)"""),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    Select(field='stan', values={'zatw': 'Zatwierdzone', 'wyk': 'Wykonane, niezatwierdzone'}, default='simple'),
    DateInput(field='dataod', title='Od', default='-1D'),
    DateInput(field='datado', title='Do', default='T'),
    Switch(field='wszystkie', title='Wszystkie parametry (domyślnie tylko zagrażające życiu)'),
    TextInput(field='kliencivip', title='Symbole VIP', textarea=True),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)
    params['kliencivip'] = list_from_space_separated(params['kliencivip'], upper=True, also_comma=True,
                                                     also_newline=True, also_semicolon=True, unique=True)
    for symbol in params['kliencivip']:
        validate_symbol(symbol)
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
    sql = SQL
    if not params['wszystkie']:
        sql = sql.replace('and y.ukryty=0', 'and y.ukryty=0 and bad.symbol in (%s)' % ','.join(
            [f"'{bad}'" for bad in ZAGRAZAJACE_BADANIA]
        ))
    if params['stan'] == 'wyk':
        sql = sql.replace('w.zatwierdzone between', 'w.zatwierdzone is null and w.prawiewykonane between')
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, [params['dataod'], params['datado'] + ' 23:59:59'])
    res_rows1 = []
    res_rows2 = []
    for row in rows:
        row = list(row)
        if not params['wszystkie']:
            bad = row[8].strip()
            par = row[10].strip()
            if bad in ZAGRAZAJACE_PARAMETRY:
                if par not in ZAGRAZAJACE_PARAMETRY[bad]:
                    continue
        if row[3] in params['kliencivip']:
            row[3] = {'value': row[3], 'fontstyle': 'b'}
            res_rows1.append(row)
        elif row[4] in params['kliencivip']:
            row[4] = {'value': row[4], 'fontstyle': 'b'}
            res_rows1.append(row)
        else:
            res_rows2.append(row)
    return [{
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(res_rows1 + res_rows2)
    }]
