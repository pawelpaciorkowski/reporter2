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

from raporty.Pomocnik._excel import kolumny_szukania, kolumny_wypelnij, ExcelCompleter, ExcelError
from raporty.Pomocnik._szukaj import szukaj_punktu, szukaj_punktu_nieaktywne

MENU_ENTRY = 'Dopasuj punkty pobrań'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Wybierz plik XLSX z danymi do dopasowania.
        Arkusz powinien mieć 1 zakładkę, bez ukrytych wierszy i kolumn i bez nadmiernego formatowania 
        (zostanie ono utracone)
        """),
    FileInput(field="plik", title="Plik"),
    InfoText(text="""Podaj oddzielone spacjami litery kolumn (od A) z danymi do wyszukiwania. Dane będą brane pod uwagę
        w podanej kolejności - np jeśli w wyszukiwanych danych jest ulica z numerem i kod pocztowy, to lepiej żeby
        kolumna ulicy wystąpiła przed kodem"""),
    TextInput(field="kol_szukaj", title="Kolumny wyszukiwania"),
    Switch(field="szukaj_nieaktywne", title="Szukaj także w nieaktywnych"),
    InfoText(text="""Podaj litery kolumn do wpisania danych odnalezionych punktów. Kolumny nie mogą
        pokrywać się z kolumnami wyszukiwania."""),
    HBox(
        TextInput(field="wyp_symbol", title="Symbol"),
        TextInput(field="wyp_nazwa", title="Nazwa"),
        TextInput(field="wyp_mpk", title="MPK"),
    ),
    HBox(
        TextInput(field="wyp_miejscowosc", title="Miejscowość"),
        TextInput(field="wyp_ulica", title="Ulica"),
        TextInput(field="wyp_kodpocztowy", title="Kod pocztowy"),
    ),
    HBox(
        TextInput(field="wyp_lab_symbol", title="Laboratorium"),
        TextInput(field="wyp_email", title="Email"),
        TextInput(field="wyp_telefony", title="Telefony"),
    ),
    HBox(
        TextInput(field="wyp_koordynator", title="Koordynator"),
        TextInput(field="wyp_koordynator_email", title="email koordynatora"),
    ),
    HBox(
        TextInput(field="wyp_dyrektor", title="Dyrektor regionalny"),
        TextInput(field="wyp_dyrektor_email", title="email dyrektora"),
        TextInput(field="wyp_region", title="Region"),
    ),
    HBox(
        TextInput(field="wyp_klasyfikacja", title="Klasyfikacja"),
        TextInput(field="wyp_typ", title="Typ"),
        TextInput(field="wyp_lokalizacja", title="Lokalizacja"),
    ),
    HBox(
        TextInput(field="wyp_partner", title="Spółka prowadząca"),
        TextInput(field="wyp_aktywny", title="Czy punkt aktywny"),
    ),
), hide_download=True)


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if params['plik'] is None:
        raise ValidationError("Nie wybrano pliku")
    params['szukaj'] = kolumny_szukania(params['kol_szukaj'])
    params['wypelnij'] = kolumny_wypelnij(params)
    report = TaskGroup(__PLUGIN__, params)
    lab_task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'function': 'raport_wypelnij',
    }
    report.create_task(lab_task)
    report.save()
    return report


def raport_wypelnij(task_params):
    params = task_params['params']
    if params['szukaj_nieaktywne']:
        funkcja_szukaj = szukaj_punktu_nieaktywne
    else:
        funkcja_szukaj = szukaj_punktu
    try:
        with ExcelCompleter(params['plik']) as excel:
            excel.do_match(funkcja_szukaj, params['szukaj'], params['wypelnij'])
            rep = ReportXlsx({'results': [
                {
                    'type': 'table',
                    'data': prepare_for_json(excel.res_rows),
                }]})
            return {
                'type': 'download',
                'content': base64.b64encode(rep.render_as_bytes()).decode(),
                'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'filename': excel.filename.replace('.xlsx', '_uzupelniony.xlsx'),
            }
    except ExcelError as e:
        return {
            'type': 'error',
            'text': str(e),
        }
