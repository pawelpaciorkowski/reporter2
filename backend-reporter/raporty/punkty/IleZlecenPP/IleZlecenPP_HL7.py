from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection
from datasources.snr import SNR
from datasources.hbz import HBZ
from api.common import get_db
from decimal import Decimal
MENU_ENTRY = 'Ile zleceń dla płatnika - HL7'

REQUIRE_ROLE = ['C-FIN', 'C-CS', 'PP-S', 'C-PP']
# REQUIRE_ROLE = 'ADMIN'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport ile zleceń dla danego płatnika zarejestrowały punkty pobra rejestrujące się samodzielnie przez HL7'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa', default='-7D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
))

sqlDH = """select
        p.NAZWISKO as SYMBOL,
        p.NAZWISKO as NAZWA,
        pl.symbol as PLATNIKS,
        pl.nazwa as PLATNIKN,
        gp.symbol as GPL,
        count (distinct z.id) as ILOSC,
        count (w.id) as BAD,
        sum (w.cena) as WART,
        cast (list(distinct z.id, ';') as varchar(32765)) as LISTA,
        cast (list(distinct z.OBCYKODKRESKOWY, ';') as varchar(32000)) as KODY
    from zlecenia z
        left outer join wykonania w on w.zlecenie=z.id
        left outer join POBORCY p on p.id = w.POBORCA
        left outer join platnicy pl on pl.id =z.platnik
        left outer join Badania B on w.badanie = b.id
        left outer join GrupyBadan GB on GB.Id = B.Grupa	
        left outer join GrupyPlatnikow GP on GP.Id = pl.Grupa
    where z.datarejestracji between ? and ? and w.anulowane is null and w.platne = '1' and (GB.Symbol != 'TECHNIC' or GB.Symbol is null) and UPPER (p.NAZWISKO) = UPPER(p.NUMER) and p.HL7SYSID is not NULL
    group by pl.symbol, pl.nazwa, gp.symbol, p.NAZWISKO
    order by p.NAZWISKO, pl.nazwa; """

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
    sql = sqlDH
    sql_params = [oddnia, dodnia]
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
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
    hbz = HBZ()

    wiersze = []
    oddzialy = []
    platnicy = []
    zestaw = []
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            for row in result:
                # print(row)
                lab = params['target']
                pozycje = []
                if next((i for i in oddzialy if i['symbol'] == prepare_for_json(row[1]) and i['nazwa'] == prepare_for_json(row[2])), None) == None:
                    oddzialy.append({'lab':prepare_for_json(row[0]),'symbol':prepare_for_json(row[1]),'nazwa':prepare_for_json(row[2])})
                if next((i for i in platnicy if i['symbol'] == prepare_for_json(row[3]) and i['nazwa'] == prepare_for_json(row[4])), None) == None:
                    platnicy.append({'lab':prepare_for_json(row[0]),'symbol':prepare_for_json(row[3]),'nazwa':prepare_for_json(row[4])})
            
                sqlSNR = "select sum(w.nettodlaplatnika) as wart from Wykonania W where W.datarejestracji between '%s' and '%s' and w.laboratorium = '%s' and w.zlecenie in ('%s') and not W.bezplatne; " %  (params['params']['dataod'], params['params']['datado'],lab,row[9].replace(';','^%s\' ,\'' % lab)+'^%s' % lab)
                _, rowsSNR = snr.select(sqlSNR)
                wartosc = row[8]
                if row[8] is None: 
                    wartosc = rowsSNR[0][0]
                pozycje.append(row[0])
                pozycje.append(row[1])
                pozycje.append(row[2])
                pozycje.append(row[3])
                pozycje.append(row[4])
                pozycje.append(row[5])
                pozycje.append(row[6])
                pozycje.append(row[7])
                pozycje.append(prepare_for_json(wartosc))
                wiersze.append(pozycje)

        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])

    for platnik in platnicy:
        wiersz = []
        wiersz.append(platnik['lab'])
        wiersz.append(platnik['symbol'])
        wiersz.append(platnik['nazwa'])
        for oddzial in oddzialy:
            iloscZlecen = ''
            iloscBadan = ''
            wartosc = ''
            for i in wiersze:
                print(i)
                if i[1] == oddzial['symbol'] and i[3] == platnik['symbol']:
                    iloscZlecen = i[6]
                    iloscBadan = i[7]
                    wartosc = i[8]
            wiersz.append(iloscZlecen)
            wiersz.append(iloscBadan)
            wiersz.append(wartosc)
        zestaw.append(wiersz)

    suma = ['','W SUMIE','W Sumie']
    for oddzial in oddzialy:
        iloscZlecenSuma = 0
        iloscBadanSuma = 0
        wartoscSuma = 0
        for wiersz in wiersze:
            if wiersz[1] == oddzial['symbol']:
                iloscZlecenSuma = iloscZlecenSuma + wiersz[6]
                iloscBadanSuma = iloscBadanSuma + wiersz[7]
                if wiersz[8] != None:
                    wartoscSuma = wartoscSuma + float(wiersz[8])
        suma.append(iloscZlecenSuma)
        suma.append(iloscBadanSuma)
        suma.append((format(float(wartoscSuma),'7.2f')))

    zestaw.append(suma)


    headerFull = []
    headerlist = []
    header = []
    header.append({'title':'Laboratorium', 'rowspan' : 2,'fontstyle': 'b'})
    header.append({'title':'Symbol Płatnika', 'rowspan' : 2,'fontstyle': 'b'})
    header.append({'title':'Nazwa Płatnika', 'rowspan' : 2,'fontstyle': 'b'})
    for oddzial in oddzialy:
        header.append({'title':oddzial['nazwa'], 'rowspan' : 1, 'colspan' : 3,'fontstyle': 'b'})
    headerFull.append(header)
    for oddzial in oddzialy:
        headerlist.append({'title':'Ilość Zleceń'})
        headerlist.append({'title':'Ilość Badań'})
        headerlist.append({'title':'Wartość'})
    headerFull.append(headerlist)

    res['progress'] = task_group.progress
    res['results'].append(
            {
                'type': 'table',
                'title': 'wykaz ile zleceń dla danego płatnika zarejestrował punkt poprzez moduł dystrybucji HL7',
                'header': headerFull,
                'data': zestaw
            })
    return res