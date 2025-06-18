import json
from api.common import get_db
from dialog import Dialog, VBox, InfoText
from tasks import TaskGroup
from helpers import prepare_for_json
from datasources.sanepid import SanepidDatasource

MENU_ENTRY = 'Sanepid - anuluj niezaakceptowane'
REQUIRE_ROLE = ['C-ADM']


LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text='Usuwa niezaakceptowane zgłoszenia starsze niż 3-msc'),
))

TO_CANCEL_SQL = '''
select n.id from notifications n
where DATE_PART('day', CURRENT_DATE - date_added) > 90
and canceled is false
and (mailing_confirmed is false or mailing_confirmed is null)
'''
TO_CANCEL_WITH_DETAILS = '''
select n.id, n.barcode from notifications n
where id in %s
'''
SQL_UPDATE = f"update notifications set canceled=true where id in ({TO_CANCEL_SQL})"

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'noc',
        'priority': 1,
        'params': params,
        'function': 'raport_anuluj'
    }
    report.create_task(task)
    report.save()
    return report

def raport_anuluj(task_params):
    res = {
        'errors': [],
        'results': [],
        'actions': []
    }
    db = SanepidDatasource(read_write=True)

    cols, rows = db.select(TO_CANCEL_SQL)    
    if rows:
        db.execute(SQL_UPDATE)
        db.commit()

        with get_db() as rep_db:
            for ident in rows:
                rep_db.execute("""
                    insert into log_zdarzenia(obj_type, obj_id, typ, opis, parametry)
                    values('external_sanepid', %s, 'cancel-old', %s, %s)
                """, [
                    ident, __PLUGIN__, json.dumps(prepare_for_json({
                        'row': ident, 'task_params': SQL_UPDATE,
                    }))
                ])
            rep_db.commit()
        ids = tuple(r[0] for r in rows)
        cols, rows = db.select(TO_CANCEL_WITH_DETAILS, [ids])
        res['results'].append({
            'type': 'table',
            'title': 'Anulowano następujące zgłoszenia',
            'header': cols,
            'data': prepare_for_json(rows) })
    else:
        res['errors'].append('Brak zleceń do anulowania')
    return res