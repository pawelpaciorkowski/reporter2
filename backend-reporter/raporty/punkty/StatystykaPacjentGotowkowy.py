from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection
from api.common import get_db
from helpers.validators import validate_date_range

MENU_ENTRY = 'Analiza struktury Klientów gotówkowych'
# REQUIRE_ROLE = ['C-FIN', 'C-CS', 'PP-S', 'C-PP']
REQUIRE_ROLE = 'ADMIN' # TODO: usunąć po implementacji

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Analiza struktury Klientów płacących gotówką lub za pomocą Sklepu Internetowego'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError('Nie wybrano żadnego laboratorium')
    # validate_date_range(params['dataod'], params['datado'], max_days=90)
    for lab in params['laboratoria']:
        task = {
            'type': 'centrum',
            'priority': 1,
            'params': params,
            'target': lab,
            'function': 'zbierz_lab'
        }
        report.create_task(task)
        task = {
            'type': 'centrum',
            'priority': 1,
            'params': params,
            'target': lab,
            'function': 'zbierz_lab2'
        }
        report.create_task(task)
        task = {
            'type': 'centrum',
            'priority': 1,
            'params': params,
            'target': lab,
            'function': 'zbierz_lab3'
        }
        report.create_task(task)
    report.save()
    return report

def zbierz_lab(task_params):
    params = task_params['params']
    lab = task_params['target']
    sql = """
        SELECT
            o.SYMBOL as ODS,
            o.nazwa as ODN,
            pl.nazwa as PLEC,
            gw.id,
            GW.Nazwa AS GW,
            count (DISTINCT(z.id)) AS ILOSC,
            count (w.id) as ILBAD,
            case when o.symbol like '%-SKIN%' then null else sum (w.CENA) end as WART
	    FROM  zlecenia z
            left outer join WYKONANIA w on z.ID= w.ZLECENIE
            LEFT OUTER JOIN Pacjenci Pa ON Pa.ID = Z.Pacjent
            LEFT OUTER JOIN Plci Pl ON Pl.ID = Pa.Plec
            LEFT OUTER JOIN GrupyWiekowe GW ON GW.ID = GrupaWiekowa2(Z.DataRejestracji, Pa.DataUrodzenia, Pa.RokUrodzenia)
            LEFT OUTER JOIN Platnicy Pla on z.platnik=pla.id
            left outer join ODDZIALY o on o.id=z.ODDZIAL		
            left outer joiN badania b on b.ID =w.BADANIE
            left outer joiN GRUPYBADAN gb on gb.id = b.GRUPA    
    	WHERE
	    	Z.DataRejestracji BETWEEN ? AND ? AND Z.Anulowane IS NULL 
            and (Pla.symbol like '%GOTOW%' or pla.symbol like '%-SKIN%') 
            and (GB.Symbol <> 'TECHNIC' or GB.symbol is null)
    	GROUP BY gw.id, Pl.nazwa, gw.nazwa, o.SYMBOL, o.NAZWA
    	ORDER BY o.symbol, gw.id, Pl.nazwa; """
    wiersze = []
    tabPlec = []
    tabPP = []
    tabGrupyWiekowe = []
    linia = []
    wynik = []
    with get_centrum_connection(lab) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, [params['dataod'], params['datado']])
        for row in rows:
            wiersze.append(prepare_for_json(row))
            if prepare_for_json(row[2]) not in tabPlec:
                tabPlec.append(prepare_for_json(row[2]))
            if next((i for i in tabPP if i['symbol'] == prepare_for_json(row[0])), None) == None:
                tabPP.append({'symbol':prepare_for_json(row[0]),'nazwa':prepare_for_json(row[1])})
            if next((i for i in tabGrupyWiekowe if i['id'] == prepare_for_json(row[3])), None) == None:
                tabGrupyWiekowe.append({'id':prepare_for_json(row[3]),'nazwa':prepare_for_json(row[4])})
        tabGrupyWiekowe = sorted(tabGrupyWiekowe, key=lambda k: (k['id'] or 0))
        for oddzial in tabPP:
            for grupa in tabGrupyWiekowe:
                linia = []
                linia.append(oddzial['symbol'])
                linia.append(oddzial['nazwa'])
                linia.append(grupa['nazwa'])
                for plec in tabPlec:
                    ilosczlecen = ''
                    iloscbadan = ''
                    wartosc = ''
                    for wiersz in wiersze:
                        if wiersz[0] == oddzial['symbol'] and wiersz[4] == grupa['nazwa'] and wiersz[2] == plec:
                            ilosczlecen = wiersz[5]
                            iloscbadan = wiersz[6]
                            wartosc = wiersz[7]
                    linia.append(ilosczlecen)
                    linia.append(iloscbadan)
                    linia.append(wartosc)
                wynik.append(linia)
    if len(wynik) == 0:
        return {
            'title': lab,
            'type': 'info',
            'text': '%s  - Brak danych' % lab
        }
    else:
        return {
            'type': 'table',
            'title': 'Analiza zleconych usług oraz ich wartości w poszczególnych grupach wiekowych\njako ilość badań liczone są zarówno pakiety jak i składniki pakietów.',
            'header': [
                        [
                            {'title':'Symbol Punktu Pobrań','fontstyle': 'b','rowspan':2},
                            {'title':'Nazwa Punktu Pobrań','fontstyle': 'b','rowspan':2},
                            {'title':'Grupa Wiekowa','fontstyle': 'b','rowspan':2},
                            {'title': 'Kobieta','fontstyle': 'b', 'rowspan':1, 'colspan': 3},
                            {'title': 'Mężczyzna','fontstyle': 'b', 'rowspan':1, 'colspan': 3}
                        ],
                        ['Ilość zleceń','Ilość badań','Wartość','Ilość zleceń','Ilość badań','Wartość']
                    ],
            # 'header': 'Symbol Punktu Pobrań	Nazwa Punktu Pobrań	Grupa Wiekowa'.split(','),
            'data': wynik
        }

def zbierz_lab2(task_params):
    params = task_params['params']
    lab = task_params['target']
    sql = """
        select
            sum (case when ilosc = 1 then 1 end) as W1,
            sum (case when ilosc = 2 then 1 end) as W2,
            sum (case when ilosc = 3 then 1 end)  as W3,
            sum (case when ilosc = 4 then 1 end)  as W4,
            sum (case when ilosc = 5 then 1 end)  as W5,
            sum (case when ilosc = 6 then 1 end)  as W6,
            sum (case when ilosc = 7 then 1 end)  as W7,
            sum (case when ilosc = 8 then 1 end)  as W8,
            sum (case when ilosc > 8 then 1 end)  as WW8,
            count (ilosc) as WSUMIE
        from (
            select count(*) as ilosc, zap2.pesel as pesel from (
                SELECT PA1.PESEL as Pesel,
                    z1.DATAREJESTRACJI
                FROM  zlecenia z1
                    LEFT OUTER JOIN Pacjenci Pa1 ON Pa1.ID = Z1.Pacjent
                    LEFT OUTER JOIN Platnicy Pla1 on z1.platnik=pla1.id
                WHERE
                    Z1.DataRejestracji BETWEEN  ? and ? AND Z1.Anulowane IS NULL and (Pla1.symbol like '%GOTOW%' or pla1.symbol like '%-SKIN%') and pa1.PESEL is not null
                GROUP BY pa1.pesel,z1.DATAREJESTRACJI
            ) as zap2
            group by zap2.pesel
        );
    """
    wiersze = []

    with get_centrum_connection(lab) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, [params['dataod'], params['datado']])
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
            'title': 'Analiza ile razy dany pacjent był u nas na pobraniu w okresie od %s do %s . Pacjenci bez peselu nie są uwzględniani' % (params['dataod'], params['datado']),
            'header': [[{'title': 'Ilość wizyt', 'fontstyle' : 'b', 'rowspan':1, 'colspan': 10},],['jedna','dwie','trzy','cztery','pięć','sześć','siedem','osiem','więcej niż osiem','w sumie']],
            'data': wiersze
        }

def zbierz_lab3(task_params):
    params = task_params['params']
    lab = task_params['target']
    sql = """
        SELECT
            EXTRACT(YEAR FROM Z.DataRejestracji) as ROK,
            EXTRACT(MONTH FROM Z.DataRejestracji) as MIESIAC,
            b.symbol AS BS,
            b.nazwa AS BN,
            count (w.id) AS ILOSC
    	FROM  zlecenia z
		    left outer join wykonania w on w.zlecenie=z.id
		    LEFT OUTER JOIN Platnicy Pla on z.platnik=pla.id
		    left outer join badania b on b.id=w.badanie
		    left outer join grupybadan gb on gb.id=b.grupa
	    WHERE
            Z.DataRejestracji BETWEEN ? and ? AND Z.Anulowane IS NULL 
            and (Pla.symbol like '%GOTOW%' or pla.symbol like '%-SKIN%') 
            and w.anulowane is null and w.bladwykonania is null and (gb.symbol <> 'TECHNIC' or gb.symbol is null)
        GROUP BY EXTRACT(YEAR FROM Z.DataRejestracji) , EXTRACT(MONTH FROM Z.DataRejestracji), b.symbol, b.nazwa
        ORDER BY EXTRACT(YEAR FROM Z.DataRejestracji), EXTRACT(MONTH FROM Z.DataRejestracji), b.symbol 
    """
    wiersze = []
    miesiace = []
    badania = []
    wynik = []

    with get_centrum_connection(lab) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, [params['dataod'], params['datado']])
        for row in rows:
            wiersze.append(prepare_for_json(row))
            if next((i for i in miesiace if i['rok'] == prepare_for_json(row[0]) and i['miesiac'] == prepare_for_json(row[1])), None) == None:
                miesiace.append({'rok':prepare_for_json(row[0]),'miesiac':prepare_for_json(row[1]), 'symbol': str(prepare_for_json(row[0]))+'-'+str(prepare_for_json(row[1])) })
            if next((i for i in badania if i['symbol'] == prepare_for_json(row[2])), None) == None:
                badania.append({'symbol':prepare_for_json(row[2]),'nazwa':prepare_for_json(row[3])})
            badania = sorted(badania, key=lambda k: k['symbol'])
            miesiace = sorted(miesiace, key=lambda k: k['symbol'])

    for badanie in badania:
        linia = []
        linia.append(badanie['symbol'])
        linia.append(badanie['nazwa'])
        for miesiac in miesiace:
            wartosc = ''
            for wiersz in wiersze:
                if wiersz[0]==miesiac['rok'] and wiersz[1] == miesiac['miesiac'] and wiersz[2]== badanie['symbol']:
                    wartosc = wiersz[4]
            linia.append(wartosc)
        wynik.append(linia)
    header = ['Symbol','Nazwa badania']
    for i in miesiace:
            header.append(i['symbol'])
    print(linia)
    # print(badania)
    if len(wynik) == 0:
        return {
            'title': lab,
            'type': 'info',
            'text': '%s  - Brak danych' % lab
        }
    else:
        return {
            'type': 'table',
            'title': 'Analiza jakie badania kupowali pacjenci w poszczególnych miesiącach zadanego okresu od %s do %s' % (params['dataod'], params['datado']),
            'header': header,
            'data': wynik
        }


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': []
    }
    for job_id, params, status, result in task_group.get_tasks_results():
        start_params = None
        bledy_polaczen = []
        if start_params is None:
            start_params = params['params']
        if status == 'finished' and result is not None:
            print('done')
        if status == 'failed':
            bledy_polaczen.append(params['target'])
    if len(bledy_polaczen) > 0:
        res['errors'].append('%s - błąd połączenia' % ', '.join(bledy_polaczen))
    # TODO XXX ten raport nie zadziała, nie ma nigdzie funkcji zrob_header_data()
    header, data = zrob_header_data()
    res['results'].append({
        'type': 'table',
        'header': header,
        'data': prepare_for_json(data)
    })
    res['progress'] = task_group.progress
    return res
