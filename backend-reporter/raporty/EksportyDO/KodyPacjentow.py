import copy
import re
import os
import shutil
import base64
import datetime
import time

# TODO: przy sprawdzaniu czy były kody sprawdzać też kody wykonań a nie tylko zleceń
# przykład LUBLINC listopad 2022 kod 5863358210

from datasources.reporter import ReporterDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from helpers.crystal_ball.marcel_servers import katalog_wydrukow
from helpers.validators import validate_date_range, validate_symbol
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none, divide_chunks, random_path, \
    copy_from_remote, ZIP, simple_password, empty

MENU_ENTRY = 'Kody zleceń pacjentów'

REQUIRE_ROLE = ['C-ADM']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Lista kodów zleceń dla pacjentów z podanymi numerami PESEL we wskazanym labie. Lista może być
        filtrowana po płatniku, zleceniodawcy lub dacie rejestracji."""),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    TextInput(field='pesele', title='PESELe pacjentów (w nowych liniach)', textarea=True),
    DateInput(field='dataod', title='Data początkowa'),
    DateInput(field='datado', title='Data końcowa'),
    TextInput(field='oddzial', title='Pojedynczy zleceniodawca (symbol)'),
    TextInput(field='platnik', title='Pojedynczy płatnik (symbol)'),
))

SQL_CENTRUM_DANE = """
SELECT z.id as zlecenie, z.kodkreskowy, pac.pesel
from ZLECENIA Z
LEFT JOIN PACJENCI pac ON z.PACJENT = pac.ID
LEFT JOIN ODDZIALY o ON z.ODDZIAL = o.ID
LEFT JOIN PLATNICY pl ON z.PLATNIK = pl.ID
WHERE 
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if empty(params['pesele']):
        raise ValidationError("Podaj pesele")
    linie = [pesel.strip() for pesel in params['pesele'].replace('\r\n', '\n').replace('=', '').split('\n')]
    pesele = []
    for linia in linie:
        if linia == '':
            continue
        if linia not in pesele:
            pesele.append(linia)
    if len(pesele) == 0:
        raise ValidationError("Podaj pesele")
    if len(pesele) > 1000:
        raise ValidationError("Max 1000 peseli")
    if not empty(params['oddzial']):
        validate_symbol(params['oddzial'])
    else:
        params['oddzial'] = None
    if not empty(params['platnik']):
        validate_symbol(params['platnik'])
    else:
        params['platnik'] = None
    adres = None
    baza_pg = None
    rep = ReporterDatasource()
    for row in rep.dict_select("select * from laboratoria where symbol=%s", [params['laboratorium']]):
        adres = row['adres_fresh']
        baza_pg = row['baza_pg']
    if adres is None:
        raise ValidationError("Brak adresu serwera dla %s" % params['laboratorium'])
    for chunk in divide_chunks(pesele, 50):
        lb_task = {
            'type': 'centrum',
            'priority': 1,
            'target': params['laboratorium'],
            'params': {
                'adres': adres,
                'baza_pg': baza_pg,
                'pesele': chunk,
                'dataod': params['dataod'],
                'datado': params['datado'],
                'oddzial': params['oddzial'],
                'platnik': params['platnik'],
            },
            'function': 'raport_pobierz',
        }
        report.create_task(lb_task)
    report.save()
    return report


def raport_pobierz(task_params):
    params = task_params['params']
    # print(params)
    sql_params = []
    where = []
    where.append('(%s)' % (' or '.join(['pesel=?' for pesel in params['pesele']])))
    for pesel in params['pesele']:
        sql_params.append(pesel)


    if not empty(params['oddzial']):
        where.append('o.symbol=?')
        sql_params.append(params['oddzial'])
    if not empty(params['platnik']):
        where.append('pl.symbol=?')
        sql_params.append(params['platnik'])
    if not empty(params['dataod']):
        where.append('z.datarejestracji >= ?')
        sql_params.append(params['dataod'])
    if not empty(params['datado']):
        where.append('z.datarejestracji <= ?')
        sql_params.append(params['datado'])
    sql = SQL_CENTRUM_DANE + ' and '.join(where)
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        _, rows = conn.raport_z_kolumnami(sql, sql_params)
        return rows

def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': []
    }

    wiersze = []
    start_params = None
    byly_pesele = []

    for job_id, params, status, result in task_group.get_tasks_results():
        if start_params is None:
            start_params = params['params']
        if status == 'finished' and result is not None:
            for row in result:
                kod = (row[1] or '').strip()
                pesel = row[2].strip()
                wiersze.append([kod, pesel])
                if pesel not in byly_pesele:
                    byly_pesele.append(pesel)
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])

    res['progress'] = task_group.progress

    nie_byly_pesele = []
    for pesel in start_params['pesele']:
        if pesel not in byly_pesele:
            nie_byly_pesele.append(pesel)

    if len(nie_byly_pesele) > 0:
        res['results'].append({
            'type': 'warning',
            'text': 'Nie znaleziono zleceń dla PESELi: %s' % ', '.join(nie_byly_pesele)
        })

    res['results'].append({
        'type': 'table',
        'header': ['kod', 'pesel'],
        'data': wiersze
    })

    return res
