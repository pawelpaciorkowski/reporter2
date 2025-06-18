from datasources.centrum import CentrumWzorcowa
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from helpers.kalendarz import Kalendarz
from tasks import TaskGroup, Task
import datetime
from csv import reader

MENU_ENTRY = 'Covid antygen - opisy metod'

TYPY_TESTOW = 'COV2ANT COVANTA COVANTN CANPOCP CANPOCA CANPOCN'.split(' ')

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="Sprawdzenie zgodności opisów metod badań COVID antygen (%s) z listą testów udostępnianą przez CeZ.\n"
                  "Wyniki badań metodami, których nie da się zmapować na id testu nie są raportowane do EWP." % ', '.join(
        TYPY_TESTOW)),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    Switch(field="tylkowykonywane", title="Tylko metody używane w przeciągu miesiąca"),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    test_id_nazwa = {}
    with open('/home/centrum-system/korona_ewp/testy.csv', 'r') as f:
        r = reader(f)
        for line in r:
            if line[2] == 'TEST_NAZWA':
                continue
            test_id_nazwa[line[1]] = line[2].lower()
    params['test_id_nazwa'] = test_id_nazwa
    for lab in params['laboratoria']:
        task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'raport_lab'
        }
        report.create_task(task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']

    def id_testu_z_opisu_metody(opis_metody):
        nonlocal params
        opis = (opis_metody or '').lower()
        for id, nazwa in params['test_id_nazwa'].items():
            if nazwa in opis:
                return id
        return None

    rows = []
    sql = """
        select trim(b.symbol) as "Badanie", trim(m.symbol) as "Metoda", m.nazwa as "Nazwa", m.opis as "Opis",
            count(w.id) as "Il. wyk. ost. mies."
        from metody m
        left join badania b on b.id=m.badanie
        left join wykonania w on w.metoda=m.id
        where m.del=0 and m.badanie in (select id from badania where symbol in (%s))
        and w.zatwierdzone > ?
        group by 1, 2, 3, 4
    """ % ', '.join(["'%s'" % bad for bad in TYPY_TESTOW])
    kal = Kalendarz()
    kal.ustaw_teraz('-31D')
    sql_params = [kal.data('T')]
    print(sql, sql_params)
    with get_centrum_connection(task_params['target']) as conn:
        cols, res_rows = conn.raport_z_kolumnami(sql, sql_params)
        cols.append("Id test")
        for row in res_rows:
            row = list(row)
            if row[4] == 0 and params['tylkowykonane']:
                continue
            id_test = id_testu_z_opisu_metody(row[3])
            if id_test is not None:
                row.append(id_test)
            else:
                row.append({
                    'background': '#ff0000',
                    'value': 'BRAK',
                })
            rows.append(row)
    if len(rows) == 0:
        return None
    return {
        'type': 'table',
        'title': task_params['target'],
        'header': cols,
        'data': prepare_for_json(rows)
    }
