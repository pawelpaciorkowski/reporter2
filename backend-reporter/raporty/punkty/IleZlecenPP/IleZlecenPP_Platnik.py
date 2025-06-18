from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection
from datasources.snr import SNR
from datasources.hbz import HBZ
from api.common import get_db
from decimal import Decimal
MENU_ENTRY = 'Ile zleceń dla płatnika - iCentrum'

REQUIRE_ROLE = ['C-FIN', 'C-CS', 'PP-S', 'C-PP']
# REQUIRE_ROLE = 'ADMIN'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport ile zleceń dla danego płatnika zarejestrowały punkty pobra rejestrujące się samodzielnie przez iCentrum'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa', default='-7D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
))

SQL_SP = """
    select
        k.symbol as SYMBOL,
        k.nazwa as NAZWA,
        pl.symbol as PLATNIKS,
        pl.nazwa as PLATNIK,
        gp.symbol as GPL,
        count (distinct z.id) as ILOSC,
        count (w.id) as BAD,
        sum (w.cena) as WART,
        cast (list(distinct z.id, ';') as varchar(32765)) as LISTA
    from zlecenia z
        left outer join pracownicy p on p.id = z.pracownikodrejestracji
        left outer join kanaly k on k.id = p.kanalinternetowy
        left outer join platnicy pl on pl.id =z.platnik
        left outer join wykonania w on w.zlecenie=z.id
        left outer join Badania B on w.badanie = b.id
        left outer join GrupyBadan GB on GB.Id = B.Grupa
        left outer join GrupyPlatnikow GP on GP.Id = pl.Grupa
    where z.datarejestracji between ? and ? and  z.pracownikodrejestracji is not null and p.kanalinternetowy is not null and w.anulowane is null and w.platne = '1' and (GB.Symbol != 'TECHNIC' or GB.Symbol is null)
    group by pl.symbol, pl.nazwa, gp.symbol, k.symbol, k.nazwa
    order by k.symbol, pl.nazwa;
"""
SQL_SP_PG = """
    select
        k.symbol as SYMBOL,
        k.nazwa as NAZWA,
        pl.symbol as PLATNIKS,
        pl.nazwa as PLATNIK,
        gp.symbol as GPL,
        count (distinct z.id) as ILOSC,
        count (w.id) as BAD,
        sum (w.cena) as WART,
        string_agg(z.id::text, ', ') as LISTA
    from zlecenia z
        left outer join pracownicy p on p.id = z.pracownikodrejestracji
        left outer join kanaly k on k.id = p.kanalinternetowy
        left outer join platnicy pl on pl.id =z.platnik
        left outer join wykonania w on w.zlecenie=z.id
        left outer join Badania B on w.badanie = b.id
        left outer join GrupyBadan GB on GB.Id = B.Grupa
        left outer join GrupyPlatnikow GP on GP.Id = pl.Grupa
    where z.datarejestracji between %s and %s and  z.pracownikodrejestracji is not null and p.kanalinternetowy is not null and w.anulowane is null and w.platne = '1' and (GB.Symbol != 'TECHNIC' or GB.Symbol is null)
    group by pl.symbol, pl.nazwa, gp.symbol, k.symbol, k.nazwa
    order by k.symbol, pl.nazwa;
"""
def start_report(params):
    laboratoria = []
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)
    for lab in params['laboratoria']:
        lab_task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'zbierz_lab',
        }
        report.create_task(lab_task)
    report.save()
    return report

def zbierz_lab(task_params):
    params = task_params['params']
    oddnia = params['dataod']
    dodnia = params['datado']
    res = []
    sql = SQL_SP
    sql_params = [oddnia, dodnia]
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_params, sql_pg=SQL_SP_PG)
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
    snr = SNR()
    wiersze = []
    wierszeg = []
    TabSkadPacjent = []
    TabSkadPacjentGrupa = []
    TabKanalySP = []
    TabPlatnicySP = []
    TabGrupa = []
    TabKanalyGrupa = []
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            for row in result:
                print('dostepne w row :',params)
                # print(row)
                lab = params['target']
                if next((i for i in TabPlatnicySP if i['symbol'] == prepare_for_json(row[3])), None) == None:
                    TabPlatnicySP.append({'lab': prepare_for_json(row[0]),'symbol':prepare_for_json(row[3]),'nazwa':prepare_for_json(row[4])})
                if next((i for i in TabKanalyGrupa if i['symbol'] == prepare_for_json(row[1])), None) == None:
                    TabKanalyGrupa.append({'lab': prepare_for_json(row[0]),'symbol':prepare_for_json(row[1]),'nazwa':prepare_for_json(row[2])})
                if next((i for i in TabGrupa if i['Gpl'] == prepare_for_json(row[5])), None) == None:
                    TabGrupa.append({'Gpl':prepare_for_json(row[5])})

                sqlSNR = "select sum(w.nettodlaplatnika) as wart from Wykonania W where W.datarejestracji between '%s' and '%s' and w.laboratorium = '%s' and w.zlecenie in ('%s') and not W.bezplatne; " %  (params['params']['dataod'], params['params']['datado'],lab,row[9].replace(';','^%s\' ,\'' % lab)+'^%s' % lab)
                _, rows = snr.select(sqlSNR)

                wartosc = 0
                if row[8] is None: 
                    wartosc = rows[0][0]
                else :
                    wartosc = row[8]
            
                TabSkadPacjent.append({'lab': prepare_for_json(row[0]),'Symbol':prepare_for_json(row[1]),'Platnik':prepare_for_json(row[3]),'Ilosc':prepare_for_json(row[6]),'Badania':prepare_for_json(row[7]),'Wartosc':prepare_for_json(wartosc)})

        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])

    for platnik in TabPlatnicySP:
        linia = []
        for kanal in TabKanalyGrupa:
            dane = next((i for i in TabSkadPacjent if i['Platnik'] == platnik['symbol'] and i['Symbol'] == kanal['symbol']), {'lab': kanal['lab'] ,'Symbol':kanal['symbol'],'Platnik':platnik['symbol'],'Ilosc':'','Badania':'','Wartosc':''})
            if dane != None:
                print(dane)
                # linia.append(list(dane.values())[2])
                linia.append(list(dane.values())[3])
                linia.append(list(dane.values())[4])
                linia.append(list(dane.values())[5])
        wiersze.append(list(platnik.values()) + linia)

    suma = ['','W SUMIE', 'W sumie']
    for kanal in TabKanalyGrupa:
        iloscZlecen = 0
        iloscBadan = 0
        wartosc = 0
        for i in TabSkadPacjent:
            if i['Symbol'] == kanal['symbol']:
                iloscZlecen = iloscZlecen + int(i['Ilosc'])
                iloscBadan = iloscBadan + int(i['Badania'])
                if i['Wartosc'] != '' and i['Wartosc'] != None:
                    wartosc = wartosc + float(i['Wartosc'])
        suma.append(iloscZlecen)
        suma.append(iloscBadan)
        suma.append((format(float(wartosc),'7.2f')))
    wiersze.append(suma)

    header = ['Laboratorium','Symbol','Nazwa płatnika']
    for platnik in TabPlatnicySP:
        header.append({'title':platnik['symbol'] or '', 'colspan' : 3})

    for platnik in TabPlatnicySP:
        if platnik['symbol'] is not None and 'GOTO' in platnik['symbol']:
            for kanal in TabKanalyGrupa:
                daneg = next((i for i in TabSkadPacjent if i['Platnik'] == platnik['symbol'] and i['Symbol'] == kanal['symbol']),None)
                if daneg != None:
                    linia = [kanal['lab'],kanal['symbol'],kanal['nazwa']]
                    # linia.append(list(daneg.values())[2])
                    linia.append(list(daneg.values())[3])
                    linia.append(list(daneg.values())[4])
                    linia.append(list(daneg.values())[5])
                    srednia = format(float(list(daneg.values())[5])/float(list(daneg.values())[3]),'7.2f')
                    linia.append(srednia)
                    wierszeg.append(linia)
    headerFull = []
    headerlist = []
    header = []
    header.append({'title':'Laboratorium', 'rowspan' : 2,'fontstyle': 'b'})
    header.append({'title':'Symbol płatnika', 'rowspan' : 2,'fontstyle': 'b'})
    header.append({'title':'Nazwa płatnika', 'rowspan' : 2,'fontstyle': 'b'})
    for kanal in TabKanalyGrupa:
        header.append({'title':kanal['symbol'], 'rowspan' : 1, 'colspan' : 3,'fontstyle': 'b'})
    headerFull.append(header)
    for kanal in TabKanalyGrupa:
        headerlist.append({'title':'Ilość zleceń'})
        headerlist.append({'title':'Ilość badań'})
        headerlist.append({'title':'Wartość'})
    headerFull.append(headerlist)

    res['progress'] = task_group.progress
    res['results'].append(
            {
                'type': 'table',
                'title': 'wykaz ile zleceń dla danego płatnika zarejestrował punkt rejstrujące się samodzielnie przez iCentrum',
                'header': headerFull,
                'data': wiersze
            })
    res['results'].append(
            {
                'type': 'table',
                'title': 'wykaz wartości sprzedaży gotówkowej w ramach zleceń zarejestrowanych przez iCentrum w punkcie pobrań z uwzględnieniem średniej ceny paragonu',
                'header': 'Laboratorium,Symbol \nPunktu Pobrań,Nazwa\nPunktu Pobrań,Ilość Zleceń,Ilość Badań,Wartość,Średnia Cena Paragonu'.split(','),
                'data': wierszeg
            }
        )
    return res