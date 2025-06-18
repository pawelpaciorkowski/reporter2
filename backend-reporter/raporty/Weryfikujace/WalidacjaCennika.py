import base64
import datetime
import json
import os
import shutil
import random

import sentry_sdk

from api.common import get_db
from datasources.reporter import ReporterDatasource
from datasources.spreadsheet import spreadsheet_to_values, find_col
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError, Switch, FileInput
from datasources.centrum import CentrumWzorcowa
from api_access_client import ApiAccessManager
from tasks import TaskGroup, Task
from helpers import prepare_for_json, generate_barcode_img_tag, get_centrum_connection, slugify, get_and_cache, empty
from helpers.files import random_path
from outlib.xlsx import ReportXlsx
from outlib.email import Email
import random
import string

MENU_ENTRY = 'Walidacja cennika'
REQUIRE_ROLE = ['C-ROZL', 'R-DYR']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Wybierz plik XLSX z cennikiem do weryfikacji.
        Arkusz powinien mieć 1 zakładkę, w niej obowiązkowe kolumny (z nagłówkiem) badanie lub symbol i cena. Inne kolumny mogą być dowolne i będą ignorowane.
        W kolumnie badanie/symbol powinien znajdować się pojedynczy symbol badania. Możliwe jest rozróżnienie na materiał i typ zlecenia (w tej chwili nie sprawdzane) 
        Arkusz nie powinien mieć poukrywanych wierszy, będą one także sprawdzane.
        Jeśli cennik przejdzie sprawdzenie - może być od razu wysłany do Działu Rozliczeń - w tym celu wprowadź w pole poniżej
        dane jednoznacznie identyfikujące klienta / umowę / aneks i zaznacz pole Wyślij. 
        """),
    TextInput(field="nazwa", title="Nazwa klienta / numer umowy itp"),
    Switch(field="wyslij", title="Wyślij poprawny cennik do Działu Rozliczeń"),
    FileInput(field="plik", title="Plik z cennikiem"),
))


def start_report(params, user_login):
    params = LAUNCH_DIALOG.load_params(params)
    if params['plik'] is None:
        raise ValidationError("Nie wybrano pliku")
    if params['wyslij'] and empty(params['nazwa']):
        raise ValidationError("Nie podano danych klienta")
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'hbz',
        'priority': 1,
        'params': params,
        'user': user_login,
        'function': 'raport_zdalny',
        'timeout': 2400,
    }
    report.create_task(task)
    report.save()
    return report


def raport_zdalny(task_params):
    params = task_params['params']
    aam = ApiAccessManager()
    api = aam['snr3']
    res = []
    resp = api.post_json('ext_v1/weryfikuj_cennik', {
        'filename': params['plik']['filename'],
        'base64_content': params['plik']['content']
    }, timeout=2300)
    print(resp)
    if resp['status']:
        res.append({'type': 'info', 'text': 'Weryfikacja przebiegła poprawnie'})
        if params['wyslij']:
            attachment_dir = random_path('reporter')
            os.makedirs(attachment_dir, 0o700)
            try:
                xlsx_fn = os.path.join(attachment_dir, 'cennik.xlsx')
                raport_fn = os.path.join(attachment_dir, 'raport.html')
                with open(xlsx_fn, 'wb') as f:
                    f.write(base64.b64decode(params['plik']['content']))
                with open(raport_fn, 'wb') as f:
                    f.write(base64.b64decode(resp['base64_verification_report']))
                sender = Email()
                subject = 'Alab Reporter: Zweryfikowany cennik %s od %s' % (params['nazwa'], task_params['user'])
                content = 'Użytkownik: %s\nKlient: %s\n\nW załączniku zweryfikowany cennik i raport z cen.'
                content %= (task_params['user'], params['nazwa'])
                sender.send(['rozliczenia@alab.com.pl', 'adam.morawski@alab.com.pl'], subject, content, {
                    xlsx_fn: os.path.basename(params['plik']['filename']),
                    raport_fn: 'raport.html',
                })
            except Exception as e:
                sentry_sdk.capture_exception()
                res.append({'type': 'error', 'text': 'Nie udało się wysłać cennika do rozliczeń: %s' % str(e)})
            finally:
                shutil.rmtree(attachment_dir)



    else:
        for line in resp['errors'].split('\n'):
            if line.strip() != '':
                if line == 'File is not a zip file':
                    line = 'Nie udało się otworzyć pliku XLSX - niepoprawny format pliku'
                res.append({'type': 'error', 'text': line})
    return res