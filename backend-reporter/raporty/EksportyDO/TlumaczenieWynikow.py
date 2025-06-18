import copy
import re
import os
import shutil
import base64
import datetime
import time

from datasources.reporter import ReporterDatasource
from datasources.sharepoint import sharepoint_filename
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from helpers.connections import get_centrum_instance
from helpers.crystal_ball.marcel_servers import katalog_wydrukow, sciezka_wydruku
from helpers.validators import validate_date_range, validate_symbol
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none, divide_chunks, random_path, \
    copy_from_remote, ZIP, simple_password, empty
from extras.sprawozdanie_word import SprawozdanieWord, SprawozdanieZCentrum, SprawozdanieWordConfig

MENU_ENTRY = 'Tłumaczenie wyników'

REQUIRE_ROLE = ['C-ADM']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Eksport sprawozdań wymagających tłumaczenia (dorejestrowane badanie TLU-EN), wg daty
        utworzenia oryginalnego sprawozdania."""),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', pokaz_nieaktywne=True),
    DateInput(field='dataod', title='Data początkowa', default='-1D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
    Switch(field='kliniczne', title='Badanie kliniczne')
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 31)
    slownik_fn = sharepoint_filename('tlumaczenia_wynikow_en.xlsx')
    if slownik_fn is None:
        raise ValidationError("Nie udało się pobrać słownika")
    tmp_dir = random_path('tlumaczenie_wynikow_')
    os.makedirs(tmp_dir, 0o755)
    lb_task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': {
            'dataod': params['dataod'],
            'datado': params['datado'],
            'tmp_dir': tmp_dir,
            'slownik_fn': slownik_fn,
            'kliniczne': params['kliniczne'],
        },
        'function': 'report_pobierz',
    }
    report.create_task(lb_task)
    report.save()
    return report


SQL_DOKUMENTY = """
    select wwz.id, wwz.plik, zl.numer, zl.datarejestracji
    from wykonania w 
    left join zlecenia zl on zl.id=w.zlecenie
    left join wydrukiwzleceniach wwz on wwz.zlecenie=zl.id
    where w.badanie in (select id from badania where symbol='TLU-EN') and w.anulowane is null and w.bladwykonania is null
    and wwz.odebrany between ? and ? and wwz.del=0
"""

def report_pobierz(task_params):
    res = {
        'errors': [],
        'results': [],
        'actions': []
    }
    params = task_params['params']
    zip_file = ZIP()
    cnt = get_centrum_instance(task_params['target'])

    word_config = SprawozdanieWordConfig(kliniczne=params['kliniczne'])
    with cnt.connection() as conn:
        cols, rows = conn.raport_z_kolumnami(SQL_DOKUMENTY, [params['dataod'], params['datado'] + ' 23:59:59'])
        ile_znalezionych = ile_pobranych = 0
        for row in rows:
            ile_znalezionych += 1
            szc = SprawozdanieZCentrum(cnt, row[0])
            spr = SprawozdanieWord(szc, params['slownik_fn'], word_config)
            fn = os.path.join(params['tmp_dir'], row[1].split('.', 1)[0] + '.docx')
            spr.generate(fn)
            ile_pobranych += 1
            zip_file.add_file(fn)

    if ile_pobranych == ile_znalezionych:
        res['results'].append({
            'type': 'info',
            'text': f"Pobrano {ile_pobranych} sprawozdań"
        })
    else:
        res['results'].append({
            'type': 'warning',
            'text': f"Pobrano {ile_pobranych}/{ile_znalezionych} sprawozdań"
        })
    if ile_pobranych > 0:
        res['results'].append({
            'type': 'download',
            'content': base64.b64encode(zip_file.save_as_bytes()).decode(),
            'content_type': 'application/zip',
            'filename': 'tlumaczenie_wynikow_%s_%s.zip' % (task_params['target'], datetime.datetime.now().strftime('%Y-%m-%d')),
        })
    shutil.rmtree(params['tmp_dir'])
    return res