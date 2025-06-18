from datasources.alabinfo import AlabInfoDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
import datetime

MENU_ENTRY = 'Aktualizacje kart badań'

REQUIRE_ROLE = ['L-KIER', 'C-FIN', 'C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="Zestawienie czasów aktualizacji kart badań w Alabinfo"),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'function': 'raport_pojedynczy'
    }
    report.create_task(task)
    report.save()
    return report


def raport_pojedynczy(task_params):
    params = task_params['params']
    info = AlabInfoDatasource()
    cols, rows = info.select("""select lab.code, t.code, tl.date_update, t.date_update
        from test_laboratory tl
        left join test t on t.id=tl.test_id
        left join laboratories lab on lab.id=tl.laboratory_id 
        """)
    wiersze = []
    for row in rows:
        if row[0] in params['laboratoria']:
            wiersze.append(row)
    return {
        'type': 'table',
        'header': 'Laboratorium,Badanie,Akt. def. w laboratorium,Akt. def. centralnej'.split(','),
        'data': prepare_for_json(wiersze)
    }