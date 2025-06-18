from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError, Switch, NumberInput
from helpers.validators import validate_symbol
from tasks import TaskGroup, Task
from helpers import prepare_for_json, generate_barcode_img_tag, get_centrum_connection, empty
from datasources.ick import IckDatasource
from datasources.vouchery import VouchersDatasource
import random
import string

MENU_ENTRY = 'Wykorzystanie voucherów'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    TabbedView(field='tab', desc_title='Typ raportu', children=[
        Tab(title='Kody jednorazowe', value='jednorazowe', panel=VBox(
            InfoText(text='''
    Raport z ilości istniejących i wykorzystanych prezleceń jednorazowych, z podziałem na punkty pobrań, w których je wykorzystano.
    Podaj symbol zleceniodawcy (bez prefiksu, tak jak w aplikacji vouchery / przy rejestrowaniu prezlecenia).
    W przypadku wydruków informacji dla pacjenta i vouczerów gotówkowych nie wskazujących na zleceniodawcę - podaj zleceniodawcę INFO.
    Raport wg dat utworzenia voucherów'''),
            TextInput(field="jzleceniodawca", title="Zleceniodawca"),
            DateInput(field='jdataod', title='Data początkowa', default='PZM'),
            DateInput(field='jdatado', title='Data końcowa', default='T'),
            Switch(field='tylkoapp', title='Tylko wygenerowane z aplikacji vouchery'),
            Switch(field='kodywyk', title='Pokaż kody wykorzystane'),
        )),
        Tab(title='Kody wielokrotnego użytku', value='wielokrotne', panel=VBox(
            InfoText(text='''
    Raport z ilości istniejących i wykorzystanych prezleceń jednorazowych, z podziałem na punkty pobrań, w których je wykorzystano.
    Podaj symbol zleceniodawcy (bez prefiksu, tak jak w aplikacji vouchery / przy rejestrowaniu prezlecenia) lub kod vouchera.
    W przypadku wydruków informacji dla pacjenta i vouczerów gotówkowych nie wskazujących na zleceniodawcę - podaj zleceniodawcę INFO.
    Raport wg dat rejestracji.'''),
            TextInput(field="wzleceniodawca", title="Zleceniodawca"),
            TextInput(field="wkod", title="Kod vouchera"),
            DateInput(field='wdataod', title='Data początkowa', default='PZM'),
            DateInput(field='wdatado', title='Data końcowa', default='T'),
        )),
        Tab(title='Sprawdź pojedynczy kod', value='pojedynczy', panel=VBox(
            InfoText(text='''Podaj kod vouchera / prezlecenia aby dowiedzieć się o nim wszystkiego'''),
            TextInput(field="kod", title="Kod"),
        )),

        Tab(title='Sprawdź pojedynczczą generacje', value='generacja', panel=VBox(
            InfoText(text='''Podaj id generacji aby dowiedzieć się o niej wszystkiego'''),
            NumberInput(field="generation_id", title="ID generacji"),
        )),
    ])
))

# TODO: zwracać id, dorobić id do raportu przebieg pracy
# [1:13 PM] Jekatierina Yashyna
# Czy udałoby się jeszcze dodać w reporterze w zakładce "Wykorzystanie voucherów" kod kreskowy do danego vouchera? W przypadku gdy voucher zostanie wykorzystany, dobrze byłoby mieć od razu podgląd do kodu kreskowego, to nam znacznie ułatwi pracę
# [1:39 PM] Adam Morawski
# w prosty sposób nie, bo w bazie prezleceń nie ma tego kodu. Są namiary na zlecenie w konkretnej bazie, gdyby tam był identyfikator który starczyłoby przekleić do raportu przebieg pracy to by było ok?
# TODO Michał Kuffel: w raporcie z wykorzystania do dodania możliwość wklejenia wielu kodów do sprawdzniea naraz i filtrowania tylko po wybranym zakresie dat rejestracji
# TODO na później info o wykonaniu badań


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['tab'] == 'jednorazowe':
        validate_symbol(params['jzleceniodawca'])
        task = {
            'type': 'ick',
            'priority': 1,
            'params': params,
            'function': 'raport_jednorazowe',
        }
        report.create_task(task)
    elif params['tab'] == 'wielokrotne':
        for fld in ('wzleceniodawca', 'wkod'):
            if not empty(params[fld]):
                if fld == 'wzleceniodawca':
                    validate_symbol(params[fld])
            else:
                params[fld] = None
        if empty(params['wzleceniodawca']) and empty(params['wkod']):
            raise ValidationError("Podaj symbol zleceniodawcy lub kod vouchera")
        task = {
            'type': 'ick',
            'priority': 1,
            'params': params,
            'function': 'raport_wielokrotne',
        }
        report.create_task(task)
    elif params['tab'] == 'pojedynczy':
        task = {
            'type': 'ick',
            'priority': 1,
            'params': params,
            'function': 'raport_pojedynczy',
        }
        report.create_task(task)

    elif params['tab'] == 'generacja':
        task = {
            'type': 'ick',
            'priority': 1,
            'params': params,
            'function': 'raport_generacja',
        }
        report.create_task(task)
    report.save()
    return report


def raport_jednorazowe(task_params):
    params = task_params['params']
    ick = IckDatasource()
    sql = """
        select badania, status_pacjenta as "status pacjenta", 
            case when platne then 'płatne' else 'bezpłatne / na płatnika' end as "czy płatne?", 
            ic_system as "lab wykorzystania", ic_kanal as "pp wykorzystania", ic_kanal_nazwa as "pp nazwa",
            sum(case when ts_rej is not null then 1 else 0 end) as "ilość wykorzystanych",
            sum(case when ts_rej is null and not wycofane then 1 else 0 end) as "ilość dostępnych",
            sum(case when ts_rej is null and wycofane then 1 else 0 end) as "ilość wycofanych"
        from zlecenia
        where zleceniodawca=%s and ts_utw between %s and %s and not coalesce(wielokrotne, false)
    """
    if params['tylkoapp']:
        sql += " and podprojekt='VOUCHERS-APP'"
    sql += "group by 1,2,3,4,5,6"
    if params['kodywyk']:
        sql = sql.replace('sum(case when ts_rej is not null then 1 else 0 end) as "ilość wykorzystanych"',
                          '''sum(case when ts_rej is not null then 1 else 0 end) as "ilość wykorzystanych",
                          array_to_string(array_agg(case when ts_rej is not null then kod_zlecenia else null end), ', ') as "kody wykorzystane"''')
    sql_params = [params['jzleceniodawca'], params['jdataod'], params['jdatado'] + ' 23:59:59']
    cols, rows = ick.select(sql, sql_params)
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows),
    }


def raport_wielokrotne(task_params):
    params = task_params['params']
    ick = IckDatasource()
    sql = """
        select z.zleceniodawca, z.kod_zlecenia as "Kod", z.badania, z.status_pacjenta as "status pacjenta", 
            case when z.platne then 'płatne' else 'bezpłatne / na płatnika' end as "czy płatne?", 
            case when z.wycofane then 'T' else '' end as "czy wycofane?",
            zr.ic_system as "lab wykorzystania", zr.ic_kanal as "pp wykorzystania", zr.ic_kanal_nazwa as "pp nazwa",
            (extract(year from zr.ts_rej))::varchar || '-'|| (extract(month from zr.ts_rej))::varchar as "miesiąc rejestracji",
            count(zr.id) as "ilość wykorzystanych"
        from zlecenia z
        left join zlecenia_rejestracja zr on zr.zlec_id=z.id
        where $WHERE$ and zr.ts_rej between %s and %s and coalesce(z.wielokrotne, false)
        group by 1,2,3,4,5,6,7,8,9,10
    """
    where = []
    sql_params = []
    if not empty(params['wzleceniodawca']):
        where.append('z.zleceniodawca=%s')
        sql_params.append(params['wzleceniodawca'])
    if not empty(params['wkod']):
        where.append('z.kod_zlecenia=%s')
        sql_params.append(params['wkod'])
    sql_params += [params['wdataod'], params['wdatado'] + ' 23:59:59']
    sql = sql.replace('$WHERE$', ' and '.join(where))
    cols, rows = ick.select(sql, sql_params)
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows),
    }

def raport_pojedynczy(task_params):
    params = task_params['params']
    ick = IckDatasource()
    sql = """
        select z.zleceniodawca, z.pacjent, z.kod_probki, z.uwagi, z.badania, z.status_pacjenta, z.ts_utw as utworzone,
            z.data_waznosci,
        (
            case when z.platne then 'płatne, ' else 'bezpłatne / na płatnika, ' end ||
            case when z.wycofane then 'wycofane, ' else '' end ||
            case when coalesce(z.bez_upiela, false) then 'bez UPIELa, ' else '' end
        ) as opis,
        (
            case when z.wielokrotne then (
                select array_to_string(array_agg(a), '; ') from (select trim(ic_system) || ':' || trim(ic_kanal) || 'x' || cast(count(zr.id) as varchar) as a from zlecenia_rejestracja zr where zr.zlec_id=z.id group by zr.ic_system, zr.ic_kanal) a
            )
            else 
                case when z.ts_rej is not null then 
                    z.ic_system || ' ' || z.ic_kanal || ' - ' || cast(z.ts_rej as varchar)
                else '' end
            end 
        ) as zarejestrowane
        from zlecenia z
        where z.kod_zlecenia=%s 
    """
    cols, rows = ick.select(sql, [params['kod']])
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows),
    }



def raport_generacja(task_params):
    params = task_params['params']
    generation_id = params['generation_id']
    ick = IckDatasource()
    v = VouchersDatasource()
    vouchery = v.get_vouchers_by_generation(generation_id)
    kody = tuple(v['barcode'] for v in vouchery)
    sql = """
        select z.zleceniodawca, z.pacjent, z.kod_probki, z.uwagi, z.badania, z.status_pacjenta, z.ts_utw as utworzone,
            z.data_waznosci,
        (
            case when z.platne then 'płatne, ' else 'bezpłatne / na płatnika, ' end ||
            case when z.wycofane then 'wycofane, ' else '' end ||
            case when coalesce(z.bez_upiela, false) then 'bez UPIELa, ' else '' end
        ) as opis,
        (
            case when z.wielokrotne then (
                select array_to_string(array_agg(a), '; ') from (select trim(ic_system) || ':' || trim(ic_kanal) || 'x' || cast(count(zr.id) as varchar) as a from zlecenia_rejestracja zr where zr.zlec_id=z.id group by zr.ic_system, zr.ic_kanal) a
            )
            else 
                case when z.ts_rej is not null then 
                    z.ic_system || ' ' || z.ic_kanal || ' - ' || cast(z.ts_rej as varchar)
                else '' end
            end 
        ) as zarejestrowane
        from zlecenia z
        where z.kod_zlecenia in %s
    """
    cols, rows = ick.select(sql, (kody,))
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows),
    }


