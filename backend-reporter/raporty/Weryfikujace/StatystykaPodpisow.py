from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
import datetime

REQUIRE_ROLE = ['C-CS']
ADD_TO_ROLE = ['R-MDO']

MENU_ENTRY = "Statystyka podpisów"

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="Ilość zleceń / wykonań podpisanych przez pracowników w danym okresie"),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', pokaz_nieaktywne=True),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
    TextInput(field='badanie', title='Pojedyncze badanie (symbol)'),
    TextInput(field='pracownia', title='Pojedyncza pracownia (symbol)'),
    Switch(field='daty', title='Podział na daty'),
    Switch(field='dnitygodnia', title='Podział na dni tygodnia'),
    Switch(field='godziny', title='Podział na godziny'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    validate_date_range(params['dataod'], params['datado'], 31)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_pojedynczy'
    }
    report.create_task(task)
    report.save()
    return report


def raport_pojedynczy(task_params):
    params = task_params['params']
    header = ['Pracownik']
    pola = ['pr.nazwisko']
    if params['daty']:
        header.append('Data')
        pola.append('cast(w.wydrukowane as date)')
    if params['dnitygodnia']:
        header.append('Dzień tygodnia')
        pola.append('''(case extract(weekday from w.wydrukowane)
            when 0 then 'nd' when 1 then 'pn' when 2 then 'wt' when 3 then 'śr'
            when 4 then 'cz' when 5 then 'pt' when 6 then 'sb' else '??' end)''')
    if params['godziny']:
        header.append('Godzina')
        pola.append('extract(hour from w.wydrukowane)')

    header += 'Ilość wykonań,Ilość zleceń'.split(',')
    sql = """
        select $POLA$, count(w.id), count(distinct w.zlecenie)
        from wykonania w 
        left join badania b on b.id=w.badanie
        left join pracownie p on p.id=w.pracownia
        left join pracownicy pr on pr.id=w.pracownikodwydrukowania
        where w.wydrukowane between ? and ?
        """.replace('$POLA$', ', '.join(pola))
    sql_params = [params['dataod'], params['datado']]
    bad = (params['badanie'] or '').strip().upper()
    prac = (params['pracownia'] or '').strip().upper()
    if bad != '':
        sql += " and b.symbol=? "
        sql_params.append(bad)
    if prac != '':
        sql += " and p.symbol=? "
        sql_params.append(prac)
    grp_fields = ','.join([str(i) for i in range(1, len(pola)+1)])
    sql += " group by %s order by %s" % (grp_fields, grp_fields)
    print(sql)
    with get_centrum_connection(task_params['target']) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
    return [{
        'type': 'table',
        'header': header,
        'data': prepare_for_json(rows)
    }]