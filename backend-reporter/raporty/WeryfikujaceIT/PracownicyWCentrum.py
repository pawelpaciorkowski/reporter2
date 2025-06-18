from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, NumberInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json, empty
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
import datetime

SQL = """
   select p.nazwisko, p.logowanie as login,
   	case when p.del != 0 then 'T' else '' end as "konto skasowane",
   	case when p.haslo = '**********' or p.haslointernetowe='**********' then 'T' else '' end as "konto zablokowane",
   	case when p.haslo is null and  p.haslointernetowe is null then 'T' else '' end as "konto techniczne",
   	case when p.data='1999-12-31' then 'T' else '' end as "hasło zmienione przez admina",
   	k.nazwa as "kanał internetowy",
   	p.data as "data ważności hasła"
   	from pracownicy p
   	left join funkcjepracownikow f on f.id=p.funkcja
   	left join kanaly k on k.id = p.kanalinternetowy
   	where upper(p.nazwisko) like ?
    """


MENU_ENTRY = "Pracownicy w Centrum"

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="""Lista kont pracowników w bazach laboratoryjnych

        """),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    TextInput(field="nazwisko", title="Nazwisko"),
    Switch(field="ostatnie", title="Pokaż ostatnie logowanie (tylko jedna baza)")
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if params['ostatnie'] and len(params['laboratoria']) > 1:
        raise ValidationError("Ostatnie logowanie - tylko jedno laboratorium")
    if empty(params['nazwisko']) or len(params['nazwisko'].strip()) < 3:
        raise ValidationError("Wpisz co najmniej 3 znaki")
    report = TaskGroup(__PLUGIN__, params)
    for lab in params['laboratoria']:
        task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'raport_pojedynczy'
        }
        report.create_task(task)
    report.save()
    return report


def raport_pojedynczy(task_params):
    params = task_params['params']
    sql = SQL
    if params['ostatnie']:
        sql = sql.replace('from pracownicy', ', (select max(logowanie) from logowanie l where l.pracownik=p.id and l.nieudane=0) as "ostatnie logowanie" from pracownicy')
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, ['%' + params['nazwisko'].upper() + '%'])
    if len(rows) == 0:
        return {'type': 'info', 'text': '%s - nie znaleziono' % task_params['target']}
    else:
        return [{
            'title': task_params['target'],
            'type': 'table',
            'header': cols,
            'data': prepare_for_json(rows)
        }]
