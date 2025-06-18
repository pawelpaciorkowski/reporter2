from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from outlib.xlsx import ReportXlsx
from helpers import prepare_for_json
from datasources.snr import SNR
import base64
import datetime

MENU_ENTRY = 'Puste ceny'

LAUNCH_DIALOG = Dialog(title='Puste ceny w SNR', panel=VBox(
    LabSelector(multiselect=False, field='lab', title='Laboratorium'),
    DateInput(field='dataod', title='Data początkowa', default='PZT'),
    DateInput(field='datado', title='Data końcowa', default='KZT'),
))

SQL = """
select w.laboratorium, pl.hs->'grupa' as "Grupa płatnika", pl.nip as "Płatnik NIP", pl.hs ->'umowa' as "Płatnik nr K", 
    pl.nazwa as "Płatnik nazwa", bad.hs->'grupacennikowa' as "Grupa cennikowa", bad.symbol as "Badanie", count(distinct w.id) as "Ilość",
    round(count(distinct w.id) * avg(c.cenadlaplatnika)) as "Wartość szacunkowa"
from wykonania w
left join platnicy pl on pl.id=w.platnik
left join pozycjekatalogow bad on bad.katalog='BADANIA' and bad.symbol=w.badanie
left join pozycjekatalogow gb on gb.katalog='GRUPYBADAN' and gb.symbol=bad.hs->'grupa'
left join ceny c on c.badanie=w.badanie and not c.del and c.cenadlaplatnika is not null and c.cenadlaplatnika > 0
where w.platnik not in ('ALAB.1.407243684')
and w.platnik is not null
and w.datarozliczeniowa between %s and %s
and not w.del and w.cenadlaplatnika is null
and not w.bezplatne and not w.jestpakietem 
and gb.symbol not in ('TECHNIC')
and pl.hs->'grupa' in ('A-PAT', 'BIODIAG', 'PRZYGOD', 'SIECIOW', 'SPECJAL', 'SZAL', 'SZPI', 'SZPR', 'ZORE', 'ZOZ', 'ZOZE', 'ZOZR')
and pl.hs->'grupa' not in ('ALAB', 'GOTOW') -- nadmiarowe ale było w konf zestawienia
and (w.powodanulowania='' or w.powodanulowania is null)
and w.laboratorium = %s
group by 1,2,3,4,5,6,7
order by 9 desc
"""

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 7)
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
    params = task_params['params']
    snr = SNR()
    cols, rows = snr.select(SQL, [params['dataod'], params['datado'], params['lab']])
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    }
