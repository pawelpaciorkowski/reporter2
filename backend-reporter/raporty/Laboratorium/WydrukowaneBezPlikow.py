from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, NumberInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
import datetime

SQL_PG = """
    select zl.datarejestracji, zl.numer, zl.kodkreskowy, pr.nazwisko as wydrukowal, array_to_string(array_agg(trim(b.symbol)), ', ') as badania, 
    min(w.wydrukowane) as minw, max(w.wydrukowane) as maxw
    from zlecenia zl
    left join wykonania w on w.zlecenie=zl.id
    left join badania b on b.id=w.badanie 
    left join pracownicy pr on pr.id=w.pracownikodwydrukowania 
    where zl.datarejestracji between %s and %s
    and not exists (select wwz.id from wydrukiwzleceniach wwz where wwz.zlecenie=zl.id and wwz.del=0) 
    and w.wydrukowane is not null and w.wydrukowane + interval '1 hour' < current_timestamp 
    group by 1, 2, 3, 4 order by 1, 2
"""

SQL_FB = """
    select zl.datarejestracji, zl.numer, zl.kodkreskowy, pr.nazwisko as wydrukowal, list(trim(b.symbol), ', ') as badania, 
    min(w.wydrukowane) as minw, max(w.wydrukowane) as maxw
    from zlecenia zl
    left join wykonania w on w.zlecenie=zl.id
    left join badania b on b.id=w.badanie 
    left join pracownicy pr on pr.id=w.pracownikodwydrukowania 
    where zl.datarejestracji between ? and ?
    and not exists (select wwz.id from wydrukiwzleceniach wwz where wwz.zlecenie=zl.id and wwz.del=0) 
    and w.wydrukowane is not null and dateadd(1 hour to w.wydrukowane) < current_timestamp 
    group by 1, 2, 3, 4 order by 1, 2
"""

MENU_ENTRY = "Wydrukowane bez plików"

ADD_TO_ROLE = ['L-PRAC']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="""
            Raport ze zleceń zawierających wykonania oznaczone jako wydrukowane ale bez podpiętych żadnych dokumentów sprawozdań.
            Taka sytuacja może oznaczać zlecenia które ktoś omyłkowo "uznał za wydrukowane" nie podpisując sprawozdań. 
            Raport wg dat rejestracji. Raport nie uwzględnia znaczników wykonania świeższych niż 1 godzina, bo są one
            nadawane także "tymczasowo" w trakcie procesu podpisu.
        """),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    DateInput(field='dataod', title='Zarejestrowane od', default='-1D'),
    DateInput(field='datado', title='Zarejestrowane do', default='T'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    validate_date_range(params['dataod'], params['datado'], 7)
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
    header = 'Data rej.,Numer,Kod kreskowy,Wydrukował,Badania,Wydrukowane od,Wydrukowane do'.split(',')
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(SQL_FB, [params['dataod'], params['datado']], sql_pg=SQL_PG)
    return [{
        'type': 'table',
        'header': header,
        'data': prepare_for_json(rows)
    }]
