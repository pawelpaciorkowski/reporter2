from datasources.snrkonf import SNRKonf
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty

MENU_ENTRY = 'Zleceniodawcy w labie'

ADD_TO_ROLE = ['L-REJ', 'R-PM', 'L-PRAC']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport z konfiguracji w SNR. Wybierz pojedynczy lab lub użyj dodatkowego filtru.'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria', symbole_snr=True),
    TextInput(field='nip', title='NIP Płatnika'),
    TextInput(field='umowa', title='Umowa (nr K)'),
))

SQL = """
    select	
        zwl.laboratorium as "Laboratorium",
        pwl.symbol as "Płatnik",
        pl.nazwa as "Płatnik nazwa",
        pl.nip as "NIP",
        pl.hs->'umowa' as "Umowa",
        case when pl.aktywny then 'T' else '' end as "Pł Aktywny",
        case when pl.hs->'bezrejestracji'='True' then 'T' else '' end as "Pł Bez rejestracji",
        case when pl.gotowy then 'T' else '' end as "Pł Gotowy",
        case when pl.hs->'douzupelnienia'='True' then 'T' else '' end as "Pł Do uzupełnienia",
        zwl.symbol as "Zleceniodawca",
        zl.nazwa as "Zleceniodawca nazwa",
        zl.hs->'stawkavat' as "Zleceniodawca VAT",
        case when zl.hs->'bezrejestracji'='True' then 'T' else '' end as "Zl bez rejestracji",
        zl.hs->'identzestgot' as "Ident zest. gotówka"
    from zleceniodawcywlaboratoriach zwl
        left join zleceniodawcy zl on zl.id=zwl.zleceniodawca
        left join platnicy pl on pl.id=zl.platnik
        left join platnicywlaboratoriach pwl on pwl.platnik=pl.id and pwl.laboratorium=zwl.laboratorium
    where $WHERE$ and not zwl.del and not zl.del and not pl.del and not pwl.del
    order by pwl.symbol, zwl.symbol
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError('Nie wybrano laboratorium')
    if len(params['laboratoria']) > 1 and empty(params['nip']) and empty(params['umowa']):
        raise ValidationError('Bez filtrowania płatników można wybrać tylko jeden lab.')
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport',
    }
    report.create_task(task)
    report.save()
    return report


def raport(task_params):
    params = task_params['params']
    snr = SNRKonf()
    where = ['zwl.laboratorium in %s']
    sql_params = [tuple(params['laboratoria'])]
    if not empty(params['nip']):
        where.append('pl.nip=%s')
        sql_params.append(params['nip'])
    if not empty(params['umowa']):
        where.append("pl.hs->'umowa'=%s")
        sql_params.append(params['umowa'])
    sql = SQL.replace('$WHERE$', ' and '.join(where))
    cols, rows = snr.select(sql, sql_params)
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    }
