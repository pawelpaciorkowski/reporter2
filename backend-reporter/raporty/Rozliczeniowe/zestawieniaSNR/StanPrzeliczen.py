from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch
from tasks import TaskGroup, Task
from outlib.xlsx import ReportXlsx
from helpers import prepare_for_json
from datasources.snr import SNR
import base64
import datetime

MENU_ENTRY = 'Stan przeliczeń'

LAUNCH_DIALOG = Dialog(title='Stan przeliczania cen', panel=VBox(
    InfoText(text='''Raport przedstawia ilości wykonań oczekujących na przeliczenie cen, w podziale na laboratoria,
        płatników i miesiące rejestracji. Tych wykonań nie da się w tej chwili rozliczyć ale nie wystąpią
        one również w raportach z błędów przeliczeń.''')
))

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport_snr'
    }
    report.create_task(task)
    report.save()
    return report


def raport_snr(task_params):
    sql = """
        select 
        w.laboratorium, pwl.symbol, to_char(w.datarejestracji, 'YYYY-MM'), count(w.id)
        from Wykonania w
        left join platnicywlaboratoriach pwl on pwl.platnik=w.platnik and pwl.laboratorium=w.laboratorium
        where w.StatusPrzeliczenia = 'CZEKA' and w.platnik is not null and not w.DEL
        group by 1, 2, 3
        order by 1,2,3

    """
    snr = SNR()
    _, rows = snr.select(sql)
    return {
        'type': 'table',
        'header': 'Laboratorium,Płatnik,Miesiąc rejestracji,Ilość'.split(','),
        'data': prepare_for_json(rows)
    }

