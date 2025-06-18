import base64
import datetime
import json
import os

from api.common import get_db
from datasources.wcf import WCFDatasource
from datasources.reporter import ReporterDatasource
from datasources.spreadsheet import spreadsheet_to_values, find_col
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError, Switch, FileInput
from datasources.centrum import CentrumWzorcowa
from tasks import TaskGroup, Task
from helpers import prepare_for_json, generate_barcode_img_tag, get_centrum_connection, slugify, get_and_cache
from helpers.files import random_path
from outlib.xlsx import ReportXlsx
import random
import string

MENU_ENTRY = 'Słowniki WCF'
REQUIRE_ROLE = ['C-ADM']

SLOWNIKI_WCF = None


def get_slowniki_wcf():
    global SLOWNIKI_WCF
    try:
        if SLOWNIKI_WCF is None:
            try:
                wcf = WCFDatasource()
            except:
                return {}
            SLOWNIKI_WCF = {}
            for row in wcf.dict_select("select * from group_services order by service_id"):
                SLOWNIKI_WCF[str(row['service_id'])] = row['name']
        return SLOWNIKI_WCF
    except:
        return {}

SQL_SELECT = """
    select icd9_code, alab_service_code, service_name, comment, service_group, translate_alab_hl7
    from services where group_service_id=%s order by service_id
"""

EXPECTED_HEADER = "icd9_code alab_service_code service_name comment service_group translate_alab_hl7".split(' ')

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Wybierz słownik aby go pobrać. Żeby zaktualizować - wybierz plik."""),
    Select(field="slownik", title="Słownik", values=get_slowniki_wcf()),
    FileInput(field="plik", title="Plik XLSX do importu")
))


def start_report(params, user_login):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'user': user_login,
        'function': 'raport_wcf'
    }
    report.create_task(task)
    report.save()
    return report


def badania_z_materialami():
    res = {'badania': [], 'materialy': []}
    wzory = CentrumWzorcowa()
    with wzory.connection() as conn:
        _, rows = conn.raport_z_kolumnami("select trim(symbol) from badania where del=0")
        for row in rows:
            res['badania'].append(row[0])
        _, rows = conn.raport_z_kolumnami("select trim(symbol) from materialy where del=0")
        for row in rows:
            res['materialy'].append(row[0])
    return res


def raport_wcf(task_params):
    params = task_params['params']
    wcf = WCFDatasource()
    res = {
        'errors': [],
        'results': [],
        'actions': ['xlsx'],
    }
    nazwa_slownika = get_slowniki_wcf()[params['slownik']]
    if params['plik'] is not None:
        rows = None
        ext = slugify(os.path.splitext(params['plik']['filename'])[-1].replace('.', ''))
        tmp_fn = random_path(prefix='reporter', extension=ext)
        with open(tmp_fn, 'wb') as f:
            f.write(base64.b64decode(params['plik']['content']))
        try:
            values = spreadsheet_to_values(tmp_fn)
            header = values[0]
            if header == EXPECTED_HEADER:
                rows = values[1:]
            else:
                res['errors'].append(
                    'Nieprawidłowy nagłówek tabeli (pierwszy wiersz), powinno być: %s' % ';'.join(EXPECTED_HEADER))
        except Exception as e:
            res['errors'].append('Błąd wczytania pliku: %s' % str(e))
        os.unlink(tmp_fn)
        if rows is not None:
            bzm = get_and_cache('badania_z_materialami_wcf', badania_z_materialami, timeout=3600)
            ile_dodanych = 0
            ile_skroconych = 0
            wcf.execute("delete from services where group_service_id=%s", [params['slownik']])
            for row in rows:
                if len(row[2]) > 200:
                    row[2] = row[2][:200]
                    ile_skroconych += 1
                # TODO: sprawdzenie badań itp
                transl = (row[5] or '').split(':=')
                if len(transl) > 1:
                    bad_mat = transl[1].split(':')
                    if bad_mat[0] != '' and bad_mat[0] not in bzm['badania']:
                        res['errors'].append("Nieprawidłowe badanie %s" % bad_mat[0])
                        continue
                    if len(bad_mat) > 1 and bad_mat[1] != '' and bad_mat[1] not in bzm['materialy']:
                        res['errors'].append("Nieprawidłowy materiał %s" % bad_mat[1])
                        continue
                ile_dodanych += 1
                wcf.execute("""
                    insert into services(group_service_id, icd9_code, alab_service_code,
                        service_name, comment, service_group, translate_alab_hl7, notuse)
                    values(%s, %s, %s, %s, %s, %s, %s, 0)
                """, [params['slownik']] + row)
            res['results'].append({
                'type': 'info',
                'text': 'Dodano %d / %d wierszy, %d nazw skróconych' % (ile_dodanych, len(rows), ile_skroconych)
            })
            rep_db = ReporterDatasource(read_write=True)
            rep_db.execute("""
                insert into log_zdarzenia(obj_type, obj_id, typ, opis, parametry)
                values('tools_slowniki_wcf', 0, 'import', %s, %s)
            """, [
                nazwa_slownika, json.dumps(prepare_for_json({
                    'params': params, 'results': res,
                }))
            ])
            rep_db.commit()
    else:
        cols, rows = wcf.select(SQL_SELECT, [params['slownik']])
        xlsx = ReportXlsx({'results': [{
            'type': 'table',
            'header': cols,
            'data': prepare_for_json(rows)
        }]})
        res['results'].append({
            'type': 'download',
            'content': base64.b64encode(xlsx.render_as_bytes()).decode(),
            'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'filename': 'wcf_slownik_%s_%s.xlsx' % (nazwa_slownika, datetime.datetime.now().strftime('%Y-%m-%d')),
        })
    return res
