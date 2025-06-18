import time

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_snr_connection
from datasources.reporter import ReporterDatasource
from api.common import get_db
from decimal import Decimal

MENU_ENTRY = 'Raport Wolski'

REQUIRE_ROLE = ['C-FIN', 'C-CS', 'C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport Wolski'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))
laby = [{'lab': 'WOLSKI', 'platnicy': ('WW-SZPI', 'WWSZPIT')}]


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
                'datado': params['datado'],
                'platnicy': lab['platnicy']
            },
            'function': 'raport_lab',
            'timeout': 3600,
        }
        report.create_task(task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']
    lab = task_params['target']
    platnicy = params['platnicy']
    wynik = []
    rows_snr = []
    # tabbid = []
    # tabbsys = []
    sql_snr = """
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
      w.material as "MATERIALS",
      array_to_string(array_agg(rozl.identyfikatorwrejestrze), ', ') as "ROZLICZENIE"
    from wykonania w
      left outer join pozycjekatalogow pk on pk.symbol=w.badanie and pk.katalog = 'BADANIA'
      left outer join platnicy p on w.platnik = p.id
      left outer join platnicywlaboratoriach pwl on pwl.laboratorium = w.laboratorium and pwl.platnik=p.id
      left outer join zleceniodawcy z on w.zleceniodawca = z.id
      left join pozycjerozliczen pr on pr.id = any(string_to_array(w.pozycjerozliczen, ' ')) and not pr.del
      left join rozliczenia rozl on rozl.id=pr.rozliczenie 
    where w.laboratorium = %s and w.datarozliczeniowa between %s and %s 
    and not W.bezPlatne and not w.jestpakietem and pwl.symbol in %s
      and (pk.hs->'grupa') is distinct from 'TECHNIC'
      group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
    """

    with get_snr_connection() as snr:
        print('Pobieram SNR...')
        start_t = time.perf_counter()
        wyniki = snr.dict_select(sql_snr, [lab, params['dataod'], params['datado'], tuple(platnicy)])
        print('  pobrane %f' % (time.perf_counter() - start_t))
        for row in wyniki:
            syss = row['SYS']
            if row['SYS'] == None:
                syss = 'BRAK'
            sbadanie = '' if row['BADANIES'] is None else row['BADANIES']
            smaterial = '' if row['MATERIALS'] is None else row['MATERIALS']

            rows_snr.append({
                'sysid': row['SYSID'],
                'sys': syss.strip(),
                'kod': row['KOD'],
                'oddzial': row['ODDZIAL'],
                'lekarz': row['LEKARZ'],
                'pesel': row['PESEL'],
                'nazwisko': row['NAZWISKO'],
                'imiona': row['IMIONA'],
                'datau': row['DATAU'],
                'badanien': row['BADANIEN'],
                'badanies': row['BADANIES'],
                'icd9': row['ICD9'],
                'tryb': row['TRYB'],
                'cena': prepare_for_json(row['CENA']),
                'badanie': sbadanie + ':' + smaterial,
                'rozliczenie': row['ROZLICZENIE']
            })

            # if next((i for i in tabbid if i['sysid'] == prepare_for_json(row['SYSID'])), None) == None:
            #     tabbid.append({'sysid': prepare_for_json(row['SYSID'])})
            #
            # if next((i for i in tabbsys if i['sys'] == prepare_for_json(row['SYS'])), None) == None:
            #     tabbsys.append({'sys': prepare_for_json(row['SYS']).strip()})

    sql_centrum = '''
    select
		w.id as ID,
		w.sysid as SYSID,
		w.system as SYS,
		substring(cast(w.zatwierdzone as varchar) from 1 for 16)  as GODZINA,
		substring(cast(w.dystrybucja as varchar) from 1 for 16)  as DYST,
		z.OBCYKODKRESKOWY as NUMERZEW,
		z.datarejestracji, z.numer
	from wykonania w
		left outer join platnicy p on p.id=w.platnik
		left outer join zlecenia z on z.id=w.zlecenie
		left outer join oddzialy o on o.id=z.oddzial
		left outer join badania b on b.id=w.badanie
		left outer join grupybadan gb on gb.id=b.grupa
	where w.rozliczone between ? and ? and w.platne ='1' and w.anulowane is null
	    and w.zatwierdzone is not null
	    and b.pakiet = '0' and p.symbol in (%s)
		and (gb.Symbol <> 'TECHNIC' or gb.symbol is null) ''' % ','.join(["'%s'" % sym for sym in platnicy])

    rows_centrum = {}
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        print('Pobieram Centrum...')
        start_t = time.perf_counter()
        cols, rows = conn.raport_z_kolumnami(sql_centrum, [params['dataod'], params['datado']])
        print('  pobrane %f' % (time.perf_counter() - start_t))
        for row in rows:
            sysz = row[2]
            if row[2] == None:
                sysz = 'WOLSKI'

            syszid = row[1]
            if row[1] == None:
                syszid = row[0]
            key = '%s:%s' % (sysz.strip(), str(syszid))
            rows_centrum[key] = {
                'sys': sysz.strip(),
                'sysid': syszid,
                'dataz': prepare_for_json(row[3]).split(' ')[0],
                'godzinaz': prepare_for_json(row[3]).split(' ')[1][0:5],
                'godzina': row[3],
                'dyst': row[4],
                'numerzew': row[5],
                'datarejestracji': row[6],
                'numer': row[7],
            }
    for row_snr in rows_snr:
        key = '%s:%s' % (row_snr['sys'], str(row_snr['sysid']))
        row_centrum = rows_centrum.get(key, {'godzina': 'BRAK DANYCH %s' % key, 'dyst': 'BRAK DANYCH', 'numerzew': 'BRAK DANYCH'})
        wynik.append([
            row_centrum['datarejestracji'],
            row_centrum['numer'],
            row_centrum['godzina'],
            row_centrum['dyst'],
            row_snr['kod'],
            row_snr['oddzial'],
            row_snr['lekarz'],
            row_snr['pesel'],
            row_snr['nazwisko'],
            row_snr['imiona'],
            row_snr['datau'],
            row_snr['badanies'],
            row_snr['badanien'],
            row_snr['icd9'],
            row_snr['tryb'],
            1,
            row_snr['cena'],
            row_centrum['numerzew'],
            row_snr['rozliczenie']
        ])

    return {
        'type': 'table',
        'header': 'Data rejestracji;Numer zlecenia;Data wykonania badania;Data przyjęcia materiału;Kod zlecenia;Oddział zlecający;Lekarz zlecający;Pesel pacjenta;Nazwisko pacjenta;Imię pacjenta;Data urodzenia pacjenta;Symbol badania;Nazwa badania;ICD9;Tryb badania;Ilość;Cena badania;Numer zewnętrzny;Rozliczenie'.split(
            ';'),
        'data': prepare_for_json(wynik)
    }
