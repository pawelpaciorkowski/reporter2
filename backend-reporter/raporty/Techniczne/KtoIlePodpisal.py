import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, \
    TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch, Select
from helpers.validators import validate_date_range
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json
from helpers.connections import get_centra, get_db_engine, \
    get_centrum_connection
import re

REQUIRE_ROLE = ['ADMIN']

MENU_ENTRY = 'Kto ile podpisał?'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Raport z ilości podpisanych wyników na osobę w zadanym okresie"""),
    LabSelector(field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))



def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)


def raport_lab(task_params):
    params = task_params['params']