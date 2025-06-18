import json
from api.common import get_db
from datasources.gjw import GJW, GJWAPI
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError, Switch
from tasks import TaskGroup, Task
from helpers import prepare_for_json, generate_barcode_img_tag, get_centrum_connection, empty
from datasources.ick import IccDatasource
import random
import string

MENU_ENTRY = 'Sprawdź/popraw w GJW'
REQUIRE_ROLE = ['C-ADM']

SQL_GJW = """
    select o.id as "Id", o.barcode as "Kod kreskowy", o.patient_pesel as "PESEL", o.patient_birthdate as "Data ur.",
        lab.symbol as "Lab", cast(o.order_registration_date as date) as "Data zlecenia", o.order_number as "Nr zlecenia",
        o.external_id, o.date_created as "Zlec. w GJW",
        lab.last_check_attempt, lab.last_check_success, lab.ftp_last_check_attempt, lab.ftp_last_check_success,
        array_to_string(array_agg(
            rf.name || ', created: ' || rf.date_created::varchar
            || (case when rf.last_updated is not null then ', updated: ' || rf.last_updated::varchar else '' end)
            || (case when not rf.in_storage then ', niepobr' else '' end) 
            || (case when rf.deleted then ', usunięty' else '' end) 
        ), '; ') as "Pliki"
    from orders o
    left join laboratories lab on lab.id=o.laboratory_id
    left join result_files rf on rf.order_id=o.id
    where left(o.barcode, 9)=%s
    group by 1,2,3,4,5,6,7,8,9,10,11,12,13
    limit 10
"""

SQL_CENTRUM = """
    select zl.datarejestracji as "Data", zl.numer as "Numer", zl.kodkreskowy as "Kod kreskowy",
        pac.pesel as "PESEL", pac.DATAURODZENIA as "Data ur.", pac.NAZWISKO as "Nazwisko", pac.IMIONA as "Imiona"
    from zlecenia zl 
    left join pacjenci pac on pac.id=zl.pacjent
    where zl.id=?
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Sprawdzenie/poprawa danych w GJW. Pole kod kreskowy jest obowiązkowe żeby znaleźć wynik.
        Pole PESEL/data urodzenia można wypełnić dla dodatkowej weryfikacji i odpytania serwisu. Wtedy będzie też możliwe podejrzenie plików PDF."""),
    TextInput(field="kod", title="Kod kreskowy"),
    TextInput(field="pesel", title="PESEL"),
    DateInput(field="dataur", title="Data urodzenia"),
    InfoText(text="""Żeby pobrać / odświeżyć dane z Centrum, zaznacz poniższą opcję oraz wybierz lab, z którego mają zostać pobrane wyniki."""),
    Switch(field="pobierz", title="Pobierz zlecenie z Centrum"),
    LabSelector(field="lab", title="Laboratorium", pokaz_nieaktywne=True)
))

SQL_CENTRUM_ZLECENIA = """
    SELECT z.id AS external_id,
        SUBSTRING(TRIM(z.kodkreskowy) FROM 1 FOR 12) AS barcode,
        TRIM(z.obcykodkreskowy) AS foreign_barcode,
        SUBSTRING(TRIM(p.pesel) FROM 1 FOR 11) AS patient_pesel,
        p.dataurodzenia AS patient_birthdate,
        p.imiona AS patient_firstname, p.nazwisko AS patient_lastname, p.plec AS patient_gender,
        p.telefon AS patient_phone, p.email AS patient_email,
        z.datarejestracji AS order_registration_date,
        z.godzinarejestracji AS order_registration_time,
        z.numer AS order_number,
        CASE WHEN z.anulowane IS NULL THEN 0 ELSE 1 END AS order_canceled,
        z.del AS order_deleted,
        TRIM(od.symbol) AS orderer_symbol, od.nazwa AS orderer_name,
        TRIM(pl.symbol) AS payer_symbol, pl.nazwa AS payer_name
        FROM zlecenia z
        LEFT JOIN pacjenci p on z.PACJENT = p.id
        LEFT JOIN typyzlecen tz on tz.id = z.typzlecenia
        LEFT JOIN oddzialy od ON z.oddzial=od.id
        LEFT JOIN platnicy pl ON z.platnik=pl.id
        WHERE z.KODKRESKOWY like ? 
        AND (tz.symbol NOT IN ('K','KZ','KW') OR tz.symbol IS NULL)
"""

SQL_CENTRUM_WYKONANIA = """
    SELECT w.id AS external_id, w.zlecenie AS order_external_id, b.symbol, b.nazwa AS name, 
        b.czasmaksymalny AS waiting_time,
        w.wydrukowane AS signed_date,
        CASE WHEN w.wydrukowane IS NULL THEN 0 ELSE 1 END AS signed,
        CASE WHEN w.anulowane IS NULL THEN 0 ELSE 1 END AS canceled,
        CASE WHEN w.bladwykonania IS NULL THEN 0 ELSE 1 END AS errored,
        w.del AS deleted
        FROM wykonania w
        LEFT JOIN badania b ON b.id = w.badanie
        LEFT JOIN grupybadan gb ON gb.id = b.grupa
        WHERE w.zlecenie=?
        AND b.niepublikowac = 0 AND b.pakiet = 0
        AND (gb.symbol not in ('TECHNIC') OR b.grupa IS NULL)
        ORDER BY w.id
"""

SQL_CENTRUM_PLIKI = """
    SELECT id AS external_id, zlecenie AS order_external_id, plik AS name, del AS deleted
        FROM wydrukiwzleceniach
        WHERE zlecenie=? AND plik IS NOT NULL
        ORDER BY id
"""

def pobierz_z_centrum(gjw, lab, kodkreskowy):
    res = []
    gjw_lab_id = None
    zlec_gjw_id = None
    for row in gjw.dict_select("select * from laboratories where symbol=%s order by length(database_name) limit 1", [lab]):
        gjw_lab_id = row['id']
    if gjw_lab_id is None:
        res.append(('error', 'Nie znaleziono laboratorium %s w GJW' % lab))
        return None, res
    with get_centrum_connection(lab, fresh=True) as conn:
        zlecenia = conn.raport_slownikowy(SQL_CENTRUM_ZLECENIA, [kodkreskowy + '%'])
        if len(zlecenia) == 0:
            res.append(('error', 'Nie znaleziono pasującego zlecenia w Centrum'))
        for zlec in zlecenia:
            zlec = dict(zlec)
            zlec['laboratory_id'] = gjw_lab_id
            zlec['canceled'] = zlec['order_canceled'] == 1
            del zlec['order_canceled']
            zlec['deleted'] = zlec['order_deleted'] == 1
            del zlec['order_deleted']
            zlecenia_gjw = gjw.dict_select("select * from orders where laboratory_id=%s and external_id=%s", [gjw_lab_id, zlec['external_id']])
            if len(zlecenia_gjw) == 0:
                res.append(('info', 'Zlecenie %d - brak w GJW, do dociągnięcia' % zlec['external_id']))
                zlec_gjw_id = gjw.insert('orders', zlec)
            else:
                zlec_gjw = zlecenia_gjw[0]
                zlec_gjw_id = zlec_gjw["id"]
                zmiany = {}
                for k, v in zlec.items():
                    if zlec_gjw[k] != v:
                        zmiany[k] = v
                opis_zmian = '; '.join(['%s: %s=>%s' % (k, str(zlec_gjw[k]), str(v))])
                if opis_zmian != '':
                    res.append(('info', 'Zlecenie %d jest w GJW, do zmiany: %s' % (zlec['external_id'], opis_zmian)))
                    gjw.update('orders', {'laboratory_id': gjw_lab_id, 'external_id': zlec['external_id']}, zmiany)
                else:
                    res.append(('info', 'Zlecenie %d jest w GJW.' % zlec['external_id']))
            wykonania_gjw = {}
            for row in gjw.dict_select("select * from medical_tests where order_id=%s", [zlec_gjw_id]):
                wykonania_gjw[row["external_id"]] = row
            for wyk in conn.raport_slownikowy(SQL_CENTRUM_WYKONANIA, [zlec['external_id']]):
                wyk = dict(wyk)
                del wyk["order_external_id"]
                for fld in 'canceled signed deleted errored'.split(' '):
                    wyk[fld] = wyk[fld] != 0
                wyk["order_id"] = zlec_gjw_id
                if wyk["external_id"] in wykonania_gjw:
                    res.append(("info", "Wykonanie %d (%s) jest w GJW" % (wyk["external_id"], wyk["symbol"])))
                    # TODO: zmiany
                else:
                    res.append(("info", "Wykonanie %d (%s) brak w GJW - dodajemy" % (wyk["external_id"], wyk["symbol"])))
                    gjw.insert("medical_tests", wyk)
            pliki_gjw = {}
            for row in gjw.dict_select("select * from result_files where order_id=%s", [zlec_gjw_id]):
                pliki_gjw[row["external_id"]] = row
            byly_centrum = []
            for plik in conn.raport_slownikowy(SQL_CENTRUM_PLIKI, [zlec['external_id']]):
                plik = dict(plik)
                plik['in_storage'] = False
                plik['awaiting_download'] = False
                plik['deleted'] = plik['deleted'] != 0
                plik['order_id'] = zlec_gjw_id
                del plik['order_external_id']
                byly_centrum.append(plik['external_id'])
                if plik["external_id"] in pliki_gjw:
                    if plik['deleted']:
                        res.append(("info", "Plik %d (%s) usunięty w Centrum ale jest w GJW - usuwam" % (plik["external_id"], plik["name"])))
                        gjw.update("result_files", {"id": pliki_gjw[plik["external_id"]]["id"]}, {"deleted": True})
                    else:
                        res.append(("info", "Plik %d (%s) jest w GJW" % (plik["external_id"], plik["name"])))
                else:
                    res.append(
                        ("info", "Plik %d (%s) brak w GJW - dodajemy" % (plik["external_id"], plik["name"])))
                    gjw.insert("result_files", plik)
            # for external_id, row in pliki_gjw.items():
            #     if external_id not in byly_centrum:
            #         res.append(("warning", "Plik %d (%s) jest w GJW, ale nie ma już w Centrum - usuwam (%s)" % (external_id, row['name'], repr(row))))


            # TODO: wykonania i pliki
    gjw.commit()
    return zlec_gjw_id, res

def start_report(params, user_login):
    params = LAUNCH_DIALOG.load_params(params)
    if params.get('kod') is None:
        raise ValidationError('Podaj kod kreskowy')
    kod = params['kod'].replace('=', '').strip()
    if len(kod) not in (8, 9, 10, 11, 12):
        raise ValidationError('Podaj pełny kod kreskowy lub pierwsze 9 cyfr')
    params['kod'] = kod
    if not empty(params['pesel']):
        params['tryb'] = 'pesel'
    elif not empty(params['dataur']):
        params['tryb'] = 'data'
    else:
        params['tryb'] = None
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'user': user_login,
        'function': 'raport_gjw'
    }
    report.create_task(task)
    report.save()
    return report


def sprawdz_rowne(val, check):
    if check is None or check.strip() == '':
        return val
    if val is not None and val.strip() == check.strip():
        return val
    return {'value': val, 'background': 'red'}


def raport_gjw(task_params):
    params = task_params['params']
    res = {
        'errors': [],
        'results': [],
        'actions': ['xlsx'],
    }
    kod = params['kod'][:9]
    gjw = GJW(read_write=True)
    if params.get('pobierz'):
        res['results'].append({'type': 'info', 'text': 'Pobieram z %s' % params['lab']})
        zlec_gjw_id, pobierz_result = pobierz_z_centrum(gjw, params['lab'], kod)
        for (text_type, text) in pobierz_result:
            res['results'].append({'type': text_type, 'text': text})
        with get_db() as rep_db:
            rep_db.execute("""
                insert into log_zdarzenia(obj_type, obj_id, typ, opis, parametry)
                values('external_gjw', %s, 'correct', %s, %s)
            """, [
                zlec_gjw_id, __PLUGIN__, json.dumps(prepare_for_json({
                    'id': zlec_gjw_id,
                    'info': pobierz_result,
                    'login': task_params['user'],
                }))
            ])
            rep_db.commit()

    cols, rows = gjw.select(SQL_GJW, [kod])
    rows = [list(row) for row in rows]
    for row in rows:
        row[2] = sprawdz_rowne(row[2], params.get('pesel'))
    if len(rows) == 0:
        res['errors'].append('Nie znaleziono kodu w GJW')
        return res
    else:
        res['results'].append({
            'type': 'table',
            'title': 'Dane w bazie GJW',
            'header': cols,
            'data': prepare_for_json(rows),
        })

    if params['tryb'] is not None:
        file_results = []
        cols = ['Usługa', 'Status', 'Odpowiedź']
        rows = []
        api = GJWAPI()
        service = '???'
        try:
            service = 'Results'
            if params['tryb'] == 'pesel':
                url = 'results/%s?pesel=%s' % (params['kod'], params['pesel'])

            else:
                url = 'results/%s?birthdate=%s' % (params['kod'], params['dataur'])
            sres = api.get(url)
            rows.append([service, 'OK', json.dumps(sres)])
            for order in sres.get('orders', []):
                for file in order.get('files', []):
                    service = 'File %d' % file['id']
                    sres = api.get('files/%d?type=PDF' % file['id'])
                    if sres.get('body') is not None:
                        if sres.get('type') == 'PDF':
                            file_results.append({
                                'type': 'download',
                                'content_type': 'application/pdf',
                                'content': sres['body'],
                                'filename': sres['name'],
                            })
                        if len(sres['body']) > 50:
                            sres['body'] = sres['body'][:50] + '...'
                    rows.append([service, 'OK', json.dumps(sres)])
        except Exception as e:
            rows.append([service, 'ERROR', str(e)])

        res['results'].append({
            'type': 'table',
            'title': 'Odpytanie serwisu GJW',
            'header': cols,
            'data': prepare_for_json(rows),
        })
        res['results'] += file_results

    return res
