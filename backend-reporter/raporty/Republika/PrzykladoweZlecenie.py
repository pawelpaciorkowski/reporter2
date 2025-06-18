# select * from republika_stream_events where order_id='BELCHAT:495566' order by id


"""

Przykłady:

 - BELCHAT:495566 - dużo wykonań, zarejestrowane na świeżo
 - BELCHAT:495570 - utworzone bez numeru, numer nadany w innej transakcji?
 - BELCHAT:496023 - zlecenie z HL7

"""

import datetime
import json
from copy import copy
from dialog import Dialog, VBox, InfoText, DateInput, Radio, Switch, TextInput, ValidationError
from tasks import TaskGroup, Task
from pprint import pprint
from helpers import prepare_for_json, empty
from datasources.nocka import NockaDatasource
from datasources.postgres import PostgresDatasource
from helpers.validators import validate_date_range
from config import Config

MENU_ENTRY = "Przykładowe zlecenie"

LAUNCH_DIALOG = Dialog(
    title=MENU_ENTRY,
    panel=VBox(
        TextInput(field="order_id", title="ID zlecenia")
    ),
)


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if empty(params['order_id']) or ':' not in params['order_id']:
        raise ValidationError("Podaj prawidłowe id zlecenia")

    task = {"type": "noc", "priority": 1, "params": params, "function": "raport"}
    report.create_task(task)
    report.save()
    return report


def raport(task_params):
    params = task_params['params']
    order_id = params['order_id']
    db = PostgresDatasource("host=2.0.202.241 port=5432 user=postgres dbname=republika")
    rows = db.dict_select("select * from republika_stream_events where order_id=%s order by id", [order_id])
    events = {}
    if len(rows) == 0:
        return {
            'type': 'error', 'text': 'Nie znaleziono żadnych zdarzeń dla tego zlecenia'
        }
    res = []
    id_pracownikow = set()
    for row in rows:
        ed = row['event_data']
        if ed.get('pracownik') is not None:
            id_pracownikow.add(ed['pracownik'])
        events[row['id']] = row
        if row['event_type'] == 'CntZewZlecenieBind':
            for zew_row in db.dict_select(
                    "select * from republika_stream_events where entity_name=%s and entity_id=%s order by id",
                    [row['entity_name'], row['entity_id']]):
                events[zew_row['id']] = zew_row
    pracownicy = {}
    for row in db.dict_select("select * from pracownicy where rpl_src_system || ':' || (id::varchar) in %s", [
        tuple(id_pracownikow)
    ]):
        ident = '%s:%d' % (row['rpl_src_system'], row['id'])
        pracownicy[ident] = row['nazwisko']
    events_to_save = []
    for id in sorted(events.keys()):
        event = events[id]
        events_to_save.append(event)
        ed = event['event_data']
        cp = [event['event_ts'].strftime('%Y-%m-%d %H:%M:%S')]
        if ed.get('pracownik') is not None:
            cp.append(pracownicy[ed['pracownik']])
        res.append([
            id,
            '\n'.join(cp),
            event['domain_name'],
            event['event_type'],
            json.dumps(event['event_data'])
        ])
    with open('/tmp/events.json', 'w') as f:
        json.dump(prepare_for_json({
            'events': events_to_save,
            'lookup': {
                'pracownicy': pracownicy,
            },
        }), f)

    return {
        'type': 'table',
        'header': 'event id,Czas/pracownik,Dziedzina,Zdarzenie,Dane'.split(','),
        'data': prepare_for_json(res)
    }