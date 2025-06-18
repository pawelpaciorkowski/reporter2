from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch
from helpers.files import run_on_remote
from tasks import TaskGroup, Task
from outlib.xlsx import ReportXlsx
from helpers import prepare_for_json
from datasources.snr import SNR
import base64
import datetime

MENU_ENTRY = 'Stan wczytywania'

LAUNCH_DIALOG = Dialog(title='Stan wczytywania przesyłek', panel=VBox(
    InfoText(text='''Informacja o tym czy aktualnie trwa wczytywanie przesyłek / kiedy ostatnio się zakończyło.''')
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport_snr'
    }
    report.create_task(task)
    report.save()
    return report


def data_z_linii(l):
    l = l.strip()
    if ' ' not in l:
        return None
    t = l.split(' ')
    return ' '.join(t[5:-1])

def raport_snr(task_params):
    res = []
    log_stdout, _ = run_on_remote('centrum-system@2.0.4.101', 'ls -la /var/www/alab/opal/rozpakuj_przesylki.sh.log')
    lck_stdout, _ = run_on_remote('centrum-system@2.0.4.101', 'ls -la /var/www/alab/opal/rozpakuj_przesylki.sh.lck')
    log_data = data_z_linii(log_stdout)
    lck_data = data_z_linii(lck_stdout)
    if lck_data is not None:
        res.append({
            "type": "info",
            "text": "Trwa wczytywanie przesyłek od %s. Ostatnia zmiana: %s" % (lck_data, log_data)
        })
    else:
        res.append({
            "type": "info",
            "text": "Obecnie przesyłki nie są wczytywane. Ostatnie sprawdzenie/wczytywanie: %s" % log_data
        })
    return res
