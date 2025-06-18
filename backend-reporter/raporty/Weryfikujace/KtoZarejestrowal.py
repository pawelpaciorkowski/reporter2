from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, Switch, ValidationError
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
import datetime

MENU_ENTRY = 'Kto zarejestrował'

SQL_ZLECENIA = """
    select zl.datarejestracji as "Data", zl.numer as "Numer",
        case when zl.anulowane is not null then 'T' else '' end as "Anulowane",
        prz.logowanie || ' - ' || prz.nazwisko as "Rejestrator",
        kanz.symbol as "Kanał rej.",
        list(zz.numer || '^' || zz.system) as "Zlec.zew."
    from zlecenia zl
    left join pracownicy prz on prz.id=zl.pracownikodrejestracji
    left join kanaly kanz on kanz.id=prz.kanalinternetowy
    left join zleceniazewnetrzne zz on zz.zlecenie=zl.id
    where zl.datarejestracji between ? and ?
    and zl.oddzial in (select id from oddzialy where symbol=?)
    group by 1,2,3,4,5
    order by 1, 2
"""

SQL_WYKONANIA = """
    select zl.datarejestracji as "Data", zl.numer as "Numer",
        case when zl.anulowane is not null then 'T' else '' end as "Zl Anul.",
        prz.logowanie || ' - ' || prz.nazwisko as "Rej.zl.",
        kanz.symbol as "Kanał rej.zl.",
        trim(bad.symbol) || case when mat.symbol is not null then ':' || trim(mat.symbol) else '' end as "Badanie",
        case when wyk.anulowane is not null then 'T' else '' end as "Bad Anul.",
        bw.symbol as "Bł.Wyk.",
        case when wyk.zatwierdzone is not null then 'T' else '' end as "Zatw.",
        prw.logowanie || ' - ' || prw.nazwisko as "Rej.bad.",
        kanw.symbol as "Kanał rej.bad.",
        list(zz.numer || '^' || zz.system) as "Zlec.zew.",
        list(wz.numer || '^' || wz.system) as "Wyk.zew."
    from zlecenia zl
    left join wykonania wyk on wyk.zlecenie=zl.id
    left join badania bad on bad.id=wyk.badanie
    left join materialy mat on mat.id=wyk.material
    left join bledywykonania bw on bw.id=wyk.bladwykonania
    left join pracownicy prz on prz.id=zl.pracownikodrejestracji
    left join kanaly kanz on kanz.id=prz.kanalinternetowy
    left join pracownicy prw on prw.id=wyk.pracownikodrejestracji
    left join kanaly kanw on kanw.id=prw.kanalinternetowy
    left join zleceniazewnetrzne zz on zz.zlecenie=zl.id
    left join wykonaniazewnetrzne wz on wz.wykonanie=wyk.id
    where zl.datarejestracji between ? and ?
    and zl.oddzial in (select id from oddzialy where symbol=?)
    group by 1,2,3,4,5,6,7,8,9,10,11
    order by 1, 2, 3
"""


LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    TextInput(field='zleceniodawca', title='Zleceniodawca (symbol)'),
    DateInput(field='dataod', title='Data rejestracji od', default='PZM'),
    DateInput(field='datado', title='Data rejestracji do', default='KZM'),
    Switch(field='wykonania', title='Rozbij na badania'),
))

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)
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
    if params['wykonania']:
        sql = SQL_WYKONANIA
    else:
        sql = SQL_ZLECENIA
    with get_centrum_connection(task_params['target']) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, [params['dataod'], params['datado'], params['zleceniodawca']])
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows),
    }
