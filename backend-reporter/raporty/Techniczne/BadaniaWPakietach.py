from datasources.centrum import CentrumWzorcowa
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, BadanieSearch, \
    Select, Radio, ValidationError, LabSearch, PlatnikSearch, Switch
from tasks import TaskGroup, Task

MENU_ENTRY = 'Badania w pakietach'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Zestawienie z bazy wzorcowej"""),
    Switch(field='tylkorej', title='Tylko dostępne do rejestracji')
))

SQL = """
    select pak.kolejnosc, bad.kolejnosc,
        trim(pak.symbol), pak.nazwa, pak.ZEROWACCENY, pak.rejestrowac,
        trim(bad.SYMBOL), bad.nazwa, list(trim(mat.symbol))
    from BADANIA pak
    left join BADANIAWPAKIETACH bwp on bwp.PAKIET=pak.id and bwp.del=0
    left join BADANIA bad on bad.id=bwp.BADANIE and bad.del=0
    left join MATERIALY mat on mat.id=bwp.material and mat.del=0
    where pak.del=0 and pak.pakiet=1
    group by 1,2,3,4,5,6,7,8
    order by 1,2
"""

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport'
    }
    report.create_task(task)
    report.save()
    return report

def raport(task_params):
    params = task_params['params']
    cnt = CentrumWzorcowa()
    sql = SQL
    if params['tylkorej']:
        sql = sql.replace('pak.pakiet=1', 'pak.pakiet=1 and pak.rejestrowac=1')
    with cnt.connection() as conn:
        cols, rows = conn.raport_z_kolumnami(sql)
    return {
        'type': 'table',
        'header': 'Pakiet,Pakiet nazwa,Pakiet zeruje ceny składowych,Pakiet do rejestracji,Składowa,Składowa nazwa,Materiały'.split(','),
        'data': [row[2:] for row in rows]
    }