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
# from raporty.Pomocnik._szukaj import szukaj_badania_w_labie
from raporty.Pomocnik._szukaj_badan_new import szukaj_badania_w_labie

MENU_ENTRY = 'Dopasuj badania'

#  Dane wprowadzone w te kolumny będą miały kolor zależny od pewności dopasowania.

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Wybierz plik XLSX z danymi do dopasowania.
        Arkusz powinien mieć 1 zakładkę, bez ukrytych wierszy i kolumn i bez nadmiernego formatowania 
        (zostanie ono utracone)
        """),
    FileInput(field="plik", title="Plik"),
    InfoText(text="""Podaj oddzielone spacjami litery kolumn (od A) z danymi do wyszukiwania..."""),
    TextInput(field="kol_szukaj", title="Kolumny wyszukiwania"),
    Select(field="rodzaj", title="Szukaj", values={
        'auto': 'Automatycznie',
        'badania': 'Tylko badania',
        'pakiety': 'Tylko pakiety',
    }, default='auto'),
    InfoText(text="""Podaj litery kolumn do wpisania danych odnalezionych badań. Kolumny nie mogą
        pokrywać się z kolumnami wyszukiwania. W przypadku wybrania opcji "rozbij pakiety na składowe"
        można wybrać tylko kolumnę symbol, a w przypadku pakietów symbole składowych będą wpisywane w tej
        i w kolejnych kolumnach."""),
    HBox(
        TextInput(field="wyp_symbol", title="Symbol"),
        TextInput(field="wyp_nazwa", title="Nazwa"),
        TextInput(field="wyp_kod", title="Kod ICD.9"),
    ),
    Switch(field='rozbij_pakiety', title='Rozbij pakiety na składowe (tylko symbol, kolejne kolumny)'),
    InfoText(text="""Poniższe dane mogą być dopasowane w kontekście konkretnego laboratorium."""),
    LabSelector(multiselect=False, field='lab', title='Laboratorium'),
    HBox(
        TextInput(field="wyp_metoda", title="Metoda"),
        TextInput(field="wyp_czasmaksymalny", title="Czas maksymalny"),
    ),
), hide_download=True)

MAX_ROWS = 500

SQL_BADANIA_W_PAKIETACH = """
    select 
        trim(pak.symbol) as pakiet,
        trim(bad.SYMBOL) as badanie,
        trim(mat.symbol) as material,
        bad.kolejnosc
    from BADANIA pak
    left join BADANIAWPAKIETACH bwp on bwp.PAKIET=pak.id and bwp.del=0
    left join BADANIA bad on bad.id=bwp.BADANIE and bad.del=0
    left join MATERIALY mat on mat.id=bwp.material and mat.del=0
    where pak.del=0 and pak.pakiet=1
    group by 1,2,3,4
    order by 1, 4
"""


def skladowe_pakietow():
    res = {}
    cnt = CentrumWzorcowa()
    with cnt.connection() as conn:
        cols, rows = conn.raport_z_kolumnami(SQL_BADANIA_W_PAKIETACH)
        for row in rows:
            if row[0] not in res:
                res[row[0]] = []
            res[row[0]].append(row[1])
    return res

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if params['plik'] is None:
        raise ValidationError("Nie wybrano pliku")
    params['szukaj'] = kolumny_szukania(params['kol_szukaj'])
    params['wypelnij'] = kolumny_wypelnij(params)
    print(params['wypelnij'])
    if params['rozbij_pakiety']:
        if len(params['wypelnij'].keys()) != 1 or 'symbol' not in params['wypelnij']:
            raise ValidationError("Przy rozbiciu pakietów na składowe można wypełniać tylko symbol.")
    report = TaskGroup(__PLUGIN__, params)
    lab_task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'function': 'raport_wypelnij',
        'timeout': 600,
    }
    report.create_task(lab_task)
    report.save()
    return report


def raport_wypelnij(task_params):
    params = task_params['params']
    if params['rodzaj'] == 'auto':
        is_bundle = None
    elif params['rodzaj'] == 'badania':
        is_bundle = False
    elif params['rodzaj'] == 'pakiety':
        is_bundle = True
    szukaj_badania = szukaj_badania_w_labie(params['lab'], is_bundle)
    try:
        if params['rozbij_pakiety']:
            skladowe = skladowe_pakietow()
            def rozbij(pole, wartosc):
                if pole == 'symbol':
                    if wartosc in skladowe:
                        return skladowe[wartosc]
                return None
        else:
            skladowe = {}
            def rozbij(pole, wartosc):
                return None
        with ExcelCompleter(params['plik']) as excel:
            if len(excel.rows) > MAX_ROWS:
                raise ExcelError(f"Arkusz zawiera {len(excel.rows)} wierszy - ze względów wydajnościowych może być max {MAX_ROWS}")
            excel.do_match(szukaj_badania, params['szukaj'], params['wypelnij'], rozbij)
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
