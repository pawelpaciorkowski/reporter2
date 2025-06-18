from api.auth import login_required
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from tasks.db import redis_conn
from helpers import prepare_for_json, Kalendarz
from datasources.ick import IckDatasource
from datasources.mop import MopDatasource
from datetime import datetime
import json

MENU_ENTRY = 'Czynne punkty w dniach'

ADD_TO_ROLE = ['R-DYR', 'R-PM']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport przedstawia pierwsze godziny logowania w punktach we wskazanych dniach'),
    DateInput(field='dataod', title='Stan na dzień', default='T'),
    DateInput(field='datado', title='Stan na dzień', default='T'),
    Switch(field='niemop', title='Pokaż punkty spoza bazy'),
    Switch(field='tylkoniecz', title='Pokaż tylko nieczynne we wskazanych dniach'),
))

SQL = """select kan.system, kan.symbol as kanal, kan.nazwa as pp, 
    lg.ts::date as data,
    substr(min(lg.ts)::time::varchar, 0, 6) as godzina 
    from logowanie lg
    left join kanaly kan on kan.id=lg.kanal
    left join pracownicy pr on pr.id=lg.pracownik
    where lg.akcja='login' and lg.ts between %s and %s
    group by 1, 2, 3, 4
    order by 1, 2, 3, 4"""

DNI_TYGODNIA = 'poniedziałek wtorek środa czwartek piątek sobota niedziela'.split(' ')


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 31)
    task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'function': 'zbierz_logowanie'
    }
    report.create_task(task)
    task = {
        'type': 'mop',
        'priority': 1,
        'params': params,
        'function': 'zbierz_godziny_otwarcia'
    }
    report.create_task(task)
    report.save()
    return report


def zbierz_logowanie(task_params):
    params = task_params['params']
    ick = IckDatasource()
    res = {}
    for row in ick.dict_select(SQL, [params['dataod'], params['datado'] + ' 23:59:59']):
        k = "%s:%s" % (row['system'].strip(), row['kanal'].strip())
        if k not in res:
            res[k] = {
                'system': row['system'].strip(),
                'kanal': row['kanal'].strip(),
                'nazwa': row['pp'],
                'godziny': {}
            }
        res[k]['godziny'][row['data'].strftime("%Y-%m-%d")] = row['godzina']
    return res


def zbierz_godziny_otwarcia(task_params):
    params = task_params['params']
    res = redis_conn.get('mop:godziny_otwarcia_punktow_v2')
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
                'periods': pp.get('periods', []),
                'isInternet': pp.get('isInternet', False),
                'user': pp.get('user'),
            }
            if pp['isActive'] and pp.get('laboratory') is not None:
                rpp['lab'] = pp['laboratory'].get('symbol')
                res.append(rpp)
        redis_conn.set('mop:godziny_otwarcia_punktow_v2', json.dumps(res), ex=3600)
    return res


@login_required
def get_result(ident, user_labs_available):
    # DNI_TYGODNIA[data.weekday()]
    kal = Kalendarz()
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': [
            'xlsx',
            {
                'type': 'xlsx',
                'label': 'Excel (płaska tabela)',
                'flat_table': True,
                'flat_table_header': 'Laboratorium',
            },
            'pdf'
        ]
    }
    dane_logowanie = None
    dane_godziny = None
    start_params = None
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            if params['function'] == 'zbierz_logowanie':
                dane_logowanie = result
                start_params = params['params']
            elif params['function'] == 'zbierz_godziny_otwarcia':
                dane_godziny = result
    if dane_logowanie is not None and dane_godziny is not None:
        wynik = {}
        for pp in dane_godziny:
            pp['mop'] = True
            pp['nazwa'] = pp['name']
            if pp['lab'] not in wynik:
                wynik[pp['lab']] = {}
            wynik[pp['lab']][pp['symbol']] = pp
        for _, pp in dane_logowanie.items():
            if pp['system'] not in wynik:
                wynik[pp['system']] = {}
            if pp['kanal'] not in wynik[pp['system']]:
                wynik[pp['system']][pp['kanal']] = {
                    'symbol': pp['kanal'],
                    'lab': pp['system'],
                }
            wynik[pp['system']][pp['kanal']]['nazwa'] = pp['nazwa']
            wynik[pp['system']][pp['kanal']]['godziny'] = pp['godziny']

        for lab, punkty in wynik.items():
            if lab not in user_labs_available and '*' not in user_labs_available:
                continue
            wiersze = []
            header = 'Kanał,Nazwa punktu pobrań,Telefon,Koordynator,Uwagi'.split(',')
            for dzien in kal.dni(start_params['dataod'], start_params['datado']):
                header.append(dzien)
            for symbol, dane in punkty.items():
                if symbol == 'FALABCY':
                    print(dane)
                bez_internetu = not dane.get('isInternet', True)
                if not start_params['niemop'] and not dane.get('mop', False):
                    continue
                bylniecz = False
                for dzien in kal.dni(start_params['dataod'], start_params['datado']):
                    if dane.get('godziny', {}).get(dzien) is None:
                        bylniecz = True
                if start_params['tylkoniecz'] and not bylniecz:
                    continue
                uwagi = []
                if bez_internetu:
                    uwagi.append('bez internetu')
                if not dane.get('mop', False):
                    uwagi.append('spoza bazy')
                wiersz = [symbol, dane.get('nazwa', '---'), dane.get('phone', '')]
                if 'user' in dane and dane['user'] is not None:
                    wiersz.append('%s %s' % (dane['user'].get('name', ''), dane['user'].get('surname', '')))
                else:
                    wiersz.append('---')
                wiersz.append(', '.join(uwagi))
                otw = {}
                zam = {}
                if 'periods' in dane:
                    for p in dane['periods']:
                        if p.get('type', 'work') != 'work':
                            continue
                        if p.get('dayOfWeek', {}).get('name') in DNI_TYGODNIA:
                            dzien = p['dayOfWeek']['name']
                            if p.get('isAllDay'):
                                otw[dzien] = '00:00'
                                zam[dzien] = '23:59'
                            else:
                                if 'startAt' in p:
                                    czas = p['startAt'].split('T')[1][:5]
                                    if otw.get(dzien) is None or otw[dzien] > czas:
                                        otw[dzien] = czas
                                if 'endAt' in p:
                                    czas = p['endAt'].split('T')[1][:5]
                                    if zam.get(dzien) is None or zam[dzien] < czas:
                                        zam[dzien] = czas
                for dzien in kal.dni(start_params['dataod'], start_params['datado']):
                    dzien_tygodnia = DNI_TYGODNIA[datetime.strptime(dzien, '%Y-%m-%d').weekday()]
                    godzina = dane.get('godziny', {}).get(dzien)
                    cell = { 'value': godzina or '---' }
                    if otw.get(dzien_tygodnia) is not None and zam.get(dzien_tygodnia) is not None and not bez_internetu:
                        if godzina is None:
                            cell['background'] = 'red'
                        else:
                            t1 = datetime.strptime(godzina, '%H:%M')
                            t2 = datetime.strptime(otw[dzien_tygodnia], '%H:%M')
                            td = (t1 - t2).total_seconds()
                            if td <= 300:
                                cell['background'] = 'lightgreen'
                            elif td <= 1800:
                                cell['background'] = 'yellow'
                            else:
                                cell['background'] = '#ffaaaa'
                    if bez_internetu and godzina is not None:
                        cell['background'] = '#aaaaff'
                    wiersz.append(cell)
                wiersze.append(wiersz)
            res['results'].append({
                'type': 'table',
                'title': lab,
                'header': header,
                'data': prepare_for_json(wiersze)
            })
    res['progress'] = task_group.progress
    return res

# dodać kolumnę że spoza bazy
