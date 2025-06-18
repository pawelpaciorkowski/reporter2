import datetime
import uuid
from datasources.reporter import ReporterDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty, Kalendarz

MENU_ENTRY = 'Zgrywanie miesiaca'
REQUIRE_ROLE = ['C-ADM']
TASK_TYPE = 'zgrywanieMiesiaca'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    TabbedView(field='tab', desc_title='Typ raportu', children=[
        Tab(title='Stan zgrywania', value='raport',
            panel=VBox(
                InfoText(
                    text='Raport ze stanu ostatnich sesji zgrywania'),
            )
            ),
        Tab(title='Uruchom zgrywanie', default=True, value='uruchom',
            panel=VBox(
                InfoText(
                    text='Proszę wybrać laboratorium. Zgrywanie zostanie uruchomione tylko jeśli od zakończenia poprzedniego zgrywania minęły co najmniej 3h i nie trwa nowe zgrywanie. Zgrywany jest ostatni miesiąc.'),
                LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
            )
            )
    ]),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': params['tab']
    }
    report.create_task(task)
    report.save()
    return report


def raport(task_params):
    params = task_params['params']
    rep = ReporterDatasource()
    cols, rows = rep.select("""
        select l.symbol as "Laboratorium",
        t.created_at as "Zadanie zaplanowane", t.started_at as "Zadanie uruchomione", t.finished_at as "Zadanie zakończone",
        case when t.success is not null then
            case when t.success then 'tak' else 'NIE' end 
        else '' end as "Skuces", t.log as "Log",
        t.guid
        from laboratoria l
        left join external_tasks t on t.task_type=%s and t.target=l.symbol 
        where l.aktywne
        and (t.id is null or not exists(select tt.id 
            from external_tasks tt 
            where tt.task_type=t.task_type and tt.target=t.target and tt.id>t.id)) 
        order by l.kolejnosc
    """, [TASK_TYPE])
    return {
        'results': [
            {
                'type': 'table',
                'header': cols,
                'data': prepare_for_json(rows)
            }
        ]
    }


def uruchom(task_params):
    params = task_params['params']
    blad = None
    kal = Kalendarz()
    rep = ReporterDatasource(read_write=True)
    rep.execute("begin")
    for row in rep.dict_select("""select * from external_tasks 
            where task_type=%s and target=%s order by id desc limit 1""", (TASK_TYPE, params['laboratorium'])):
        if row['finished_at'] is None:
            blad = 'Poprzednie zgrywanie jeszcze się nie zakończyło'
        elif datetime.datetime.now() - row['finished_at'] < datetime.timedelta(hours=3) and row['success']:
            blad = 'Poprzednie zgrywanie zakończyło się mniej niż 3 godziny temu'
    if blad is None:
        rep.insert('external_tasks', {
            'guid': str(uuid.uuid4()),
            'task_type': TASK_TYPE,
            'target': params['laboratorium'],
            'created_at': datetime.datetime.now(),
            'params': {
                'system': params['laboratorium'],
                'vpn': rep.dict_select("select adres_fresh from laboratoria where symbol=%s",
                                       [params['laboratorium']])[0]['adres_fresh'],
                'dataOd': kal.data('PZM'),
                'dataDo': kal.data('KZM'),
            }
        })
        rep.commit()
        return {
            'results': [
                {
                    'type': 'info',
                    'text': '%s - zaplanowano zgrywanie' % (params['laboratorium'])
                }
            ]
        }
    else:
        rep.commit()
        return {
            'results': [
                {
                    'type': 'error',
                    'text': '%s - %s' % (params['laboratorium'], blad)
                }
            ]
        }
