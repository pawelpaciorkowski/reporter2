from datasources.centrum import CentrumWzorcowa
from datasources.snr import SNR
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from raporty.Rozliczeniowe.dlaKlientow.raportNFZ import wiersze
from tasks import TaskGroup, Task
import datetime

MENU_ENTRY = 'Czynne pracownie'

REQUIRE_ROLE = ['L-KIER', 'C-FIN', 'C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="Lista pracowni z SNR"),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    Switch(field="bezwysylek", title="Bez wysyłkowych"),
    Switch(field="tylkowysylki", title="Tylko wysyłkowe"),
    Switch(field="bazylab", title="Raport z baz laboratoryjnych (a nie z SNR, w której nie wszystko jest)"),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    if params['bazylab']:
        for lab in params['laboratoria']:
            task = {
                'type': 'centrum',
                'priority': 1,
                'target': lab,
                'params': params,
                'function': 'raport_pojedynczy'
            }
            report.create_task(task)
    else:
        task = {
            'type': 'snr',
            'priority': 1,
            'params': params,
            'function': 'raport_snr'
        }
        report.create_task(task)
    report.save()
    return report


def raport_pojedynczy(task_params):
    params = task_params['params']
    warunki = []
    sql = """
        select trim(s.symbol), trim(pr.symbol), pr.nazwa, trim(gr.symbol)
        from pracownie pr
        left join systemy s on s.id=pr.SYSTEM
        left join grupypracowni gr on gr.id=pr.grupa
        where pr.del = 0 
    """
    res = {
        'type': 'table',
        'header': 'System,Symbol,Nazwa,Grupa'.split(','),
    }
    get_connection = lambda: CentrumWzorcowa().connection()
    if params['bezwysylek']:
        warunki.append('pr.zewnetrzna=0')
    if params['tylkowysylki']:
        warunki.append('pr.zewnetrzna=1')
    if params['bazylab']:
        get_connection = lambda: get_centrum_connection(task_params['target'])
        res['title'] = task_params['target']
    if len(warunki) > 0:
        sql += " and " + " and ".join(warunki)
    sql += """ order by 1, 2"""
    wiersze = []
    with get_connection() as conn:
        cols, rows = conn.raport_z_kolumnami(sql)
        for row in rows:
            if params['bazylab']:
                if row[0] is None or row[0].strip() == task_params['target']:
                    wiersze.append(row)
            else:
                if (row[0] or '').strip() in params['laboratoria']:
                    wiersze.append(row)
    res['data'] = wiersze
    return res

def raport_snr(task_params):
    params = task_params['params']
    sql = """
        select symbol, nazwa, hs->'grupa' as grupa, hs->'system' as system, 
        hs->'zewnetrzna'='True' as zewnetrzna, hs->'wykluczlaboratoria' as wykluczlaboratoria,
        wszystkielaboratoria, wybranelaboratoria 
        from pozycjekatalogow where katalog='PRACOWNIE' and not del
    """
    snr = SNR()
    wiersze = []
    pws = {}
    for row in snr.dict_select(sql):
        for lab in params['laboratoria']:
            if not row['wszystkielaboratoria'] and lab not in (row['wybranelaboratoria'] or ''):
                continue
            if lab in (row['wykluczlaboratoria'] or ''):
                continue
            if params['bezwysylek'] and row['grupa'] in ('ALAB', 'ZEWN'):
                continue
            if params['tylkowysylki'] and row['grupa'] == 'WEWN':
                continue
            if row['grupa'] == 'ALAB' and row['system'][:7] == lab[:7]:
                continue
            if lab not in pws:
                pws[lab] = []
            pws[lab].append([row['symbol'], row['nazwa'], row['grupa']])
    for lab, wiersze_l in pws.items():
        for wiersz in wiersze_l:
            wiersze.append([lab] + wiersz)
    return {
        'type': 'table',
        'header': 'System,Symbol,Nazwa,Grupa'.split(','),
        'data': prepare_for_json(wiersze)
    }