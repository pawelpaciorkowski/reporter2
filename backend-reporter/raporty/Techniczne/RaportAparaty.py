import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch, Select
from helpers.validators import validate_date_range
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none

MENU_ENTRY = 'Raport z Aparatów'

CACHE_TIMEOUT = 7200

"""
[12:58] Adam Morawski

zrobić oddzielny wiersz z błędem BALAB, a liczby zostają tak jak wcześniej
"""

PODZIALY = {
  '--': '-- Wybierz --',
  'platne' : 'Płatne',
  'bezplatne': 'Bezpłatne',
  'platneibezplatne' : 'Płatne i bezpłatne',
}

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Raport z ilości wykonanych badań na Analizatorach (wg dat zatwierdzenia)."""),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria', pokaz_nieaktywne=True),
    DateInput(field='dataod', title='Data początkowa', default='-1D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
    Select(field="podzial", title="Płatne", values=PODZIALY),
    Switch(field="tylko_aktywne", title="Tylko aktywne laboratoria"),
))

DUMMY_ONLY_ACTIVE_LAB_SELECTOR = LabSelector(multiselect=True, field='laboratoria', title='Laboratoria')

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    if 'podzial' not in params or params['podzial'] is None or params['podzial'] == '--':
        raise ValidationError("Wybierz podział płatne/bezpłatne")
    validate_date_range(params['dataod'], params['datado'], 31)
    active_labs = [item['value'] for item in DUMMY_ONLY_ACTIVE_LAB_SELECTOR.get_widget_data('')]
    for lab in params['laboratoria']:
        if params['tylko_aktywne'] and lab not in active_labs:
            continue
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
    lab = task_params['target']
    wiersze = []
    with get_centrum_connection(lab) as conn:
        sql_parameters = [params['dataod'], params['datado'] + ' 23:59:59', lab]
        sql = """
           select
            AP.Symbol as APARAT,
            AP.Nazwa as AN,
            case when AP.Grupa is not null then AG.Symbol || ' - ' || AG.Nazwa else null end as AG,
            B.Symbol as BADANIE,
            B.Nazwa as BADANIENAZWA, 
            trim(bl.symbol) as BLADWYKONANIA,
            count(W.ID) as ILOSCB,
            sum(case
                when tz.symbol in ('K', 'KZ', 'KW') or pl.symbol like '%KONT%' then 1
                else 0 end) as ILOSCK,
            sum(case
                when (tz.symbol is null or tz.symbol not in ('K', 'KZ', 'KW')) 
                    and (pl.symbol is null or pl.symbol not like '%KONT%') then 1
                else 0 end) as ILOSCBK,
            sum(case
                when w.powtorka=1 then 1
                else 0 end) as ILOSCP
            from Wykonania W
            left outer join Aparaty AP on W.aparat = AP.ID
            left join GrupyAparatow AG on AG.id=AP.Grupa
            left outer join Badania B on W.Badanie = B.ID
            left outer join GrupyBadan GB on B.Grupa = GB.ID
            left outer join systemy S on S.id = AP.System
            left join bledywykonania bl on bl.id=w.bladwykonania
            left join zlecenia z on z.id=w.zlecenie
            left join typyzlecen tz on tz.id=z.typzlecenia
            left join platnicy pl on pl.id=z.platnik
            where
            W.Zatwierdzone between ? and ?
            and W.Anulowane is null
            and (w.bladwykonania is null or bl.symbol='BALAB') and S.Symbol = ?
            group by 1,2,3,4,5,6
            order by 2,1
            """
        print(params['podzial'])
        if params['podzial'] == 'platne':
            sql = sql.replace('W.Anulowane is null', 'W.Anulowane is null and w.platne=1')
        elif params['podzial'] == 'bezplatne':
            sql = sql.replace('W.Anulowane is null', 'W.Anulowane is null and w.platne=0')
        cols, rows = conn.raport_z_kolumnami(sql,sql_parameters )

        for row in rows:
            print(row)
            wiersze.append(prepare_for_json(row))

    if len(wiersze) == 0:
        return {
            'title': lab,
            'type': 'info',
            'text': '%s  - Brak danych' % lab
        }
    else:
        return {
            'type': 'table',
            'title': lab,
            'header': 'Aparat,Nazwa,Producent,Badanie,Badanie nazwa,Błąd wykonania,Ilość wszystkie,Ilość kontrole,Ilość niekontrole,Ilość powtórki'.split(','),
            'data': wiersze
        }



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
            res['results'].append(result)
            if start_params is None:
                start_params = params['params']
        elif status == 'failed':
            res['errors'].append("%s - błąd połączenia" % params['target'])
    res['progress'] = task_group.progress
    return res


