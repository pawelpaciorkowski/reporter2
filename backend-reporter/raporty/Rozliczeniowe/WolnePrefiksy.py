import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none
from datasources.snr import SNR

MENU_ENTRY = 'Wolne prefiksy'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
))

ALFABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'

# TODO opcjonalnie symbole analizatorów wzięte z labów

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'snr',
        'priority': 0,
        'params': params,
        'function': 'raport',
    }
    report.create_task(task)
    report.save()
    return report


def raport(task_params):
    zajete = {
        'p': {}, 'z': {}
    }
    snr = SNR()
    for tab in ('platnicy', 'zleceniodawcy'):
        lit = tab[0]
        cols, rows = snr.select("select symbol from %swlaboratoriach where not del" % tab)
        for row in rows:
            pref = row[0][:2]
            if pref not in zajete[lit]:
                zajete[lit][pref] = 0
            zajete[lit][pref] += 1
    jednoliterowe = {}
    for lab in snr.dict_select("""select symbol, vpn, nazwa, hs->'bazapg' as bazapg, hs->'hostcentrum' as hostcentrum, 
                                    hs->'bazazdalna' as baza, hs->'przedrosteksymbolu' as prefix  
                                    from 
                                     laboratoria where not del and aktywne and vpn is not null and vpn != ''
                                    and hs->'nowesk' = 'True'"""):
        prefix = lab['prefix']
        if len(prefix) == 1:
            jednoliterowe[prefix] = lab['symbol']

    header = ['Prefiks', 'Płatnicy', 'Zleceniodawcy', 'Wolne', 'Uwagi']
    data = []
    for l1 in ALFABET:
        for l2 in ALFABET:
            pref = l1 + l2
            uwagi = []
            juz_zajete = False
            ilep = zajete['p'].get(pref, 0)
            ilez = zajete['z'].get(pref, 0)
            if ilep + ilez > 0:
                juz_zajete = True
            if l1 == 'Y':
                juz_zajete = True
                uwagi.append('Zarezerwowane dla Pośrednika Zleceń')
            if l1 in jednoliterowe:
                uwagi.append(f'Uwaga na możliwe konflikty z {l1} - {jednoliterowe[l1]}')
            if l1 == '9':
                uwagi.append('Zarezerwowane na symbole "skasowane"')
            if l1 == 'T' and l2 == 'B':
                uwagi.append('Wielkoszyński')
                juz_zajete = True

            data.append([pref, ilep, ilez, 'T' if not juz_zajete else '', ', '.join(uwagi)])
    return {
        'type': 'table',
        'header': header,
        'data': prepare_for_json(data)
    }
