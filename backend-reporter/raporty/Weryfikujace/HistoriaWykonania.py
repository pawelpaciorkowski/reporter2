import time

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError, Switch
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty, odpiotrkuj

MENU_ENTRY = 'Historia wykonania'
REQUIRE_ROLE = ['C-ROZL']


LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="Pobieranie historii pojedynczego wykonania z bazy laboratoryjnej"),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', pokaz_nieaktywne=True),
    TextInput(field='id', title='id'),
    TextInput(field='sysid', title='sys_id^system'),
))

SQL = """
    select 
        w.id, w.dc, w.dd, coalesce(pc.nazwisko, pc.logowanie) as pc, coalesce(pd.nazwisko, pd.logowanie) as pd, 
        w.system, w.sysid, w.rozliczone, w.zatwierdzone, w.anulowane,
        trim(bl.symbol) as bladwykonania, trim(bad.symbol) as badanie,
        trim(plw.symbol) as platnikwykonania, trim(plz.symbol) as platnikzlecenia,
        trim(o.symbol) as zleceniodawca, trim(pr.symbol) as pracownia, trim(ap.symbol) as aparat,
        w.kodkreskowy, zl.kodkreskowy as zl_kodkreskowy, zl.datarejestracji, zl.numer,
        w.platne, w.koszty, w.wyslanerozliczenie 
    from $TAB$ w 
    left join zlecenia zl on zl.id=w.zlecenie
    left join oddzialy o on o.id=zl.oddzial
    left join platnicy plz on plz.id=zl.platnik
    left join platnicy plw on plw.id=w.platnik
    left join badania bad on bad.id=w.badanie
    left join bledywykonania bl on bl.id=w.bladwykonania
    left join pracownie pr on pr.id=w.pracownia
    left join aparaty ap on ap.id=w.aparat
    left join pracownicy pc on pc.id=w.pc
    left join pracownicy pd on pd.id=w.pd
    where $WARUNEK$
"""

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    task_params = {}
    if empty(params['laboratorium']):
        raise ValidationError("Wybierz lab")
    if not empty(params['id']):
        try:
            task_params['mode'] = 'id'
            task_params['id'] = int(params['id'])
        except:
            raise ValidationError("Nieprawidłowy format id")
    elif not empty(params['sysid']):
        try:
            tab_sysid = params['sysid'].split('^')
            task_params['mode'] = 'sysid'
            task_params['sysid'] = int(tab_sysid[0])
            task_params['system'] = str(tab_sysid[1]).strip()
            if len(task_params['system']) < 3 or len(task_params['system']) > 7:
                raise ValidationError("Nieprawidłowy symbol systemu")
        except:
            raise ValidationError("Nieprawidłowy format sys_id^system")
    else:
        raise ValidationError("Nie podano namiarów na wykonanie")
    task = {
        'type': 'centrum',
        'priority': 0,
        'target': params['laboratorium'],
        'params': task_params,
        'function': 'raport_lab'
    }
    report.create_task(task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']
    if params['mode'] == 'id':
        sqlb = SQL.replace('$TAB$', 'wykonania').replace('$WARUNEK$', 'w.id=?')
        sqlb_params = [params['id']]
    elif params['mode'] == 'sysid':
        sqlb = SQL.replace('$TAB$', 'wykonania').replace('$WARUNEK$', 'w.system=? and w.sysid=?')
        sqlb_params = [params['system'], params['sysid']]
    else:
        raise ValueError(params['mode'])
    cols = None
    res_rows = []
    wyk_id = None
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        for row in conn.raport_slownikowy(sqlb, sqlb_params):
            if cols is not None:
                raise RuntimeError("Za dużo wierszy")
            cols = []
            res_row = []
            for k, v in row.items():
                if k == 'id':
                    wyk_id = v
                else:
                    cols.append(k)
                    res_row.append(v)
            res_rows.append(res_row)
        if wyk_id is not None:
            sqlh = SQL.replace('$TAB$', 'hstwykonania').replace('$WARUNEK$', 'w.del=? order by id desc')
            sqlh_params = [wyk_id]
            for row in conn.raport_slownikowy(sqlh, sqlh_params):
                res_rows.append([row.get(c) for c in cols])
    if len(res_rows) > 0:
        return {
            'type': 'table',
            'header': cols,
            'data': prepare_for_json(list(reversed(res_rows)))
        }
    else:
        return {
            'type': 'error', 'text': 'Nie znaleziono wykonania'
        }
