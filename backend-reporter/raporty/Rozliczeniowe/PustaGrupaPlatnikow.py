import base64

import openpyxl

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from tasks import TaskGroup, Task
from api.common import get_db
from helpers import prepare_for_json, get_centrum_connection
from helpers.validators import validate_date_range

MENU_ENTRY = 'Raport Pusta Grupa Płatników'
# REQUIRE_ROLE = 'ADMIN'  # TODO: usunąć po implementacji


LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Wykaz imienny zleceń z wybranych laboratoriów prezentujący zlecenia zarejestrowane na płatników z pustą grupą płatników'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria', replikacje=True),
    DateInput(field='dataod', title='Data od', default='PZM'),
    DateInput(field='datado', title='Data do', default='KZM'),
))

ADD_TO_ROLE = ['R-MDO', 'L-REJ']

"""
    report.save()
    return report
"""


def start_report(params):
    laboratoria = []
    params = LAUNCH_DIALOG.load_params(params)
    print('startReport', __PLUGIN__, params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    if params['dataod'] is None:
        raise ValidationError("Nie podano daty")
    if params['datado'] is None:
        raise ValidationError("Nie podano daty")
    validate_date_range(params['dataod'], params['datado'], 90)
    for lab in params['laboratoria']:
        lab_task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'raport_pusta_grupa_platnikow',
        }
        report.create_task(lab_task)
    report.save()
    return report


def raport_pusta_grupa_platnikow(task_params):
    params = task_params['params']
    lab = task_params['target']
    wiersze = []
    with get_centrum_connection(lab) as conn:
        cols, rows = conn.raport_z_kolumnami(
            """
	          select
	        o.symbol as OS,
	        o.nazwa as ODN,
            P.Symbol as PS,
            P.Nazwa as PN,
            z.datarejestracji as D,
            z.numer as N,
            z.kodkreskowy as kod,
            (cast(list(trim(b.Symbol), ' ') as varchar(2000))) as BS
	          from Wykonania W
            left outer join Platnicy P on W.platnik = P.ID
            left outer join Badania B on W.Badanie = B.ID
            left outer join GrupyBadan GB on B.Grupa = GB.ID
            left outer join zlecenia z on z.id=w.zlecenie
            left outer join typyzlecen tz on tz.id=z.typzlecenia
            left join oddzialy o on o.id=z.oddzial
	          where
            W.Datarejestracji >= '2021-01-01' and W.Rozliczone between ? and ?
            and W.Anulowane is null	and W.Platne = 1 and p.grupa is null and (w.platnik is not null or (w.platnik is null and w.taryfa is null)) and w.bladwykonania is null
            and tz.symbol not in ('K', 'KW', 'KZ')
            group by O.Symbol, O.Nazwa, P.Symbol, P.Nazwa, z.datarejestracji, z.numer, z.kodkreskowy
            order by P.Symbol, z.datarejestracji, z.numer
            """, [params['dataod'], params['datado']])

        for row in rows:
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
            'header': 'Zleceniodawca symbol,Zleceniodawca nazwa,Płatnik Symbol,Płatnik Nazwa,Data rejestracji,Numer,Kod,Badania'.split(','),
            'data': wiersze
        }
