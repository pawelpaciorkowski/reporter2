import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none

MENU_ENTRY = 'Metody wszystkie'

REQUIRE_ROLE = ['L-KIER', 'C-CS', 'L-PRAC']

SQL = """
    select b.symbol as badanie, b.nazwa as badanie_nazwa,
        m.symbol as metoda, m.nazwa as metoda_nazwa,
        case when pm.id is not null then 'T' else '' end as domyslna,
        case when pm.id is not null then 
            case when pm.dowolnytypzlecenia=1 then '(dowolny)' else tz.symbol end
        else '' end as domyslna_typzlecenia,
        case when pm.id is not null then 
            case when pm.dowolnarejestracja=1 then '(dowolna)' else rej.symbol end
        else '' end as domyslna_rejestracja,
        case when pm.id is not null then 
            case when pm.dowolnymaterial=1 then '(dowolny)' else mat.symbol end
        else '' end as domyslna_material,
        pm.DNITYGODNIA as domyslna_dnitygodnia
    from badania b
    left join metody m on m.badanie=b.ID
    left join POWIAZANIAMETOD pm on pm.BADANIE=b.id and pm.METODA=m.id and pm.DEL=0 and (pm.DOWOLNYSYSTEM=1 or pm.SYSTEM=(select id from systemy where symbol=? and del=0))
    left join TYPYZLECEN tz on tz.id=pm.TYPZLECENIA
    left join REJESTRACJE rej on rej.id=pm.REJESTRACJA
    left join MATERIALY mat on mat.id=pm.MATERIAL
    where b.del=0 and m.del=0 and m.NIECZYNNA=0    
    order by b.KOLEJNOSC, b.symbol, m.KOLEJNOSC
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria', pracownie_domyslne=True),
    BadanieSearch(field='badanie', title='Pojedyncze badanie'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    if len(params['laboratoria']) > 1 and (params['badanie'] is None or params['badanie'] == ''):
        raise ValidationError("Albo pojedyncze badanie albo pojedynczy lab")
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
    sql = SQL
    sql_params = [task_params['target']]
    if params['badanie'] is not None and params['badanie'] != '':
        sql = sql.replace('m.NIECZYNNA=0', 'm.NIECZYNNA=0 and b.symbol=?')
        sql_params.append(params['badanie'])
    res = []
    with get_centrum_connection(task_params['target']) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
        return rows

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
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            if isinstance(result, list):
                for row in result:
                    wiersze.append([params['target']] + row)
            else:
                res['results'].append(result)
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])
    res['progress'] = task_group.progress
    res['results'].append({
        'type': 'table',
        'header': 'Laboratorium,Badanie,Badanie nazwa,Metoda,Metoda nazwa,Domyślna,Domyślna - typ zlecenia,Domyślna - rejestracja,Domyślna - materiał,Domyślna - dni tygodnia'.split(','),
        'data': prepare_for_json(wiersze)
    })
    return res