import json
from datasources.mop import MopDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError, Switch, Select
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty, get_snr_connection
from datasources.reporter import ReporterDatasource
from tasks.db import redis_conn

MENU_ENTRY = 'Raport ze sprzedaży'

REQUIRE_ROLE = ['C-FIN', 'C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="""Raport Ze Sprzedaży
Wartości nie uwzględniają korekt oraz rabatów naliczanych indywidualnie
Raport wykonany z baz rozliczeniowych, zawiera płatne badania brane pod uwagę podczas wystawiania faktur
Nie uwzględnia pakietów, kontroli, badań wykonywanych dla grupy ALAB
prezentowane dane są wiarygodne jeżeli data końcowa jest przynajmnie dwa dni wstecz od dnia dzisiejszego.

Uwaga, ze względu na błędną konfigurację cenników w niektórych laboratoriach pojawia się niepusta wartość sprzedaży
dla sklepu internetowego w bazie SNR. Ponieważ wartość ta nie ma związku z prawdziwą sprzedażą w sklepie internetowym
od dnia 8.11.2024 raport pomija grupy płatników sklepu internetowego przy wyluczaniu wartości (ilości są uwzględnione,
ale dotyczą momentu zatwierdzenia badań, a nie właściwej sprzedaży w sklepie).

Prawidłowa wartość sprzedaży ze sklepu internetowego jest możliwa do uzyskania od działu ecommerce oraz z systemu Eureca.
        """),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),        
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
    Select(field="grupy", title="Podział na grupy", values={'brak':'Nie','platnicy':'Płatników','badania':'Badań'}, default = 'brak'),
    Switch(field="techniczne", title="Uwzględniać techniczne")
))

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 90)
    laby =  params['laboratoria']
    if len(laby) == 0:
        raise ValidationError('Nie wybrano żadnego laboratorium')
    rep = ReporterDatasource()
    for lab in laby:
        task = {
            'type': 'snr',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'raport_snr'
        }
        report.create_task(task)
    report.save()
    return report

def raport_snr(task_params):
    lab = task_params['target']
    params = task_params['params']
    if params['grupy'] == 'platnicy':
        sql = """select pg.nazwa as "GRUPA", count(W.id) as "ILOSC", sum(case when pg.symbol like '%SKLE' then null else W.nettodlaplatnika end) as "WARTOSC" """
    elif params['grupy'] == 'badania':
        sql = """select pk.hs->'grupa' as "GRUPA", count(W.id) as "ILOSC", sum(case when pg.symbol like '%SKLE' then null else W.nettodlaplatnika end) as "WARTOSC" """
    else:
        sql = """select count(W.id) as "ILOSC", sum(case when pg.symbol like '%SKLE' then null else W.nettodlaplatnika end) as "WARTOSC" """
    sql = sql + """
                from Wykonania W
                    left outer join Platnicy P on W.platnik = P.ID
                    left outer join Platnicywlaboratoriach Pwl on PWL.laboratorium = w.laboratorium and PWL.platnik = P.ID and not pwl.del
                    left outer join pozycjekatalogow pk on pk.symbol=w.badanie and pk.katalog = 'BADANIA'
                    left outer join pozycjekatalogow pg on pg.symbol=pwl.hs->'grupa' and pg.katalog = 'GRUPYPLATNIKOW'
                where
                    w.datarozliczeniowa between
                    and (p.hs->'grupa') is distinct from '%KONT%'  and w.typzlecenia not in ('K', 'KZ', 'KW') and (pwl.hs->'grupa') is distinct from 'ALAB'
            """
    # TODO XXX możliwe sql injection, wrzucać to do parametrów zapytania a nie podstawiać w sqlu
    sql = sql.replace('w.datarozliczeniowa between',"w.datarozliczeniowa between '%s' and '%s' and not W.bezPlatne and not w.jestpakietem and w.laboratorium = '%s'" % (params['dataod'], params['datado'],lab))
    if not params['techniczne']:
        sql = sql + "and (pk.hs->'grupa') is distinct from 'TECHNIC'"
    if params['grupy'] == 'platnicy':
        sql = sql + """group by pg.Nazwa
                       order by Pg.Nazwa"""
    elif params['grupy'] == 'badania':
        sql = sql + """group by pk.hs->'grupa'
                       order by pk.hs->'grupa'"""

    res = []
    with get_snr_connection() as snr:
        wyniki = snr.dict_select(sql)
        for row in wyniki:
            if params['grupy'] == 'brak':
                res.append([lab,row['ILOSC'],prepare_for_json(row['WARTOSC'])])
            else:
                if row['GRUPA'] is None:
                    res.append([lab + ' (Gotówka)',row['ILOSC'],prepare_for_json(row['WARTOSC'])])
                else : 
                    res.append([lab + ' (' + row['GRUPA']+')',row['ILOSC'],prepare_for_json(row['WARTOSC'])])

        rilosc = 0
        rwart = 0
        for row in wyniki:
            if row['ILOSC'] is not None:
                rilosc = rilosc + row['ILOSC']
            if row['WARTOSC'] is not None:
                rwart = rwart + row['WARTOSC']
        if params['grupy'] != 'brak':
            res.append([lab+" RAZEM:",rilosc,prepare_for_json(rwart)])
  
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
    
    for job_id, params, status, result in task_group.get_tasks_results():
        if params['params']['grupy'] == 'platnicy':
            header = ['Laboratorium (grupa płatników)','Liczba badań','Wartość badań']
        elif params['params']['grupy'] == 'badania':
            header = ['Laboratorium (grupa badań)','Liczba badań','Wartość badań']
        else:
            header = ['Laboratorium','Liczba badań','Wartość badań']

        if status == 'finished' and result is not None:
            for wiersz in result:
                wiersze.append(wiersz)
            
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])
    res['results'].append({
        'type': 'table',
        'header': header,
        'data': wiersze,
    })
    res['progress'] = task_group.progress
    return res


