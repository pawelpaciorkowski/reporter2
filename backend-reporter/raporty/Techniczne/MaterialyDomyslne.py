import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none

MENU_ENTRY = 'Materiały domyślne'

REQUIRE_ROLE = ['L-KIER', 'C-FIN', 'C-ROZL', 'L-PRAC']

CACHE_TIMEOUT = 7200

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Materiały Domyślne w poszczególnych laboratoriach.
             Aktualność danych: nie starsze niż 2 godziny, dla pojedynczego badania bieżące, dla Stępińskiej zawsze dane z wczoraj."""),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria', pracownie_domyslne=True),
    BadanieSearch(field='badanie', title='Pojedyncze badanie'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    lb_task = {
        'type': 'centrum',
        'priority': 1,
        'target': 'GWROCLA',
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
                    trim(b.SYMBOL) as BADANIE, 
                    trim(g.symbol) as GRUPA, 
                    b.NAZWA 
                FROM BADANIA b 
                left outer join grupybadan g on g.id=b.grupa 
                WHERE 
                    b.DEL = 0
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
        return get_and_cache('pd:lista_badan_mat_dom', get_data, CACHE_TIMEOUT)


def raport_lab(task_params):
    params = task_params['params']

    def get_data(badanie=None):
        sql_metody_w_badaniach = """
          select trim(b.SYMBOL) as BADANIE, trim(m.SYMBOL) as material 
          from MATERIALYWBADANIACH mwb
          left join BADANIA b on mwb.BADANIE = b.ID
          left join MATERIALY m on mwb.MATERIAL = m.id
          where mwb.KOLEJNOSC = 0
          and b.DEL = 0
          """
        params_badania = []
        if badanie is not None:
            sql_metody_w_badaniach = sql_metody_w_badaniach.replace('b.DEL = 0', 'b.DEL = 0 and b.symbol=?')
            params_badania.append(badanie)
        metody_w_badaniach = None
        with get_centrum_connection(task_params['target'], load_config=True) as conn:
            system = conn.system_config['system_symbol']
            metody_w_badaniach = conn.raport_slownikowy(sql_metody_w_badaniach, params_badania )
        if metody_w_badaniach is None:
            raise Exception("Nie udało się pobrać danych")
        res = {
            'pojedyncze_badanie': badanie,
            'system': system,
            'metody_w_badaniach': metody_w_badaniach,
        }
        return res

    if params['badanie'] is not None:
        return get_data(params['badanie'])
    else:
        return get_and_cache('matdom:lab:%s' % task_params['target'], get_data, CACHE_TIMEOUT)


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
            else:
                badania_w_systemach[params['target']] = result
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
    if not jedno_badanie and lista_badan is not None and (not tylko_excel or task_group.progress == 1.0):
        for elem in lista_badan:
            symbol = elem[0].strip()
            badania.append(symbol)
            wszystko_o_badaniach[symbol] = {
                'grupa_badan': (elem[1] or '').strip(),
                'nazwa': elem[2] or '',
                'materialy_w_systemach' : {}
            }
        for _, stan in badania_w_systemach.items():
            system = stan['system'].strip()
            laboratoria.append(system)
            for mwb in stan['metody_w_badaniach']:
                symbol = mwb['badanie'].strip()
                if symbol not in wszystko_o_badaniach:
                    wszystko_o_badaniach[symbol] = { 'grupa_badan': '---', 'nazwa': symbol,'materialy_w_systemach' : {}}
                    badania.append(symbol)
                wszystko_o_badaniach[symbol]['materialy_w_systemach'][system] = mwb['material']
    if jedno_badanie:
        if lista_badan is not None:
            [symbol, grupa, nazwa] = lista_badan[0]
            res['results'].append({'type': 'info',
                                   'text': 'Materiały domyślne badania %s (%s), grupa badań %s' % (symbol, nazwa, grupa)})
            data = []
            header = ['Laboratorium', 'Materiał']
            for system, stan in badania_w_systemach.items():
                # TODO: sortowanie w kolejnosci, najlepiej w jakimś helperze
                wiersz = [system]
                mwb = first_or_none(stan['metody_w_badaniach'])
                wiersz.append(mwb['material'] if mwb is not None else '')
                data.append(wiersz)
            res['results'].append({
                'type': 'table',
                'header': header,
                'data': prepare_for_json(data)
            })
    else:
        def zrob_header_data():
            header = [{'title': 'Badanie (symbol, nazwa)', 'colspan': 2, 'fontstyle': 'b'}, 'Grupa']
            for lab in laboratoria:
              header.append(lab)
            data = []
            for bad in badania:
                wob = wszystko_o_badaniach[bad]
                wiersz = [bad, wob['nazwa'], wob['grupa_badan']]
                for lab in laboratoria:
                    wiersz.append({'value': wob['materialy_w_systemach'].get(lab, ''),})
                data.append(wiersz)
            return header, data

        if tylko_excel:
            res['results'].append({'type': 'info', 'text': 'Wybrano więcej niż 3 laboratoria - raport zostanie wygenerowany od razu do xlsx'})
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
                    'filename': 'MaterialyDomyslne_%s.xlsx' % datetime.datetime.now().strftime('%Y-%m-%d'),
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
