from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_snr_connection
from datasources.snr import SNRTest as SNR
from datasources.reporter import ReporterDatasource
from api.common import get_db
from decimal import Decimal

MENU_ENTRY = 'Poprawnosc replikacji - dokładne TEST'

REQUIRE_ROLE = ['C-FIN', 'C-ROZL']
# REQUIRE_ROLE = 'ADMIN'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text='Poprawnosc replikacji - dokładne BAZA TESTOWA'),
    LabSelector(field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
    Switch(field="filtrowac", title="Podział na grupy płatników"),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)
    rep = ReporterDatasource()
    lab_task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratoria'],
        'params': params,
        'function': 'raport_lab',
        'timeout': 2400,
    }
    report.create_task(lab_task)
    report.save()
    return report


def raport_lab(task_params):
    lab = task_params['target']
    params = task_params['params']
    wynik = []
    tabb = []
    grupybadan = []
    grupyplatnikow = []
    tabbid = []
    tabbsys = []
    sql = """
    select 
        (EXTRACT(DAY FROM w.datarozliczeniowa) || ' - ' || w.badanie) as "GRUPA", 
        count(W.id) as "ILOSC",
        trim(Pwl.hs->'grupa') as "GP"
    from Wykonania W
        left outer join Platnicy P on W.platnik = P.ID
        left outer join Platnicywlaboratoriach Pwl on PWL.laboratorium = w.laboratorium and PWL.platnik = P.ID and not pwl.del
        left outer join pozycjekatalogow pk on pk.symbol=w.badanie and pk.katalog = 'BADANIA'
    where 
        w.datarozliczeniowa between '%s' and '%s'	and 
        W.bezPlatne = 'f' and 
        w.jestpakietem = 'f' and 
        w.laboratorium = '%s' and 
        (pk.hs->'grupa') is distinct from 'TECHNIC'
    group by EXTRACT(DAY FROM w.datarozliczeniowa), w.badanie, pwl.hs->'grupa' 
    order by EXTRACT(DAY FROM w.datarozliczeniowa), w.badanie, pwl.hs->'grupa'
    """ % (params['dataod'], params['datado'], lab)
    # TODO XXX sql injection

    with get_snr_connection() as snr:
        wyniki = snr.dict_select(sql)
        for row in wyniki:
            tabb.append({
                'grupa': row['GRUPA'],
                'ilosc': row['ILOSC'],
                'gp': row['GP'],
            })
            if prepare_for_json(row['GRUPA']) not in grupybadan:
                grupybadan.append(prepare_for_json(row['GRUPA']))
            if prepare_for_json(row['GP']) not in grupyplatnikow:
                grupyplatnikow.append(prepare_for_json(row['GP']))

    sqlz = """
    select 
        (EXTRACT(DAY FROM W.Rozliczone) || ' - ' || trim(B.SYMBOL)) as GRUPA, 
        count(W.id) as ILOSC,
        trim(GP.SYMBOL) as symbol
    from Wykonania W
        left outer join Badania B on B.Id = W.Badanie 
        left outer join GrupyBadan gb on gb.id=b.grupa
        left outer join Platnicy P on P.Id = W.Platnik
        left outer join GrupyPlatnikow GP on GP.Id = P.Grupa
    where 
        W.Rozliczone between '%s' and '%s' and 
        W.Anulowane is null	and 
        W.Platne = 1 and 
        B.Pakiet = 0 and 
        (gb.symbol not in ('TECHNIC') or b.grupa is null)
    group by EXTRACT(DAY FROM W.Rozliczone), B.SYMBOL, GP.SYMBOL 
    order by GP.SYMBOL, EXTRACT(DAY FROM W.Rozliczone), B.SYMBOL
    """ % (params['dataod'], params['datado'])
    # TODO XXX sql injection

    tabz = []
    with get_centrum_connection(task_params['target'], fresh=False) as conn:
        cols, rows = conn.raport_z_kolumnami(sqlz)
        for row in rows:
            tabz.append({
                'grupa': row[0],
                'ilosc': row[1],
                'gp': row[2],
            })
            if prepare_for_json(row[2]) not in grupyplatnikow:
                grupyplatnikow.append(prepare_for_json(row[2]))
            if prepare_for_json(row[0]) not in grupybadan:
                grupybadan.append(prepare_for_json(row[0]))

    print(grupyplatnikow)
    if params['filtrowac']:
        for platnik in grupyplatnikow:
            if platnik == None:
                platnik = 'Gotówka'
            for badanie in grupybadan:
                tmpz = (i for i in tabz if i['gp'] == platnik and i['grupa'] == badanie)
                tmpb = (i for i in tabb if i['gp'] == platnik and i['grupa'] == badanie)
                wartz = wartb = 0
                for t in tmpz:
                    if t is None:
                        wartz = 0
                    else:
                        wartz = t['ilosc']
                for t in tmpb:
                    print(t)
                    if t is None:
                        wartb = 0
                    else:
                        wartb = t['ilosc']

                if wartz - wartb != 0:
                    wynik.append([
                        lab,
                        platnik,
                        badanie,
                        wartz,
                        wartb,
                        wartz - wartb
                    ])
    else:
        tmpz = []
        tmpb = []
        for badanie in grupybadan:
            tzilosc = sum(i['ilosc'] for i in tabz if i['grupa'] == badanie)
            tmpz.append({'ilosc': tzilosc, 'grupa': badanie})
            tbilosc = sum(i['ilosc'] for i in tabb if i['grupa'] == badanie)
            tmpb.append({'ilosc': tbilosc, 'grupa': badanie})

        for badanie in grupybadan:
            tz = next((i for i in tmpz if i['grupa'] == prepare_for_json(badanie)), None)
            tb = next((i for i in tmpb if i['grupa'] == prepare_for_json(badanie)), None)
            if tz is None:
                wartz = 0
            else:
                wartz = tz['ilosc']

            if tb is None:
                wartb = 0
            else:
                wartb = tb['ilosc']

            if wartz - wartb != 0:
                wynik.append([
                    lab,
                    badanie,
                    wartz,
                    wartb,
                    wartz - wartb
                ])

    return wynik


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

    filtrowac = False
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            for row in result:
                wiersze.append(prepare_for_json(row))
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])
        filtrowac = filtrowac or params['params']['filtrowac']
    if filtrowac:
        header = [{'title': 'Laboratorium', 'fontstyle': 'b'}, {'title': 'Grupa', 'fontstyle': 'b'},
                  {'title': 'Badanie', 'fontstyle': 'b'}, {'title': 'Zdalne', 'fontstyle': 'b'},
                  {'title': 'Bieżące', 'fontstyle': 'b'}, {'title': 'Różnica', 'fontstyle': 'b'}],
    else:
        header = [{'title': 'Laboratorium', 'fontstyle': 'b'}, {'title': 'Badanie', 'fontstyle': 'b'},
                  {'title': 'Zdalne', 'fontstyle': 'b'}, {'title': 'Bieżące', 'fontstyle': 'b'},
                  {'title': 'Różnica', 'fontstyle': 'b'}]

    res['progress'] = task_group.progress
    res['results'].append(
        {
            'type': 'table',
            'title': 'Tabela prezentuje różnicę ilościową między poszczególnymi badaniami wykonanymi w danym laboratorium, z rozbiciem na dni',
            'header': header,

            'data': wiersze
        })
    return res
