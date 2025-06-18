import json

from datasources.mop import MopDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty
from datasources.ick import IccDatasource
from tasks.db import redis_conn

MENU_ENTRY = 'Prośby o fakturę'
STATUSY = {
    'NEW': 'Nowa, niewydrukowany',
    'GEN': 'Wydrukowana, NIEPOTWIERDZONA',
    'ACK': 'Potwierdzona',
    'DEL': 'Wycofana'
}

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    TabbedView(field='tab', desc_title='Typ raportu', children=[
        Tab(title='Szukaj prośby', default=True, value='prosba',
            panel=VBox(
                InfoText(text='''Znajdź prośbę na podstawie 10-literowego identyfikatora prośby lub kodu kreskowego zlecenia.
                    Zostaną wyświetlone podstawowe informacje, aby pobrać treść prośby wejdź pod adres
                    http://2.0.1.101:8081/pof/pdf/IDENTYFIKATOR lub http://10.1.1.114:8081/pof/pdf/IDENTYFIKATOR
                    podstawiając w adresie identyfikator prośby.'''),
                TextInput(field='ident', title='Identyfikator'),
                TextInput(field='kodkreskowy', title='Kod kreskowy'),
            )
            ),
        Tab(title='Zestawienie', value='zbiorczy',
            panel=VBox(
                InfoText(text='Proszę wybrać zakres dat utworzenia prośby'),
                DateInput(field='dataod', title='Data początkowa', default='-1D'),
                DateInput(field='datado', title='Data końcowa', default='T'),
            )
            )
    ]),
))

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['tab'] == 'prosba':
        if not empty(params['ident']):
            if len(params['ident']) != 10:
                raise ValidationError('Podaj 10-znakowy identyfikator')
            params['_szukaj'] = 'ident'
        elif not empty(params['kodkreskowy']):
            if len(params['kodkreskowy']) < 9:
                raise ValidationError('Podaj co najmniej 9 znaków kodu kreskowego')
            params['_szukaj'] = 'kodkreskowy'
        else:
            raise ValidationError('Podaj kod kreskowy lub identyfikator')
        task = {
            'type': 'ick',
            'priority': 0,
            'params': params,
            'function': 'raport_prosba',
        }
        report.create_task(task)
    elif params['tab'] == 'zbiorczy':
        validate_date_range(params['dataod'], params['datado'], 366)
        task = {
            'type': 'ick',
            'priority': 0,
            'params': params,
            'function': 'raport_zbiorczy'
        }
        report.create_task(task)
    task = {
        'type': 'mop',
        'priority': 1,
        'params': params,
        'function': 'raport_punkty'
    }
    report.create_task(task)
    report.save()
    return report


def raport_prosba(task_params):
    params = task_params['params']
    if params['_szukaj'] == 'ident':
        sql = "select * from pof where ident=%s"
        sql_params = [params['ident']]
    elif params['_szukaj'] == 'kodkreskowy':
        sql = "select * from pof where barcode like %s order by id"
        sql_params = [params['kodkreskowy'][:9] + '%']
    icc = IccDatasource()
    prosby = icc.dict_select(sql, sql_params)
    res = []
    for pr in prosby:
        pr['statusy'] = icc.dict_select("select * from pof_statusy where pof_ident=%s order by ts", [pr['ident']])
        res.append(pr)
    return res


def raport_zbiorczy(task_params):
    params = task_params['params']
    sql = """
        select pof.ident, pof.system, pof.state, pof.created_at, pof.accepted_at,
            case when pof.system='hbz' then 'ZL: '||pof.long_sys_id else pof.barcode end as barcode,
            pof.simple_data, pof.helper_data,
            array_agg(ps.status) as statusy, array_agg(ps.ts) as statusy_ts
        from pof 
        left join pof_statusy ps on ps.pof_ident=pof.ident 
        where cast(pof.created_at as date) between %s and %s
        group by 1,2,3,4,5,6,7,8
        order by pof.created_at
    """
    icc = IccDatasource()
    return icc.dict_select(sql, [params['dataod'], params['datado']])


def raport_punkty(task_params):
    params = task_params['params']
    res = redis_conn.get('mop:nazwy_punktow')
    if res is not None:
        res = json.loads(res.decode())
    else:
        mop = MopDatasource()
        mop_res = mop.get_data('api/v2/collection-point')
        res = []
        for pp in mop_res:
            rpp = {
                'symbol': pp['marcel'],
                'name': pp['name'],
                'phone': pp.get('phone'),
            }
            if pp['isActive'] and pp.get('laboratory') is not None:
                rpp['lab'] = pp['laboratory'].get('symbol')
                res.append(rpp)
        redis_conn.set('mop:nazwy_punktow', json.dumps(res), ex=3600)
    return res

def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': ['xlsx', 'pdf']
    }
    dane_prosba = None
    dane_zbiorczy = None
    dane_punkty = None
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            if params['function'] == 'raport_prosba':
                dane_prosba = result
            elif params['function'] == 'raport_zbiorczy':
                dane_zbiorczy = result
            elif params['function'] == 'raport_punkty':
                dane_punkty = result
    if dane_punkty is not None:
        if dane_prosba is not None:
            if len(dane_prosba) == 0:
                res['errors'].append('Nie znaleziono prośby')
            for dp in dane_prosba:
                sd = json.loads(dp['simple_data'])
                hd = json.loads(dp['helper_data'])
                pp = hd.get('kanal', hd.get('punktPobranSymbol')) or ''
                ppm = 'NIE ZNALEZIONO !!!'
                for punkt_mop in dane_punkty:
                    if (punkt_mop['symbol'] or '').upper().strip() == pp.upper().strip():
                        ppm = 'Nazwa: %s, lab %s, tel %s' % (punkt_mop['name'], punkt_mop['lab'], punkt_mop['phone'])
                data = [
                    ('System, id', '%s, %s' % (dp['system'], dp['sys_id'] or dp['long_sys_id'])),
                    ('Punkt pobrań', pp),
                    ('Punkt pobrań MOP', ppm),
                    ('Status', STATUSY.get(dp['state'], dp['state'])),
                    ('Id gotowej', dp['ready']),
                    ('Utworzona', dp['created_at']),
                ]
                if dp['accepted_at'] is not None:
                    data.append(('Potwierdzona', dp['accepted_at']))

                data.append(('Akcje robota', '\n'.join('%s: %s' % (st['ts'], st['status']) for st in dp['statusy'])))
                data.append(('Dane prośby', repr(sd)))
                data.append(('Dane pomocnicze', repr(hd)))
                res['results'].append({
                    'type': 'vertTable',
                    'title': dp['ident'],
                    'data': [{'title': r[0], 'value': str(r[1])} for r in data]
                })
        if dane_zbiorczy is not None:
            data = []
            for row in dane_zbiorczy:
                sd = json.loads(row['simple_data'])
                hd = json.loads(row['helper_data'])
                pp = hd.get('kanal', hd.get('punktPobranSymbol')) or ''
                ppm = 'NIE ZNALEZIONO!!!'
                suma = 0.0
                akcje = 0
                akcja_ts = ''
                akcja_status = ''
                if len(row['statusy_ts']) > 0 and row['statusy_ts'][0] is not None:
                    akcje = len(row['statusy_ts'])
                    for ts, st in zip(row['statusy_ts'], row['statusy']):
                        if akcja_ts == '' or ts > akcja_ts:
                            akcja_ts = ts
                            akcja_status = st
                for punkt_mop in dane_punkty:
                    if (punkt_mop['symbol'] or '').upper().strip() == pp.upper().strip():
                        ppm = 'Nazwa: %s, lab %s, tel %s' % (punkt_mop['name'], punkt_mop['lab'], punkt_mop['phone'])
                if 'badania' in hd:
                    for bad in hd['badania']:
                        if bad['badanie_symbol'] in sd['badania']:
                            try:
                                suma += float(bad['cena'])
                            except:
                                pass
                else:
                    for bad in sd['pozycje']:
                        try:
                            suma += float(bad.get('cena', bad.get('cenaNetto')))
                        except:
                            pass
                data_row = [
                    row['ident'], row['barcode'], row['system'], pp, ppm,
                    STATUSY.get(row['state'], row['state']), row['created_at'], row['accepted_at'],
                    suma, akcje, akcja_ts, akcja_status
                ]
                if data_row[4] == 'NIE ZNALEZIONO!!!':
                    data_row[4] = {'value': data_row[4], 'background': 'red'}
                if row['state'] == 'GEN':
                    data_row[5] = {'value': data_row[5], 'background': 'red'}
                if data_row[11] == 'error':
                    data_row[11] = {'value': data_row[11], 'background': 'red'}
                data.append(data_row)
            res['results'].append({
                'type': 'table',
                'header': 'Identyfikator,Kod kreskowy,System,Punkt,Punkt baza,Status,Utworzono,Potwierdzono,Suma,Robot akcje,Ost akcja czas,Ost akcja status'.split(','),
                'data': prepare_for_json(data)
            })
    res['progress'] = task_group.progress
    return res