import json
from datasources.mop import MopDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty, get_snr_connection
from datasources.reporter import ReporterDatasource
from tasks.db import redis_conn

MENU_ENTRY = 'Raport Diaverum'

REQUIRE_ROLE = ['C-FIN', 'C-CS', 'C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport z wykonanych badań dla Diaverum'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))
labs = ['CZERNIA','LUBLIN','LUBLINC','GWROCLA','WODZISL','LUBARTO', 'ZAWODZI', 'PRZ-ZUR', 'RZESZOW', 'PRZ-TOR']

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 90)
    task = {
            'type': 'snr',
            'priority': 1,
            'params': params,
            'function': 'raport_snr'
        }
    report.create_task(task)
    report.save()
    return report


def raport_snr(task_params):
    params = task_params['params'] # pwl.symbol like '%DIA%' and lower(z.nazwa) like '%diaverum%'
    sql = """
            select
                ZWL.symbol as "PPS",
                Z.nazwa as "PPN",
                w.badanie as "BS",
                w.nazwa as "BN",
                count (w.id) as "ILOSC",
                sum(w.nettodlaplatnika) as "WARTOSC"
            from Wykonania W
                left outer join platnicy p on w.platnik = p.id
                left outer join zleceniodawcy z on W.Zleceniodawca = Z.ID
                left outer join zleceniodawcywlaboratoriach Zwl on ZWL.laboratorium = w.laboratorium and ZWL.zleceniodawca = z.ID and not zwl.del
                left outer join pozycjekatalogow pk on pk.symbol=w.badanie and pk.katalog = 'BADANIA'
                left outer join platnicywlaboratoriach pwl on pwl.laboratorium = w.laboratorium and pwl.platnik=p.id
            where
                w.datarozliczeniowa between
                and not W.bezPlatne and not w.jestpakietem and p.nip='5272534132' and (pk.hs->'grupa') is distinct from 'TECHNIC'
            group by
                ZWL.symbol, z.nazwa, w.badanie, w.nazwa
            order by
                ZWL.symbol, w.badanie

    """ 
    sql = sql.replace('w.datarozliczeniowa between',"""w.datarozliczeniowa between '%s' and '%s' """ % (params['dataod'], params['datado']))

    # and w.laboratorium in ('%s') ### , "','".join(labs)
    res = []
    with get_snr_connection() as snr:
        wyniki = snr.dict_select(sql)
        for row in wyniki:
            res.append([
                row['PPS'],
                row['PPN'],
                row['BS'],
                row['BN'],
                row['ILOSC'],
                prepare_for_json(row['WARTOSC']),
                ])
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
        if status == 'finished' and result is not None:
            for wiersz in result:
                wiersze.append(wiersz)
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])
    res['results'].append({
        'type': 'table',
        'header': 'Symbol Oddziału,Nazwa Oddziału,Symbol Badania,Nazwa Badania,Ilość,Wartość'.split(','),
        'data': wiersze,
    })
    res['progress'] = task_group.progress
    return res