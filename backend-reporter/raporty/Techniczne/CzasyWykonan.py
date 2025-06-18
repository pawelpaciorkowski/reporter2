import datetime

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch
from helpers.validators import validate_date_range, validate_symbol
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, Kalendarz, empty

MENU_ENTRY = 'Średnie czasy wykonania'

REQUIRE_ROLE = ['L-KIER', 'C-FIN', 'C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport ze średniego czasu wykonywania badań w trybie Cito i Rutyna (w minutach). Raport wg dat rozliczeniowych.'),
    DateInput(field='oddnia', title='Data początkowa', default='-7D'),
    DateInput(field='dodnia', title='Data końcowa', default='-1D'),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', pokaz_nieaktywne=True),
    TextInput(field='platnik', title='Pojedynczy płatnik (symbol)'),
    TextInput(field='badanie', title='Pojedyncze badanie (symbol)'),
    Switch(field='pracownie', title='Pracownie zamiast grup pracowni')
))

SQL_WYKONANIA_BADANIA = """
select distinct b.SYMBOL as SYMBOLB, b.NAZWA as NAZWAB, GP.symbol as SYMBOLGPB from wykonania w
	left outer join badania b on b.id = w.badanie
	left outer join Pracownie p on p.id=w.pracownia
	left outer join grupypracowni gp on gp.id=p.grupa
	where w.rozliczone between ? and ? 
	and b.pakiet = 0 and w.BLADWYKONANIA is null and w.ANULOWANE is null
	and (w.prawiewykonane - w.DYSTRYBUCJA) > 0;
"""

SQL_WYKONANIA_BADANIA_PG = """
select distinct b.SYMBOL as SYMBOLB, b.NAZWA as NAZWAB, GP.symbol as SYMBOLGPB from wykonania w
	left outer join badania b on b.id = w.badanie
	left outer join Pracownie p on p.id=w.pracownia
	left outer join grupypracowni gp on gp.id=p.grupa
	where w.rozliczone between %s and %s 
	and b.pakiet = 0 and w.BLADWYKONANIA is null and w.ANULOWANE is null
	and w.prawiewykonane > w.DYSTRYBUCJA;
"""

SQL_WYKONANIA_CITO = """
select b.SYMBOL as SYMBOLC, b.NAZWA as NAZWAC, gp.symbol as SYMBOLGPC, count(*) as LiczbaBadan,
	cast (avg((w.DYSTRYBUCJA - z.GODZINAREJESTRACJI) * 1440) as decimal(18,0)) as CCR,	
	cast (avg((w.PRAWIEWYKONANE - w.DYSTRYBUCJA) * 1440) as decimal(18,0)) as CCW,
	cast (avg((w.WYKONANE - w.DYSTRYBUCJA) * 1440) as decimal(18,0)) as CCA,
	cast (avg((w.ZATWIERDZONE - w.DYSTRYBUCJA) * 1440) as decimal(18,0)) as CCZ,
	cast (avg((w.WYDRUKOWANE  - w.DYSTRYBUCJA) * 1440) as decimal(18,0)) as CCD,
	count (*) as IC
	from wykonania w
	left outer join badania b on b.id = w.badanie
	left outer join zlecenia z on z.id = w.zlecenie
	left outer join typyzlecen t on t.id = z.TYPZLECENIA
	left outer join Pracownie p on p.id=w.pracownia
	left outer join grupypracowni gp on gp.id=p.grupa
	where w.rozliczone between ? and ?
	and b.pakiet = 0 and w.BLADWYKONANIA is null and w.ANULOWANE is null
	and (w.prawiewykonane - w.DYSTRYBUCJA) > 0 and t.SYMBOL = 'C'
	group by  b.SYMBOL, b.NAZWA, gp.symbol;
"""

# cast (((extract(epoch from w.dystrybucja) - extract(epoch from w.GodzinaRejestracji)) / 60) as decimal(18,0)) as rejprzyj,

SQL_WYKONANIA_CITO_PG = """
select b.SYMBOL as SYMBOLC, b.NAZWA as NAZWAC, gp.symbol as SYMBOLGPC, count(*) as LiczbaBadan,
	cast (avg((extract(epoch from w.dystrybucja) - extract(epoch from z.GodzinaRejestracji)) / 60) as decimal(18,0)) as CCR,	
	cast (avg((extract(epoch from w.prawiewykonane) - extract(epoch from w.dystrybucja)) / 60) as decimal(18,0)) as CCW,
	cast (avg((extract(epoch from w.wykonane) - extract(epoch from w.dystrybucja)) / 60) as decimal(18,0)) as CCA,
	cast (avg((extract(epoch from w.zatwierdzone) - extract(epoch from w.dystrybucja)) / 60) as decimal(18,0)) as CCZ,
	cast (avg((extract(epoch from w.wydrukowane) - extract(epoch from w.dystrybucja)) / 60) as decimal(18,0)) as CCD,
	count (*) as IC
	from wykonania w
	left outer join badania b on b.id = w.badanie
	left outer join zlecenia z on z.id = w.zlecenie
	left outer join typyzlecen t on t.id = z.TYPZLECENIA
	left outer join Pracownie p on p.id=w.pracownia
	left outer join grupypracowni gp on gp.id=p.grupa
	where w.rozliczone between %s and %s
	and b.pakiet = 0 and w.BLADWYKONANIA is null and w.ANULOWANE is null
	and w.prawiewykonane > w.DYSTRYBUCJA and t.SYMBOL = 'C'
	group by  b.SYMBOL, b.NAZWA, gp.symbol;
"""

SQL_WYKONANIA_RUTYNA = """
select b.SYMBOL as SYMBOLR, b.NAZWA as NAZWAR, gp.symbol as SYMBOLGPR, count(*) as LiczbaBadan,
	cast (avg((w.DYSTRYBUCJA - z.GODZINAREJESTRACJI) * 1440) as decimal(18,0)) as RCR,	
	cast (avg((w.PRAWIEWYKONANE - w.DYSTRYBUCJA) * 1440) as decimal(18,0)) as RCW,	
	cast (avg((w.WYKONANE - w.DYSTRYBUCJA) * 1440) as decimal(18,0)) as RCA,
	cast (avg((w.ZATWIERDZONE - w.DYSTRYBUCJA) * 1440) as decimal(18,0)) as RCZ,
	cast (avg((w.WYDRUKOWANE  - w.DYSTRYBUCJA) * 1440) as decimal(18,0)) as RCD,
	count (*) as IR
	from wykonania w
	left outer join badania b on b.id = w.badanie
	left outer join zlecenia z on z.id = w.zlecenie
	left outer join typyzlecen t on t.id = z.TYPZLECENIA
	left outer join Pracownie p on p.id=w.pracownia
	left outer join grupypracowni gp on gp.id=p.grupa
	where w.rozliczone between ? and ?
	and b.pakiet = 0 and w.BLADWYKONANIA is null and w.ANULOWANE is null
	and (w.prawiewykonane - w.DYSTRYBUCJA) > 0 and t.SYMBOL not in ('K','KZ','KW','C')
	group by  b.SYMBOL, b.NAZWA, gp.symbol;
"""

SQL_WYKONANIA_RUTYNA_PG = """
select b.SYMBOL as SYMBOLR, b.NAZWA as NAZWAR, gp.symbol as SYMBOLGPR, count(*) as LiczbaBadan,
	cast (avg((extract(epoch from w.dystrybucja) - extract(epoch from z.GodzinaRejestracji)) / 60) as decimal(18,0)) as RCR,	
	cast (avg((extract(epoch from w.prawiewykonane) - extract(epoch from w.dystrybucja)) / 60) as decimal(18,0)) as RCW,
	cast (avg((extract(epoch from w.wykonane) - extract(epoch from w.dystrybucja)) / 60) as decimal(18,0)) as RCA,
	cast (avg((extract(epoch from w.zatwierdzone) - extract(epoch from w.dystrybucja)) / 60) as decimal(18,0)) as RCZ,
	cast (avg((extract(epoch from w.wydrukowane) - extract(epoch from w.dystrybucja)) / 60) as decimal(18,0)) as RCD,
	count (*) as IR
	from wykonania w
	left outer join badania b on b.id = w.badanie
	left outer join zlecenia z on z.id = w.zlecenie
	left outer join typyzlecen t on t.id = z.TYPZLECENIA
	left outer join Pracownie p on p.id=w.pracownia
	left outer join grupypracowni gp on gp.id=p.grupa
	where w.rozliczone between %s and %s
	and b.pakiet = 0 and w.BLADWYKONANIA is null and w.ANULOWANE is null
	and w.prawiewykonane > w.DYSTRYBUCJA and t.SYMBOL not in ('K','KZ','KW','C')
	group by  b.SYMBOL, b.NAZWA, gp.symbol;
"""



def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    print('startReport', __PLUGIN__, params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    validate_date_range(params['oddnia'], params['dodnia'], 31)
    for fld in ('platnik', 'badanie'):
        if not empty(params[fld]):
            params[fld] = params[fld].upper().strip()
            validate_symbol(params[fld])
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
    oddnia = params['oddnia']
    dodnia = params['dodnia']

    badania = {}
    grupy = {}
    grupy_w_badaniach = {}
    srednie_czasy = {}

    sql_wb = SQL_WYKONANIA_BADANIA
    sql_wb_pg = SQL_WYKONANIA_BADANIA_PG
    sql_wc = SQL_WYKONANIA_CITO
    sql_wc_pg = SQL_WYKONANIA_CITO_PG
    sql_wr = SQL_WYKONANIA_RUTYNA
    sql_wr_pg = SQL_WYKONANIA_RUTYNA_PG
    sql_params = [oddnia, dodnia]

    if not empty(params['platnik']):
        sql_params.append(params['platnik'])
        sql_wb = sql_wb.replace('b.pakiet = 0', 'w.platnik=(select id from platnicy where del=0 and symbol=?) and b.pakiet = 0')
        sql_wc = sql_wc.replace('b.pakiet = 0', 'w.platnik=(select id from platnicy where del=0 and symbol=?) and b.pakiet = 0')
        sql_wr = sql_wr.replace('b.pakiet = 0', 'w.platnik=(select id from platnicy where del=0 and symbol=?) and b.pakiet = 0')
        sql_wb_pg = sql_wb_pg.replace('b.pakiet = 0', 'w.platnik=(select id from platnicy where del=0 and symbol=%s) and b.pakiet = 0')
        sql_wc_pg = sql_wc_pg.replace('b.pakiet = 0', 'w.platnik=(select id from platnicy where del=0 and symbol=%s) and b.pakiet = 0')
        sql_wr_pg = sql_wr_pg.replace('b.pakiet = 0', 'w.platnik=(select id from platnicy where del=0 and symbol=%s) and b.pakiet = 0')
    if not empty(params['badanie']):
        sql_params.append(params['badanie'])
        sql_wb = sql_wb.replace('b.pakiet = 0', 'b.symbol=? and b.pakiet = 0')
        sql_wc = sql_wc.replace('b.pakiet = 0', 'b.symbol=? and b.pakiet = 0')
        sql_wr = sql_wr.replace('b.pakiet = 0', 'b.symbol=? and b.pakiet = 0')
        sql_wb_pg = sql_wb_pg.replace('b.pakiet = 0', 'b.symbol=%s and b.pakiet = 0')
        sql_wc_pg = sql_wc_pg.replace('b.pakiet = 0', 'b.symbol=%s and b.pakiet = 0')
        sql_wr_pg = sql_wr_pg.replace('b.pakiet = 0', 'b.symbol=%s and b.pakiet = 0')
    if params['pracownie']:
        sql_wb = sql_wb.replace('GP.symbol as SYMBOLGPB', 'P.symbol as SYMBOLGPB')
        sql_wc = sql_wc.replace('GP.symbol as SYMBOLGPB', 'P.symbol as SYMBOLGPB').replace(', gp.symbol', ', p.symbol')
        sql_wr = sql_wr.replace('GP.symbol as SYMBOLGPB', 'P.symbol as SYMBOLGPB').replace(', gp.symbol', ', p.symbol')
        sql_wb_pg = sql_wb_pg.replace('GP.symbol as SYMBOLGPB', 'P.symbol as SYMBOLGPB')
        sql_wc_pg = sql_wc_pg.replace('GP.symbol as SYMBOLGPB', 'P.symbol as SYMBOLGPB').replace(', gp.symbol', ', p.symbol')
        sql_wr_pg = sql_wr_pg.replace('GP.symbol as SYMBOLGPB', 'P.symbol as SYMBOLGPB').replace(', gp.symbol', ', p.symbol')
    with get_centrum_connection(task_params['target']) as conn:
        for row in conn.raport_slownikowy(sql_wb, sql_params, sql_pg=sql_wb_pg):
            symbol_b = row['symbolb'].strip()
            symbol_gpb = (row['symbolgpb'] or '').strip()
            if symbol_b not in badania:
                badania[symbol_b] = {
                    'symbolb': symbol_b,
                    'nazwab': row['nazwab'].strip()
                }
            if row['symbolgpb'] not in grupy:
                grupy[symbol_gpb] = {
                    'symbolgpb': symbol_gpb
                }
            if symbol_b not in grupy_w_badaniach:
                grupy_w_badaniach[symbol_b] = {}
            if symbol_gpb not in grupy_w_badaniach[symbol_b]:
                grupy_w_badaniach[symbol_b][symbol_gpb] = {
                    'symbolb': symbol_b,
                    'nazwab': row['nazwab'].strip(),
                    'symbolgpb': symbol_gpb
                }

    with get_centrum_connection(task_params['target']) as conn:
        for row in conn.raport_slownikowy(sql_wc, sql_params, sql_pg=sql_wc_pg):
            symbol = row['symbolc'].strip()
            symbol_g = (row['symbolgpc'] or '').strip()
            if symbol not in srednie_czasy:
                srednie_czasy[symbol] = {}
            if symbol_g not in srednie_czasy[symbol]:
                srednie_czasy[symbol][symbol_g] = {}
            for fld in 'ccr ccw cca ccz ccd ic'.split(' '):
                srednie_czasy[symbol][symbol_g][fld] = row[fld]

    with get_centrum_connection(task_params['target']) as conn:
        for row in conn.raport_slownikowy(sql_wr, sql_params, sql_pg=sql_wr_pg):
            symbol = row['symbolr'].strip()
            symbol_g = (row['symbolgpr'] or '').strip()
            if symbol not in srednie_czasy:
                srednie_czasy[symbol] = {}
            if symbol_g not in srednie_czasy[symbol]:
                srednie_czasy[symbol][symbol_g] = {}
            for fld in 'rcr rcw rca rcz rcd ir'.split(' '):
                srednie_czasy[symbol][symbol_g][fld] = row[fld]

    res = []
    # jedna skomplkowana tabelka
    # symbol badania, nazwa badania, grupa pracowni, średni czas rejestracji w trybie cito, średni czas rejestracji w trybie rutynowym, ilość badań
    #                                                od rej   / od dystrybucji
    #                                                do dystr / do wyk / do akcept / do zatw. / do wydruk.

    for badanie in badania:
        for grupa in grupy:
            if grupa in srednie_czasy.get(badanie, {}):
                row = [
                    badanie,
                    badania[badanie]['nazwab'],
                    grupa,
                    srednie_czasy[badanie][grupa].get('ccr', ''),
                    srednie_czasy[badanie][grupa].get('ccw', ''),
                    srednie_czasy[badanie][grupa].get('cca', ''),
                    srednie_czasy[badanie][grupa].get('ccz', ''),
                    srednie_czasy[badanie][grupa].get('ccd', ''),
                    srednie_czasy[badanie][grupa].get('ic', ''),
                    '',
                    srednie_czasy[badanie][grupa].get('rcr', ''),
                    srednie_czasy[badanie][grupa].get('rcw', ''),
                    srednie_czasy[badanie][grupa].get('rca', ''),
                    srednie_czasy[badanie][grupa].get('rcz', ''),
                    srednie_czasy[badanie][grupa].get('rcd', ''),
                    srednie_czasy[badanie][grupa].get('ir', ''),
                ]
                res.append(row)

    header = [
        [{'title': 'Symbol Badania', 'rowspan': 3, 'fontstyle': 'b'},
         {'title': 'Nazwa Badania', 'rowspan': 3, 'fontstyle': 'b'},
         {'title': 'Grupa Pracowni', 'rowspan': 3, 'fontstyle': 'b'},
         {'title': 'Średni czas w trybie CITO', 'colspan': 5, 'fontstyle': 'b'},
         {'title': 'Liczba badań', 'rowspan': 3}, {'rowspan': 3},
         {'title': 'Średni czas w trybie RUTYNOWYM', 'colspan': 5, 'fontstyle': 'b'},
         {'title': 'Liczba badań', 'rowspan': 3}],
        [{'title': 'od rejestracji'}, {'title': 'od dystrybucji', 'colspan': 4}, {'title': 'od rejestracji'},
         {'title': 'od dystrybucji', 'colspan': 4}],
        [{'title': 'do dystrybucji'}, {'title': 'do wykonania'}, {'title': 'do akceptacji'},
         {'title': 'do zatwierdzenia'}, {'title': 'do wydrukowania'},
         {'title': 'do dystrybucji'}, {'title': 'do wykonania'}, {'title': 'do akceptacji'},
         {'title': 'do zatwierdzenia'}, {'title': 'do wydrukowania'}]
    ]
    if params['pracownie']:
        header[0][2]['title'] = 'Pracownia'

    return {
        'results': [{
            'type': 'table',
            'header': header,
            'data': prepare_for_json(res),
        }],
        'actions': ['xlsx', {
                'type': 'pdf',
                'landscape': True,
                'base_font_size': '7pt'
            }],
    }
