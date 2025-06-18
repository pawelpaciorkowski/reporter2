from datasources.bic import BiCDatasource
from datasources.centrum import CentrumWzorcowa
from datasources.snr import SNR
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json, divide_chunks, empty, odpiotrkuj
from helpers.validators import validate_date_range, validate_symbol
from datasources.snrkonf import SNRKonf
from datasources.helper import HelperDb
from tasks import TaskGroup, Task
import datetime
from helpers.connections import get_centra, get_db_engine

MENU_ENTRY = 'System na Wzorach'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="Sprawdzenie aktualnego systemu na bazie wzorcowej i historii zmian"),
    HBox(DateInput(field='dataod', title='Data początkowa', default='-7D')),
    HBox(DateInput(field='datado', title='Data końcowa', default='T')),
))

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], max_days=96)
    task = {
        'type': 'snr',
        'priority': 0,
        'params': params,
        'function': 'raport_wzory'
    }
    report.create_task(task)
    report.save()
    return report


def raport_wzory(task_params):
    params = task_params['params']
    res = []
    cnt = CentrumWzorcowa()
    systemy = {}
    with cnt.connection() as conn:
        cols, rows = conn.raport_z_kolumnami("""
            select id, symbol from systemy where del=0
        """)
        for row in rows:
            systemy[row[0]] = row[1].strip()
        cols, rows = conn.raport_z_kolumnami("""
            select system from wygladidostosowanie where nazwakomputera='^__^__^'
        """)
        akt_system = systemy[rows[0][0]]
        res.append({
            'type': 'info' if akt_system == 'MARC' else 'warning',
            'text': 'Aktualny system: %s' % akt_system
        })
        cols, rows = conn.raport_z_kolumnami("""
            select h.dc, pr.nazwisko, h.parametry
            from hstwygladidostosowanie h
            left join pracownicy pr on pr.id=h.pc
            where h.dc between ? and ?
            order by h.id
        """, [params['dataod'], params['datado']+' 23:59:59'])
        hst_rows = []
        for row in rows:
            parametry = odpiotrkuj(row[2])
            sys_id = int(parametry['System'])
            row[2] = systemy[sys_id]
            hst_rows.append(row)
        res.append({
            'type': 'table',
            'title': 'Historia zmian',
            'header': 'Godzina zmiany,Pracownik,System'.split(','),
            'data': prepare_for_json(hst_rows)
        })
    return res
