from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_snr_connection
from datasources.reporter import ReporterDatasource
from api.common import get_db
from decimal import Decimal
MENU_ENTRY = 'Raport Bychawa'

REQUIRE_ROLE = ['C-FIN', 'C-CS', 'C-ROZL']
# REQUIRE_ROLE = 'ADMIN'

laby = [
        # TODO XXX nic nie da tu dopisywanie kolejnych pozycji dopóki symbole są i tak wpisane na sztywno w zapytanie
        {'lab':'BYCHAWA', 'platnicy':'LYSZPIT'},
        ]

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport Bychawa'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 90)
    rep = ReporterDatasource()
    for lab in laby:
        task = {
                'type': 'centrum',
                'priority': 1,
                'target': lab['lab'],
                'params': params,
                'function': 'raport_lab',
            }
        report.create_task(task)
    report.save()
    return report

def raport_lab(task_params):
    params = task_params['params']
    aparaty = []
    badania = []
    tabb = []
    tabid = []
    tabz = []
    zbiorczo = []
    wynik = []
    sql = """
        select
                substring(w.wykonanie,1,position('^' in w.wykonanie)-1) as sysid,
                trim(substring(w.wykonanie,position('^' in w.wykonanie)+1,7)) as sys,
                w.nazwa as badanien,
                trim(w.badanie) as badanies,
                w.nettodlaplatnika as cena
            from wykonania w
                left outer join pozycjekatalogow pk on pk.symbol=w.badanie and pk.katalog = 'BADANIA'
                left outer join platnicy p on w.platnik = p.id
                left outer join platnicywlaboratoriach pwl on pwl.laboratorium = w.laboratorium and pwl.platnik=p.id
            where w.datarozliczeniowa between '%s' and '%s' and w.laboratorium = 'BYCHAWA'  and not W.bezPlatne and not w.jestpakietem and pwl.symbol = 'LYSZPIT'
                and (pk.hs->'grupa') is distinct from 'TECHNIC'
    """ % (params['dataod'], params['datado'])
    with get_snr_connection() as snr:
        wyniki = snr.dict_select(sql)
        for row in wyniki:
            sys = row['sys']
            if row['sys'] == None:
                sys = 'BRAK'
            # if not any(d['sysid'] == row['sysid'] for d in tabid):                
            # if next((i for i in tabid if i['sysid'] == prepare_for_json(row['sysid'])), None) == None:
            #     tabid.append({'sysid':prepare_for_json(row['sysid']), 'sys': sys.strip()})            
            if row['sysid'] not in tabid:
                tabid.append(row['sysid'])
            # if not any(d['symbol'] == row['badanies'] for d in badania):                
            if next((i for i in badania if i['symbol'] == row['badanies']), None) == None:
                badania.append({'symbol':row['badanies'], 'nazwa': row['badanien']})            
            tabb.append({
                'sysid':row['sysid'],
                'sys':sys.strip(),
                'badanien':row['badanien'],
                'badanies':row['badanies'],
                'cena':prepare_for_json(row['cena']),
                })

    sqlz =	'''
    select
			trim(w.id) as id,
			trim(w.sysid) as sysid,
			w.system as sys,
			b.nazwa as badanien,
			trim(b.symbol) as badanies,
			a.nazwa as aparat,
			trim(a.symbol) as aparats,
			w.cena as cena
		from wykonania w
			left outer join zlecenia z on z.id=w.zlecenie
			left outer join badania b on b.id=w.badanie
			left outer join grupybadan gb on gb.id=b.grupa
			left outer join platnicy p on p.id=w.platnik
			left outer join aparaty a on a.id=w.aparat
		where w.rozliczone between '%s' and '%s' and b.pakiet = '0' and p.symbol = 'LYSZPIT' and w.platne ='1' and w.anulowane is null  
			and (gb.Symbol <> 'TECHNIC' or gb.symbol is null) 
		''' % (params['dataod'], params['datado'])

    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sqlz)
        for row in rows:
            sys = row[2]
            if row[2] == None:
                sys = 'BRAK'
            sysid = row[1]
            if row[1] == None:
                sysid = row[0]         
            # if not any(d['sysid'] == sysid for d in tabid):
            # if next((i for i in tabid if i['sysid'] == sysid), None) == None:
            #     tabid.append({'sysid':sysid, 'sys' : sys.strip()})           
            if sysid not in tabid:
                tabid.append(sysid)
            # if not any(d['symbol'] == row[6] for d in aparaty):
            if next((i for i in aparaty if i['symbol'] == row[6]), None) == None:
                aparaty.append({'symbol':row[6], 'nazwa': row[5]})
            # if not any(d['symbol'] == row[4] for d in badania):
            if next((i for i in badania if i['symbol'] == row[4]), None) == None:
                badania.append({'symbol':row[4], 'nazwa': row[3]})

            tabz.append({
                'sysid':sysid,
                'sys':sys.strip(),
                'badanien' : row[3],
                'badanies' : row[4],
                'aparat' : row[5],
                'aparats' : row[6],
                'cena' : row[7]
                })
    
    for tid in tabid:
        rowz = next((i for i in tabz if i['sysid'] == tid), None)
        rows = next((i for i in tabb if i['sysid'] == tid), None)
        if rowz is not None:
            sys = rowz['sys']
            badanien = rowz['badanien']
            badanies = rowz['badanies']
            aparat = rowz['aparat']
            aparats = rowz['aparats']
        else:            
            sys = rows['sys']
            badanien = rows['badanien']
            badanies = rows['badanies']
            aparat = ''
            aparats = ''
        sysid = tid
        cena = 0
        if rows is not None:
            cena = prepare_for_json(rows['cena'])

        zbiorczo.append({
                'sysid':sysid,
                'sys':sys,
                'badanien' : badanien,
                'badanies' : badanies,
                'aparat' : aparat,
                'aparats' : aparats,
                'cena' : cena
        })

    for aparat in aparaty:
        for badanie in badania:
            cena = 0
            ilosc = 0
            for lista in zbiorczo:
                if lista['badanies'] == badanie['symbol'] and lista['aparats'] == aparat['symbol']:
                    cena = lista['cena']
                    ilosc = ilosc +1
            if ilosc > 0:
                wynik.append([
                        aparat['symbol'],
                        aparat['nazwa'],
                        badanie['symbol'],
                        badanie['nazwa'],
                        cena,
                        ilosc,
                        format(float(cena)*int(ilosc),'7.2f') if cena is not None else None
                    ])

    return {
        'type': 'table',
        'header': 'Aparat Symbol,Aparat Nazwa,Badanie symbol,Badanie Nazwa,Cena,Ilość,Wartość'.split(','),
        'data': wynik
    }