from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError
from helpers.validators import validate_date_range, validate_symbol
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty

MENU_ENTRY = 'Średnie czasy Cito'

REQUIRE_ROLE = ['L-KIER', 'C-FIN', 'C-ROZL']

BADANIA_CITO = ['DD-IL', 'D-DIMER', 'MORF', 'PT', 'APTT', 'FIBR', 'GLU', 'KREA', 'NA', 'K', 'CL', 'AMYL', 'CRP-IL',
                'CK-MB', 'TROP-I', 'TROP-T', 'RKZ', 'RKZ-PAK', 'TSH', 'ETYL', 'GRUPA', 'PR-ZGOD', 'B-HCG', 'NARKOT',
                'PMR', 'MOCZ']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport ze średniego czasu wykonania 21 podstawowych badań w trybie Cito dla Szpitala. Brane są pod uwagę następujące badania: %s. Raport wg dat rejestracji.' % ', '.join(
            BADANIA_CITO)),
    DateInput(field='oddnia', title='Data początkowa', default='-7D'),
    DateInput(field='dodnia', title='Data końcowa', default='-1D'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    TextInput(field='platnik', title='Pojedynczy płatnik (symbol)')
))

SQL_CITO_WYBRANE = """
SELECT
			W.DataRejestracji AS DATA,
			Z.Numer AS NUMER,
			B.Symbol AS BADANIE,
			case when w.godzinarejestracji > w.DYSTRYBUCJA then cast (((w.zatwierdzone - w.godzinarejestracji) * 1440) as decimal(18,0)) else cast (((w.zatwierdzone - w.DYSTRYBUCJA) * 1440) as decimal(18,0))  end AS DOZATW,
			case when w.godzinarejestracji > w.DYSTRYBUCJA then cast (((w.Wydrukowane - w.godzinarejestracji) * 1440) as decimal(18,0)) else cast (((w.Wydrukowane - w.DYSTRYBUCJA) * 1440) as decimal(18,0))  end AS DOWYDR,
			w.zatwierdzone as ZATWIERDZONE
		FROM Wykonania W
			LEFT OUTER JOIN Zlecenia Z ON Z.ID = W.Zlecenie
			LEFT OUTER JOIN TypyZlecen T ON T.ID = Z.TypZlecenia
			LEFT OUTER JOIN Badania B ON B.ID = W.Badanie
			left outer join platnicy pl on pl.id=w.platnik
			left outer join grupyplatnikow gp on gp.id=pl.grupa
		WHERE
			W.DataRejestracji between ? and ? and w.BladWykonania is null and w.anulowane is null and
			not exists (select w1.id from wykonania w1 where w1.zlecenie=W.zlecenie and w1.badanie=w.badanie and w1.material=w.material and w1.powtorka='1' and w1.id<>w.id ) and
			b.symbol in ('DD-IL', 'D-DIMER', 'MORF', 'PT', 'APTT', 'FIBR', 'GLU', 'KREA', 'NA', 'K', 'CL', 'AMYL', 'CRP-IL', 'CK-MB', 'TROP-I', 'TROP-T', 'RKZ', 'RKZ-PAK', 'TSH', 'ETYL', 'GRUPA', 'PR-ZGOD', 'B-HCG', 'NARKOT', 'PMR', 'MOCZ')
			and W.Zatwierdzone IS NOT NULL and gp.symbol like '%SZP%' and t.symbol = 'C'
		ORDER BY W.DataRejestracji, Z.Numer, B.Symbol; 
"""

SQL_CITO_WYBRANE_PG = """
SELECT
			W.DataRejestracji AS DATA,
			Z.Numer AS NUMER,
			B.Symbol AS BADANIE,
			case when w.godzinarejestracji > w.DYSTRYBUCJA then cast  (((extract(epoch from w.zatwierdzone) - extract(epoch from w.GodzinaRejestracji)) / 60) as decimal(18,0)) else cast  (((extract(epoch from w.zatwierdzone) - extract(epoch from w.dystrybucja)) / 60) as decimal(18,0))  end AS DOZATW,
			case when w.godzinarejestracji > w.DYSTRYBUCJA then cast  (((extract(epoch from w.wydrukowane) - extract(epoch from w.GodzinaRejestracji)) / 60) as decimal(18,0)) else cast  (((extract(epoch from w.wydrukowane) - extract(epoch from w.dystrybucja)) / 60) as decimal(18,0))  end AS DOWYDR,
			w.zatwierdzone as ZATWIERDZONE
		FROM Wykonania W
			LEFT OUTER JOIN Zlecenia Z ON Z.ID = W.Zlecenie
			LEFT OUTER JOIN TypyZlecen T ON T.ID = Z.TypZlecenia
			LEFT OUTER JOIN Badania B ON B.ID = W.Badanie
			left outer join platnicy pl on pl.id=w.platnik
			left outer join grupyplatnikow gp on gp.id=pl.grupa
		WHERE
			W.DataRejestracji between %s and %s and w.BladWykonania is null and w.anulowane is null and
			not exists (select w1.id from wykonania w1 where w1.zlecenie=W.zlecenie and w1.badanie=w.badanie and w1.material=w.material and w1.powtorka='1' and w1.id<>w.id ) and
			b.symbol in ('DD-IL', 'D-DIMER', 'MORF', 'PT', 'APTT', 'FIBR', 'GLU', 'KREA', 'NA', 'K', 'CL', 'AMYL', 'CRP-IL', 'CK-MB', 'TROP-I', 'TROP-T', 'RKZ', 'RKZ-PAK', 'TSH', 'ETYL', 'GRUPA', 'PR-ZGOD', 'B-HCG', 'NARKOT', 'PMR', 'MOCZ')
			and W.Zatwierdzone IS NOT NULL and gp.symbol like '%%SZP%%' and t.symbol = 'C'
		ORDER BY W.DataRejestracji, Z.Numer, B.Symbol; 
"""

SQL_CITO_WSZYSTKIE = """
SELECT
    count (w.id) as WSZYSTKIE
FROM Wykonania W
    LEFT OUTER JOIN Zlecenia Z ON Z.ID = W.Zlecenie
    LEFT OUTER JOIN TypyZlecen T ON T.ID = Z.TypZlecenia
    left outer join platnicy pl on pl.id=w.platnik
    left outer join grupyplatnikow gp on gp.id=pl.grupa
WHERE
    W.DataRejestracji between ? and ? and w.BladWykonania is null and w.anulowane is null and
    not exists (select w1.id from wykonania w1 where w1.DataRejestracji = 'YESTERDAY' and w1.zlecenie=W.zlecenie and w1.badanie=w.badanie and w1.material=w.material and w1.powtorka='1' and w1.id<>w.id ) and
    W.Zatwierdzone IS NOT NULL and gp.symbol like '%SZP%' and t.symbol = 'C';
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    print('startReport', __PLUGIN__, params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    if not empty(params['platnik']):
        validate_symbol(params['platnik'])
    validate_date_range(params['oddnia'], params['dodnia'], 31)
    for lab in params['laboratoria']:
        lab_task = {
            'type': 'centrum',
            'priority': 0,
            'target': lab,
            'params': params,
            'function': 'raport_cito_lab',
        }
        report.create_task(lab_task)
    report.save()
    return report


def raport_cito_lab(task_params):
    params = task_params['params']
    oddnia = params['oddnia']
    dodnia = params['dodnia']
    sql_params = [oddnia, dodnia]

    ilosci = {'WS': 0, 'T60': 0, 'T90': 0, 'T120': 0, 'Tmax': 0, 'Wszystkie': 0}
    powyzej120 = []
    rozklad = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    with get_centrum_connection(task_params['target']) as conn:
        sql = SQL_CITO_WYBRANE
        sql_pg = SQL_CITO_WYBRANE_PG
        sql_wszystkie = SQL_CITO_WSZYSTKIE

        if not empty(params['platnik']):
            sql = sql.replace('w.BladWykonania is null', 'w.BladWykonania is null and pl.symbol=?')
            sql_pg = sql_pg.replace('w.BladWykonania is null', 'w.BladWykonania is null and pl.symbol=%s')
            sql_wszystkie = sql_wszystkie.replace('w.BladWykonania is null', 'w.BladWykonania is null and pl.symbol=?')
            sql_params.append(params['platnik'])

        for row in conn.raport_slownikowy(sql, sql_params, sql_pg=sql_pg):
            dozatw = row['dozatw']
            ilosci['WS'] += 1
            if dozatw <= 60:
                ilosci['T60'] += 1
            elif 60 < dozatw <= 90:
                ilosci['T90'] += 1
            elif 90 < dozatw <= 120:
                ilosci['T120'] += 1
            else:
                ilosci['Tmax'] += 1
                powyzej120.append(row)
            if row['zatwierdzone'] is not None:
                godzina = int(row['zatwierdzone'].strftime('%H'))
                rozklad[godzina] += 1

    with get_centrum_connection(task_params['target']) as conn:
        for row in conn.raport_slownikowy(sql_wszystkie, sql_params):
            ilosci['Wszystkie'] = row['wszystkie']

    """
    wybrane: data, numer, badanie, dozatw, dowydr
    wszystkie: wszystkie
    """

    return {
        'ilosci': ilosci,
        'powyzej120': powyzej120,
        'rozklad': rozklad,
    }


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    results = []
    errors = []
    dane_tabelka = []
    dane_powyzej120 = []
    dane_diagram = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            ilosci = result['ilosci']
            srednie = {}
            srednie['WS'] = '%.2f' % (ilosci['WS'] / ilosci['Wszystkie'] * 100)
            for col in ('T60', 'T90', 'T120', 'Tmax'):
                srednie[col] = '%.2f' % (ilosci[col] / ilosci['WS'] * 100)
            dane_tabelka.append([
                params['target'],
                ilosci['Wszystkie'],
                ilosci['WS'], srednie['WS'],
                ilosci['T60'], srednie['T60'],
                ilosci['T90'], srednie['T90'],
                ilosci['T120'], srednie['T120'],
                ilosci['Tmax'], srednie['Tmax'],
            ])
            for wiersz in result['powyzej120']:
                dane_powyzej120.append([
                    params['target'],
                    wiersz['data'], wiersz['numer'],
                    wiersz['badanie'], wiersz['dozatw'], wiersz['dowydr']
                ])
            for i in range(len(result['rozklad'])):
                dane_diagram[i] += result['rozklad'][i]
        if status == 'failed':
            errors.append('%s - błąd połączenia' % params['target'])
    results.append({
        'type': 'table',
        'header': [
            [
                {'title': 'Laboratorium', 'rowspan': 2, 'fontstyle': 'b'},
                {'title': 'Razem Cito', 'rowspan': 2, 'fontstyle': 'b'},
                {'title': '21 parametrów', 'rowspan': 2, 'fontstyle': 'b'},
                {'title': '%21 w cito', 'rowspan': 2, 'fontstyle': 'b'},
                {'title': 'do 60 min.', 'colspan': 2}, {'title': '60 - 90 min.', 'colspan': 2},
                {'title': '90 - 120 min.', 'colspan': 2}, {'title': 'pow. 120 min.', 'colspan': 2}, ],
            ['ilość', '%', 'ilość', '%', 'ilość', '%', 'ilość', '%'],
        ],
        'data': prepare_for_json(dane_tabelka)
    })
    if task_group.progress == 1:
        results.append({
            'type': 'diagram',
            'subtype': 'bars',
            'title': 'Rozkład badań zatwierdzonych w poszczególnych godzinach',
            'x_axis_title': 'Godzina',
            'y_axis_title': 'Ilość zatwierdzonych badań',
            'data': [[i, v] for i, v in enumerate(dane_diagram)]
        })
    results.append({
        'type': 'table',
        'title': 'Wykaz badań, których czas wykonania przekroczył 120 minut',
        'header': 'Laboratorium,Data rejestracji,Numer,Badanie,Czas do zatw.,Czas do wydr.'.split(','),
        'data': prepare_for_json(dane_powyzej120),
    })
    return {
        'errors': errors,
        'results': results,
        'actions': ['xlsx', 'pdf'],
        'progress': task_group.progress,
    }
