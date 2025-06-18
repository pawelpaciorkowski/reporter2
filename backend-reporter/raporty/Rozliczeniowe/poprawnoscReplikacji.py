from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_snr_connection
from datasources.snr import SNR
from datasources.reporter import ReporterDatasource
from api.common import get_db
from decimal import Decimal
MENU_ENTRY = 'Poprawnosc replikacji'

REQUIRE_ROLE = ['C-FIN', 'C-ROZL']
# REQUIRE_ROLE = 'ADMIN'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Poprawnosc replikacji'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria', symbole_snr=True),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
    Switch(field="filtrowac", title="Podział na grupy płatników"),
))

def start_report(params):
    laboratoria = []
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)
    rep = ReporterDatasource()
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

def raport_lab(task_params):
    lab = task_params['target']
    params = task_params['params']
    wynik = []
    tabb = []
    grupy = []
    tabbid = []
    tabbsys = []
    sql = """
    select 
      count(W.id) as "ILOSC", 
      sum(w.nettodlaplatnika) as "WARTOSC"
    from Wykonania W
        left outer join Platnicy P on W.platnik = P.ID	
        left outer join pozycjekatalogow pk on pk.symbol=w.badanie and pk.katalog = 'BADANIA'
    where 
        w.datarozliczeniowa between %s and %s and not W.bezPlatne and not w.jestpakietem and w.laboratorium = %s and (pk.hs->'grupa') is distinct from 'TECHNIC'
    """

    sql_gp = """
    select 
        pwl.hs->'grupa' as "GRUPA",
        count(W.id) as "ILOSC",
        sum(w.nettodlaplatnika) as "WARTOSC"
    from Wykonania W
        left outer join Platnicy P on W.platnik = P.ID
        left outer join Platnicywlaboratoriach Pwl on PWL.laboratorium = w.laboratorium and PWL.platnik = P.ID and not pwl.del				
        left outer join pozycjekatalogow pk on pk.symbol=w.badanie and pk.katalog = 'BADANIA'
    where 
        w.datarozliczeniowa between %s and %s and not W.bezPlatne and not w.jestpakietem and w.laboratorium = %s and (pk.hs->'grupa') is distinct from 'TECHNIC'
    group by pwl.hs->'grupa' 
    order by pwl.hs->'grupa'
    """

    with get_snr_connection() as snr:
        ostatnia_przesylka = snr.dict_select("select * from przesylki p where laboratorium = %s order by godzinaodebrania  desc limit 1", [lab])
        if params['filtrowac'] :
            wyniki = snr.dict_select(sql_gp, (params['dataod'], params['datado'], lab))
        else:
            wyniki = snr.dict_select(sql, (params['dataod'], params['datado'], lab))
        for row in wyniki:
            if params['filtrowac']:
                tabb.append({
                    'grupa' : row['GRUPA'],
                    'ilosc':row['ILOSC'],
                    'wartosc':row['WARTOSC'],
                    })
                if prepare_for_json(row['GRUPA']) not in grupy:
                      grupy.append(prepare_for_json(row['GRUPA']))
            else:
                tabb.append({
                    'ilosc':row['ILOSC'],
                    'wartosc':row['WARTOSC'],
                    })
            
    sqlz =	"""
    select 
        count(W.id) as ILOSC, 
        sum(w.cena) as WARTOSC
    from Wykonania W
        left outer join Badania B on B.Id = W.Badanie 
        left outer join GrupyBadan gb on gb.id=b.grupa
        left outer join Platnicy P on P.Id = W.Platnik
    where 
        W.Rozliczone between '%s' and '%s' and W.Anulowane is null and W.Platne = 1 and B.Pakiet = 0 and (gb.symbol not in ('TECHNIC') or b.grupa is null)
    """ % (params['dataod'], params['datado'])
    # TODO XXX sql injection

    sqlz_gp = """
    select 
        trim(GP.SYMBOL) as GRUPA, 
        count(W.id) as ILOSC, 
        sum(w.cena) as WARTOSC
    from Wykonania W
        left outer join Badania B on B.Id = W.Badanie 
        left outer join GrupyBadan gb on gb.id=b.grupa
        left outer join Platnicy P on P.Id = W.Platnik
        left outer join GrupyPlatnikow GP on GP.Id = P.Grupa
    where 
        W.Rozliczone between '%s' and '%s' and W.Anulowane is null and W.Platne = 1 and B.Pakiet = 0 and (gb.symbol not in ('TECHNIC') or b.GRUPA is null)
    group by GP.symbol order by GP.symbol
    """ % (params['dataod'], params['datado'])
    # TODO XXX sql injection

    tabz = []
    with get_centrum_connection(task_params['target'][:7], fresh=True) as conn:
        if params['filtrowac']:
            cols, rows = conn.raport_z_kolumnami(sqlz_gp)
            for row in rows:
                tabz.append({
                    'grupa':row[0],
                    'ilosc':row[1],
                    'wartosc':row[2],
                    })
                if prepare_for_json(row[0]) not in grupy:
                    grupy.append(prepare_for_json(row[0]))
                
        else:
            cols, rows = conn.raport_z_kolumnami(sqlz)
            for row in rows:
                tabz.append({
                    'ilosc':row[0],
                    'wartosc':row[1],
                    })
    if params['filtrowac']:
        for gr in grupy:
            tz = next((i for i in tabz if i['grupa'] == prepare_for_json(gr)), None)
            tb = next((i for i in tabb if i['grupa'] == prepare_for_json(gr)), None)
            tzilosc = 0
            tzwartosc = 0
            if tz is not None:
                tzilosc = tz['ilosc']
                tzwartosc = prepare_for_json(tz['wartosc'])
            tbilosc = 0
            tbwartosc = 0
            if tb is not None:
                tbilosc = tb['ilosc']
                tbwartosc = prepare_for_json(tb['wartosc'])


            wynik.append([
                lab,
                gr,
                tzilosc,
                tzwartosc,
                tbilosc,
                tbwartosc,
                tzilosc-tbilosc
      ])

    else:
        wynik.append([
            lab,
            tabz[0]['ilosc'],
            prepare_for_json(tabz[0]['wartosc']),
            tabb[0]['ilosc'],
            prepare_for_json(tabb[0]['wartosc']),
            tabz[0]['ilosc']-tabb[0]['ilosc']
        ])
            

    return wynik, ostatnia_przesylka


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
            result_rows, ostatnia_przesylka = result
            for row in result_rows:
                wiersze.append(prepare_for_json(row))
            if len(ostatnia_przesylka) > 0:
                op_row = ostatnia_przesylka[0]
                res['results'].append({
                    'type': 'info',
                    'text': f"Ostatnia przesyłka odebrana {op_row['godzinaodebrania']} {op_row['status']} {op_row['godzinawczytania']}"
                })
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])
    if params['params']['filtrowac']:
        header = [
                      [{'title': 'Laboratorium', 'fontstyle' : 'b', 'rowspan':2},{'title': 'Grupa', 'fontstyle' : 'b', 'rowspan':2},{'title': 'Zdalne', 'fontstyle': 'b', 'colspan': 2},{'title': 'Bieżące', 'fontstyle': 'b', 'colspan': 2}, {'title': 'Różnica', 'fontstyle' : 'b', 'rowspan':2}],
                      [{'title': 'Ilość badań'}, {'title': 'Wartość gotówki'},{'title': 'Ilość badań'}, {'title': 'Wartość badań'}], 
                ]
    else :
        header = [
                      [{'title': 'Laboratorium', 'fontstyle' : 'b', 'rowspan':2},{'title': 'Zdalne', 'fontstyle': 'b', 'colspan': 2},{'title': 'Bieżące', 'fontstyle': 'b', 'colspan': 2}, {'title': 'Różnica', 'fontstyle' : 'b', 'rowspan':2}],
                      [{'title': 'Ilość badań'}, {'title': 'Wartość gotówki'},{'title': 'Ilość badań'}, {'title': 'Wartość badań'}], 
                ]

    res['progress'] = task_group.progress
    res['results'].append(
      {
                'type': 'table',
                'title': 'Tabela prezentuje ilość i wartość płatnych nie anulowanych badań wykonanych w danym laboratorium, bez uwzględniania pakietów.',
                'header':header,

                'data': wiersze
            })
    return res

