from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_snr_connection
from datasources.snr import SNR
from datasources.reporter import ReporterDatasource
from api.common import get_db
from decimal import Decimal
MENU_ENTRY = 'Raport Szpitale'

REQUIRE_ROLE = ['C-FIN', 'C-CS', 'C-ROZL']
# REQUIRE_ROLE = 'ADMIN'
laby = [
        {'lab':'TARN-WS', 'platnicy':'RWSWSZ'},
        {'lab':'SYCOW', 'platnicy':'SY-SZPI'},
        {'lab':'OLESNIC', 'platnicy':'OY-SZPI'},
        {'lab': 'GWROCLA', 'platnicy': 'GZSOLES'},
        ]
lab = []
for l in laby:
    lab.append(l['lab']) 

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport Szpitale'),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium',show_only= lab ),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)

    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'timeout': 3000,
        'function': 'raport_lab',
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
      w.material as "MATERIALS"
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
            sbadanie = '' if row['BADANIES'] is None else row['BADANIES']
            smaterial = '' if row['MATERIALS'] is None else row['MATERIALS']

            tabb.append({
                'sysid':row['SYSID'],
                'sys':syss.strip(),
                'kod':row['KOD'],
                'oddzial':row['ODDZIAL'],
                'lekarz':row['LEKARZ'],
                'pesel':row['PESEL'],
                'nazwisko':row['NAZWISKO'],
                'imiona':row['IMIONA'],
                'datau':prepare_for_json(row['DATAU']),
                'badanien':row['BADANIEN'],
                'badanies':row['BADANIES'],
                'icd9':row['ICD9'],
                'tryb':row['TRYB'],
                'cena':prepare_for_json(row['CENA']),
                'badanie':sbadanie+':'+smaterial
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
		z.datarejestracji as DATAR,
		substring(cast(w.zatwierdzone as varchar(32)) from 1 for 16)  as GODZINA,
		substring(cast(w.dystrybucja as varchar(32)) from 1 for 16)  as DYST,
		z.OBCYKODKRESKOWY as NUMERZEW,
   		(select min(wwz.odebrany) from wydrukiwzleceniach wwz where wwz.zlecenie=w.zlecenie) as DATAWYD
	from wykonania w
		left outer join zlecenia z on z.id=w.zlecenie

		left outer join badania b on b.id=w.badanie
		left outer join grupybadan gb on gb.id=b.grupa
		left outer join platnicy p on p.id=w.platnik
	where w.rozliczone between '%s' and '%s' and b.pakiet = '0' and p.symbol in ('%s')  and w.platne ='1' and w.anulowane is null
		and (gb.Symbol <> 'TECHNIC' or gb.symbol is null) ''' % (params['dataod'], params['datado'],','.join(platnicy))

    tabz = []
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sqlz)
        for row in rows:
            sysz = row[2]
            if row[2] == None:
                sysz = 'WOLSKI'

            syszid = row[1]
            if row[1] == None:
                syszid = row[0]
            godzina = prepare_for_json(row[4])
            if row[4] == None:
                godzina = '0000-00-00 00:00'
            tabz.append({
                'sys':sysz.strip(),
                'sysid':syszid,
                'dataz':prepare_for_json(godzina).split(' ')[0],
                'godzinaz':prepare_for_json(godzina).split(' ')[1][0:5],
                'godzina':prepare_for_json(godzina),
                'dyst':row[5],
                'numerzew':row[6],
                'datar':prepare_for_json(row[3]),
                'dataw':prepare_for_json(row[7])
                })

    for bsys in tabbsys:
        for bid in tabbid:
            listab = list(i for i in tabb if i['sys'] == bsys['sys'] and i['sysid'] == bid['sysid'])
            listaz = list(d for d in tabz if d['sys'] == bsys['sys'] and str(d['sysid']) == bid['sysid'])
            for lb in listab:
                for lz in listaz:
                    if lb is not None and lz is not None:
                        wynik.append([
                            lz['datar'],
                            lz['dataz'],
                            lz['godzinaz'],
                            lz['dyst'],
                            lb['kod'],
                            lb['oddzial'],
                            lb['lekarz'],
                            lb['pesel'],
                            lb['nazwisko'],
                            lb['imiona'],
                            lb['datau'],
                            lb['badanien'],
                            # lb['icd9'],
                            lb['tryb'],
                            1,
                            lb['cena'],
                            lz['numerzew'],
                            lb['badanie'],
                            lz['dataw']
                            ])
            

    return {
        'type': 'table',
        'header': 'Data rejestracji;Data wykonania badania;Godzina;Data przyjęcia materiału;Kod zlecenia;Oddział zlecający;Lekarz zlecający;Pesel pacjenta;Nazwisko pacjenta;Imię pacjenta;Data urodzenia pacjenta;Nazwa badania;Tryb badania;Ilość;Cena badania;Numer zewnętrzny;Kod Usługi;Data Wydania wyniku'.split(';'),
        'data': wynik
    }




