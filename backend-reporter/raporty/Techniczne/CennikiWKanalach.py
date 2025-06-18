import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none

MENU_ENTRY = 'Cenniki w kanałach'

REQUIRE_ROLE = ['L-KIER', 'C-FIN', 'C-ROZL']

ADD_TO_ROLE = ['R-DYR', 'C-PP']

CACHE_TIMEOUT = 7200

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Symbole cenników dla kanałów rejestracji internetowej"""),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
))

SQL = """
    select trim(k.symbol) as kanal_symbol, k.nazwa as kanal_nazwa,
    trim(c.SYMBOL) as cennik
    from kanaly k
    left join oddzialy o on o.id=k.oddzial 
    left join platnicy pl on pl.id=o.platnik
    left join POWIAZANIACENNIKOW pc on (
        (pc.PLATNIKNOTNULL=NULLASZERO(pl.id) or pc.dowolnyplatnik=1)
        AND (Pc.TaryfaNotNull = NullAsZero((select first 1 id from taryfy where del=0 and innyplatnik=1)) OR Pc.DowolnaTaryfa = 1)
        AND (Pc.StatusPacjentaNotNull = 0 OR Pc.DowolnyStatusPacjenta = 1)
        AND (Pc.TypZleceniaNotNull = NullAsZero(k.TYPZLECENIA) OR Pc.DowolnyTypZlecenia = 1)
        AND (Pc.MaterialNotNull = 0 OR Pc.DowolnyMaterial = 1)
        AND (Pc.RejestracjaNotNull = NullAsZero(k.REJESTRACJA) OR Pc.DowolnaRejestracja = 1)
        AND (Pc.ObowiazujeDo IS NULL OR Pc.ObowiazujeDo >= 'NOW')
        AND Pc.DEL = 0
    )
    left join cenniki c on c.id=pc.CENNIK
    where k.del=0 and k.tylkopodglad=0 and k.ceny=1
    ORDER BY K.SYMBOL, Pc.DowolnaRejestracja, Pc.DowolnaTaryfa, Pc.DowolnyPlatnik, Pc.DowolnyStatusPacjenta,
    Pc.DowolnyTypZlecenia, Pc.DowolnyMaterial, Pc.ObowiazujeOd DESC NULLS LAST, Pc.ObowiazujeDo NULLS LAST, Pc.ID DESC
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    for lab in params['laboratoria']:
        lab_task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'raport_lab',
        }
        report.create_task(lab_task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']

    symbole_byly = set()
    res = []
    with get_centrum_connection(task_params['target']) as conn:
        sql = SQL
        if conn.db_engine == 'postgres':
            sql = sql.replace('select first 1 id from taryfy where del=0 and innyplatnik=1', 'select id from taryfy where del=0 and innyplatnik=1 limit 1')
        cols, rows = conn.raport_z_kolumnami(sql)
        for row in rows:
            if row[0] not in symbole_byly and row[2] is not None:
                res.append([task_params['target']] + row)
                symbole_byly.add(row[0])
    return res


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': [
            'xlsx',
            {
                'type': 'xlsx',
                'label': 'Excel (płaska tabela)',
                'flat_table': True,
                'flat_table_header': 'Laboratorium',
            }
        ]
    }
    start_params = None
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            res['results'].append({
                'type': 'table',
                'title': params['target'],
                'header': 'Laboratorium,Kanał,Kanał nazwa,Cennik'.split(','),
                'data': prepare_for_json(result)
            })
            if start_params is None:
                start_params = params['params']
        elif status == 'failed':
            res['errors'].append("%s - błąd połączenia" % params['target'])
    res['progress'] = task_group.progress
    return res
