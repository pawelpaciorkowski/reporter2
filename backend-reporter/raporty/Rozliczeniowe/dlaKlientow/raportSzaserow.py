from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_snr_connection
from datasources.snr import SNR
from datasources.reporter import ReporterDatasource
from api.common import get_db
from decimal import Decimal
MENU_ENTRY = 'Raport Szaserów'

REQUIRE_ROLE = ['C-FIN', 'C-CS', 'C-ROZL']
# REQUIRE_ROLE = 'ADMIN'
laby = [
        {'lab':'CZERNIA', 'platnicy':'CZWIM'},
        {'lab':'ZAWODZI', 'platnicy':'FZWIM'},
        ]

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport Szaserów'),
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
                'params': {
                    'dataod': params['dataod'],
                    'datado': params['datado']
                },
                'function': 'raport_lab',
                'timeout': 3000,
            }
        report.create_task(task)
    report.save()
    return report

def raport_lab(task_params):
    lab = task_params['target']
    platnicy = []
    for l in laby:
        if l['lab'] == lab:
            platnicy.append(l['platnicy'])

    params = task_params['params']
    wynik = []
    tabb = []
    tabbid = []
    tabbsys = []
    sql = """
    select
        substring(w.wykonanie,1,position('^' in w.wykonanie)-1) as "SYSID",
        trim(substring(w.wykonanie,position('^' in w.wykonanie)+1,7)) as "SYS",
        w.hs->'kodkreskowy' as "KOD",
        z.nazwa as "ODDZIAL",
        (w.hs->'lekarzenazwisko' || ' ' || (w.hs->'lekarzeimiona')) as "LEKARZ",
        w.hs->'pacjencipesel' as "PESEL",
        w.hs->'pacjencinazwisko' as "NAZWISKO",
        w.hs->'pacjenciimiona' as "IMIONA",
        w.hs->'pacjencidataurodzenia' as "DATAU",
        w.nazwa as "BADANIEN",
        w.badanie as "BADANIES",
        coalesce(nullif(trim(PK.hs->'kod'), ''), '-BRAK-') as "ICD9",
        w.typzlecenia as "TRYB",
        w.nettodlaplatnika as "CENA",
        w.datarejestracji as "DATA",
        w.datarozliczeniowa as "DATA_K",
        (w.hs->'numer') as "NUMER"
    from wykonania w
        left outer join pozycjekatalogow pk on pk.symbol=w.badanie and pk.katalog = 'BADANIA'
        left outer join platnicy p on w.platnik = p.id
        left outer join platnicywlaboratoriach pwl on pwl.laboratorium = w.laboratorium and pwl.platnik=p.id
        left outer join zleceniodawcy z on w.zleceniodawca = z.id
    where w.datarozliczeniowa between '%s' and '%s' and w.laboratorium = '%s' and not W.bezPlatne and not w.jestpakietem and pwl.symbol in ('%s')
      and (pk.hs->'grupa') is distinct from 'TECHNIC'
    """ % (params['dataod'], params['datado'], lab, ','.join(platnicy))

    with get_snr_connection() as snr:
        wyniki = snr.dict_select(sql)
        for row in wyniki:
            syss = row['SYS']
            if row['SYS'] == None:
                syss = 'BRAK'

            tabb.append({
                'sysid':row['SYSID'],
                'sys':syss.strip(),
                'kod':row['KOD'],
                'oddzial':row['ODDZIAL'],
                'lekarz':row['LEKARZ'],
                'pesel':row['PESEL'],
                'nazwisko':row['NAZWISKO'],
                'imiona':row['IMIONA'],
                'datau':row['DATAU'],
                'badanien':row['BADANIEN'],
                'badanies':row['BADANIES'],
                'icd9':row['ICD9'],
                'tryb':row['TRYB'],
                'cena':prepare_for_json(row['CENA']),
                'data':prepare_for_json(row['DATA']),
                'nr':row['NUMER'],
                'datak':prepare_for_json(row['DATA_K']),
                })
   
            if next((i for i in tabbid if i['sysid'] == prepare_for_json(row['SYSID'])), None) == None:
                tabbid.append({'sysid':prepare_for_json(row['SYSID'])})            

            if next((i for i in tabbsys if i['sys'] == prepare_for_json(row['SYS'])), None) == None:
                tabbsys.append({'sys':prepare_for_json(row['SYS']).strip()})            
                
    sqlz =	'''
    select
		w.id as ID,
		w.sysid as SYSID,
		w.system as SYS,
		z.opis as OPIS
	from wykonania w
		left outer join zlecenia z on z.id=w.zlecenie
		left outer join platnicy p on p.id=w.platnik
	where w.rozliczone between '%s' and '%s' and p.symbol in ('%s')  and w.platne ='1' and w.anulowane is null''' % (params['dataod'], params['datado'],','.join(platnicy))

    tabz = []
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sqlz)
        for row in rows:
            sysz = row[2]
            if row[2] == None:
                sysz = 'CZERNIA'

            syszid = row[1]
            if row[1] == None:
                syszid = row[0]
    		
            tabz.append({
                'sys':sysz.strip(),
                'sysid':syszid,
                'opis':row[3].replace('$&','')
                })
    for bid in tabbid:
        for bsys in tabbsys:
            listab = list(i for i in tabb if i['sys'] == bsys['sys'] and i['sysid'] == bid['sysid'])
            listaz = list(d for d in tabz if d['sys'] == bsys['sys'] and str(d['sysid']) == bid['sysid'])
            for lb in listab:
                for lz in listaz:
                    if lb is not None and lz is not None:
                        wynik.append([
                            lb['data'],
                            lb['nr'],
                            lb['datak'],
                            lb['kod'],
                            lb['oddzial'],
                            lb['lekarz'],
                            lb['pesel'],
                            lb['nazwisko'],
                            lb['imiona'],
                            lb['datau'],
                            lb['badanien'],
                            lb['tryb'],
                            lb['cena'],
                            lz['opis']
                            ])
            

    return {
        'type': 'table',
        'header': "Data rejestracji zlecenia;Numer zlecenia;Data zakończenia badania;Kod zlecenia;Oddział zlecający;Lekarz zlecający;Pesel pacjenta;Nazwisko pacjenta;Imię pacjenta;Data urodzenia pacjenta;Nazwa badania;Tryb badania;Cena badania;Zewnętrzne oznaczenie".split(';'),
        'data': wynik
    }