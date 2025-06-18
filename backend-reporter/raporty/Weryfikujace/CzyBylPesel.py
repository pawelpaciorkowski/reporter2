import requests
from pprint import pprint

from config import Config
from datasources.nocka import NockaDatasource
from datasources.mkurier import MKurierDatasource
from datasources.alabserwis import AlabSerwisDatasource
from datasources.postgres import PostgresDatasource
from datasources.reporter import ReporterExtraDatasource
from datasources.wyniki_stats import WynikiStats
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range, validate_pesel
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty

from helpers.strings import ident_pacjenta_sw_gellert

MENU_ENTRY = 'Czy był PESEL?'
REQUIRE_ROLE = ['C-CS']
ADD_TO_ROLE = ['R-MDO', 'C-CS', 'L-PRAC']


LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    TextInput(field='pesel', title='PESEL'),
))


SQL = 'select * from raporty_reporter.czy_przetwarzamy_dane_osobowe(%s)'


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if empty(params['pesel']):
        raise ValidationError("Podaj pesel")
    else:
        params['pesel'] = validate_pesel(params['pesel'])
    task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'function': 'raport_pesele',
    }
    report.create_task(task)
    report.save()
    return report

def tables_from_multisync(task_params):
    result = []
    res = []
    pesel = task_params['params']['pesel']
    db = PostgresDatasource(Config.DATABASE_MULTISYNC)

    adres = telefon = email = zew = False
    data = db.dict_select(SQL, [pesel])
    if len(data) == 0:
        result.append({
            'type': 'info', 'text': 'MULTISYNC: Nie znaleziono pacjenta o podanym pesel',
        })
        return result
    else:
        cols = list([k for k in data[0].keys() if k != 'wyciek'])
        for d in data:
            row = [d[v] for v in cols]
            for indx,r in enumerate(row):
                if isinstance(r,bool):
                    row[indx] = 'Tak' if r else 'Nie'
            res.append(row)
            if d['jest_adres']:
                adres = True
            if d['jest_telefon']:
                telefon = True
            if d['jest_email']:
                email = True
            if d['systemy_zewnetrzne']:
                zew = True

        result.append({
            'type': 'vertTable',
            'title': f'MULTISYNC: PESEL: {pesel}',
            'data': [
                {'title': 'w bazach laboratoryjnych', 'value': 'Tak' if len(data) > 0 else 'Nie'},
                {'title': 'był adres', 'value': 'Tak' if adres else 'Nie'},
                {'title': 'był telefon', 'value': 'Tak' if telefon else 'Nie'},
                {'title': 'był email', 'value': 'Tak' if email else 'Nie'},
                {'title': 'dane z systemów klientów', 'value': 'Tak' if zew else 'Nie'},
                # {'title': 'w wyciekach danych', 'value': ', '.join(wycieki) if len(wycieki) > 0 else 'NIE'},

            ]
        })
        result.append({
            'type': 'table', 'title': 'MULTISYNC: W bazach',
            'header': cols,
            'data': prepare_for_json(res)
        })
    return result


def raport_pesele(task_params):
    res = []
    params = task_params['params']
    db = PostgresDatasource(Config.DATABASE_PESELE)
    for row in db.dict_select("""
        select min(last_sync::date) as valid_min, max(last_sync::date) as valid_max 
        from bazy where last_sync is not null and orders_to is null
    """):
        akt = f"{row['valid_min']} ~ {row['valid_max']} (w zależności od bazy)" if row['valid_min'] != row['valid_max'] else row['valid_min']
        res.append({
            'type': 'warning',
            'text': f"Aktualność danych: {akt}"
        })

    rows = db.dict_select("select * from pacjenci where pesel=%s", [params['pesel']])
    if len(rows) == 0:
        res.append({
            'type': 'info', 'text': 'Nie znaleziono pacjenta o podanym pesel',
        })
    elif len(rows) > 1:
        res.append({
            'type': 'error', 'text': 'Więcej niż 1 rekord pacjenta!',
        })
    else:
        bazy = {}
        bazy_dane = db.dict_select("select * from bazy")
        for row in bazy_dane:
            idx = str(row['id'])
            opis = row['symbol']
            if row['orders_to'] is not None:
                if row['orders_from'] is not None:
                    opis += f' (Archiwum {row["orders_from"].strftime("%Y-%m-%d")}-{row["orders_to"].strftime("%Y-%m-%d")})'
                else:
                    opis += f' (Archiwum do {row["orders_to"].strftime("%Y-%m-%d")})'
            bazy[idx] = opis
        dane = rows[0]['params']
        wycieki = dane.get('wycieki') or []
        wiersze = []
        adres = telefon = email = hl7 = False
        for baza, dwb in dict(dane.get('bazy') or {}).items():
            row = [bazy.get(baza)]
            if dwb['adres']:
                row.append('T')
                adres = True
            else:
                row.append('')
            if dwb['telefon']:
                row.append('T')
                telefon = True
            else:
                row.append('')
            if dwb['email']:
                row.append('T')
                email = True
            else:
                row.append('')
            row.append(len(dwb['zlecenia']))
            if len(dwb['hl7sys']) > 0:
                row.append(', '.join(dwb['hl7sys']))
                hl7 = True
            else:
                row.append('')
            wiersze.append(row)
        res.append({
            'type': 'vertTable',
            'title': params['pesel'],
            'data': [
                {'title': 'w bazach laboratoryjnych', 'value': 'TAK' if len(wiersze) > 0 else 'NIE'},
                {'title': 'był adres', 'value': 'TAK' if adres else 'NIE'},
                {'title': 'był telefon', 'value': 'TAK' if telefon else 'NIE'},
                {'title': 'był email', 'value': 'TAK' if email else 'NIE'},
                {'title': 'dane z systemów klientów', 'value': 'TAK' if hl7 else 'NIE'},
                {'title': 'w wyciekach danych', 'value': ', '.join(wycieki) if len(wycieki) > 0 else 'NIE'},

            ]
        })
        res.append({
            'type': 'table', 'title': 'w bazach',
            'header': 'Baza,Adres,Telefon,Email,Ile zleceń,Systemy klientów'.split(','),
            'data': prepare_for_json(wiersze)
        })
        res += tables_from_multisync(task_params)

    return res