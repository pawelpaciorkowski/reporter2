import config
from datasources.postgres import PostgresDatasource
from datasources.republika import RepublikaDatasource
from datasources.snrkonf import SNRKonf
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, NumberInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
import datetime

MENU_ENTRY = "Stan CDC z Centrum"

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox())

SQL_LAB_SLOTS = """
    SELECT slot_name, confirmed_flush_lsn, pg_current_wal_lsn(), 
        (pg_current_wal_lsn() - confirmed_flush_lsn) AS lsn_distance, active
        FROM pg_catalog.pg_replication_slots where slot_name=?;
"""

SQL_INTERNAL_SLOTS = """
    SELECT slot_name, confirmed_flush_lsn, pg_current_wal_lsn(), 
        (pg_current_wal_lsn() - confirmed_flush_lsn) AS lsn_distance, active
        FROM pg_catalog.pg_replication_slots;
"""


#     select * from  pg_replication_slot_advance ( 'local_processing_bio_klc', '2C8/3E988F18' )

def start_report(params):
    report = TaskGroup(__PLUGIN__, params)
    snr = SNRKonf()
    labs = []
    for row in snr.dict_select("select symbol from laboratoria where hs->'cdc'='True'"):
        labs.append(row['symbol'][:7])
    params['labs'] = labs
    for lab in labs:
        task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'lab_report'
        }
        report.create_task(task)
    task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'function': 'republika_report'
    }
    report.create_task(task)
    task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'function': 'logstream_report'
    }
    report.create_task(task)
    report.save()
    return report


def republika_report(task_params):
    params = task_params['params']
    res = {}
    for lab in params['labs']:
        res[lab] = {'cdc_last_trans': None, 'cdc_last_repl': None, 'lp_last_trans': None, 'lp_dist': None}
    rep = RepublikaDatasource()
    active_labs = []
    for row in rep.dict_select("""
        select src, last_ts  from republika_local_processing rlp where process = 'centrum_indexing'
    """):
        if row['src'] not in res:
            continue
        active_labs.append(row['src'])
        res[row['src']]['lp_last_trans'] = row['last_ts']
    for lab in active_labs:
        for row in rep.dict_select("""
            select src, ts_repl, ts_trans 
            from republika_transactions_raw rtr 
            where src=%s
            order by id desc limit 1
        """, [lab]):
            res[lab]['cdc_last_trans'] = row['ts_trans']
            res[lab]['cdc_last_repl'] = row['ts_repl']
    for row in rep.dict_select(SQL_INTERNAL_SLOTS):
        lab = row['slot_name'].split('_')[-1].upper()
        if lab == 'ZUR':
            lab = 'PRZ-ZUR'
        if lab == 'KLC':
            lab = 'BIO-KLC'
        if lab in res:
            res[lab]['lp_dist'] = row['lsn_distance']
            res[lab]['lp_active'] = row['active']
    return res


def lab_report(task_params):
    params = task_params['params']
    lab = task_params['target']
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(SQL_LAB_SLOTS, [f'{conn.alias}_republika'])
    return rows[0] if len(rows) > 0 else None

def logstream_report(task_params):
    sql = "select * from barcode_occurrences order by id desc limit 1"
    db = PostgresDatasource(dsn=config.Config.DATABASE_REPUBLIKA.replace('dbname=republika', 'dbname=logstream'))  # XXX
    for row in db.dict_select(sql):
        ts = row['ts']
        if datetime.datetime.now() - row['ts'] < datetime.timedelta(hours=2):
            res_type = 'info'
        else:
            res_type = 'warning'
        return { 'type': res_type, 'text': f"Ostatni przetworzony ruch z sorterów: {ts}" }

def lsn_dist_cell(value):
    if value is None:
        return None
    if value < 5000000:
        return value
    if value < 50000000:
        return {'value': value, 'background': '#ffff00'}
    return {'value': value, 'background': '#ff0000'}


def active_cell(value, is_active):
    if is_active:
        return value
    return {'value': value, 'background': '#ff0000', 'title': 'nieaktywne'}


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': []
    }
    lab_status = None
    for job_id, params, status, result in task_group.get_tasks_results():
        if lab_status is None:
            lab_status = {}
            for lab in params['params']['labs']:
                lab_status[lab] = {
                    'symbol': lab, 'lsn_distance': None,
                    'cdc_last_trans': None, 'cdc_last_repl': None, 'lp_last_trans': None, 'lp_dist': None,
                    'cdc_active': None, 'lp_active': None,
                    'uwagi': []
                }
        if status == 'finished' and result is not None:
            if params['function'] == 'lab_report':
                lab = params['target']
                if result is None or result[3] is None:
                    lab_status[lab]['uwagi'].append('Brak slota replikacji!')
                else:
                    lab_status[lab]['lsn_distance'] = result[3]
                    lab_status[lab]['cdc_active'] = result[4]
                    if not result[4]:
                        lab_status[lab]['uwagi'].append('CDC nieaktywne')
            elif params['function'] == 'republika_report':
                for lab, rep_data in result.items():
                    for k, v in rep_data.items():
                        lab_status[lab][k] = v
                    if not lab_status[lab]['lp_active']:
                        lab_status[lab]['uwagi'].append('LP nieaktywny')
            elif params['function'] == 'logstream_report':
                res['results'].append(result)
            else:
                raise RuntimeError(params['function'])
        elif status == 'failed':
            if 'target' in params:
                res['errors'].append('%s - błąd połączenia' % params['target'])
    rows = []
    if lab_status is not None:
        for lab in lab_status.values():
            rows.append([
                active_cell(lab['symbol'], lab['cdc_active']),
                lsn_dist_cell(lab['lsn_distance']),
                lab['cdc_last_trans'],
                lab['cdc_last_repl'],
                lsn_dist_cell(lab['lp_dist']),
                lab['lp_last_trans'],
                ', '.join(lab['uwagi'])
            ])
    # TODO wypełnić
    res['progress'] = task_group.progress
    res['results'].append({
        'type': 'table',
        'header': 'Laboratorium,Opóźnienie slota replikacji,CDC ost. transakcja,CDC ost. replikacja,Opóźn. slota local process,local process ost.,Uwagi'.split(
            ','),
        'data': prepare_for_json(rows)
    })
    return res
