import base64
import datetime
import os
import subprocess

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from tasks import TaskGroup, Task
from helpers import empty
from helpers.files import random_path, copy_from_remote

MENU_ENTRY = 'Zestawienia gotówki'

ZNAKI = '-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyząćęłńóśźżĄĆĘŁŃÓŚŹŻ'
ADD_TO_ROLE = ['R-DYR', 'R-PM']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Podaj identyfikator zestawień gotówkowych klienta i dowolną datę z miesiąca, dla którego chcesz pobrać zestawienie.\nUWAGA! Wielkość liter ma znaczenie.'),
    DateInput(field='data', title='Data rozliczenia', default='KZM'),
    TextInput(field='ident', title='Identyfikator')
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['data'] is None:
        raise ValidationError("Nie podano daty")
    if empty(params['ident']):
        raise ValidationError("Nie podano identyfikatora")
    for c in params['ident']:
        if c not in ZNAKI:
            raise ValidationError("Niedozwolone znaki w identyfikatorze")
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport_pobierz'
    }
    report.create_task(task)
    report.save()
    return report


def raport_pobierz(task_params):
    params = task_params['params']
    params['data'] = datetime.datetime.strptime(params['data'], '%Y-%m-%d')
    remote_path = os.path.join('/home/lab/Marcel/Lab/Raport/Gotowka/', params['data'].strftime('%Y-%m'))
    remote_path = os.path.join(remote_path, '%s.xlsx' % params['ident'])
    local_path = random_path('reporter_gotowki', 'xlsx')
    if copy_from_remote('2.0.0.1', remote_path, local_path):
        with open(local_path, 'rb') as f:
            content = base64.b64encode(f.read()).decode()
        os.unlink(local_path)
        return {
            "type": "download",
            "content": content,
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "filename": '%s.xlsx' % params['ident'],
        }
    else:
        return {
            'type': 'error', 'text': 'Nie odnaleziono pliku %s' % remote_path.replace('/home/lab/Marcel/Lab/', '')
        }
