from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from outlib.xlsx import ReportXlsx
from helpers import prepare_for_json
from datasources.snr import SNR
import base64
import datetime

MENU_ENTRY = 'Statusy wykonań'

LAUNCH_DIALOG = Dialog(title='Statusy wykonań', panel=VBox(
    LabSelector(field="laboratoria", multiselect=True, title="Laboratoria"),
    DateInput(field="dataod", title="Data rozliczeniowa od", default='PZM'),
    DateInput(field="datado", title="Data rozliczeniowa do", default='KZM'),
))

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    validate_date_range(params['dataod'], params['datado'], 31)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano laboratorium")
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport_snr'
    }
    report.create_task(task)
    report.save()
    return report


def raport_snr(task_params):
    params = task_params['params']
    sql = """
        select laboratorium, statusprzeliczenia, statusrozliczenia, count(id) as cnt
        from wykonania where datarozliczeniowa between %s and %s
        and laboratorium in %s
        group by 1,2,3
        order by 2,3,1
    """
    snr = SNR()
    rows = snr.dict_select(sql, [params['dataod'], params['datado'], tuple(params['laboratoria'])])
    kolumny = {}
    ilosci = {}
    for row in rows:
        for col in ('statusprzeliczenia', 'statusrozliczenia'):
            lab = row['laboratorium']
            status = row[col]
            ilosc = row['cnt']
            if col not in kolumny:
                kolumny[col] = []
            if status not in kolumny[col]:
                kolumny[col].append(status)
            if lab not in ilosci:
                ilosci[lab] = {}
            if col not in ilosci[lab]:
                ilosci[lab][col] = {}
            if status not in ilosci[lab][col]:
                ilosci[lab][col][status] = 0
            ilosci[lab][col][status] += ilosc
    header = ['Laboratorium']
    for col, statusy in kolumny.items():
        for status in statusy:
            header.append("%s: %s" % (col, status))
    result = []
    for lab in sorted(ilosci.keys()):
        res_row = [lab]
        for col, statusy in kolumny.items():
            for status in statusy:
                res_row.append(ilosci[lab][col].get(status, 0))
        result.append(res_row)
    return {
        'type': 'table',
        'header': header,
        'data': prepare_for_json(result)
    }
