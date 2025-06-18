import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from outlib.xlsx_standalone import RaportXlsxStandalone
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none, list_from_space_separated
from helpers.validators import validate_symbol

MENU_ENTRY = 'Normy Liczbowe'

SQL_PG = """
    select 
    trim(b.symbol) as badanie,
    trim(m.symbol) as metoda,
    trim(ap.symbol) as aparat,
    trim(par.symbol) as parametr,
    par.wyrazenie,
	split_part(par.format, ' ', 2) as jednostka,
    n.opis,
	n.krytycznyponizej as "Krytyczny poniżej", n.zakresod as "Od", 
	n.zakresdo as "Do", n.krytycznypowyzej as "Krytyczny powyżej",
	case when n.dowolnywiek=1 then 'dowolny'
	else (
		case 
			when wiekod is not null and wiekdo is not null then cast(wiekod as varchar(16)) || '-' || cast(wiekdo as varchar(16))
			when wiekod is null and wiekdo is not null then '< ' || cast(wiekdo as varchar(16))
			when wiekod is not null and wiekdo is null then '> ' || cast(wiekod as varchar(16))
		else '???' end 
		|| 
		case 
			when jednostkawieku=1 then ' lat'
			when jednostkawieku=2 then ' mies.'
			when jednostkawieku=3 then ' dni'
        else '???' end
 	) end as "Wiek",
	case when n.dowolnaplec=1 then 'dowolna'
	else pl.symbol end as "Płeć",
	case when n.dowolnytypnormy=1 then 'dowolny'
	else tn.symbol end as "Typ normy",
	case when n.dowolnymaterial=1 then 'dowolny'
	else mat.symbol end as "Materiał"

    from normy n

    left join parametry par on par.id=n.PARAMETR
    left join metody m on m.id=par.METODA
    left join aparaty ap on ap.id=m.APARAT
    left join badania b on b.id=m.badanie
	left join plci pl on pl.id=n.plec
	left join typynorm tn on tn.id=n.typnormy
	left join materialy mat on mat.id=n.material

    where $WARUNEK$
    and (n.zakresod is not null or n.zakresdo is not null or n.krytycznyponizej is not null or n.krytycznypowyzej is not null)
    and n.del=0 and par.del=0 and m.del=0 and b.del=0 and coalesce(m.nieczynna, 0)=0
    order by 1,2,3,4,5,n.dowolnywiek, n.dowolnaplec, n.dowolnytypnormy, n.dowolnymaterial
"""

SQL_FB = SQL_PG.replace("split_part(par.format, ' ', 2) as jednostka", "(SUBSTRING(par.format FROM (POSITION(' ' IN par.format)+1))) as jednostka")

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="""Normy liczbowe (zakresy referencyjne) dla aktywnych metod. Wpisz symbole badań/metod/aparatów oddzielone spacjami, dla których mają być pobrane dane."""),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria', pracownie_domyslne=True),
    TextInput(field='badania', title='Badania'),
    TextInput(field='metody', title='Metody'),
    TextInput(field='aparaty', title='Aparaty'),
    Switch(field='zakladki', title='Badania w zakładkach (excel)'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    for fld in ('badania', 'metody', 'aparaty'):
        params[fld] = list_from_space_separated(params[fld], upper=True, also_comma=True, also_semicolon=True,
                                                      unique=True)
        for sym in params[fld]:
            validate_symbol(sym)
    if len(params['badania']) + len(params['metody']) + len(params['aparaty']) == 0:
        raise ValidationError("Nie podano żadnego warunku filtrowania")
    for lab in params['laboratoria']:
        lab_task = {
            'type': 'centrum',
            'priority': 0,
            'timeout': 60,
            'target': lab,
            'params': params,
            'function': 'raport_lab',
        }
        report.create_task(lab_task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']
    warunki = []
    for tab, fld in [
        ('badania', 'b.symbol'),
        ('metody', 'm.symbol'),
        ('aparaty', 'ap.symbol')
    ]:
        if len(params[tab]) > 0:
            warunki.append('%s in (%s)' % (fld, ','.join(["'%s'" % sym for sym in params[tab]])))
    sql = SQL_FB.replace('$WARUNEK$', ' and '.join(warunki))
    sql_pg = SQL_PG.replace('$WARUNEK$', ' and '.join(warunki))
    with get_centrum_connection(task_params['target'], load_config=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_pg=sql_pg)
    res = []
    for row in rows:
        res.append([task_params['target']] + row)
    return res


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': ['xlsx']
    }
    wiersze = []
    wiersze_badan = {}
    bledy_polaczen = []
    excel = False
    for job_id, params, status, result in task_group.get_tasks_results():
        ile_filtrow = len(params['params']['badania']) + len(params['params']['metody']) + len(params['params']['aparaty'])
        if params['params']['zakladki'] or ile_filtrow > 3:
            excel = True
        if status == 'finished' and result is not None:
            wiersze += result
            for wiersz in result:
                bad = wiersz[1]
                if bad not in wiersze_badan:
                    wiersze_badan[bad] = []
                wiersze_badan[bad].append([wiersz[0]] + wiersz[2:])
        if status == 'failed':
            bledy_polaczen.append(params['target'])
    if len(bledy_polaczen) > 0:
        res['errors'].append('%s - błąd połączenia' % ', '.join(bledy_polaczen))
    if not excel:
        res['results'].append({
            'type': 'table',
            'header': 'Laboratorium,Badanie,Metoda,Aparat,Parametr,Wyrażenie,Jednostka,Opis,Krytyczny poniżej,Od,Do,Krytyczny powyżej,Wiek,Płeć,Typ normy,Materiał'.split(','),
            'data': prepare_for_json(wiersze)
        })
    if excel and task_group.progress == 1.0:
        xlsx = RaportXlsxStandalone()
        if params['params']['zakladki']:
            for badanie, wiersze in wiersze_badan.items():
                xlsx.add_sheet(badanie)
                xlsx.set_columns('Laboratorium,Metoda,Aparat,Parametr,Jednostka,Opis,Krytyczny poniżej,Od,Do,Krytyczny powyżej,Wiek,Płeć,Typ normy,Materiał'.split(','))
                xlsx.add_rows(wiersze)
        else:
            xlsx.set_columns('Laboratorium,Badanie,Metoda,Aparat,Parametr,Jednostka,Opis,Krytyczny poniżej,Od,Do,Krytyczny powyżej,Wiek,Płeć,Typ normy,Materiał'.split(','))
            xlsx.add_rows(prepare_for_json(wiersze))
        res['results'].append({
            'type': 'download',
            'content': base64.b64encode(xlsx.render_as_bytes()).decode(),
            'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'filename': 'normy_liczbowe_%s.xlsx' % datetime.datetime.now().strftime('%Y-%m-%d'),
        })
    res['progress'] = task_group.progress
    return res
