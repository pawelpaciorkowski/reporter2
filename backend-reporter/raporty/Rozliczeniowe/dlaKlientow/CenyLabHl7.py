from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range, validate_symbol
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_snr_connection, empty
from datasources.snr import SNR
from datasources.reporter import ReporterDatasource
from api.common import get_db
from decimal import Decimal

MENU_ENTRY = 'Ceny lab + HL7'

SQL = """
    select 
        zl.datarejestracji as "data", zl.numer, pac.nazwisko, pac.imiona, pac.pesel, pac.dataurodzenia as "data ur.",
        o.symbol || ': ' || o.nazwa as zleceniodawca, list(trim(bad.symbol)) as badania, sum(w.cena) as wartosc,
        list(distinct zz.NUMER) as hl7
    from wykonania w
    left join zlecenia zl on zl.id=w.zlecenie
    left join oddzialy o on o.id=zl.ODDZIAL
    left join pacjenci pac on pac.id=zl.pacjent
    left join badania bad on bad.id=w.badanie
    left join ZLECENIAZEWNETRZNE zz on zz.zlecenie=zl.id
    where w.platnik=(select id from platnicy where symbol=?)
    and w.rozliczone between ? and ?
    and w.PLATNE=1 and w.ANULOWANE is null and w.platnik is not null
    group by 1, 2, 3, 4, 5, 6, 7
    order by 1, 2
"""

SQL_BADANIA = """
    select 
        zl.datarejestracji as "data", zl.numer, pac.nazwisko, pac.imiona, pac.pesel, pac.dataurodzenia as "data ur.",
        o.symbol || ': ' || o.nazwa as zleceniodawca, trim(bad.symbol) || ' - ' || bad.nazwa as badanie, w.cena,
        list(distinct zz.NUMER) as hl7
    from wykonania w
    left join zlecenia zl on zl.id=w.zlecenie
    left join oddzialy o on o.id=zl.ODDZIAL
    left join pacjenci pac on pac.id=zl.pacjent
    left join badania bad on bad.id=w.badanie
    left join ZLECENIAZEWNETRZNE zz on zz.zlecenie=zl.id
    where w.platnik=(select id from platnicy where symbol=?)
    and w.rozliczone between ? and ?
    and w.PLATNE=1 and w.ANULOWANE is null
    group by 1,2,3,4,5,6,7,8,9
    order by 1, 2, 8
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport dla klientów rozliczanych przez Centrum, a nie SNR (np z BCAM).\n'
             'Raport może być albo na płatnika wg dat rozliczeniowych (jeśli zostanie podany symbol płatnika)'
             'lub dla faktury w Centrum (jeśli zostanie podany numer faktury, wtedy zakres dat nie ma znaczenia).'),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    TextInput(field='platnik', title='Płatnik (symbol)'),
    TextInput(field='faktura', title='lub nr faktury'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
    Switch(field='badania', title='Podział na badania')
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    if empty(params['platnik']):
        if empty(params['faktura']):
            raise ValidationError("Nie podano ani symbolu płatnika ani numeru faktury")
        params['tryb'] = 'faktura'
    else:
        validate_symbol(params['platnik'])
        validate_date_range(params['dataod'], params['datado'], 31)
        params['tryb'] = 'platnik'
        if not empty(params['faktura']):
            raise ValidationError("Podaj albo symbol płatnika albo numer faktury")
    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_lab',
    }
    report.create_task(task)
    report.save()
    return report


def raport_lab(task_params):
    lab = task_params['target']
    params = task_params['params']
    with get_centrum_connection(lab, fresh=True) as conn:
        sql = SQL_BADANIA if params['badania'] else SQL
        res = []
        if params['tryb'] == 'platnik':
            sql_params = [params['platnik'], params['dataod'], params['datado']]
        elif params['tryb'] == 'faktura':
            cols, rows = conn.raport_z_kolumnami("select id, datawystawienia, nabywca from faktury where numer=?", [params['faktura']])
            if len(rows) == 0:
                return { 'type': 'error', 'text': 'Nie znaleziono faktury o podanym numerze' }
            row = rows[0]
            res.append({'type': 'info', 'text': 'Faktura nr %s wystawiona %s dla %s' % (params['faktura'], row[1], row[2])})
            sql = sql.replace('w.platnik=(select id from platnicy where symbol=?)', 'w.faktura=?')
            sql = sql.replace('and w.rozliczone between ? and ?', '')
            sql_params = [row[0]]
        else:
            raise ValueError(params['tryb'])

        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
        res.append({
            'type': 'table',
            'header': cols,
            'data': prepare_for_json(rows)
        })
    return res
