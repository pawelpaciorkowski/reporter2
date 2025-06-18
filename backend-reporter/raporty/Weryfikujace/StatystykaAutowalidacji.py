import base64

from api.auth import login_required
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError, Switch
from helpers.strings import get_filename
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection
from datasources.centrum import Centrum
from outlib.xlsx_standalone import RaportXlsxStandalone

SQL = """
    select 
        (EXTRACT(MONTH FROM w.DataRejestracji) || '-' || EXTRACT(DAY FROM w.DataRejestracji)) as DATAREJESTRACJI,
        count (w.id) AS WSZYSTKIE,
        count (distinct w.zlecenie) as WSZYSTKIEZ,
        sum (case when coalesce(w.AUTOWYKONANE, 0) = 1 then 1 else 0 end) AS AW,
        sum (case when coalesce(w.AUTOZATWIERDZONE, 0) = 1 then 1 else 0 end) as AZ
    from wykonania w 
        left outer joiN badania b on b.ID =w.BADANIE
        left outer joiN GRUPYBADAN gb on gb.id = b.GRUPA    
        left outer joiN PRACOWNIE p on p.id =w.PRACOWNIA
        left outer joiN GRUPYPRACOWNI gp on gp.id =p.GRUPA
    WHERE
        w.DATAREJESTRACJI between ? and ? and w.ANULOWANE is null and w.BLADWYKONANIA is null and w.ZATWIERDZONE is not null 
        and (GB.Symbol <> 'TECHNIC' or GB.symbol is null) and gp.symbol ='WEWN' 
        and p.symbol not like '%SERO%' and p.symbol not like '%BAKT%' and p.symbol not like '%GENE%'
          and p.symbol not like '%GENCZ%' and p.symbol not like '%TOKS%' and p.symbol not like '%IMMSE%' 
          and p.symbol not in ('LIGRUZ', 'LICHRO', 'LISPEK')
        and p.symbol <> 'XROZL'
    group by EXTRACT(MONTH FROM w.DataRejestracji), EXTRACT(DAY FROM w.DataRejestracji)
    order by EXTRACT(MONTH FROM w.DataRejestracji), EXTRACT(DAY FROM w.DataRejestracji);
"""

"""
    wywalone na prośbę Angieliki
        sum (case when coalesce(w.AUTOWYKONANE, 0) = -1 then 1 else 0 end) AS NAW,
        sum (case when coalesce(w.AUTOZATWIERDZONE, 0) = -1 then 1 else 0 end) as NAZ
"""

MENU_ENTRY = 'Statystyka autowalidacji'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="Brane są pod uwagę badania wykonane na pracowniach wewnętrznych z wykluczeniem pracowni zawierających w symbolu SERO, BAKT, GENE, GENCZ, TOKS, IMMSE i XROZL"),
    DateInput(field='dataod', title='Data początkowa', default='-7D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    Switch(field='bazatest', title='Baza testowa autowalidacji'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    if params['bazatest'] and len(params['laboratoria']) > 0:
        raise ValidationError("Baza testowa - tylko 1 lab")
    validate_date_range(params['dataod'], params['datado'], 93)
    for lab in params['laboratoria']:
        task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'raport_pojedynczy'
        }
        report.create_task(task)
    report.save()
    return report


def raport_pojedynczy(task_params):
    params = task_params['params']
    oddnia = params['dataod']
    dodnia = params['datado']
    if params['bazatest']:
        cnt = Centrum(adres='2.0.205.233', alias='/var/lib/firebird/autowalidacja.ib')
        conn = cnt.connection()
    else:
        conn = get_centrum_connection(task_params['target'])
    with conn:
        cols, sql_rows = conn.raport_z_kolumnami(SQL, [oddnia, dodnia])
        rows = []
        for row in sql_rows:
            row = list(row)
            row.append("%.02f %%" % (row[3] * 100 / row[1]))
            row.append("%.02f %%" % (row[4] * 100 / row[1]))
            rows.append(row)
        return {
            'type': 'table',
            'header': 'Data rejestracji,Wszystkie badania,Wszystkie zlecenia,Auto wykonane,Auto zatwierdzone,Auto wykonane %,Auto zatwierdzone %'.split(
                ','),
            'data': prepare_for_json(rows)
        }


@login_required
def get_result(ident, user_labs_available):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
    }
    start_params = None
    dane_laby = {}
    for job_id, params, status, result in task_group.get_tasks_results():
        start_params = params['params']
        if status == 'finished' and result is not None:
            dane_laby[params['target']] = result
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])
    if start_params is not None:
        if len(start_params['laboratoria']) == 1 and len(dane_laby.keys()) == 1:
            res['results'].append(list(dane_laby.values())[0])
            res['actions'] = ['xlsx', 'pdf']
        elif task_group.progress == 1:
            xlsx = RaportXlsxStandalone()
            for lab, lab_data in dane_laby.items():
                xlsx.add_sheet(lab)
                xlsx.set_columns(lab_data['header'])
                xlsx.add_rows(lab_data['data'])
            res['results'].append({
                'type': 'download',
                'content': base64.b64encode(xlsx.render_as_bytes()).decode(),
                'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'filename': get_filename('StatystykaAutowalidacji', 'xlsx'),
            })
    res['progress'] = task_group.progress
    return res
