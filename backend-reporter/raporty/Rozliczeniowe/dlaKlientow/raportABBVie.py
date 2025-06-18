from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection
from datasources.reporter import ReporterDatasource
from api.common import get_db
from decimal import Decimal
MENU_ENTRY = 'Raport ABBVie'

REQUIRE_ROLE = ['C-FIN', 'C-CS', 'C-ROZL']
# REQUIRE_ROLE = 'ADMIN'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport z ilości wykonanych badań dla ABBVie'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 90)
    laby = []
    rep = ReporterDatasource()
    for row in rep.dict_select("""select symbol from laboratoria where aktywne and wewnetrzne or zewnetrzne and adres is not null"""):
      if row['symbol'] not in laby:
        laby.append(row['symbol'])
   
    for lab in laby:
        task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': {
                'dataod': params['dataod'],
                'datado': params['datado'],
            },
            'function': 'raport_lab'
        }
        report.create_task(task)
    report.save()
    return report

def raport_lab(task_params):
    lab = task_params['target']
    params = task_params['params']
    sql = """
    select
      coalesce(nullif(trim(k.symbol), ''), s.symbol) as KS,
      coalesce(nullif(trim(o.nazwa), ''), nullif(trim(k.nazwa), ''), 'Punkt Pobrań ' || s.nazwa) as KP,
      case when trim(o2.symbol) like '%UA' then 'UA' else 'PL' end as KRAJ,
      count(distinct case when trim(b.symbol) = 'AHCV' then w.id end) as AHCV2,
      count(case when trim(b.symbol) = 'AHCV' and (pa.symbol = 'WYNIK' or pa.symbol = 'AHCV' or pa.symbol = 'AHCVI') 
        and (
            (lower(wy.wyniktekstowy) like '%reaktywn%' and lower(wy.wyniktekstowy) not like '%niereaktywn%')
            or (lower(wy.wyniktekstowy) like '%obecn%' and lower(wy.wyniktekstowy) not like '%nieobecn%')
            or (lower(wy.wyniktekstowy) like '%dodatn%')
            or (lower(wy.wyniktekstowy) like '%pozytywn%')
        ) and wy.ukryty = '0' then w.id end) as AHCVDOD,
      count(case when trim(b.symbol) = 'HCV-PCR' and (pa.symbol = 'WYNIK' or pa.symbol = 'HCV-PCR') then w.id end) as HCVPCR,
      count(case when trim(b.symbol) = 'HCV-PCR' and (pa.symbol = 'WYNIK' or pa.symbol = 'HCV-PCR') and wy.wyniktekstowy like 'Wykryto%' and wy.ukryty = '0' then w.id end) as HCVPCRDOD
    from wykonania w
      left outer join zlecenia z on z.id=w.ZLECENIE
      left outer join wyniki wy on wy.WYKONANIE=w.ID
      left outer join parametry pa on pa.id =wy.PARAMETR
      left outer join PRACOWNICY pr on pr.id=z.PRACOWNIKODREJESTRACJI
      left outer join KANALY k on k.id=pr.KANALINTERNETOWY
      left outer join platnicy p on p.id= w.platnik
      left outer join badania b on b.id=w.BADANIE
      left outer join REJESTRACJE r on r.id=z.REJESTRACJA
      left outer join systemy s on S.id=r.system
      left outer join oddzialy o on o.id = k.oddzial
      left join oddzialy o2 on o2.id=z.oddzial
    where w.ROZLICZONE BETWEEN ? and ? and w.zatwierdzone is not null
      and p.nip='5252515835' and w.PLATNE ='1' and w.anulowane is null and b.symbol in ('KWAHCV', 'AHCV', 'HCV-PCR')
    group by o.nazwa, k.symbol, k.NAZWA, s.symbol, s.NAZWA, case when trim(o2.symbol) like '%UA' then 'UA' else 'PL' end
    order by k.symbol, k.NAZWA; 
    """
    with get_centrum_connection(lab) as conn:
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
        'header': 'Laboratorium,Symbol Punktu Pobrań,Nazwa Punktu Pobrań,Kraj,Liczna osób gdzie wykonano AHCV wykonany w laboratorium,AHCV dodatni,Liczba osób z HCV-RNA,Liczba osób z HCV-RNA dodatni'.split(','),
        'data': wiersze,
    })
    res['progress'] = task_group.progress
    return res