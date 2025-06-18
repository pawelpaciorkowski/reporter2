import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none

MENU_ENTRY = 'Opisy metod'

SQL = """
    select
        trim(p.symbol) as pracownia,
        trim(m.Symbol) as METODA,
        m.NAZWA as METODA_NAZWA,
        m.Opis as METODA_OPIS

    FROM PowiazaniaMetod pm 
    left outer join Badania b on b.id = pm.badanie and b.del = 0 
    left outer join Metody m on m.id = pm.metoda and m.del = 0 
    left outer join Systemy s on s.id = pm.system and s.del = 0 
    left outer join Pracownie p on p.id = m.pracownia and p.del = 0 
    WHERE 
        s.SYMBOL=? and b.symbol=? and pm.del=0 and m.del=0 and b.del=0 and p.del=0
        and pm.dowolnytypzlecenia=1 and pm.dowolnarejestracja=1 and pm.dowolnyoddzial=1 and pm.dowolnyplatnik=1 and pm.dowolnymaterial=1
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Opisy metod domyślnych wskazanego badania w laboratoriach"""),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria', pracownie_domyslne=True),
    BadanieSearch(field='badanie', title='Badanie'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    if params['badanie'] is None:
        raise ValidationError("Nie wybrano badania")
    for lab in params['laboratoria']:
        lab_task = {
            'type': 'centrum',
            'priority': 0,
            'timeout': 60,
            'target': lab,
            'params': params,
            'function': 'raport_lab',
        }
        report.create_task(lab_task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']
    with get_centrum_connection(task_params['target'], load_config=True) as conn:
        system = conn.system_config['system_symbol']
        cols, rows = conn.raport_z_kolumnami(SQL, [system, params['badanie']])
    res = []
    for row in rows:
        res.append([task_params['target']] + row)
    return res


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': ['xlsx']
    }
    wiersze = []
    bledy_polaczen = []
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            wiersze += result
        if status == 'failed':
            bledy_polaczen.append(params['target'])
    if len(bledy_polaczen) > 0:
        res['errors'].append('%s - błąd połączenia' % ', '.join(bledy_polaczen))
    res['results'].append({
        'type': 'table',
        'header': 'Laboratorium,Pracownia,Metoda,Metoda nazwa,Metoda opis'.split(','),
        'data': prepare_for_json(wiersze)
    })
    res['progress'] = task_group.progress
    return res
