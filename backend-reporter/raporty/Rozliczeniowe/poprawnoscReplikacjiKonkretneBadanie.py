from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_snr_connection
from datasources.snr import SNR
from datasources.reporter import ReporterDatasource
from api.common import get_db
from decimal import Decimal

MENU_ENTRY = 'Poprawnosc replikacji - konkretne badanie'

REQUIRE_ROLE = ['C-FIN', 'C-ROZL']
# REQUIRE_ROLE = 'ADMIN'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text=MENU_ENTRY),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', symbole_snr=True),
    DateInput(field='data', title='Data', default='PZM'),
    TextInput(field='symbol', title='Symbol badania'),
    TextInput(field='grupa', title='Filtr grupa płatników'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    params['symbol'] = (params['symbol'] or '').upper().strip()
    params['grupa'] = (params['grupa'] or '').upper().strip()
    if params['symbol'] is None or len(params['symbol'].strip()) == 0:
        raise ValidationError("Nie wybrano badania")
    snr = SNR()
    badania = snr.dict_select("select * from badania where symbol=%s and not del", [params['symbol']])
    if len(badania) > 0:
        params['badanie_nazwa'] = badania[0]['nazwa']
    else:
        raise ValidationError("Nie znaleziono badania o podanym symbolu")
    if params['grupa'] != '':
        grupy = snr.dict_select(
            "select * from pozycjekatalogow where katalog='GRUPYPLATNIKOW' and symbol=%s and not del",
            [params['grupa']])
        if len(grupy) > 0:
            params['grupa'] = grupy[0]['symbol']
            params['grupa_nazwa'] = grupy[0]['nazwa']
        else:
            raise ValidationError("Nie znaleziono grupy płatników o podanym symbolu")
    else:
        params['grupa'] = None
    lab_task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_lab',
    }
    report.create_task(lab_task)
    report.save()
    return report


def raport_lab(task_params):
    lab = task_params['target']
    params = task_params['params']
    sql_centrum = """
        select w.id as ID, w.sysid as SYSID, z.numer as numer,  z.datarejestracji as data, p.symbol as platnik
        from Wykonania W
            left outer join Badania B on B.Id = W.Badanie 
            left outer join zlecenia z on z.id=w.zlecenie
            left outer join GrupyBadan gb on gb.id=b.grupa
            left outer join Platnicy P on P.Id = W.Platnik
            left outer join GrupyPlatnikow GP on GP.Id = P.Grupa
        where 
            W.Rozliczone = ? and W.Anulowane is null and W.Platne = 1 and B.Pakiet = 0 
            and (gb.symbol not in ('TECHNIC') or b.grupa is null) and b.symbol = ?
        order by z.datarejestracji, z.numer, B.SYMBOL
    """
    sql_centrum_params = [params['data']]
    if params['grupa'] is not None:
        sql_centrum = sql_centrum.replace('B.Pakiet = 0', 'B.Pakiet = 0 and gp.symbol=?')
        sql_centrum_params.append(params['grupa'])
    sql_centrum_params.append(params['symbol'])

    sql_snr = """
        select substring(w.wykonanie,1,position('^' in w.wykonanie)-1) as ID, (w.hs->'numer') as numer, 
            w.datarejestracji as data, pwl.symbol as platnik
        from Wykonania W
            left outer join Platnicy P on W.platnik = P.ID	
            left outer join Platnicywlaboratoriach Pwl on PWL.laboratorium = w.laboratorium and PWL.platnik = P.ID and not pwl.del
            left outer join pozycjekatalogow pk on pk.symbol=w.badanie and pk.katalog = 'BADANIA'
        where 
            w.datarozliczeniowa = %s and W.bezPlatne = 'f' and w.jestpakietem = 'f' and w.laboratorium = %s 
            and w.badanie = %s 
            and (pk.hs->'grupa') is distinct from 'TECHNIC'
    """
    sql_snr_params = [params['data'], lab, params['symbol']]
    if params['grupa'] is not None:
        sql_snr = sql_snr.replace('w.badanie = %s', 'w.badanie = %s and pwl.hs->\'grupa\' = %s')
        sql_snr_params.append(params['grupa'])

    dane_centrum = {}
    dane_snr = {}
    dane_razem = {}

    with get_centrum_connection(lab[:7]) as conn:
        for row in conn.raport_slownikowy(sql_centrum, sql_centrum_params):
            id = int(row['sysid'] or row['id'])
            dane_centrum[id] = {
                'Nr': row['numer'],
                'D': row['data'],
                'P': row['platnik'],
                'id': row['id'],
                'sysid': row['sysid'],
                'nad': 'Nadmiar Zdalna',
            }
            dane_razem[id] = dane_centrum[id]
    snr = SNR()
    for row in snr.dict_select(sql_snr, sql_snr_params):
        id = int(row['id'])
        dane_snr[id] = {
            'Nr': row['numer'],
            'D': row['data'],
            'P': row['platnik'],
            'id': row['id'],
            'sysid': row['id'],
            'nad': 'Nadmiar Bieżąca'
        }
        if id in dane_razem:
            del dane_razem[id]
        else:
            dane_razem[id] = dane_snr[id]
    title = "Niezgodność replikacji %s, rozliczone %s, badanie %s"
    title %= (lab, params['data'], params['symbol'])
    if params['grupa'] is not None:
        title += ", grup płatników %s" % params['grupa']
    header = 'ID,SYSID,Numer,Data,Płatnik,Pochodzenie'.split(',')
    data = []
    for id, row in dane_razem.items():
        data.append([
            row['id'], row['sysid'], row['Nr'], row['D'], row['P'], row['nad']
        ])
    return {
        'type': 'table',
        'title': title,
        'header': header,
        'data': prepare_for_json(data)
    }

