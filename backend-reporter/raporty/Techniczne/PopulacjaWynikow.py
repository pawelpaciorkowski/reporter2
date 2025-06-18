import datetime

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, BadanieSearch, Switch
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, Kalendarz

MENU_ENTRY = 'Populacja wyników'

REQUIRE_ROLE = ['C-CS']
ADD_TO_ROLE = ['R-MDO']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='''Raport populacyjny z wyników liczbowych. Można wpisać przedziały wyników (liczby oddzielone spacjami) 
                lub zostawić to pole puste - wtedy wyniki zostaną podzielone wg wartości referencyjnych. Max okres 1 rok.'''),
    TextInput(field="badanie", title="Symbol badania"),
    TextInput(field="parametr", title="Symbol parametru"),
    DateInput(field='oddnia', title='Data początkowa', default='PZM'),
    DateInput(field='dodnia', title='Data końcowa', default='KZM'),
    TextInput(field='przedzialy', title='Przedziały wyników'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria', pokaz_nieaktywne=True),
    Switch(field='podzial_wiek', title='Podział na grupy wiekowe')
))

SQL_WYNIKI = """
    select extract(year from w.zatwierdzone) as "Rok",
            extract(month from w.zatwierdzone) as "Miesiąc",
            pl.symbol as "Płeć", 
            gw.nazwa as "Grupa wiekowa", 
            $PRZEDZIALY$
        from badania bad
        left join wykonania w on bad.id=w.badanie
        left join wyniki y on y.wykonanie=w.id
        left join parametry par on par.id=y.parametr
        left join zlecenia z on z.id=w.zlecenie
        left join pacjenci pac on pac.id=z.pacjent
        left join plci pl on pl.id=pac.plec
        left join GrupyWiekowe GW ON GW.ID = GrupaWiekowa2(Z.DataRejestracji, Pac.DataUrodzenia, Pac.RokUrodzenia)
        left join TypyZlecen TZ on TZ.id = Z.TypZlecenia
    where bad.symbol=? and par.symbol=? and w.zatwierdzone between ? and ?
    and w.bladwykonania is null and y.ukryty=0 and TZ.Symbol not in ('K', 'KW', 'KZ')
"""

SQL_PRZEDZIALY_NORMY = """
            sum(case when y.flaganormy=1 then 1 else 0 end) as "Poniżej", 
            sum(case when y.flaganormy=0 or y.flaganormy is null then 1 else 0 end) as "W normie", 
            sum(case when y.flaganormy=2 then 1 else 0 end) as "Powyżej"
"""



def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    print('startReport', __PLUGIN__, params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    validate_date_range(params['oddnia'], params['dodnia'], 366)
    przedzialy = []
    if params['przedzialy'] is not None:
        for val in params['przedzialy'].replace(',', '.').split(' '):
            if len(val) > 0:
                try:
                    nval = float(val)
                except:
                    raise ValidationError("Nieprawidłowa wartość liczbowa %s" % val)
                if len(przedzialy) > 0 and nval <= przedzialy[-1]:
                    raise ValidationError("Podaj przedziały w kolejności rosnącej")
                przedzialy.append(nval)
    params['przedzialy'] = przedzialy
    for fld in ('badanie', 'parametr'):
        if params[fld] is None or len(params[fld].strip()) == 0:
            raise ValidationError("Podaj %s" % fld)
    for lab in params['laboratoria']:
        task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'raport_wyniki'
        }
        report.create_task(task)
    report.save()
    return report

"""
            sum(case when y.flaganormy=1 then 1 else 0 end) as "Poniżej", 
            sum(case when y.flaganormy=0 or y.flaganormy is null then 1 else 0 end) as "W normie", 
            sum(case when y.flaganormy=2 then 1 else 0 end) as "Powyżej"
"""

def raport_wyniki(task_params):
    params = task_params['params']
    oddnia = params['oddnia']
    dodnia = params['dodnia']
    badanie = params['badanie'].strip().upper()
    parametr = params['parametr'].strip().upper()
    res = []
    sql = SQL_WYNIKI
    if len(params['przedzialy']) == 0:
        sql_przedzialy = SQL_PRZEDZIALY_NORMY
    else:
        przedz = params['przedzialy']
        sql_przedzialy = []
        sql_przedzialy.append('sum(case when y.wynikliczbowy < %f then 1 else 0 end) as "< %0.2f"' % (przedz[0], przedz[0]))
        if len(przedz) > 1:
            for i in range(len(przedz)-2):
                vmin = przedz[i]
                vmax = przedz[i+1]
                sql_przedzialy.append('sum(case when y.wynikliczbowy >= %f and y.wynikliczbowy < %f then 1 else 0 end) as "%0.2f - %0.2f"' % (vmin, vmax, vmin, vmax))
        sql_przedzialy.append('sum(case when y.wynikliczbowy >= %f then 1 else 0 end) as ">= %0.2f"' % (przedz[-1], przedz[-1]))
        sql_przedzialy = ',\n'.join(sql_przedzialy)
    sql = sql.replace('$PRZEDZIALY$', sql_przedzialy)
    if params['podzial_wiek']:
        sql += 'group by 1, 2, 3, 4 order by 1, 2, 3, 4'
    else:
        sql = sql.replace('gw.nazwa as "Grupa wiekowa",', '')
        sql += 'group by 1, 2, 3 order by 1, 2, 3'
    with get_centrum_connection(task_params['target']) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, [badanie, parametr, oddnia, dodnia + ' 23:59:59'])
        cols = ["Laboratorium"] + cols
        for row in rows:
            res.append([task_params['target']] + row)
    return cols, res

def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': [
            'xlsx',
        ]
    }
    start_params = None
    header = None
    rows = []
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            cols, res_rows = result
            if header is None:
                header = cols
            for row in res_rows:
                rows.append(row)
            if start_params is None:
                start_params = params['params']
        elif status == 'failed':
            res['errors'].append("%s - błąd połączenia" % params['target'])
    if header is not None:
        res['results'].append({
            'type': 'table',
            'header': header,
            'data': prepare_for_json(rows)
        })
    res['progress'] = task_group.progress
    return res
