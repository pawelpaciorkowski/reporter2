from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_snr_connection
from datasources.snr import SNR
from datasources.reporter import ReporterDatasource
from api.common import get_db
from decimal import Decimal

MENU_ENTRY = 'Poprawność replikacji - płatnikami'

REQUIRE_ROLE = ['C-FIN', 'C-ROZL']
# REQUIRE_ROLE = 'ADMIN'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Poprawnosc replikacji płatnikami - pokazuje symbole i grupy płatników, dla których istnieją różnice w ilości wykonanych badań między bazą laboratoryjną i rozliczeniową'),
    LabSelector(multiselect=False, field='lab', title='Laboratorium', symbole_snr=True),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))


def start_report(params):
    laboratoria = []
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 31)
    rep = ReporterDatasource()
    lab_task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['lab'],
        'params': params,
        'function': 'raport_lab',
    }
    report.create_task(lab_task)
    report.save()
    return report


def raport_lab(task_params):
    lab = task_params['target']
    params = task_params['params']
    ilosci_snr = {}
    ilosci_lab = {}

    sql_snr = """
    select
        pwl.symbol as "PLATNIK",
        pwl.hs->'grupa' as "GRUPA",
        count(W.id) as "ILOSC"
    from Wykonania W
        left outer join Platnicy P on W.platnik = P.ID
        left outer join Platnicywlaboratoriach Pwl on PWL.laboratorium = w.laboratorium and PWL.platnik = P.ID and not pwl.del				
        left outer join pozycjekatalogow pk on pk.symbol=w.badanie and pk.katalog = 'BADANIA'
    where 
        w.datarozliczeniowa between %s and %s and not W.bezPlatne and not w.jestpakietem and w.laboratorium = %s and (pk.hs->'grupa') is distinct from 'TECHNIC'
    group by pwl.symbol, pwl.hs->'grupa' 
    order by pwl.symbol, pwl.hs->'grupa'
    """

    sql_centrum = """
    select 
        trim(P.Symbol) as PLATNIK,
        trim(GP.SYMBOL) as GRUPA, 
        count(W.id) as ILOSC
    from Wykonania W
        left outer join Badania B on B.Id = W.Badanie 
        left outer join GrupyBadan gb on gb.id=b.grupa
        left outer join Platnicy P on P.Id = W.Platnik
        left outer join GrupyPlatnikow GP on GP.Id = P.Grupa
    where 
        W.Rozliczone between ? and ? and W.Anulowane is null and W.Platne = 1 and B.Pakiet = 0 and (gb.symbol not in ('TECHNIC') or b.GRUPA is null)
    group by GP.symbol, P.Symbol order by P.Symbol, GP.symbol
    """

    with get_snr_connection() as snr:
        for row in snr.dict_select(sql_snr, (params['dataod'], params['datado'], lab)):
            idx = '%s.%s' % (row['GRUPA'] or '', row['PLATNIK'] or '')
            ilosci_snr[idx] = row['ILOSC']

    with get_centrum_connection(task_params['target'][:7], fresh=True) as conn:
        for row in conn.raport_slownikowy(sql_centrum, [params['dataod'], params['datado']]):
            idx = '%s.%s' % (row['grupa'] or '', row['platnik'] or '')
            ilosci_lab[idx] = row['ilosc']

    res = []
    for idx, ilosc in ilosci_snr.items():
        (grupa, platnik) = idx.split('.')
        if idx in ilosci_lab:
            if ilosc == ilosci_lab[idx]:
                continue
            else:
                res.append([grupa, platnik, ilosci_lab[idx], ilosc, ilosci_lab[idx] - ilosc])
        else:
            res.append([grupa, platnik, 0, ilosc, -ilosc])
    for idx, ilosc in ilosci_lab.items():
        (grupa, platnik) = idx.split('.')
        if idx in ilosci_snr:
            continue
        else:
            res.append([grupa, platnik, ilosc, 0, ilosc])

    if len(res) > 0:
        return {
            'type': 'table',
            'header': 'Grupa płatnika,Płatnik,Ilość lab,Ilość SNR,Różnica'.split(','),
            'data': prepare_for_json(res),
        }
    else:
        return {
            'type': 'info',
            'text': 'Brak rozbieżności'
        }
