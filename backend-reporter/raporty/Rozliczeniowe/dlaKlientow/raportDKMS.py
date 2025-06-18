import json
from datasources.mop import MopDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty, get_snr_connection
from datasources.reporter import ReporterDatasource
from tasks.db import redis_conn

MENU_ENTRY = 'Raport DKMS'

REQUIRE_ROLE = ['C-FIN', 'C-CS', 'C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport z wykonanych badań dla DKMS'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 90)
    wewn = []
    rep = ReporterDatasource()
    for row in rep.dict_select("""select symbol from laboratoria where aktywne and wewnetrzne and adres is not null"""):
        if row['symbol'] not in wewn:
            wewn.append(row['symbol'])

    zewn = []
    for row in rep.dict_select("""select symbol from laboratoria where aktywne and zewnetrzne and adres is not null"""):
        if row['symbol'] not in zewn:
            zewn.append(row['symbol'])

    for lab in wewn:
        task = {
            'type': 'snr',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'raport_snr'
        }
        report.create_task(task)
    for lab in zewn:
        task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'raport_lab'
        }
        report.create_task(task)
    report.save()
    return report


def raport_snr(task_params):
    lab = task_params['target']
    params = task_params['params']
    sql = """
        select
            w.datarejestracji as "DATA",
            w.hs->'numer' as "NR",
            w.hs->'zewnetrznyidentyfikator' as "NZ",
            w.hs->'zleceniodawcazlecenia' as "PPS",
            Z.nazwa as "PPN",
            PWL.symbol as "PLS",
            P.Nazwa as "PLN",
            w.hs->'pacjencinazwisko' as "PACN",
            w.hs->'pacjenciimiona' as "PACI",
            w.hs->'pacjencipesel' as "PACP",
            w.hs->'pacjencidataurodzenia' as "PACU",
            w.hs->'plec' as "PACS",
            w.hs->'pacjencinumer' as "PACNR",
            w.badanie as "BS",
            w.nazwa  as "BN",
            w.material as "MS",
            pkm.nazwa as "MN",
            W.nettodlaplatnika as "CENA"
        from Wykonania W
                left outer join Platnicy P on W.platnik = P.ID
                left outer join Platnicywlaboratoriach Pwl on PWL.laboratorium = w.laboratorium and PWL.platnik = P.ID and not pwl.del
                left outer join zleceniodawcy z on W.Zleceniodawca = Z.ID
                left outer join pozycjekatalogow pk on pk.symbol=w.badanie and pk.katalog = 'BADANIA'
                left outer join pozycjekatalogow pkm on pkm.symbol=w.material and pkm.katalog = 'MATERIALY'
        where
            w.datarozliczeniowa between 
            and not W.bezPlatne and not w.jestpakietem and p.nazwa like '%DKMS%' and (pk.hs->'grupa') is distinct from 'TECHNIC'
        order by
            w.Datarejestracji,	w.hs->'numer', w.badanie, w.material
    """
    sql = sql.replace('w.datarozliczeniowa between',"""w.datarozliczeniowa between '%s' and '%s' and w.laboratorium = '%s'""" % (params['dataod'], params['datado'], lab))
    res = []
    with get_snr_connection() as snr:
        wyniki = snr.dict_select(sql)
        for row in wyniki:
            res.append([
                lab,
                prepare_for_json(row['DATA']),
                row['NR'],
                row['NZ'],
                row['PPS'],
                row['PPN'],
                row['PLS'],
                row['PLN'],
                row['PACN'],
                row['PACI'],
                row['PACP'],
                row['PACU'],
                row['PACS'],
                row['PACNR'],
                row['BS'],
                row['BN'],
                row['MS'],
                row['MN'],
                prepare_for_json(row['CENA'])
            ])
    return res

def raport_lab(task_params):
    lab = task_params['target']
    params = task_params['params']
    with get_centrum_connection(lab) as conn:
        sql = """
            select
                Z.DataRejestracji as DATA,
                Z.Numer as NR,
                Z.zewnetrznyidentyfikator as NZ,
                PP.Nazwa  as PPN,
                PP.Symbol as PPS,
                PL.Nazwa  as PLN,
                PL.Symbol as PLS,
                PAC.Nazwisko      as PACN,
                PAC.Imiona        as PACI,
                PAC.PESEL         as PACP,
                PAC.DataUrodzenia as PACU,
                PAC.Plec          as PACS,
                PAC.Numer         as PACNR,
                BAD.Symbol as BS,
                BAD.Nazwa  as BN,
                MAT.Symbol as MS,
                MAT.Nazwa  as MN,
                W.Cena   as CENA
            from Wykonania W
                left outer join Zlecenia Z on W.Zlecenie = Z.ID
                left outer join Oddzialy PP on Z.Oddzial = PP.ID
                left outer join Platnicy PL on W.Platnik = PL.ID
                left outer join Pacjenci PAC on W.Pacjent = PAC.ID
                left outer join Badania BAD on W.Badanie = BAD.ID
                left outer join grupybadan GBAD on GBAD.id=BAD.Grupa
                left outer join Materialy MAT on W.Material = MAT.ID
            where
                W.Rozliczone between ? and ?  and
                W.Platne = 1 and W.Anulowane is Null and (PL.Symbol like '%DKMS%' or trim(PL.Symbol) like '%DKM') and GBAD.Symbol <> 'TECHNIC'
            order by
                Z.Datarejestracji,	Z.Numer, BAD.Symbol, MAT.Symbol  

        """
        cols, rows = conn.raport_z_kolumnami(sql, [params['dataod'], params['datado']])
    res = []
    for row in rows:
        res.append([lab] + row)
    print(prepare_for_json(res))
    return prepare_for_json(res)



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
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            for wiersz in result:
                wiersze.append(wiersz)
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])
    res['results'].append({
        'type': 'table',
        'header': 'Laboratorium;Data Rejestracji;Numer Zlecenia;Numer zewnętrzny;Symbol Zleceniodawcy;Nazwa Zleceniodawcy;Symbol Płatnika;Nazwa Płatnika;Pacjent Nazwisko;Pacjent Imiona;Pesel;Data Urodzenia;Płeć;Pacjent Numer;Badanie Symbol;Badanie Nazwa;Materiał Symbol;Materiał Nazwa;Cena'.split(';'),
        'data': wiersze,
    })
    res['progress'] = task_group.progress
    return res