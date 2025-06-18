import time
import os
from helpers import Kalendarz, get_centrum_connection, divide_chunks, prepare_for_json
from datasources.nocka import NockaDatasource
from datasources.snrkonf import SNRKonf
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task

MENU_ENTRY = None

SQL_ZLECENIODAWCY = """
    select zl.hs->'identzestgot' as identzestgot, zl.nazwa,
           zwl.symbol, zwl.laboratorium, lab.nazwa as lab_nazwa
    from zleceniodawcy zl
    left join zleceniodawcywlaboratoriach zwl on zwl.zleceniodawca=zl.id
    left join laboratoria lab on lab.symbol=zwl.laboratorium
    where zl.hs->'identzestgot' is not null and zl.hs->'identzestgot' != '' and not zl.del and not zwl.del
    order by 1, 3
"""

SQL_WYKONANIA = """
    select lab, zleceniodawca, lab_zlecenie_data, lab_zlecenie_nr, typ_zlecenia, lab_zlecenie, 
        sum(coalesce(lab_cena, 0)) as wartosc, array_to_string(array_agg(trim(badanie)), ' ') as badania
    from wykonania_pelne 
    where lab_zlecenie_data between %s and %s
    and zleceniodawca in %s
    and lab_bladwykonania is null and lab_powodanulowania is null and lab_platne and grupa_badan != 'TECHNIC'
    and lab_system=lab
    group by lab, zleceniodawca, lab_zlecenie_data, lab_zlecenie_nr, typ_zlecenia, lab_zlecenie
    having sum(coalesce(lab_cena, 0)) > 0
    order by lab_zlecenie_data, lab_zlecenie_nr
"""

SQL_PACJENCI = """
    select z.id, coalesce(p.nazwisko, '') || ' ' || coalesce(p.imiona, '') as pacjent
    from zlecenia z
    left join pacjenci p on p.id=z.pacjent
    where z.id in ($IDENTYFIKATORY$)
"""


def zbierz_nocka(task_params):
    params = task_params['params']
    nocka = NockaDatasource()
    return nocka.dict_select(SQL_WYKONANIA, [params['dataod'], params['datado'], tuple(params['symbole'])])


def zbierz_centrum(task_params):
    params = task_params['params']
    res = {}
    for chunk in divide_chunks(params['zlecenia'], 1000):
        sql = SQL_PACJENCI.replace('$IDENTYFIKATORY$', ','.join(['%d' % int(id) for id in chunk]))
        with get_centrum_connection(task_params['target'], fresh=True) as conn:
            cols, rows = conn.raport_z_kolumnami(sql)
            for row in rows:
                res[row[0]] = row[1]
    return res


def zrob_zestawienia_zeszly_miesiac(katalog_nadrzedny):
    kal = Kalendarz()
    snr = SNRKonf()
    pzm = kal.data('PZM')
    kzm = kal.data('KZM')
    katalog = os.path.join(katalog_nadrzedny, pzm[:7])
    if not os.path.isdir(katalog):
        os.mkdir(katalog, 0o775)
    do_zestawien = []
    zleceniodawcy = []
    for row in snr.dict_select(SQL_ZLECENIODAWCY):
        row['symbol'] = row['symbol'].strip()
        zleceniodawcy.append([row['identzestgot'], row['symbol'], row['nazwa']])
        row['identzestgot'] = row['identzestgot'].replace('/', '_').replace('.', '_').replace(' ', '_')
        row['plik'] = os.path.join(katalog, row['identzestgot'] + '.xlsx')
        if not os.path.exists(row['plik']):
            do_zestawien.append(row)

    zl_xlsx = ReportXlsx({'results': [{
        'type': 'table',
        'header': 'Identyfikator,Symbol,Nazwa'.split(','),
        'data': prepare_for_json(zleceniodawcy),
    }]})
    zl_xlsx.render_to_file(os.path.join(katalog, 'zleceniodawcy.xlsx'))
    if len(do_zestawien) == 0:
        return
    print('Do zebrania', [(row['identzestgot'], row['symbol']) for row in do_zestawien])
    symbole = [row['symbol'] for row in do_zestawien]
    task_group = TaskGroup(__PLUGIN__, {})
    task_group.create_task({
        'type': 'noc',
        'priority': 1,
        'params': {'dataod': pzm, 'datado': kzm, 'symbole': [s.strip() for s in symbole]},
        'function': 'zbierz_nocka',
        'timeout': 1800
    })
    task_group.save()
    finished = False
    wykonania = None
    zbierz_pacjentow = {}
    dane_pacjentow = {}
    while not finished:
        for job_id, params, status, result in task_group.get_tasks_results():
            if params['function'] == 'zbierz_nocka':
                if status == 'finished' and result is not None and wykonania is None:
                    print('Zebrana nocka', len(result))
                    wykonania = result
                    finished = True
                    for row in wykonania:
                        if row['lab'] not in zbierz_pacjentow:
                            print(row['lab'])
                            zbierz_pacjentow[row['lab']] = []
                            finished = False
                        zbierz_pacjentow[row['lab']].append(row['lab_zlecenie'])
                    for lab, zlecenia in zbierz_pacjentow.items():
                        print('Pacjenci do zebrania z', lab, len(zlecenia))
                        task_group.create_task({
                            'type': 'centrum',
                            'priority': 1,
                            'target': lab,
                            'params': {'zlecenia': zlecenia},
                            'function': 'zbierz_centrum',
                        })
                    task_group.save()
            elif params['function'] == 'zbierz_centrum':
                lab = params['target']
                if status in ('finished', 'failed') and lab not in dane_pacjentow:
                    print('Zebrani pacjenci z', lab)
                    dane_pacjentow[lab] = result
        if len(zbierz_pacjentow.keys()) > 0 and len(zbierz_pacjentow.keys()) == len(dane_pacjentow.keys()):
            finished = True
        else:
            time.sleep(5)
    pelne_wykonania = {}  # lab, symbol
    for row in wykonania:
        if row['lab'] not in pelne_wykonania:
            pelne_wykonania[row['lab']] = {}
        if row['zleceniodawca'] not in pelne_wykonania[row['lab']]:
            pelne_wykonania[row['lab']][row['zleceniodawca'].strip()] = []
        if dane_pacjentow[row['lab']] is not None:
            row['pacjent'] = dane_pacjentow[row['lab']][row['lab_zlecenie']]
        else:
            row['pacjent'] = 'BRAK POŁĄCZENIA Z LABORATORIUM'  # To jakoś odznaczyć żeby się nie generował plik
        pelne_wykonania[row['lab']][row['zleceniodawca']].append(row)
        print(row)
    zestawienia = {}
    for row in do_zestawien:
        plik = row['plik']
        if plik not in zestawienia:
            zestawienia[plik] = []
        wykonania_zest = pelne_wykonania.get(row['laboratorium'], {}).get(row['symbol'], [])
        if len(wykonania_zest) > 0:
            data = []
            for wyk in wykonania_zest:
                data.append([
                    wyk['lab_zlecenie_data'],
                    wyk['lab_zlecenie_nr'],
                    wyk['typ_zlecenia'],
                    wyk['pacjent'],
                    wyk['wartosc'],
                    wyk['badania']
                ])
            zestawienia[plik].append({
                'type': 'table',
                'title': '%s (%s - %s)' % (row['nazwa'], row['laboratorium'], row['symbol']),
                'header': 'Data rej.,Nr zlec.,Typ zlec.,Pacjent,Wartość [zł],Badania'.split(','),
                'data': prepare_for_json(data),
            })
    for plik, tabelki in zestawienia.items():
        xlsx = ReportXlsx({'results': tabelki})
        xlsx.render_to_file(plik)

def zrob_zestawienia_zalegle(katalog_nadrzedny):
    kal = Kalendarz()
    snr = SNRKonf()
    pzm = kal.data('2020-10-01')
    kzm = kal.data('2020-12-31')
    katalog = os.path.join(katalog_nadrzedny, 'zalegle')
    if not os.path.isdir(katalog):
        os.mkdir(katalog, 0o775)
    do_zestawien = []
    for row in snr.dict_select(SQL_ZLECENIODAWCY):
        if row['identzestgot'] not in ('GAPKRA', 'GAZSTEL'):
            continue
        # row['symbol'] = row['symbol'].ljust(7)
        row['symbol'] = row['symbol'].strip()
        row['identzestgot'] = row['identzestgot'].replace('/', '_').replace('.', '_').replace(' ', '_')
        row['plik'] = os.path.join(katalog, row['identzestgot'] + '.xlsx')
        if not os.path.exists(row['plik']):
            do_zestawien.append(row)
    if len(do_zestawien) == 0:
        return
    symbole = [row['symbol'] for row in do_zestawien]
    print('Do zebrania', [row['identzestgot'] for row in do_zestawien], symbole)
    task_group = TaskGroup(__PLUGIN__, {})
    task_group.create_task({
        'type': 'noc',
        'priority': 1,
        'params': {'dataod': pzm, 'datado': kzm, 'symbole': symbole},
        'function': 'zbierz_nocka',
        'timeout': 1800
    })
    task_group.save()
    finished = False
    wykonania = None
    zbierz_pacjentow = {}
    dane_pacjentow = {}
    while not finished:
        for job_id, params, status, result in task_group.get_tasks_results():
            if params['function'] == 'zbierz_nocka':
                if status == 'finished' and result is not None and wykonania is None:
                    print('Zebrana nocka', len(result))
                    wykonania = result
                    finished = True
                    for row in wykonania:
                        if row['lab'] not in zbierz_pacjentow:
                            print(row['lab'])
                            zbierz_pacjentow[row['lab']] = []
                            finished = False
                        zbierz_pacjentow[row['lab']].append(row['lab_zlecenie'])
                    for lab, zlecenia in zbierz_pacjentow.items():
                        print('Pacjenci do zebrania z', lab, len(zlecenia))
                        task_group.create_task({
                            'type': 'centrum',
                            'priority': 1,
                            'target': lab,
                            'params': {'zlecenia': zlecenia},
                            'function': 'zbierz_centrum',
                        })
                    task_group.save()
            elif params['function'] == 'zbierz_centrum':
                lab = params['target']
                if status in ('finished', 'failed') and lab not in dane_pacjentow:
                    print('Zebrani pacjenci z', lab)
                    dane_pacjentow[lab] = result
        if len(zbierz_pacjentow.keys()) > 0 and len(zbierz_pacjentow.keys()) == len(dane_pacjentow.keys()):
            finished = True
        else:
            time.sleep(5)
    pelne_wykonania = {}  # lab, symbol
    for row in wykonania:
        if row['lab'] not in pelne_wykonania:
            pelne_wykonania[row['lab']] = {}
        if row['zleceniodawca'] not in pelne_wykonania[row['lab']]:
            pelne_wykonania[row['lab']][row['zleceniodawca']] = []
        if dane_pacjentow[row['lab']] is not None:
            row['pacjent'] = dane_pacjentow[row['lab']][row['lab_zlecenie']]
        else:
            row['pacjent'] = 'BRAK POŁĄCZENIA Z LABORATORIUM'  # To jakoś odznaczyć żeby się nie generował plik
        pelne_wykonania[row['lab']][row['zleceniodawca']].append(row)
        print(row)
    zestawienia = {}
    for row in do_zestawien:
        plik = row['plik']
        if plik not in zestawienia:
            zestawienia[plik] = []
        wykonania_zest = pelne_wykonania.get(row['laboratorium'], {}).get(row['symbol'], [])
        if len(wykonania_zest) > 0:
            data = []
            for wyk in wykonania_zest:
                data.append([
                    wyk['lab_zlecenie_data'],
                    wyk['lab_zlecenie_nr'],
                    wyk['typ_zlecenia'],
                    wyk['pacjent'],
                    wyk['wartosc'],
                    wyk['badania']
                ])
            zestawienia[plik].append({
                'type': 'table',
                'title': '%s (%s - %s)' % (row['nazwa'], row['laboratorium'], row['symbol']),
                'header': 'Data rej.,Nr zlec.,Typ zlec.,Pacjent,Wartość [zł],Badania'.split(','),
                'data': prepare_for_json(data),
            })
    for plik, tabelki in zestawienia.items():
        xlsx = ReportXlsx({'results': tabelki})
        xlsx.render_to_file(plik)
