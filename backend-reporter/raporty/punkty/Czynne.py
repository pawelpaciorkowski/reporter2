from api.auth import login_required
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch
from tasks import TaskGroup, Task
from tasks.db import redis_conn
from helpers import prepare_for_json
from datasources.ick import IckDatasource
from datasources.mop import MopDatasource
from datetime import datetime
import json

MENU_ENTRY = 'Czynne punkty pobrań'

ADD_TO_ROLE = ['R-DYR', 'R-PM']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport przedstawia pierwsze godziny logowania w danym punkcie pobrań danego dnia oraz osoby, które się w tym dniu logowały'),
    DateInput(field='data', title='Stan na dzień', default='T'),
    Switch(field='niemop', title='Pokaż punkty spoza bazy')
))

SQL = """select kan.system, kan.symbol as kanal, kan.nazwa as pp, 
    substr(min(lg.ts)::time::varchar, 0, 6) as godzina, 
    array_to_string(array_agg(distinct pr.nazwisko), ', ') as pracownicy
    from logowanie lg
    left join kanaly kan on kan.id=lg.kanal
    left join pracownicy pr on pr.id=lg.pracownik
    where lg.akcja='login' and lg.ts::date=%s
    group by 1, 2, 3
    order by 1, 2, 3"""

DNI_TYGODNIA = 'poniedziałek wtorek środa czwartek piątek sobota niedziela'.split(' ')


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    data = datetime.strptime(params['data'], '%Y-%m-%d')
    params['dzien_tygodnia'] = DNI_TYGODNIA[data.weekday()]
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
    cols, rows = ick.select(SQL, [params['data']])
    return rows


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
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    dzien_tygodnia = task_group.params['dzien_tygodnia']
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
    res['results'].append({
        'type': 'info',
        'text': 'Stan na dzień %s - %s' % (task_group.params['data'], dzien_tygodnia)
    })
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
        for pp in dane_logowanie:
            if pp[0] not in wynik:
                wynik[pp[0]] = {}
            if pp[1] not in wynik[pp[0]]:
                wynik[pp[0]][pp[1]] = {
                    'symbol': pp[1],
                    'lab': pp[0],
                }
            wynik[pp[0]][pp[1]]['nazwa'] = pp[2]
            wynik[pp[0]][pp[1]]['godzina'] = pp[3]
            wynik[pp[0]][pp[1]]['pracownicy'] = pp[4]

        for lab, punkty in wynik.items():
            # TODO: tu przefiltrować przez laboratoria usera
            if lab not in user_labs_available and '*' not in user_labs_available:
                continue
            wiersze = []
            header = 'Kanał,Nazwa punktu pobrań,Czynne od,Czynne do,Pierwsze logowanie,Stan,Pracownicy,Telefon,Koordynator'.split(
                ',')
            if start_params['niemop']:
                header.append('Spoza bazy')
            for symbol, dane in punkty.items():
                bez_internetu = not dane.get('isInternet', True)
                if not start_params['niemop'] and not dane.get('mop', False):
                    continue

                wiersz = [symbol, dane.get('nazwa', '---'), '', '', {
                    'value': dane.get('godzina', '---'),
                }, '?', dane.get('pracownicy', ''), dane.get('phone', '')]
                otw = None
                zam = None
                if bez_internetu:
                    wiersz[5] = 'bez internetu'
                if 'periods' in dane:
                    for p in dane['periods']:
                        if p.get('type', 'work') != 'work':
                            continue
                        if p.get('dayOfWeek', {}).get('name') == dzien_tygodnia:
                            if p.get('isAllDay'):
                                otw = '00:00'
                                zam = '23:59'
                            else:
                                if 'startAt' in p:
                                    czas = p['startAt'].split('T')[1][:5]
                                    if otw is None or otw > czas:
                                        otw = czas
                                if 'endAt' in p:
                                    czas = p['endAt'].split('T')[1][:5]
                                    if zam is None or zam < czas:
                                        zam = czas
                logowanie = wiersz[4]['value']
                if otw is not None and zam is not None and not bez_internetu:
                    wiersz[2] = otw
                    wiersz[3] = zam
                    if logowanie == '---':
                        wiersz[4]['background'] = 'red'
                        wiersz[5] = 'nieczynny'
                    else:
                        t1 = datetime.strptime(logowanie, '%H:%M')
                        t2 = datetime.strptime(otw, '%H:%M')
                        td = (t1 - t2).total_seconds()
                        if td <= 300:
                            wiersz[4]['background'] = 'lightgreen'
                            wiersz[5] = 'czynny'
                        elif td <= 1800:
                            wiersz[4]['background'] = 'yellow'
                            wiersz[5] = 'spóźn pow 5 min'
                        else:
                            wiersz[4]['background'] = '#ffaaaa'
                            wiersz[5] = 'spóźn pow 30 min'
                if bez_internetu and logowanie != '---':
                    wiersz[4]['background'] = '#aaaaff'
                if 'user' in dane and dane['user'] is not None:
                    wiersz.append('%s %s' % (dane['user'].get('name', ''), dane['user'].get('surname', '')))
                else:
                    wiersz.append('---')
                if start_params['niemop']:
                    wiersz.append('' if dane.get('mop', False) else 'T')
                wiersze.append(wiersz)
            res['results'].append({
                'type': 'table',
                'title': lab,  # TODO: wyciągać nazwy
                'header': header,
                'data': prepare_for_json(wiersze)
            })
    res['progress'] = task_group.progress
    return res

# dodać kolumnę że spoza bazy
