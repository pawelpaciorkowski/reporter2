from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch
from tasks import TaskGroup, Task
from outlib.xlsx import ReportXlsx
from helpers import prepare_for_json
from datasources.snr import SNR
import base64
import datetime

MENU_ENTRY = 'Umowy'

ADD_TO_ROLE = ['R-PM']

LAUNCH_DIALOG = Dialog(title='Eksport umów z SNR', panel=VBox(
    Switch(field='aktywne', title='Tylko aktywne')
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'eksport_snr'
    }
    report.create_task(task)
    report.save()
    return report


def eksport_snr(task_params):
    params = task_params['params']
    cols = 'Numer K,Nazwa,NIP,Rodzaj,Data wystawienia,Identyfikator,Centrum rozliczeniowe,Obowiązuje od,Obowiązuje do,Data podpisania,Status'.split(
        ',')
    sql = """select
        pl.hs->'umowa',
        pl.nazwa,
        pl.nip,
        um.rejestr,
        um.datawystawienia,
        um.identyfikatorwrejestrze,
        um.centrumrozliczeniowe,
        um.oddnia,
        um.dodnia,
		um.hs->'datapodpisania' as datapodpisania,
        CASE
                WHEN um.aktywna THEN 'Aktywna'::text
                ELSE
                CASE
                    WHEN public.chartoboolean(((um.hs->'wycofana'::text))::character varying, false) THEN 'Wycofana'::text
                    ELSE
                    CASE
                        WHEN um.gotowa THEN 'Gotowa'::text
                        ELSE 'Wprowadzana'::text
                    END
                END
            END as status
        
    
    from umowy um
    left join platnicy pl on pl.id=um.platnik
    
    where not um.del
    order by pl.hs->'umowa', oddnia, dodnia"""
    if params['aktywne']:
        sql = sql.replace('not um.del', 'not um.del and um.aktywna')
    snr = SNR()
    _, rows = snr.select(sql)
    return cols, rows


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    results = []

    for job_id, task_params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            cols, rows = result
            rep = ReportXlsx({'results': [{
                'type': 'table',
                'header': cols,
                'data': prepare_for_json(rows)
            }]})
            results.append({
                'type': 'download',
                'content': base64.b64encode(rep.render_as_bytes()).decode(),
                'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'filename': 'umowy_snr_%s.xlsx' % datetime.datetime.now().strftime('%Y%m%d'),
            })

    return {
        'results': results,
        'progress': task_group.progress,
        'actions': [],
        'errors': [],
    }
