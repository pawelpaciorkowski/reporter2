import copy
import re
import os
import shutil
import base64
import datetime
import time

from datasources.reporter import ReporterDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from helpers.crystal_ball.marcel_servers import katalog_wydrukow
from helpers.validators import validate_date_range
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none, divide_chunks, random_path, \
    copy_from_remote, ZIP, simple_password, empty, odpiotrkuj

MENU_ENTRY = 'Nieprzyjęte HL7'

REQUIRE_ROLE = ['L-KIER']

LAUNCH_DIALOG = Dialog(title="Raport ze zleceń nieprzyjętych z HL7", panel=VBox(
    InfoText(text="""W raporcie widoczne sa zlecenia i badania, które zostały przesłane przez Klientów po HL-7, a nie zostały automatycznie zarejestrowane w laboratorium."""),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    TextInput(field='system', title='System'),
    DateInput(field='dataod', title='Data początkowa', default='-7D'),
    DateInput(field='datado', title='Data końcowa', default='T'),
    Switch(field='ignoruj_zbwz', title='Ignoruj "Zdublowane badanie w zleceniu!"', default=True),
    Switch(field='pomijaj_wnpz', title='Pomijaj badania z nieprzyjętych w całości zleceń', default=True),
))

SQL_ZZ = """
    select zz.id as zz_id, zz.system, zz.numer, zz.przyszlozzewnatrz as "przyszło", zz.oddzial as zleceniodawca, zz.pacjent,
        zz.parametry, 
        wz.id, wz.numer as wz_numer, wz.badanie, wz.material, wz.wynik as "błąd", wz.parametry as wz_parametry
    from zleceniazewnetrzne zz
    left join wykonaniazewnetrzne wz on wz.zleceniezewnetrzne=zz.id
    where zz.zlecenie is null and zz.przyszlozzewnatrz between ? and ?
    order by zz.id, wz.id
"""

SQL_WZ = """
    select zz.id as zz_id, zl.id as zl_id, zl.datarejestracji, zl.numer as zl_numer, zl.kodkreskowy, 
        trim(pl.symbol) as platnik, trim(o.symbol) as zleceniodawca, wz.system, 
        coalesce(wz.przyszlozcentrum, wz.poszlonazewnatrz) as "przyszło",
        wz.numer, wz.badanie, wz.material, wz.wynik as "błąd", wz.parametry
    from wykonaniazewnetrzne wz
    left join zleceniazewnetrzne zz on zz.id=wz.zleceniezewnetrzne
    left join zlecenia zl on zl.id=zz.zlecenie
    left join oddzialy o on o.id=zl.oddzial
    left join platnicy pl on pl.id=zl.platnik
    where wz.wykonanie is null and (wz.przyszlozcentrum between ? and ? or wz.poszlonazewnatrz between ? and ?)
    order by zz.id, wz.id
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 365)
    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_lab',
    }
    report.create_task(task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']
    dataod = params['dataod']
    datado = params['datado'] + ' 23:59:59'
    res = []
    id_zz = []
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        zlecenia = {}
        sql = SQL_ZZ
        sql_params = [dataod, datado]
        if not empty(params['system']):
            sql = sql.replace('order by zz.id', 'and zz.system=? order by zz.id')
            sql_params.append(params['system'])
        for row in conn.raport_slownikowy(sql, sql_params):
            if row['zz_id'] not in zlecenia:
                id_zz.append(row['zz_id'])
                par = odpiotrkuj(row['parametry'].replace('\n', '\r\n'))
                adres = par.get('Adres')
                if adres is not None and '@' in adres:
                    adres = adres.split('@')[0].replace("\\\\", "\n")
                zlecenia[row['zz_id']] = {
                    'zrodlo': '%s - system: %s\nPrzyszło %s\nID HL7: %s' % (
                        row['zleceniodawca'], row['system'],
                        row['przyszło'], row['numer']
                    ),
                    'dane': 'Kody: %s zewn. %s\nPilność: %s, termin: %s\nLekarz: %s %s\nUwagi: %s' % (
                        par.get('KodKreskowy'), par.get('ObcyKodKreskowy'),
                        par.get('Pilnosc'), par.get('Termin'),
                        par.get('NazwiskoLekarza'), par.get('ImionaLekarza'),
                        par.get('Uwagi')
                    ),
                    'pacjent': '%s\nPESEL: %s\nur. %s\nAdres: %s' % (
                        row['pacjent'], par.get('PESEL'), par.get('DataUrodz'), adres
                    ),
                    'uslugi': [],
                }
            if row['wz_parametry'] is not None:
                wz_par = odpiotrkuj(row['wz_parametry'].replace('\n', '\r\n'))
                zlecenia[row['zz_id']]['uslugi'].append("%s:%s\n&nbsp;&nbsp;&nbsp;&nbsp;(%s, %s)\n&nbsp;&nbsp;&nbsp;&nbsp;pobr. %s, ID HL7: %s; %s" % (
                    row['badanie'], row['material'],
                    wz_par.get('Nazwa usługi'), wz_par.get('Nazwa materiału'),
                    wz_par.get('Godzina'), row['wz_numer'], row['błąd']
                ))
        header = ['Źródło', 'Dane zlecenia', 'Pacjent', 'Zlecone usługi']
        res_rows = []
        for id, zlec in zlecenia.items():
            res_rows.append([
                {'value': zlec['zrodlo'], 'html': zlec['zrodlo'].replace('\n', '<br />') },
                {'value': zlec['dane'], 'html': zlec['dane'].replace('\n', '<br />')},
                {'value': zlec['pacjent'], 'html': zlec['pacjent'].replace('\n', '<br />')},
                {'value': '\n'.join(zlec['uslugi']), 'html': '\n'.join(zlec['uslugi']).replace('\n', '<br />')}
            ])
        res.append({
            'type': 'table',
            'title': 'Zlecenia nieprzyjęte w całości',
            'header': header,
            'data': prepare_for_json(res_rows)
        })
        sql = SQL_WZ
        if params['ignoruj_zbwz']:
            sql = sql.replace("order by", "and wz.wynik <> 'Zdublowane badanie w zleceniu!' order by")
        sql_params = [dataod, datado, dataod, datado]
        if not empty(params['system']):
            sql = sql.replace('order by zz.id', 'and zz.system=? order by zz.id')
            sql_params.append(params['system'])
        rows = conn.raport_slownikowy(sql, sql_params)
        res_rows = []
        for row in rows:
            if params['pomijaj_wnpz'] and row['zz_id'] in id_zz:
                continue
            if row['zl_id'] is not None:
                zlec = '%s / %s\n%s\n%s / %s' % (
                    row['zl_numer'], row['datarejestracji'],
                    row['kodkreskowy'],
                    row['platnik'], row['zleceniodawca']
                )
            else:
                zlec = 'BRAK'
            zlec_hl7 = "System: %s\nID HL7:%s\n%s" % (
                row['system'], row['numer'], row['przyszło'],

            )
            par = odpiotrkuj(row['parametry'].replace('\n', '\r\n'))
            usluga = ["Bad: %s, Mat: %s" % (row['badanie'], row['material'])]
            if (par.get('Nazwa usługi') or '') != '':
                usluga.append("%s (mat.: %s)" % (par.get('Nazwa usługi'), par.get('Nazwa materiału')))
            if (par.get('Godzina') or '') != '':
                usluga.append("Pobr. %s" % par.get('Godzina'))
            res_row = [
                {'value': zlec, 'html': zlec.replace('\n', '<br />')},
                {'value': zlec_hl7, 'html': zlec_hl7.replace('\n', '<br />')},
                {'value': '\n'.join(usluga), 'html': '<br />'.join(usluga)},
                row["błąd"]
            ]
            res_rows.append(res_row)
        cols = ["Zlecenie w Centrum", "Zlecenie HL7", "Usługa", "Problem"]
        res.append({
            'type': 'table',
            'title': 'Nieprzyjęte pojedyncze badania',
            'header': cols,
            'data': prepare_for_json(res_rows)
        })
    return res
