import base64

import openpyxl

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from tasks import TaskGroup, Task
from api.common import get_db
from helpers import prepare_for_json, get_centrum_connection
from helpers.validators import validate_date_range

MENU_ENTRY = 'Raport Niezgodny Płatnik'

ADD_TO_ROLE = ['R-MDO', 'L-REJ']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Wykaz zleceń z płatnikiem niezgodnym ze zleceniodawcą'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria', replikacje=True),
    DateInput(field='dataod', title='Data od', default='PZM'),
    DateInput(field='datado', title='Data do', default='KZM'),
))


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
            'function': 'raport_niezgodny_platnik',
        }
        report.create_task(lab_task)
    report.save()
    return report


def raport_niezgodny_platnik(task_params):
    params = task_params['params']
    lab = task_params['target']
    wiersze = []
    with get_centrum_connection(lab) as conn:
        cols, rows = conn.raport_z_kolumnami(
            """
            select
                trim(O.Symbol) as ZS,
                O.Nazwa as ZN,
                trim(P.Symbol) as PS,
                P.Nazwa as PN,
                trim(PZ.Symbol) as PZS,
                PZ.Nazwa as PZN,
                z.datarejestracji as D,
                z.numer as N,
                z.kodkreskowy as kod,
                (cast(list(trim(b.Symbol), ' ') as varchar(2000))) as BS
            from Wykonania W
                left outer join zlecenia z on z.id=w.zlecenie
                left outer join Platnicy P on W.platnik = P.ID
                left outer join oddzialy o on z.oddzial = o.ID
                left join platnicy pz on pz.id=o.platnik
                left outer join Badania B on W.Badanie = B.ID
                left outer join GrupyBadan GB on B.Grupa = GB.ID
                left outer join typyzlecen tz on tz.id=z.typzlecenia
            where
                W.Rozliczone between ? and ?
                and W.Anulowane is null	and W.Platne = 1 and w.platnik is not null and
                    w.platnik != o.platnik 
                    and w.bladwykonania is null 
                and tz.symbol not in ('K', 'KW', 'KZ')
            group by 1,2,3,4,5,6,7,8,9
            order by 1,7,8
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
            'header': 'Zleceniodawca,Zleceniodawca Nazwa,Płatnik,Płatnik Nazwa,Płatnik zleceniodawca,Płatnik zleceniodawcy nazwa,Data rejestracji,Numer,Kod kreskowy,Badania'.split(','),
            'data': wiersze
        }
