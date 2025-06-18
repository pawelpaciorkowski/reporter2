from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json, get_snr_connection
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task

MENU_ENTRY = 'Ile badań pracownie'

REQUIRE_ROLE = ['C-FIN']
ADD_TO_ROLE = ['R-MDO']

SQL = """
    select Pr.Symbol AS Pracownia, Gb.Symbol as GrupaBadan, GPL.Symbol as GrupaPlatnikow,
    cast(W.Rozliczone as DATE) as Data, count(W.id) as ILOSC
    from Wykonania W 
    left outer join Badania B on B.Id = W.Badanie 
    left outer join Pracownie Pr on Pr.Id = W.Pracownia 
    left outer join GrupyPracowni GP on GP.Id = Pr.Grupa 
    left outer join zlecenia z on z.id=w.zlecenie 
    left outer join typyzlecen tz on tz.id = z.typzlecenia 
    left outer join Platnicy P on P.Id = W.Platnik 
    left outer join GrupyPlatnikow GPL on GPL.Id = P.Grupa
    left outer join GrupyBadan GB on GB.Id = B.Grupa 
    left outer join Aparaty ap on ap.id = w.aparat
    where 
    W.Rozliczone between ? and ?
    and W.Anulowane is null and (GB.Symbol not in ('TECHNIC', 'DOPLATY', 'INNE') or GB.Symbol is null)
    and W.Platne = 1
    and B.Pakiet = 0 
    and (P.Symbol not like '%KONT%' or P.Symbol is null) 
    and ((TZ.symbol <> 'K' and Tz.symbol <> 'KZ' and Tz.symbol <> 'KW') or Tz.symbol is null)
    and (GP.Symbol <> 'ALAB' or GP.Symbol is null)
    group by 1, 2, 3, 4 order by 1, 2, 3, 4
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="""Raport z liczby wykonanych badań w laboratoriach z rozbiciem na pracownie, grupy badań i grupy płatników.
            W przypadku CZERNIA używana jest baza bieżąca, a nie raportowa. Dołączanie cen możliwe jest tylko przy wykonywaniu raportu
            z jednego dnia i z pojedynczego badania. Raport pokazuje oddzielnie ceny z bazy laboratoryjnej i ceny z bazy rozliczeniowej.
            Dla badań gotówkowych ceny tych samych badań mogą pojawić się w obu kolumnach. W przypadku baz nierozliczanych przez SNR - ceny wszystkich badań
            będą w kolumnie suma lab. Kolumna SNR braki oznacza dla ilu wykonań z danego wiersza nie znaleziono odpowiedników w SNR - taka sytuacja
            jest możliwa w przypadku problemów z połączeniem, bazy której nie rozliczamy centralnie lub gdy jest zatrzymana synchronizacja do SNR bieżących badań w okresie rozliczeń.
            Dla badań wykonywanych w innym laboratorium niż rejestracja ceny dla klientów pojawią się po stronie laboratorium rejestracji.
            Raport wg daty rozliczeniowej"""),
    DateInput(field='dataod', title='Data początkowa', default='-1D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
    TextInput(field='badanie', title='Pojedyncze badanie (symbol)'),
    TextInput(field='platnik_nip', title='NIP'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    Switch(field='pokaz_badania', title='Grupuj po badaniach (a nie po grupach)'),
    Switch(field='pokaz_aparat', title='Podział na aparaty'),
    Switch(field='dolacz_ceny', title='Dołącz ceny')
))


def start_report(params):
    laboratoria = []
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)
    if params['dolacz_ceny'] and params['dataod'] != params['datado']:
        raise ValidationError("W przypadku dołączania cen należy wybrać okres 1 dnia.")
    if params['dolacz_ceny'] and (params['badanie'] or '').strip().upper() == '':
        raise ValidationError("W przypadku dołączania cen należy wybrać pojedyncze badanie.")
    for lab in params['laboratoria']:
        lab_task = {
            'type': 'centrum',
            'priority': 1,
            'timeout': 90,
            'target': lab,
            'params': params,
            'function': 'zbierz_lab',
        }
        report.create_task(lab_task)
    report.save()
    return report


def zbierz_lab(task_params):
    params = task_params['params']
    oddnia = params['dataod']
    dodnia = params['datado']
    res = []
    sql = SQL
    sql_params = [oddnia, dodnia]
    bad = (params['badanie'] or '').strip().upper()
    if bad != '':
        with get_centrum_connection(task_params['target'], fresh=True) as conn:
            cols, rows = conn.raport_z_kolumnami("select id from badania where symbol=? and del=0", [bad])
            if len(rows) > 0:
                sql = sql.replace('and W.Anulowane is null', 'and W.Badanie=? and W.Anulowane is null')
                sql_params.append(rows[0][0])
            else:
                raise Exception('Nie znaleziono badania')
    nip = (params['platnik_nip'] or '').strip().upper()
    if nip != '':
        with get_centrum_connection(task_params['target'], fresh=True) as conn:
            cols, rows = conn.raport_z_kolumnami("select id from platnicy where nip=? and del=0", [nip])
            # TODO XXX może być więcej płatników z tym samym NIPem
            if len(rows) > 0:
                sql = sql.replace('and W.Anulowane is null', 'and W.Platnik=? and W.Anulowane is null')
                sql_params.append(rows[0][0])
            else:
                raise Exception('Nie znaleziono płatnika o podanym numerze NIP')
    if params['pokaz_badania']:
        sql = sql.replace('Gb.Symbol as GrupaBadan', 'B.Symbol as Badanie')
    if params['pokaz_aparat']:
        sql = sql.replace('cast(W.Rozliczone as DATE) as Data',
                          'cast(W.Rozliczone as DATE) as Data, Ap.symbol as aparat, Ap.nazwa as aparat_nazwa')
        sql = sql.replace('1, 2, 3, 4', '1, 2, 3, 4, 5, 6')
    if params['dolacz_ceny']:
        sql = sql.replace("count(W.id) as ILOSC",
                          "count(W.id) as ILOSC, sum(coalesce(W.cena, 0)) as SumaGot, List(cast(W.sysid as varchar(20)) || '^' || W.system ) as Wykonania")
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
        for row in rows:
            res.append([task_params['target']] + row)
    return res


def zbierz_snr(task_params):
    params = task_params['params']
    result = {}
    with get_snr_connection() as conn:
        for lab, ident_lists in params['identyfikatory'].items():
            snr_lab = lab
            if snr_lab == 'KOPERNI':
                snr_lab = 'KOPERNIKA'
            result[lab] = {}
            for ident_list in ident_lists:
                idents = ["'%s'" % id.replace("'", "\\'").strip() for id in ident_list.split(',')]
                joined_idents = ','.join(idents)
                sql = """select count(id) as ilosc, sum(nettodlaplatnika) as suma from wykonania where
                    laboratorium=%s and datarozliczeniowa between %s and %s and
                    wykonanie in (""" + joined_idents + """)
                    """
                for row in conn.dict_select(sql, [snr_lab, params['dataod'], params['datado']]):
                    braki = len(idents)-row['ilosc']
                    result_braki = braki
                    if braki != 0:
                        result_braki = { 'value': braki, 'background': '#ff0000' if braki == len(idents) else '#ffa500' }
                    result[lab][ident_list] = (row['suma'], result_braki)
    return result


def get_result(ident):
    task_group = TaskGroup.load(ident)
    header = 'Laboratorium,Pracownia,Grupa badań,Grupa płatników,Data,Ilość'.split(',')
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': ['xlsx']
    }
    wiersze = []
    jest_raport_snr = False
    identyfikatory_wykonan = {}
    dataod = datado = None
    dolacz_ceny = False
    snr_results = None
    for job_id, params, status, result in task_group.get_tasks_results():
        if params['function'] == 'zbierz_snr':
            jest_raport_snr = True
            if status == 'finished':
                snr_results = result
    for job_id, params, status, result in task_group.get_tasks_results():
        if params['function'] == 'zbierz_lab':
            if status == 'finished' and result is not None:
                if params['params']['pokaz_badania']:
                    header[2] = 'Badanie'
                if params['params']['pokaz_aparat']:
                    if 'Aparat' not in header:
                        header.insert(5, 'Aparat')
                        header.insert(6, 'Aparat nazwa')
                if params['params']['dolacz_ceny']:
                    if 'Suma lab.' not in header:
                        header += ['Suma lab.', 'Suma SNR', 'Braki SNR']
                    if snr_results is not None:
                        for row in result:
                            suma, braki = snr_results.get(params['target'], {}).get(row[-1], ('???', '???'))
                            row[-1] = suma
                            row.append(braki)
                            wiersze.append(row)
                    else:
                        dolacz_ceny = True
                        dataod = params['params']['dataod']
                        datado = params['params']['datado']
                        if params['target'] not in identyfikatory_wykonan:
                            identyfikatory_wykonan[params['target']] = []
                        for row in result:
                            identyfikatory_wykonan[params['target']].append(row[-1])
                            wiersze.append(row[:-1])
                else:
                    for row in result:
                        wiersze.append(row)
            if status == 'failed':
                res['errors'].append('%s - błąd połączenia' % params['target'])
    if dolacz_ceny and task_group.progress == 1.0 and not jest_raport_snr:
        task = {
            'type': 'snr',
            'priority': 1,
            'params': {
                'dataod': dataod,
                'datado': datado,
                'identyfikatory': identyfikatory_wykonan,
            },
            'function': 'zbierz_snr',
        }
        task_group.create_task(task)
        task_group.save()
        res['progress'] = 0.5
    else:
        res['progress'] = task_group.progress
    res['results'].append({
        'type': 'table',
        'header': header,
        'data': prepare_for_json(wiersze)
    })
    return res
