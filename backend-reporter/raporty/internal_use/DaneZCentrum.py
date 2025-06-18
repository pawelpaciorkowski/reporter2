import re
import os
import shutil
import base64
import datetime
import time

from datasources.reporter import ReporterDatasource
from datasources.kakl import KaKlDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from helpers.validators import validate_date_range
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none, divide_chunks, random_path, \
    copy_from_remote, ZIP, simple_password, list_from_space_separated

MENU_ENTRY = 'Dane z Centrum'

LAUNCH_DIALOG = Dialog(title="Dane wykonań z baz Centrum", panel=VBox(
    LabSelector(multiselect=False, field='lab', title='Laboratorium'),
    TextInput(field='wykonania', title='Id wykonań (oddzielone spacjami)', textarea=True),
))

SQL = """
    select w.id, 
        pac.numer as pacjent_numer,
        wz.numer as wykonaniezewnetrzne_numer,
        zz.numer as zleceniezewnetrzne_numer,
        wz.system as s1, zz.system as s2 
    
    from wykonania w
    left join zlecenia zl on zl.id=w.zlecenie
    left join pacjenci pac on pac.id=zl.pacjent
    left join zleceniazewnetrzne zz on zz.zlecenie=zl.id
    left join wykonaniazewnetrzne wz on wz.wykonanie=w.id and  wz.zleceniezewnetrzne=zz.id
    
    where w.id in ($IDENTS$)
    
    order by id, wz.numer nulls first 
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    wykonania = []
    for wyk in list_from_space_separated(params['wykonania'], also_comma=True, also_semicolon=True, unique=True):
        if len(wyk) > 0:
            try:
                wykonania.append(str(int(wyk)))
            except:
                raise ValidationError("Nieprawidłowe id: %s" % wyk)
    params['wykonania'] = wykonania
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['lab'],
        'params': params,
        'function': 'raport_lab'
    }
    report.create_task(task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']
    res = None
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        for chunk in divide_chunks(params['wykonania'], 500):
            sql = SQL.replace('$IDENTS$', ','.join(chunk))
            cols, rows = conn.raport_z_kolumnami(sql)
            if res is None:
                res = {
                    'type': 'table',
                    'header': cols,
                    'data': prepare_for_json(rows)
                }
            else:
                res['data'] += prepare_for_json(rows)
    return res
