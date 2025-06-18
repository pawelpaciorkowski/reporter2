import json

from datasources.mop import MopDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty
from datasources.snrkonf import SNRKonf
from tasks.db import redis_conn

MENU_ENTRY = 'Grupa Gotówka'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Zestawienie sprzedaży gotówkowej zleceniodawców z grupy GOTOWKA. Wg dat rejestracji.'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 90)
    snr = SNRKonf()
    laby = {}
    for row in snr.dict_select("""
        select zl.nazwa, zwl.symbol, zwl.laboratorium
        from zleceniodawcy zl
        left join zleceniodawcywlaboratoriach zwl on zwl.zleceniodawca=zl.id
        where zl.hs->'grupa'='GOTOWKA' and not zl.del and not zwl.del"""):
        if row['laboratorium'] not in laby:
            laby[row['laboratorium']] = []
        laby[row['laboratorium']].append(
            [row['nazwa'], row['symbol']]
        )
    for lab, zleceniodawcy in laby.items():
        if lab == 'KOPERNIKA':
            lab = 'KOPERNI' # HAHA
        task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': {
                'dataod': params['dataod'],
                'datado': params['datado'],
                'zleceniodawcy': zleceniodawcy,
            },
            'function': 'raport_lab'
        }
        report.create_task(task)
    report.save()
    return report


def raport_lab(task_params):
    lab = task_params['target']
    params = task_params['params']
    symbole = [zl[1] for zl in params['zleceniodawcy']]
    with get_centrum_connection(lab) as conn:
        cols, rows = conn.raport_z_kolumnami("select id from oddzialy where del=0 and symbol in (%s)" % ','.join(
            ["'%s'" % symbol for symbol in symbole]))
        oddzialy = [str(row[0]) for row in rows]
    with get_centrum_connection(lab) as conn:
        sql = """
            select o.nazwa, o.symbol, count(zl.id), sum(coalesce(w.cena, 0.0))
            from zlecenia zl
            left join oddzialy o on o.id=zl.oddzial
            left join wykonania w on w.zlecenie=zl.id
            where zl.datarejestracji between ? and ?
            and zl.oddzial in (%s)
            and w.platne=1
            group by 1, 2 order by 2, 1
        """
        sql %= ','.join(["%s" % id for id in oddzialy])
        cols, rows = conn.raport_z_kolumnami(sql, [params['dataod'], params['datado']])
    res = []
    for row in rows:
        res.append([lab] + row)
    return prepare_for_json(res)


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': ['xlsx']
    }
    wiersze = []
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            for wiersz in result:
                wiersze.append(wiersz)
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])
    res['results'].append({
        'type': 'table',
        'header': 'Laboratorium Zleceniodawca Symbol Ilość Wartość'.split(' '),
        'data': wiersze,
    })
    res['progress'] = task_group.progress
    return res
