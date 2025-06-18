from datasources.bic import BiCDatasource
from datasources.centrum import CentrumWzorcowa
from datasources.snr import SNR
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json, divide_chunks, empty, get_and_cache
from helpers.validators import validate_date_range, validate_symbol
from datasources.snrkonf import SNRKonf
from datasources.helper import HelperDb
from datasources.synchronizator import SynchronizatorDatasource
from tasks import TaskGroup, Task
import datetime
from helpers.connections import get_centra, get_db_engine

MENU_ENTRY = 'Punkty pobrań'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""
TODO opis
    """),
    # TextInput(field='pojedynczy', title='Pojedynczy punkt (symbol)')
))

SQL_CENTRUM_KANALY = """
    select k.del, k.dc, trim(k.symbol) as symbol, k.nazwa,
        trim(o.symbol) as oddzial, o.nazwa as oddzial_nazwa,
        trim(tz.symbol) as typ_zlecenia, k.ceny
    from kanaly k 
    left join oddzialy o on o.id=k.oddzial 
    left join typyzlecen tz on tz.id=k.typzlecenia 
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    # if not empty(params['pojedynczy']):
    #     validate_symbol(params['pojedynczy'])
    # else:
    #     params['pojedynczy'] = None
    params['pojedynczy'] = None
    task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'function': 'raport_bic',
    }
    report.create_task(task)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport_skarbiec',
    }
    report.create_task(task)
    snr = SNRKonf()
    for row in snr.dict_select("""
        select symbol, vpn as host_centrum_2,
        hs->'vpnic' as host_icentrum_2,
        hs->'adres10' as host_centrum_10,
        hs->'vpnhost' as host_lxd_2,
        hs->'twojewyniki' as nazwa_twojewyniki,
        hs->'instancjappalab' as instancja_ppalab,
        case when hs->'nowesk'='True' then true else false end as nowe_sk,
        case when hs->'cdc'='True' then true else false end as cdc,
        hs->'mpk' as mpk,
        hs->'centrumrozliczeniowe' as centrum_rozliczeniowe,
        hs->'przedrosteksymbolu' as prefiks,
        hs->'symbolplatnika' as po_prefiksie
        from laboratoria where not del and aktywne
    """):
        if empty(row['host_centrum_2']) or empty(row['nazwa_twojewyniki']):
            continue
        task = {
            'type': 'centrum',
            'priority': 1,
            'target': row['symbol'][:7],
            'params': params,
            'function': 'raport_lab',
        }
        report.create_task(task)
    report.save()
    return report


def raport_bic(task_params):
    params = task_params['params']
    bic = BiCDatasource()
    if params['pojedynczy'] is not None:
        return bic.dict_select("select * from config_collection_points where symbol=%s and is_active",
                               [params['pojedynczy']])
    else:
        return bic.dict_select("select * from config_collection_points where is_active order by id desc")


def raport_skarbiec(task_params):
    params = task_params['params']
    return None  # TODO


def raport_lab(task_params):
    lab = task_params['target']
    with get_centrum_connection(lab) as conn:
        return conn.raport_slownikowy(SQL_CENTRUM_KANALY)


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': []
    }
    dane_bic = None
    dane_lab = {}
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            if params['function'] == 'raport_lab':
                for row in result:
                    if row['del'] == 0:
                        if params['target'] not in dane_lab:
                            dane_lab[params['target']] = {}
                        dane_lab[params['target']][row['symbol']] = row
            elif params['function'] == 'raport_bic':
                dane_bic = result
        elif status == 'failed':
            if 'target' in params:
                res['errors'].append('%s - błąd połączenia' % params['target'])
            else:
                res['errors'].append('%s - błąd połączenia' % params['function'])
    res['progress'] = task_group.progress
    if task_group.progress == 1:
        if dane_bic is not None:
            rows = []
            for row in dane_bic:
                symbol = row['symbol']
                lab = row['lab_symbol'][:7]
                nazwa = row['name']
                if lab in dane_lab:
                    if symbol in dane_lab[lab]:
                        kanal = symbol
                        zleceniodawca = dane_lab[lab][symbol]['oddzial']
                    else:
                        kanal = {
                            'background': '#ff0000',
                            'value': 'NIE ZNALEZIONO'
                        }
                        zleceniodawca = None
                else:
                    kanal = zleceniodawca = {
                            'background': '#ffff00',
                            'value': 'BRAK DANYCH'
                        }
                res_row = [symbol, nazwa, lab, kanal, zleceniodawca]
                rows.append(res_row)
            res['results'].append({
                'type': 'table',
                'header': 'Symbol,Nazwa,Lab,Kanał,Domyślny zleceniodawca'.split(','),
                'data': prepare_for_json(rows),
            })
    return res
