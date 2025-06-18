from google.protobuf import symbol_database

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    BadanieSearch, ValidationError
from helpers.validators import validate_symbol
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, list_from_space_separated
from api.common import get_db

MENU_ENTRY = 'Sprzedaż gotówkowa Punkty Pobrań'

BADANIA_LIMIT = [
    'PKLIPID',
    'PKELEKN',
    'PKMOROZ',
    'PKTKRCU',
    'PKTKCIN',
    'PKDIACR',
    'MOCZ+OS',
    'PKTKRCP',
    'LIPID',
    'PKWBAD',
    'WBKZKB',
]

REQUIRE_ROLE = ['C-FIN', 'C-CS', 'PP-S', 'C-PP']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport Ze Sprzedaży Gotówkowej Pakietów w podziale na Pracowników Punkty Pobrań wykonany z baz laboratoryjnych, zawiera tylko płatne gotówką badania/pakiety.\n'
             'Uwaga, w przypadku pakietów nie posiadających cen (sumujących ceny składowych) wartość sprzedaży będzie sumowana po stronie badań, a nie pakietów.\n'
             'Pakiety wyłączone z systemu premiowego dla PP: ' + ', '.join(BADANIA_LIMIT)),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa',default='-7D'),
    DateInput(field='datado', title='Data końcowa',default='-1D'),
    HBox(
        Switch(field="tylkopak", title="Tylko pakiety"),
        Switch(field="bezpak", title="Bez pakietów"),
        Switch(field="bezskl", title="Bez składowych pakietów"),
        Switch(field="limit011023", title="Wyklucz pakiety wyłączone z systemu premiowego", default=True)
        ),
    TextInput(field='badania', title='Tylko wybrane badania/pakiety (symbole oddzielone ,)'),
))

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['tylkopak'] and params['bezpak']:
        raise ValidationError('Tylko pakiety i bez pakietów?')
    if params['badania'] and params['limit011023']:
        raise ValidationError('Odznacz limit na pakiety lub wyczyść wpisane badania')
    if params['bezpak'] and params['limit011023']:
        raise ValidationError('Limit pakietów i bez pakietów ?')
    if params['bezskl'] and params['limit011023']:
        raise ValidationError('Limit pakietów i bez składowych pakietów ?')
    if params['tylkopak'] and params['bezskl']:
        raise ValidationError('Tylko pakiety i bez składowych pakietów?')
    params['badania'] = list_from_space_separated(params['badania'], upper=True, also_comma=True)
    for bad in params['badania']:
        validate_symbol(bad)
    if len(params['laboratoria']) == 0:
        raise ValidationError('Nie wybrano żadnego laboratorium')
    for lab in params['laboratoria']:
        task = {
            'type': 'centrum',
            'priority': 1,
            'params': params,
            'target': lab,
            'function': 'zbierz_lab'
        }
        report.create_task(task)
    report.save()
    return report


def zbierz_lab(task_params):
    params = task_params['params']
    lab = task_params['target']
    wyniki = []
    sql = """
    select 
		pr.NAZWISKO as PRAC, 
		k.symbol as SYMBOL_PP,
		(cast(list(distinct(trim(k.nazwa)), '; ') as varchar(4000))) as PP,
        count(case when EXTRACT(MONTH FROM W.DataRejestracji) = '1' then w.cena end) as M01_count,
		sum(case when EXTRACT(MONTH FROM W.DataRejestracji) = '1' then w.cena end) as M01,
        count(case when EXTRACT(MONTH FROM W.DataRejestracji) = '2' then w.cena end) as M02_count,
		sum(case when EXTRACT(MONTH FROM W.DataRejestracji) = '2' then w.cena end) as M02,
        count(case when EXTRACT(MONTH FROM W.DataRejestracji) = '3' then w.cena end) as M03_count,
		sum(case when EXTRACT(MONTH FROM W.DataRejestracji) = '3' then w.cena end) as M03,
        count(case when EXTRACT(MONTH FROM W.DataRejestracji) = '4' then w.cena end) as M04_count,
		sum(case when EXTRACT(MONTH FROM W.DataRejestracji) = '4' then w.cena end) as M04,
        count(case when EXTRACT(MONTH FROM W.DataRejestracji) = '5' then w.cena end) as M05_count,
		sum(case when EXTRACT(MONTH FROM W.DataRejestracji) = '5' then w.cena end) as M05,
        count(case when EXTRACT(MONTH FROM W.DataRejestracji) = '6' then w.cena end) as M06_count,
		sum(case when EXTRACT(MONTH FROM W.DataRejestracji) = '6' then w.cena end) as M06,
        count(case when EXTRACT(MONTH FROM W.DataRejestracji) = '7' then w.cena end) as M07_count,
		sum(case when EXTRACT(MONTH FROM W.DataRejestracji) = '7' then w.cena end) as M07,
        count(case when EXTRACT(MONTH FROM W.DataRejestracji) = '8' then w.cena end) as M08_count,
		sum(case when EXTRACT(MONTH FROM W.DataRejestracji) = '8' then w.cena end) as M08,
        count(case when EXTRACT(MONTH FROM W.DataRejestracji) = '9' then w.cena end) as M09_count,
		sum(case when EXTRACT(MONTH FROM W.DataRejestracji) = '9' then w.cena end) as M09,
        count(case when EXTRACT(MONTH FROM W.DataRejestracji) = '10' then w.cena end) as M10_count,
		sum(case when EXTRACT(MONTH FROM W.DataRejestracji) = '10' then w.cena end) as M10,
        count(case when EXTRACT(MONTH FROM W.DataRejestracji) = '11' then w.cena end) as M11_count,
		sum(case when EXTRACT(MONTH FROM W.DataRejestracji) = '11' then w.cena end) as M11,
        count(case when EXTRACT(MONTH FROM W.DataRejestracji) = '12' then w.cena end) as M12_count,
		sum(case when EXTRACT(MONTH FROM W.DataRejestracji) = '12' then w.cena end) as M12,
        count(w.cena) as ILOSC,
		sum(w.cena) as SUMA		
	from wykonania w
		left outer join zlecenia z on z.id=w.ZLECENIE
		left outer join PRACOWNICY pr on pr.id=z.PRACOWNIKODREJESTRACJI
		left outer join KANALY k on k.id=pr.KANALINTERNETOWY
		left outer join taryfy t on t.id=w.TARYFA
		left outer join badania b on b.id=w.BADANIE
	where w.DataRejestracji BETWEEN ? and ? and t.SYMBOL = 'X-GOTOW' and w.PLATNE ='1' and pr.id <> 0 and (w.cena <> '0.00' or w.cena is null) $CZY_PAKIETY$ $BADANIA$ $LIMIT011023$ $SKLADOWE$
	group by pr.NAZWISKO, k.symbol
	order by pr.NAZWISKO, k.symbol
    """
    sql_params = [params['dataod'], params['datado']]
    if len(params['badania']) > 0:
        sql = sql.replace('$BADANIA$', ' and b.symbol in (%s) ' % ','.join(["'%s'" % s for s in params['badania']]))
    else:
        sql = sql.replace('$BADANIA$', '')
    if params['tylkopak']:
        sql = sql.replace('$CZY_PAKIETY$', ' and b.pakiet=1')
    elif params['bezpak']:
        sql = sql.replace('$CZY_PAKIETY$', ' and b.pakiet=0')
    else:
        sql = sql.replace('$CZY_PAKIETY$', '')
    if params['bezskl']:
        sql = sql.replace('$SKLADOWE$', ' and w.pakiet is null')
    else:
        sql = sql.replace('$SKLADOWE$', '')
    if params['limit011023']:
        sql = sql.replace('$LIMIT011023$', ' and b.symbol not in (%s) ' % ','.join(["'%s'" % s for s in BADANIA_LIMIT]))
    else:
        sql = sql.replace('$LIMIT011023$', '')
    print(sql)
    print(sql_params)
    with get_centrum_connection(lab) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
        for row in rows:
            wyniki.append(prepare_for_json(row))

    # header= ['Pracownik','Punkt Pobrań']
    # for i in 'Styczeń,Luty,Marzec,Kwiecień,Maj,Czerwiec,Lipiec,Sierpień,Wrzesień,Październik,Listopad,Grudzień,Suma'.split(','):
    #     header.append({'title':i, 'fontstyle' : 'b', 'colspan': 2})

    header = [[
                {'title': 'Pracownik', 'fontstyle' : 'b', 'rowspan':2},
                {'title': 'Symbol PP', 'fontstyle' : 'b', 'rowspan':2},
                {'title': 'Punkt Pobrań', 'fontstyle' : 'b', 'rowspan':2},
                {'title': 'Styczeń', 'fontstyle': 'b', 'colspan': 2}, 
                {'title': 'Luty', 'fontstyle': 'b', 'colspan': 2}, 
                {'title': 'Marzec', 'fontstyle': 'b', 'colspan': 2}, 
                {'title': 'Kwiecień', 'fontstyle': 'b', 'colspan': 2}, 
                {'title': 'Maj', 'fontstyle': 'b', 'colspan': 2}, 
                {'title': 'Czerwiec', 'fontstyle': 'b', 'colspan': 2}, 
                {'title': 'Lipiec', 'fontstyle': 'b', 'colspan': 2}, 
                {'title': 'Sierpień', 'fontstyle': 'b', 'colspan': 2}, 
                {'title': 'Wrzesień', 'fontstyle': 'b', 'colspan': 2},
                {'title': 'Październik', 'fontstyle': 'b', 'colspan': 2}, 
                {'title': 'Listopad', 'fontstyle': 'b', 'colspan': 2}, 
                {'title': 'Grudzień', 'fontstyle': 'b', 'colspan': 2}, 
                {'title': 'Suma', 'fontstyle': 'b', 'colspan': 2}],
                [
                {'title': 'Ilość'}, {'title': 'Wartość'}, 
                {'title': 'Ilość'}, {'title': 'Wartość'}, 
                {'title': 'Ilość'}, {'title': 'Wartość'}, 
                {'title': 'Ilość'}, {'title': 'Wartość'}, 
                {'title': 'Ilość'}, {'title': 'Wartość'},
                {'title': 'Ilość'}, {'title': 'Wartość'}, 
                {'title': 'Ilość'}, {'title': 'Wartość'}, 
                {'title': 'Ilość'}, {'title': 'Wartość'}, 
                {'title': 'Ilość'}, {'title': 'Wartość'}, 
                {'title': 'Ilość'}, {'title': 'Wartość'}, 
                {'title': 'Ilość'}, {'title': 'Wartość'}, 
                {'title': 'Ilość'}, {'title': 'Wartość'}, 
                {'title': 'Ilość'}, {'title': 'Wartość'}]]

    if len(wyniki) == 0:
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
            'data': wyniki
        }
