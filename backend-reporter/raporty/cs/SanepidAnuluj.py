import json

from api.common import get_db
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError
from tasks import TaskGroup, Task
from helpers import prepare_for_json, generate_barcode_img_tag, get_centrum_connection
from datasources.sanepid import SanepidDatasource
import random
import string

MENU_ENTRY = 'Sanepid - anuluj zgłoszenie'
REQUIRE_ROLE = ['C-ADM']


LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text='''Wprowadź kod kreskowy i datę urodzenia aby odszukać zgłoszenie.
        Po upewnieniu się że to właściwe zgłoszenie, wprowadź także jego ID żeby anulować.
        Można anulować tylko niepotwierdzone, niewysłane i nieanulowane zgłoszenia.'''),
    TextInput(field='kodkreskowy', title='Kod kreskowy'),
    DateInput(field='dataurodzenia', title='Data urodzenia pacjenta'),
    TextInput(field='id', title='ID zgłoszenia')
))

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if params['kodkreskowy'] is None or len(params['kodkreskowy']) < 6:
        raise ValidationError('Wprowadź prawidłowy kod kreskowy')
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'noc',
        'priority': 1,
        'params': params,
        'function': 'raport_anuluj'
    }
    report.create_task(task)
    report.save()
    return report

def raport_anuluj(task_params):
    params = task_params['params']
    res = {
        'errors': [],
        'results': [],
        'actions': []
    }
    db = SanepidDatasource(read_write=True)
    if params['dataurodzenia'] is not None:
        cols, rows = db.select("""
            select f.name as czynnik, n.* 
            from notifications n
            left join factors f on f.id=n.factor_id 
            where n.barcode=%s and n.patient_birthdate=%s""",
                               [params['kodkreskowy'], params['dataurodzenia']])
    else:
        cols, rows = db.select("""
            select f.name as czynnik, n.* 
            from notifications n
            left join factors f on f.id=n.factor_id 
            where n.barcode=%s and n.patient_birthdate is null""",
                               [params['kodkreskowy']])
    if len(rows) == 0:
        res['errors'].append('Nie znaleziono zgłoszenia')
    else:
        if params['id'] is not None and params['id'] != '':
            ident = canceled_row = None
            for row in rows:
                print('ZZZ', row)
                if str(row[1]) == str(params['id']):
                    ident = row[1]
                    for col, val in zip(cols, row):
                        if col in ('date_sent', 'mail_confirmed') and val is not None:
                            ident = None
                            res['errors'].append('Zgłoszenie już potwierdzone / wysłane :(')
                        if col in ('canceled') and val:
                            ident = None
                            res['errors'].append('Zgłoszenie już anulowane :(')
                    if ident is not None:
                        canceled_row = row
            if ident is not None:
                if params['dataurodzenia'] is not None:
                    db.execute("update notifications set canceled=true where id=%s and barcode=%s and patient_birthdate=%s",
                           [ident, params['kodkreskowy'], params['dataurodzenia']])
                else:
                    db.execute("update notifications set canceled=true where id=%s and barcode=%s and patient_birthdate is null",
                           [ident, params['kodkreskowy']])
                db.commit()
                with get_db() as rep_db:
                    rep_db.execute("""
                        insert into log_zdarzenia(obj_type, obj_id, typ, opis, parametry)
                        values('external_sanepid', %s, 'cancel', %s, %s)
                    """, [
                        ident, __PLUGIN__, json.dumps(prepare_for_json({
                            'row': canceled_row, 'task_params': task_params,
                        }))
                    ])
                    rep_db.commit()
                res['results'].append({'type': 'info', 'text': 'Zgłoszenie anulowane'})
            elif len(res['errors']) == 0:
                res['errors'].append('Nieprawidłowe id')
        else:
            res['results'].append({
                'type': 'table',
                'title': 'zgłoszenia',
                'header': cols,
                'data': prepare_for_json(rows)
            })
    return res
