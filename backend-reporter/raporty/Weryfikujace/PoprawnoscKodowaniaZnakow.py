import json

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_snr_connection
from datasources.snr import SNR
from datasources.reporter import ReporterDatasource
from api.common import get_db
from decimal import Decimal

MENU_ENTRY = 'Poprawność kodowania znaków'

REQUIRE_ROLE = ['C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Sprawdzenie poprawności kodowania znaków pod kątem raportów generowanych z SNR.'
             ' Raport z bazy SNR, wg dat rozliczeniowych'),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if params['laboratorium'] is None:
        raise ValidationError('')
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 31)
    lab_task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport_snr',
    }
    report.create_task(lab_task)
    report.save()
    return report


def raport_snr(task_params):
    params = task_params['params']
    rows = []
    rep = ReporterDatasource()
    snr = SNR()
    symbol = params['laboratorium']
    for row in rep.dict_select("select symbol_snr from laboratoria where symbol=%s", [symbol]):
        symbol = row['symbol_snr']
    for row in snr.dict_select("""select w.*, w.hs->'numer' as numerzlecenia, hs->'kodkreskowy' as kodkreskowy
        from wykonaniaipolaczone w
        where w.laboratorium=%s and w.datarozliczeniowa between %s and %s""",
                               [symbol, params['dataod'], params['datado']]):
        try:
            source = json.dumps(prepare_for_json(row))
            encoded = source.encode('cp1250')
            for i, char in enumerate(encoded):
                if int(char) < 32:
                    start = min(0, i-20)
                    raise Exception("Nieprawidłowy znak %s: %s" % (repr(char), repr(encoded[start:][:40])))
            for i, char in enumerate(row['hs']):
                if ord(char) < 32:
                    start = max(0, i-20)
                    raise Exception("Nieprawidłowy znak %s: %s" % (repr(char), repr(row['hs'][start:][:40])))
            decoded = encoded.decode('cp1250')
            if source != decoded:
                raise Exception('Niepoprawne kodowanie (znak spoza CP1250)')
        except Exception as e:
            problem = str(e)
            rows.append([
                row['datarejestracji'],
                row['numerzlecenia'],
                row['kodkreskowy'],
                row['badanie'],
                row['material'],
                problem,
                row['id']
            ])
    return {
        'type': 'table',
        'title': '%s - wykonania z problemami w kodowaniu znaków' % symbol,
        'header': 'Data zlecenia,Numer,Kod kreskowy,Badanie,Materiał,Problem'.split(','),
        'data': prepare_for_json(rows),
    }
