import base64
import datetime
import json
import os
import shutil
import random

import sentry_sdk

from datasources.spreadsheet import spreadsheet_to_values, find_col
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError, Switch, FileInput
from tasks import TaskGroup, Task
from helpers import prepare_for_json, generate_barcode_img_tag, get_centrum_connection, slugify, get_and_cache, empty
from helpers.files import random_path
import random
from datasources.efaktura import EFakturaDatasource


from raporty.Pomocnik._excel import kolumny_szukania, kolumny_wypelnij, ExcelCompleter, ExcelError
# from raporty.Pomocnik._szukaj import szukaj_badania_w_labie
from raporty.Pomocnik._szukaj_badan_new import szukaj_badania_w_labie

MENU_ENTRY = 'Uprawnienia przedstawicieli e-faktura'

#  Dane wprowadzone w te kolumny będą miały kolor zależny od pewności dopasowania.

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Wybierz plik XLSX z danymi do dopasowania.
        Arkusz powinien mieć 1 zakładkę, bez ukrytych wierszy i kolumn
        Powinien zawierać następujące kolumny:
        - Pierwsza kolumna - Numer K
        - Ostatnia kolumna - Email Przedstawiciela
        """),
    FileInput(field="plik", title="Plik"),
), hide_download=True)

MAX_ROWS = 500

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if params['plik'] is None:
        raise ValidationError("Nie wybrano pliku")
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'noc',
        'priority': 1,
        'params': params,
        'function': 'raport_wypelnij',
        'timeout': 600,
    }
    report.create_task(task)
    report.save()
    return report


def aktualizuj_powiazania(db_instance: EFakturaDatasource, success_rows):
    for success_row in success_rows:
        k_number = success_row[0]
        email = success_row[-1]
        user_id = db_instance.get_user_id_by_email(email)
        if user_id and k_number:
            db_instance.update_user_payment_owner_link(user_id, k_number)



def raport_wypelnij(task_params):
    params = task_params['params']
    tmp_fn = random_path(prefix='reporter', extension='.xlsx')
    efak = EFakturaDatasource()
    po_ids = [item[0] for item in efak.get_payment_owners_ids()]
    u_data = [item[0] for item in efak.get_users_email()]
    err_mails = []
    err_knums = []
    success_rows = []
    res = []
    with open(tmp_fn, 'wb') as f:
        f.write(base64.b64decode(params['plik']['content']))
    rows = [row for row in spreadsheet_to_values(tmp_fn) if not all(col is None for col in row)]
    cels = rows.pop(0)
    for row in rows:
        if not row[-1] in u_data:
            err_mails.append(row[-1])
            continue
        if not row[0] in po_ids:
            err_knums.append(row[0])
            continue
        success_rows.append(row)
    table = {"type": "table", "header": cels, "data": success_rows}
    if (err_knums):
        res.append({
            'type': 'error',
            'text': f"Błędne dane w kolumnie numer klienta ({', '.join(err_knums)})"
        })

    if (err_mails):
        res.append({
            'type': 'error',
            'text': f"Błędne dane w kolumnie adres email ({', '.join(err_mails)})"                  
        })
    aktualizuj_powiazania(efak, success_rows)
    res.append(table)
    return res