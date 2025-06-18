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
    copy_from_remote, ZIP, simple_password

MENU_ENTRY = 'Płatnicy bez kart'

REQUIRE_ROLE = ['C-CS']
ADD_TO_ROLE = ['R-DYR', 'R-PM']

SQL = """
    select kp.nazwa, kp.symbole, kp.nip, concat(ks.imie, ' ', ks.nazwisko) AS przedstawiciel_snr from kartoteki_platnik kp
    left join kartoteki_laboratorium_platnicy klp on klp.platnik_id = kp.id
    left join kartoteki_snrprzedstawiciel ks on kp.snr_przedstawiciel_id = ks.id
    left join kartoteki_laboratorium kl on kl.id = klp.laboratorium_id
    where not exists (select kk2.platnik_id from kakl_kartaklienta kk2 where kk2.platnik_id = kp.id) and kl.symbol in %s
"""

LAUNCH_DIALOG = Dialog(title="Zestawienie płatników, którzy nie mają podpiętej karty klienta", panel=VBox(
    LabSelector(multiselect=True, field='laboratoria', title='Laboratorium'),
))


def start_report(params):
    report = TaskGroup(__PLUGIN__, params)
    params = LAUNCH_DIALOG.load_params(params)
    if len(params['laboratoria']) == 0:
        raise ValidationError('')
    task = {"type": "noc", "priority": 1, "params": params, "function": "raport_djalab"}
    report.create_task(task)
    report.save()
    return report


def raport_djalab(task_params):
    params = task_params['params']
    kakl = KaKlDatasource()
    cols, rows = kakl.select(SQL, [tuple(params['laboratoria'])])
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    }
