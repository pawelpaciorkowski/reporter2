from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_bank_krwi_connection, get_snr_connection

MENU_ENTRY = 'Wyniki z dnia'


LAUNCH_DIALOG = Dialog(title='Wyniki pojedynczego parametru wpisane w dniu', panel=VBox(
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    DateInput(field='data', title='Data', default='-1D'),
    TextInput(field='parametr', title='Symbol parametru'),
))

SQL = """
    select z.numer, z.datarejestracji, z.kodkreskowy, z.zewnetrznyidentyfikator,
        b.symbol, p.symbol, y.wyniktekstowy, y.opis, y.dc as wynik_wpisany,
        (select list(b2.symbol) from wykonania w2 left join badania b2 on b2.id=w2.badanie where w2.zlecenie=z.id) as badaniawzleceniu
    from wyniki y
    left join parametry p on p.id=y.parametr
    left join wykonania w on w.id=y.wykonanie
    left join zlecenia z on z.id=w.zlecenie
    left join badania b on b.id=w.badanie
    where y.dc between ? and ? and y.ukryty=0 and y.wyniktekstowy is not null
        and p.symbol=?
    order by 2, 1
"""

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError('Wybierz lab')
    if params['data'] is None:
        raise ValidationError('Wpisz datę')
    if params['parametr'] is None or params['parametr'].strip() == '':
        raise ValidationError('Wpisz symbol parametru')

    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_lab'
    }
    report.create_task(task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']
    with get_centrum_connection(task_params['target']) as conn:
        cols, rows = conn.raport_z_kolumnami(SQL, [params['data'], params['data']+' 23:59:59', params['parametr']])
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    }
