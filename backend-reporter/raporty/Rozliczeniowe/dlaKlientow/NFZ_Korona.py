import base64

import openpyxl

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, ValidationError
from tasks import TaskGroup, Task
from api.common import get_db
from helpers import prepare_for_json, get_centrum_connection

MENU_ENTRY = 'Koronawirus - Raport dla NFZ'
# REQUIRE_ROLE = 'ADMIN'  # TODO: usunąć po implementacji


LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport NFZ Korona dla wybranego laboratorium i płatnika'),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    DateInput(field='dataod', title='Data od', default='T'),
    DateInput(field='datado', title='Data do', default='T'),
    TextInput(field='platnik', title='Symbol płatnika'),
    TextInput(field='zleceniodawca', title='Symbol zleceniodawcy')
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    print('startReport', __PLUGIN__, params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    if params['dataod'] is None:
        raise ValidationError("Nie podano daty")
    if params['datado'] is None:
        raise ValidationError("Nie podano daty")
    if params['platnik'] is None:
        raise ValidationError("Nie podano płatnika")

    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'timeout': 2400,
        'function': 'raport_sars_cov2_nfz_centrum'
    }
    report.create_task(task)
    report.save()
    return report


def raport_sars_cov2_nfz_centrum(task_params):
    params = task_params['params']
    lab = task_params['target']
    wiersze = []
    sql = """
        select
        p.symbol,
        o.symbol,
            TRIM(pa.NAZWISKO||' '||pa.IMIONA) AS "Pacjent", 
            pa.PESEL, 
            b.SYMBOL as "Symbol badania", 
            b.NAZWA as "Nazwa badania", 
            b.KOD as "Kod ICD9", 
            z.kodkreskowy as "Kod kreskowy zlecenia",
            z.datarejestracji as "Data rejestracji zlecenia",
            CAST(w.WYKONANE as date) AS "Data wykonania badania", 
            CAST(w.DYSTRYBUCJA as timestamp) AS "Data dystrybucji", 
            w.ZATWIERDZONE as "Data zatwierdzenia", 
            DATEDIFF(HOUR FROM w.DYSTRYBUCJA TO w.ZATWIERDZONE) as "Czas wykonania badania" 
            FROM wykonania w 
            LEFT JOIN PACJENCI pa ON pa.id = w.PACJENT 
            LEFT JOIN  badania b ON b.id = w.BADANIE 
            LEFT JOIN ZLECENIA z ON z.id = w.ZLECENIE 
            left join ODDZIALY o on o.id = z.oddzial
            left join PLATNICY p on p.id = o.PLATNIK
            WHERE 
            w.BADANIE in (SELECT id FROM badania WHERE symbol in ('2019COV','COV-GEN')) 
            and w.platne = 1
            AND w.ROZLICZONE between ? and ?
            and p.SYMBOL = ? and o.del = 0 """
    parametry_sql =  [params['dataod'], params['datado'], params['platnik']]
    if params['zleceniodawca']:
        sql = sql + """ and o.SYMBOL = ?"""
        parametry_sql.append(params['zleceniodawca'])

    with get_centrum_connection(lab) as conn:
        cols, rows = conn.raport_z_kolumnami(sql,parametry_sql)

        for row in rows:
            wiersze.append(prepare_for_json(row))
            print(prepare_for_json(row))

    return {
        'type': 'table',
        'header': 'Symbol płatnika,Symbol zleceniodawcy,Pacjent,PESEL,Symbol badania,Nazwa badania, Kod ICD9, Kod kreskowy zlecenia, Data rejestracji zlecenia,Data wykonania badania,Data dystrybucji,Data zatwierdzenia,Czas wykonania badania'.split(','),
        'data': wiersze
    }
    # TODO: dostosować do innych wariantów
