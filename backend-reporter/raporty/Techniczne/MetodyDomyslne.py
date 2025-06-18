import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none

MENU_ENTRY = 'Metody domyślne'

REQUIRE_ROLE = ['L-KIER', 'C-FIN', 'C-ROZL', 'L-PRAC']

CACHE_TIMEOUT = 7200

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Metody domyślne i czasy wykonania dla poszczególnych badań w wybranych laboratoriach.
             Aktualność danych: nie starsze niż 2 godziny, dla pojedynczego badania bieżące, dla Stępińskiej zawsze dane z wczoraj."""),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria', pracownie_domyslne=True),
    BadanieSearch(field='badanie', title='Pojedyncze badanie'),
    Switch(field='czasy', title='Dołączyć czasy maksymalne na wykonanie'),
    Switch(field='listametod', title='Lista metod zamiast pojedynczej (w przypadku więcej niż jednej metody domyślnej)')
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    lb_task = {
        'type': 'centrum',
        'priority': 1,
        'target': 'CZERNIA',
        'params': params,
        'function': 'raport_lista_badan',
    }
    report.create_task(lb_task)
    for lab in params['laboratoria']:
        lab_task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'raport_lab',
        }
        report.create_task(lab_task)
    report.save()
    return report


def raport_lista_badan(task_params):
    params = task_params['params']

    def get_data(badanie=None):
        sql = """select 
                    b.SYMBOL, 
                    g.symbol as GRUPA, 
                    gd.symbol as GRUPAD, 
                    b.NAZWA 
                FROM BADANIA b 
                left outer join grupybadan g on g.id=b.grupa 
                left outer join grupydodrukowania gd on gd.id=b.grupadodrukowania 
                WHERE 
                    b.DEL = 0 and (g.symbol <> 'TECHNIC' or g.symbol is null) 
                    AND ((b.PAKIET = 0) OR (b.REJESTROWAC=1)) 
                ORDER BY b.SYMBOL """
        params = []
        if badanie is not None:
            sql = sql.replace('b.DEL = 0', 'b.DEL = 0 and b.symbol=?')
            params.append(badanie)
        with get_centrum_connection(task_params['target']) as conn:
            cols, rows = conn.raport_z_kolumnami(sql, params)
            return rows

    if params['badanie'] is not None:
        return get_data(params['badanie'])
    else:
        return get_and_cache('pd:lista_badan_met_dom', get_data, CACHE_TIMEOUT)


def raport_lab(task_params):
    params = task_params['params']
    cache_key = 'metdom:lab:%s' % task_params['target']
    if params['listametod']:
        cache_key = cache_key.replace('metdom', 'metdoml')

    def get_data(badanie=None):
        sql_metody_w_badaniach = """select 
                b.Symbol as BADANIE, 
                b.CzasMaksymalny as MAXY, 
                s.Symbol as SYSTEM, 
                m.Symbol as METODA 
            FROM PowiazaniaMetod pm 
            left outer join Badania b on b.id = pm.badanie and b.del = 0 
            left outer join Metody m on m.id = pm.metoda and m.del = 0 
            left outer join Systemy s on s.id = pm.system and s.del = 0 
            left outer join Pracownie p on p.id = m.pracownia and p.del = 0 
            WHERE 
                m.DEL = 0 and b.DEL = 0 and s.DEL = 0 and p.del =0 and pm.DEL =0 and s.symbol = ?
                and pm.dowolnytypzlecenia=1 and pm.dowolnarejestracja=1 and pm.dowolnyoddzial=1 and pm.dowolnyplatnik=1 and pm.dowolnymaterial=1 
            ORDER BY b.symbol, p.symbol """
        sql_badania_aktywne = """select 
                b.Symbol as BADANIE, 
                b.bezrejestracji as BEZR, 
                b.ukryte as UKRYTE, 
                b.dorozliczen as DOROZLICZEN 
            FROM Badania b 
            WHERE 
                b.DEL = 0 """
        params_badania = []
        if params['listametod']:
            sql_metody_w_badaniach = sql_metody_w_badaniach.replace('m.Symbol as METODA', 'list(m.Symbol) as METODA')
            sql_metody_w_badaniach = sql_metody_w_badaniach.replace('ORDER BY b.symbol, p.symbol', 'GROUP BY 1,2,3 ORDER BY 1')
        if badanie is not None:
            sql_metody_w_badaniach = sql_metody_w_badaniach.replace('b.DEL = 0', 'b.DEL = 0 and b.symbol=?')
            sql_badania_aktywne = sql_badania_aktywne.replace('b.DEL = 0', 'b.DEL = 0 and b.symbol=?')
            params_badania.append(badanie)
        metody_w_badaniach = badania_aktywne = None
        with get_centrum_connection(task_params['target'], load_config=True) as conn:
            system = conn.system_config['system_symbol'] # dla BRUSKWI mamy LABKWI i nie działa, ale BRUSKWI też nie działa
            metody_w_badaniach = conn.raport_slownikowy(sql_metody_w_badaniach, params_badania + [system])
            badania_aktywne = conn.raport_slownikowy(sql_badania_aktywne, params_badania)
        if metody_w_badaniach is None or badania_aktywne is None:
            raise Exception("Nie udało się pobrać danych")
        res = {
            'pojedyncze_badanie': badanie,
            'system': system,
            'metody_w_badaniach': metody_w_badaniach,
            'badania_aktywne': badania_aktywne
        }
        return res

    if params['badanie'] is not None:
        return get_data(params['badanie'])
    else:
        return get_and_cache(cache_key, get_data, CACHE_TIMEOUT)


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': []
    }
    wiersze = []
    start_params = None
    lista_badan = None
    badania_w_systemach = {}
    bledy_polaczen = []
    badania = []
    laboratoria = []
    wszystko_o_badaniach = {}
    for job_id, params, status, result in task_group.get_tasks_results():
        if start_params is None:
            start_params = params['params']
        if status == 'finished' and result is not None:
            if params['function'] == 'raport_lista_badan':
                lista_badan = result
                # wiersze.append(['Lista badań', repr({'lista_badan': result})])
            else:
                badania_w_systemach[params['target']] = result
                # wiersze.append([params['target'], repr(result)])
                # params['target'], row['system'], row['platnik'], row['data'], row['numer'],
                # row['pacjent'], row['pesel'], row['badania']
        if status == 'failed':
            bledy_polaczen.append(params['target'])
    if len(bledy_polaczen) > 0:
        res['errors'].append('%s - błąd połączenia' % ', '.join(bledy_polaczen))
    jedno_badanie = False
    tylko_excel = False
    if start_params['badanie'] is not None:
        jedno_badanie = True
    if not jedno_badanie and len(start_params['laboratoria']) > 3:
        tylko_excel = True
    dolacz_czasy = start_params['czasy']
    if not jedno_badanie and lista_badan is not None and (not tylko_excel or task_group.progress == 1.0):
        for elem in lista_badan:
            symbol = elem[0].strip()
            badania.append(symbol)
            wszystko_o_badaniach[symbol] = {
                'grupa_badan': (elem[1] or '').strip(),
                'grupa_cennikowa': (elem[2] or '').strip(),
                'nazwa': elem[3] or '',
                'pracownie_w_systemach': {},
                'czasy_w_systemach': {},
                'czynne_w_systemach': {},
            }
        for _, stan in badania_w_systemach.items():
            system = stan['system'].strip()
            laboratoria.append(system)
            for mwb in stan['metody_w_badaniach']:
                symbol = mwb['badanie'].strip()
                if symbol not in wszystko_o_badaniach:
                    wszystko_o_badaniach[symbol] = {'grupa_badan': '---', 'grupa_cennikowa': '---', 'nazwa': symbol,
                                                    'pracownie_w_systemach': {}, 'czasy_w_systemach': {},
                                                    'czynne_w_systemach': {}}
                    badania.append(symbol)
                wszystko_o_badaniach[symbol]['pracownie_w_systemach'][system] = mwb['metoda']
                wszystko_o_badaniach[symbol]['czasy_w_systemach'][system] = mwb['maxy'] or ''
            for ba in stan['badania_aktywne']:
                symbol = ba['badanie'].strip()
                if symbol not in wszystko_o_badaniach:
                    wszystko_o_badaniach[symbol] = {'grupa_badan': '---', 'grupa_cennikowa': '---', 'nazwa': symbol,
                                                    'pracownie_w_systemach': {}, 'czasy_w_systemach': {},
                                                    'czynne_w_systemach': {}}
                    badania.append(symbol)
                czynne = ba['bezr'] == 0 and ba['ukryte'] == 0 and ba['dorozliczen'] == 0
                wszystko_o_badaniach[symbol]['czynne_w_systemach'][system] = czynne
        # TODO: sortowanie laboratoriów

    if jedno_badanie:
        if lista_badan is not None:
            [symbol, grupa, grupad, nazwa] = lista_badan[0]
            res['results'].append({'type': 'info',
                                   'text': 'Pracownie domyślne badania %s (%s), grupa badań %s, grupa cennikowa %s' % (
                                   symbol, nazwa, grupa, grupad)})
            data = []
            header = ['Laboratorium', 'Pracownia', 'Bez rejestracji', 'Ukryte', 'Do rozliczeń']
            if dolacz_czasy:
                header.append('Czas max')
            for system, stan in badania_w_systemach.items():
                # TODO: sortowanie w kolejnosci, najlepiej w jakimś helperze
                wiersz = [system]
                mwb = first_or_none(stan['metody_w_badaniach'])
                ba = first_or_none(stan['badania_aktywne'])
                wiersz.append(mwb['metoda'] if mwb is not None else '')
                if ba is not None:
                    wiersz.append('T' if ba['bezr'] else '')
                    wiersz.append('T' if ba['ukryte'] else '')
                    wiersz.append('T' if ba['dorozliczen'] else '')
                else:
                    wiersz += ['', '', '']
                if dolacz_czasy:
                    wiersz.append(mwb['maxy'] if mwb is not None else '')
                data.append(wiersz)
            res['results'].append({
                'type': 'table',
                'header': header,
                'data': prepare_for_json(data)
            })
    else:
        def zrob_header_data():
            header = [{'title': 'Badanie (symbol, nazwa)', 'colspan': 2, 'fontstyle': 'b'}, 'Grupa', 'Grupa cennikowa']
            for lab in laboratoria:
                if dolacz_czasy:
                    header.append({'title': lab, 'colspan': 2})
                else:
                    header.append(lab)
            data = []
            for bad in badania:
                wob = wszystko_o_badaniach[bad]
                wiersz = [bad, wob['nazwa'], wob['grupa_badan'], wob['grupa_cennikowa']]
                for lab in laboratoria:
                    kolor = '#ffffff' if wob['czynne_w_systemach'].get(lab, False) else '#cccccc'
                    wiersz.append({'value': wob['pracownie_w_systemach'].get(lab, ''), 'background': kolor})
                    if dolacz_czasy:
                        wiersz.append({'value': wob['czasy_w_systemach'].get(lab, ''), 'background': kolor})
                data.append(wiersz)
            return header, data

        if tylko_excel:
            res['results'].append({'type': 'info',
                                   'text': 'Wybrano więcej niż 3 laboratoria - raport zostanie wygenerowany od razu do xlsx'})
            if task_group.progress == 1:
                # print('Robimy dane', datetime.datetime.now().strftime('%H:%M:%S'))
                header, data = zrob_header_data()
                # print('Robimy excela', datetime.datetime.now().strftime('%H:%M:%S'))
                rep = ReportXlsx({'results': [{
                    'type': 'table',
                    'header': header,
                    'data': prepare_for_json(data)
                }]}, freeze_before='E2')
                res['results'].append({
                    'type': 'download',
                    'content': base64.b64encode(rep.render_as_bytes()).decode(),
                    'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'filename': 'MetodyDomyslne_%s.xlsx' % datetime.datetime.now().strftime('%Y-%m-%d'),
                })
                # print('Gotowe', datetime.datetime.now().strftime('%H:%M:%S'))
        else:
            header, data = zrob_header_data()
            res['results'].append({
                'type': 'table',
                'header': header,
                'data': prepare_for_json(data)
            })
    if not tylko_excel:
        res['actions'].append('xlsx')
    res['progress'] = task_group.progress
    return res
