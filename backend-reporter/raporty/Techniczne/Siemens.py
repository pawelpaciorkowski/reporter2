import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch, Select
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none

MENU_ENTRY = 'Siemens'

RODZAJ_DAT_PODPIS = {
    'dystrybucja': 'przyjęcia',
    'zatwierdzenie': 'zatwierdzenia',
}

RODZAJ_DAT_POLE = {
    'dystrybucja': 'WYK.Dystrybucja',
    'zatwierdzenie': 'WYK.Zatwierdzone',
}

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Raport z badań wykonywanych jednego dnia, wymagany do analizy przez Siemensa. W przypadku
        raportu po datach przyjęcia (domyślnie) zwracane są wszystkie wykonania nieanulowane."""),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    HBox(
    DateInput(field='data', title='Data', default='-1D'),
        Select(field="rodzaj_dat", title='według', values=RODZAJ_DAT_PODPIS)
    ),
    Switch(field='bez_bledow', title='Pomiń błędy wykonania')
))

SQL = """select 
        Z.Datarejestracji||' / '||Z.Numer as "Order No.",
        WYK.Kodkreskowy as "Sample ID",
        A.Symbol as "Instrument mnemonic",
        A.Nazwa as "Instrument name",
        T.Nazwa as "Sample Priority",
        M.Symbol as "Tube type mnemonic",
        M.Nazwa as "Tube type name",
        Z.Godzinarejestracji as "Time and Date Ordered",
        WYK.Godzina as "Time and Date Collected",
        WYK.Dystrybucja as "Time and Date Received",
        WYK.Wykonane as "Time and Date of Result",
        WYK.Zatwierdzone as "Time and Date Verified",
        B.Symbol as "Test Mnemonic",
        B.Nazwa as "Test Name",
        Pak.Symbol as "Panel Mnemonic",
        Pak.Nazwa as "Panel Name",
        P.Nazwa as "Lab department"
    from Wykonania WYK
        left outer join zlecenia z on z.id = wyk.zlecenie
        left outer join badania b on b.id = wyk.badanie
        left outer join materialy m on m.id = wyk.material
        left outer join pracownie p on p.id = wyk.pracownia
        left outer join aparaty a on a.id = wyk.aparat
        left outer join typyzlecen t on t.id = z.typzlecenia
        left outer join wykonania wykp on wykp.id=wyk.pakiet
        left outer join badania pak on pak.id=wykp.badanie
    where
     $RODZAJ_DAT$ BETWEEN ? AND ? AND WYK.Anulowane is NULL"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if params['laboratorium'] is None:
        raise ValidationError('Nie wybrano laboratorium')
    if params['data'] is None:
        raise ValidationError('Nie wybrano daty')
    report = TaskGroup(__PLUGIN__, params)
    lab_task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_lab',
    }
    report.create_task(lab_task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']
    lab = task_params['target']
    data_od = datetime.datetime.strptime(params['data'], '%Y-%m-%d')
    data_do = data_od + datetime.timedelta(days=1)
    sql = SQL.replace('$RODZAJ_DAT$', RODZAJ_DAT_POLE[params['rodzaj_dat']])
    if params['bez_bledow']:
        sql += ' and wyk.bladwykonania is null'
    with get_centrum_connection(lab) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, [data_od, data_do])
    return cols, prepare_for_json(rows)


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    results = []
    errors = []
    cols = rows = None
    params = None
    lab = None
    for job_id, task_params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            cols, rows = result
            params = task_params['params']
            lab = task_params['target']
        if status == 'failed':
            errors.append('%s - błąd połączenia' % task_params['target'])
    if rows is not None:
        fn = 'siemens_%s_%s.xlsx' % (lab, params['data'])
        rep = ReportXlsx({'results': [{
            'type': 'table',
            'header': cols,
            'data': rows
        }]})
        results.append({
            'type': 'download',
            'content': base64.b64encode(rep.render_as_bytes()).decode(),
            'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'filename': fn,
        })

    return {
        'results': results,
        'progress': task_group.progress,
        'actions': [],
        'errors': errors,
    }