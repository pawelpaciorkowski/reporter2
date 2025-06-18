import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none
from datasources.snr import SNR

MENU_ENTRY = 'Wolne symbole'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    TextInput(field="symbol", title="Symbol bez prefiksu labu")
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['symbol']) == 0 or len(params['symbol']) > 6:
        raise ValidationError("Nieprawidłowa długość")
    task = {
        'type': 'snr',
        'priority': 0,
        'params': params,
        'function': 'raport_platnicy',
    }
    report.create_task(task)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport_zleceniodawcy',
    }
    report.create_task(task)
    report.save()
    return report


def raport_platnicy(task_params):
    params = task_params['params']
    snr = SNR()
    cols, rows = snr.select("""
        select l.symbol as lab, l.hs->'przedrosteksymbolu' as prefiks, l.hs->'przedrosteksymbolu' || %s as symbol,
        case when length(l.hs->'przedrosteksymbolu' || %s) > 7 then 'ZA DŁUGI SYMBOL'
        else 
            case when coalesce(l.hs->'przedrosteksymbolu', '') = '' then 'BRAK PREFIKSU LABU' 
            else 
                case when pwl.id is null then 'wolny' else 'ZAJĘTY' end 
            end
        end as status,
        pwl.laboratorium as lab_symbolu, pl.nazwa as platnik, pl.hs->'umowa' as nrk
        from laboratoria l
        left join platnicywlaboratoriach pwl on pwl.symbol = l.hs->'przedrosteksymbolu' || %s and not pwl.del
        left join platnicy pl on pl.id=pwl.platnik
        where not l.del and l.aktywne order by l.symbol
    """, [params['symbol'], params['symbol'], params['symbol']])
    return {
        'type': 'table',
        'title': 'Płatnicy',
        'header': cols,
        'data': prepare_for_json(rows)
    }

def raport_zleceniodawcy(task_params):
    params = task_params['params']
    snr = SNR()
    cols, rows = snr.select("""
        select l.symbol as lab, l.hs->'przedrosteksymbolu' as prefiks, l.hs->'przedrosteksymbolu' || %s as symbol,
        case when length(l.hs->'przedrosteksymbolu' || %s) > 7 then 'ZA DŁUGI SYMBOL'
        else 
            case when coalesce(l.hs->'przedrosteksymbolu', '') = '' then 'BRAK PREFIKSU LABU' 
            else 
                case when zwl.id is null then 'wolny' else 'ZAJĘTY' end 
            end
        end as status,
        zwl.laboratorium as lab_symbolu, zl.nazwa as zleceniodawca, pl.nazwa as platnik, pl.hs->'umowa' as nrk
        from laboratoria l
        left join zleceniodawcywlaboratoriach zwl on zwl.symbol = l.hs->'przedrosteksymbolu' || %s and not zwl.del
        left join zleceniodawcy zl on zl.id=zwl.zleceniodawca
        left join platnicy pl on pl.id=zl.platnik
        where not l.del and l.aktywne order by l.symbol
    """, [params['symbol'], params['symbol'], params['symbol']])
    return {
        'type': 'table',
        'title': 'Zleceniodawcy',
        'header': cols,
        'data': prepare_for_json(rows)
    }
