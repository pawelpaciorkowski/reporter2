import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from helpers.validators import validate_date_range, validate_symbol, validate_phone_number
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none, list_from_space_separated, \
    empty, slugify, simple_password, send_sms, send_sms_flush_queue, get_snr_connection
from helpers.email import simple_send

MENU_ENTRY = 'Dorejestrowane ręcznie'

REQUIRE_ROLE = ['C-ADM']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Wykaz badań zarejestrowanych ręcznie (nie przez HL7)"""),
    TextInput(field="nipy", title="NIPy płatników (oddzielone spacjami)"),
    DateInput(field='dataod', title='Data początkowa', default='-1D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
    TextInput(field='emails', title='Emaile (oddzielone spacją)'),
))

TRESC_MAILA = """W załączniku zestawienie badań dorejestrowanych ręcznie (przez pracowników laboratorium)"""

SQL = """
    select z.datarejestracji, z.numer, z.KodKreskowy, trim(o.symbol) as "Zleceniodawca",
    o.nazwa as "Zleceniodawca nazwa",
    pr.nazwisko as pracownik,
    trim(b.symbol) as badanie,
    trim(gb.symbol) as grupa_badan
    from Wykonania W
    left join Zlecenia Z on Z.id = W.zlecenie
    left join oddzialy o on o.id=z.oddzial
    left join badania B on B.id = W.Badanie
    left join pracownicy pr on pr.id = w.pracownikodrejestracji
    left join grupybadan gb on gb.id=b.grupa
    where
    w.godzinarejestracji between ? and ? 
    and z.oddzial in (select id from oddzialy where platnik in (select id from platnicy where symbol in ($PLATNICY$)))
    and W.anulowane is null and w.platne=1
    order by z.datarejestracji
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    nipy = list_from_space_separated(params['nipy'], also_comma=True, also_semicolon=True, unique=True)
    params['emails'] = list_from_space_separated(params['emails'], also_comma=True, also_semicolon=True, unique=True)
    if len(nipy) == 0:
        raise ValidationError("Podaj co najmniej 1 nip")
    validate_date_range(params['dataod'], params['datado'], 7)
    sql = """select pwl.symbol, l.symbol as lab, l.vpn 
            from platnicy pl
            left join platnicywlaboratoriach pwl on pwl.platnik=pl.id and not pwl.del
            left join laboratoria l on l.symbol=pwl.laboratorium and not l.del
            where pl.nip in %s and not pl.del"""
    sql_params = [tuple(nipy)]
    with get_snr_connection() as snr:
        pwl = snr.dict_select(sql, sql_params)
        if len(pwl) == 0:
            raise ValidationError(
                "Nie znaleziono pasujących płatników"
            )
    laby = {}
    for row in pwl:
        row['lab'] = row['lab'][:7]
        if row['lab'] not in laby:
            laby[row['lab']] = {'vpn': row['vpn'], 'symbole': []}
        laby[row['lab']]['symbole'].append(row['symbol'])
    report = TaskGroup(__PLUGIN__, params)
    for lab in laby:
        # if lab != 'CZERNIA':
        #     continue # TODO XXX usunąć
        lb_task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': {
                'symbole': laby[lab]['symbole'],
                'dataod': params['dataod'],
                'datado': params['datado'],
                'emails': params['emails'],
            },
            'function': 'raport_lab',
        }
        report.create_task(lb_task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']
    sql = SQL.replace('$PLATNICY$', ','.join(["'%s'" % s for s in params['symbole']]))
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, [params['dataod'], params['datado'] + ' 23:59:59'])
    return rows


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    results = []
    download_results = []
    errors = []
    wiersze = []
    params = None
    for job_id, task_params, status, result in task_group.get_tasks_results():
        if params is None:
            params = task_params['params']
        if status == "finished" and result is not None:
            for row in result:
                [data, numer, kod, zlec, zlec_n, pracownik, badanie, grupa] = row
                if pracownik is None or pracownik.startswith('hl7'):
                    continue
                if grupa == 'TECHNIC':
                    continue
                wiersze.append([task_params['target']] + [data, numer, kod, zlec, zlec_n, badanie])
        elif status == "failed":
            results.append({ "type": "error", "text": "%s - błąd połączenia" % task_params['target'] })
    if task_group.progress == 1.0:
        raport_xlsx = ReportXlsx({"results": [{
            "type": "table",
            "header": "Lab,Data,Numer,Kod kreskowy,Zleceniodawca,Zleceniodawca nazwa,Badanie".split(","),
            "data": prepare_for_json(wiersze),
        }]})
        fn = 'DorejestrowaneRecznie_%s.xlsx' % slugify(params['dataod'])
        raport = {
            "type": "download",
            "content": base64.b64encode(raport_xlsx.render_as_bytes()).decode(),
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "filename": fn,
        }
        results.append(raport)
        download_results.append(raport)
        if len(params['emails']) > 0 and len(wiersze) > 0:
            simple_send(params['emails'], download_results, subject='Zestawienie badań dorejestrowanych ręcznie',
                        content=TRESC_MAILA)
            results.append({
                'type': 'info',
                'text': 'Wygenerowano i wysłano'
            })
    return {
        "results": results,
        "progress": task_group.progress,
        "actions": [],
        "errors": errors,
    }
