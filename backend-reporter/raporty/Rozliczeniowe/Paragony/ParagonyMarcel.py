import base64
import json

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, Kalendarz, empty
from datasources.ick import IccDatasource
from api.common import get_db
from decimal import Decimal
import datetime

MENU_ENTRY = 'Paragony z Marcela'

REQUIRE_ROLE = ['C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Paragony wg rejestrów z baz marcelowych - wg dat wystawienia + informacja o prośbach o fakturę'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))

SQL_PARAGONY = """
    select par.ZLECENIE, rej.symbol as rejestr, rej.nazwa as rejestr_nazwa, 
        par.DATAWYSTAWIENIA, par.NUMER, par.ANULOWANY, par.DOPISEK as nip, fpl.nazwa as forma_platnosci, 
        case when poz.ZWOLNIONY = 1 then 'ZW' else cast(poz.vat as varchar(10)) end as vat,
        list(trim(bad.SYMBOL)) as BADANIA, sum(poz.WARTOSC) as wartosc
        
    from paragony par 
    left join POZYCJENAPARAGONACH poz on poz.paragon=par.id
    left join REJESTRYPARAGONOW rej on rej.id=par.rejestr
    left join FORMYPLATNOSCI fpl on fpl.id=par.FORMAPLATNOSCI
    left join WYKONANIA wyk on wyk.id=poz.WYKONANIE
    left join badania bad on bad.id=wyk.BADANIE
    
    where par.DATAWYSTAWIENIA between ? and ? and par.del=0
    
    group by 1,2,3,4,5,6,7,8,9
    order by 1
"""

SQL_PROSBY = """
    select pof.ident, pof.system, pof.sys_id, pof.state, pof.created_at, pof.accepted_at,
        pof.barcode, pof.simple_data, pof.helper_data,
        array_agg(ps.status) as statusy, array_agg(ps.ts) as statusy_ts
    from pof 
    left join pof_statusy ps on ps.pof_ident=pof.ident 
    where pof.created_at between %s and %s and system in %s and pof.state != 'DEL'
    group by 1,2,3,4,5,6,7,8,9
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)
    for lab in params['laboratoria']:
        lab_task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'zbierz_lab',
        }
        report.create_task(lab_task)
    lab_task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'function': 'zbierz_icc',
    }
    report.create_task(lab_task)
    report.save()
    return report


def zbierz_lab(task_params):
    params = task_params['params']
    oddnia = params['dataod']
    dodnia = params['datado']
    sql_params = [oddnia, dodnia]
    sql_pg = SQL_PARAGONY.replace('list(trim(bad.SYMBOL))',
                                  "array_to_string(array_agg(trim(bad.symbol)), ' ')").replace('?', '%s')
    with get_centrum_connection(task_params['target']) as conn:
        cols, rows = conn.raport_z_kolumnami(SQL_PARAGONY, sql_params, sql_pg=sql_pg)
        return rows


def zbierz_icc(task_params):
    params = task_params['params']
    kal = Kalendarz()
    kal.ustaw_teraz(params['datado'])
    oddnia = params['dataod']
    dodnia = kal.data('+31D')
    labs = tuple(params['laboratoria'])
    icc = IccDatasource()
    res = {}
    for row in icc.dict_select(SQL_PROSBY, [oddnia, dodnia, labs]):
        if row['system'] not in res:
            res[row['system']] = {}
        res[row['system']][int(row['sys_id'])] = row
    return res


def brutto(netto, vat):
    if empty(vat) or vat == 'ZW':
        return netto
    res = float(netto) * (100 + float(vat))
    return Decimal('%.02f' % (res / 100.0))


def raport_kompletny(dane_marcel, dane_icc):
    cols = "Lab,Rejestr,Rejestr nazwa,Data paragonu,Nr paragonu,Anulowany,NIP,Forma płatności,VAT,Badania,Wartość netto,Wartość brutto".split(
        ',')
    cols += "Prośba o fakturę,Prośba badania,Prośba wartość,Prośba status".split(',')
    rows = []
    for lab in sorted(dane_marcel.keys()):
        for mrow in dane_marcel[lab]:
            zlec_id = mrow[0]
            row = [lab] + mrow[1:]
            wartosc_brutto = brutto(row[-1], row[-3])
            row.append(wartosc_brutto)
            prosba = dane_icc.get(lab, {}).get(zlec_id, None)
            if prosba is not None:
                badania = []
                wartosc = 0.0
                print(prosba['statusy'])
                if prosba['state'] != 'ACK':
                    status = 'Niepotwierdzona'
                elif 'OK' in prosba['statusy']:
                    status = 'BOT wystawił fakturę'
                elif 'error' in prosba['statusy']:
                    status = 'BOT nie potrafił wystawić faktury'
                else:
                    status = 'Potwierdzona, nieobsłużona przez BOTa'
                hd = json.loads(prosba['helper_data'])
                for bad in hd['badania']:
                    badania.append(bad['badanie_symbol'])
                    try:
                        cena = float(bad['cena'])
                    except:
                        cena = 0.0
                    wartosc += cena
                row += [
                    prosba['ident'], ','.join(badania), wartosc, status
                ]
            else:
                row += ['', '', '', '']
            rows.append(row)
    return ReportXlsx({'results': [{
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    }]})


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': ['xlsx']
    }

    results_marcel = {}
    results_icc = {}
    waiting = 0
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            if params['type'] == 'centrum':
                results_marcel[params['target']] = result
            else:
                results_icc = result
        elif status == 'failed':
            if params['type'] == 'centrum':
                res['errors'].append('%s - błąd połączenia' % params['target'])
            else:
                res['errors'].append('Prośby o fakturę - błąd połączenia')
        else:
            waiting += 1

    if waiting == 0:
        rep = raport_kompletny(results_marcel, results_icc)
        fn = 'paragony_marcel_%s.xlsx' % datetime.datetime.now().strftime('%Y%m%d_%H%M')
        res['results'].append({
            'type': 'download',
            'content': base64.b64encode(rep.render_as_bytes()).decode(),
            'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'filename': fn,
        })

    res['progress'] = task_group.progress
    return res
