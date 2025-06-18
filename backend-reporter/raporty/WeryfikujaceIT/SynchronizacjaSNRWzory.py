from datasources.bic import BiCDatasource
from datasources.centrum import CentrumWzorcowa
from datasources.snr import SNR
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json, divide_chunks, empty
from helpers.validators import validate_date_range, validate_symbol
from datasources.snrkonf import SNRKonf
from datasources.helper import HelperDb
from tasks import TaskGroup, Task
import datetime
from helpers.connections import get_centra, get_db_engine

MENU_ENTRY = 'Synchr. SNR -> Wzory'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="Sprawdzenie stanu synchronizacji z SNR do bazy wzorcowej i do laboratorium"),
    Select(field="rodzaj", title="Rodzaj zapisu", values={
        'platnik': 'Płatnik', 'zleceniodawca': 'Zleceniodawca', 'pracownia': 'Pracownia', 'cena': 'Ceny badań'
    }),
    TextInput(field='symbol', title='Symbol'),
    Switch(field='sprawdz_lab', title='Sprawdź w laboratorium (a nie tylko we wzorach)'),
    LabSelector(field='lab', title='Laboratorium', multiselect=False),
))

def dane_snr(rodzaj, symbol, lab=None):
    res = {}
    snr = SNR()
    if lab == 'KOPERNI':
        lab = 'KOPERNIKA'
    if rodzaj == 'cena':
        res['ceny'] = snr.dict_select("""
            select c.symbol as cennik_snr, c.nazwa as cennik_nazwa, c.del as cennik_del, c.dc as cennik_dc,
                c.hs->'symbolwlaboratorium' as cennik_lab_symbol, cb.badanie, cb.del as cena_del, cb.dc as cena_dc,
                coalesce(cb.cenadlaplatnika, cb.cenadlapacjenta) as cena
            from cenniki c
            left join ceny cb on cb.cennik=c.symbol and cb.badanie=%s
            where c.laboratorium=%s and c.hs->'symbolwlaboratorium' is not null
        """, [symbol, lab])
        if len(res['ceny']) == 0:
            return None
        return prepare_for_json(res)
    if rodzaj == 'platnik':
        symbol_platnika = symbol
    elif rodzaj == 'zleceniodawca':
        for row in snr.dict_select("""
            select zwl.symbol, zl.id, zwl.laboratorium, zl.nazwa, pwl.symbol as platnik
            from zleceniodawcywlaboratoriach zwl
            left join zleceniodawcy zl on zl.id=zwl.zleceniodawca
            left join platnicy pl on pl.id=zl.platnik
            left join platnicywlaboratoriach pwl on pwl.platnik=pl.id and pwl.laboratorium=zwl.laboratorium and not pwl.del
            where zwl.symbol=%s and not zwl.del        
        """, [symbol]):
            res['zleceniodawca'] = row
        if 'zleceniodawca' not in res:
            return None
        symbol_platnika = res['zleceniodawca']['platnik']
    elif rodzaj == 'pracownia':
        symbol_platnika = None
        for row in snr.dict_select("""
            select symbol, nazwa, hs->'grupa' as grupa, hs->'system' as system, hs->'zewnetrzna' as zewnetrzna
            from pozycjekatalogow where katalog='PRACOWNIE' and symbol=%s
        """, [symbol]):
            res['pracownia'] = row
    else:
        raise ValidationError("Nie wiem")
    if symbol_platnika is not None:
        for row in snr.dict_select("""
            select pwl.symbol, pl.id, pwl.laboratorium, pl.nazwa, pwl.hs->'grupa' as grupa
            from platnicywlaboratoriach pwl 
            left join platnicy pl on pwl.platnik=pl.id 
            where pwl.symbol=%s and not pwl.del        
        """, [symbol_platnika]):
            res['platnik'] = row
        if 'platnik' not in res:
            return None
    return res

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if empty(params['symbol']):
        raise ValidationError("Podaj symbol")
    params['symbol'] = params['symbol'].upper().strip()
    validate_symbol(params['symbol'])
    if params['rodzaj'] == 'cena' and not params['sprawdz_lab']:
        raise ValidationError("Sprawdzenie synchronizacji cen - tylko dla pojedynczego labu. Zaznacz sprawdź w laboratorium i wybierz lab.")
    params['dane_snr'] = dane_snr(params['rodzaj'], params['symbol'], params['lab'])
    if params['dane_snr'] is None:
        raise ValidationError("Nie znaleziono %s %s w SNR" % (params['rodzaj'], params['symbol']))
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport_snr'
    }
    report.create_task(task)
    if params['rodzaj'] in ('platnik', 'zleceniodawca', 'pracownia'):
        task = {
            'type': 'snr',
            'priority': 0,
            'params': params,
            'function': 'raport_wzory'
        }
        report.create_task(task)
    if params['sprawdz_lab']:
        task = {
            'type': 'centrum',
            'priority': 1,
            'target': params['lab'],
            'params': params,
            'function': 'raport_lab'
        }
        report.create_task(task)
    if params['rodzaj'] == 'cena':
        task = {
            'type': 'ick',
            'priority': 1,
            'params': params,
            'function': 'raport_bic'
        }
        report.create_task(task)
    report.save()
    return report

"""
tabele:
"CenyBadan"
"Oddzialy"
"__CenyBadan"
"Platnicy"
"Pracownie"

"""

TABELE_SNR = {
    'platnik': 'Platnicy',
    'zleceniodawca': 'Oddzialy',
    'pracownia': 'Pracownie',
    'cena': '__CenyBadan',
}

def raport_snr(task_params):
    params = task_params['params']
    if params['lab'] == 'KOPERNI':
        params['lab'] = 'KOPERNIKA'
    snr = SNR()
    snrkonf = SNRKonf()
    res = []
    if params['rodzaj'] == 'cena':
        cols = 'cennik_snr cennik_nazwa cennik_del cennik_dc cennik_lab_symbol badanie cena_del cena_dc cena'.split(' ')
        res.append({
            'title': 'Aktualne ceny w SNR',
            'type': 'table',
            'header': cols,
            'data': [prepare_for_json([row[fld] for fld in cols]) for row in params['dane_snr']['ceny']],
        })
        cols, rows = snr.select("""
            select id, laboratorium, tabela, operacja, klucz, nakiedy, godzina, status, dane from synchronizacje where tabela=%s and klucz->'badanie'=%s
                and laboratorium=%s
            order by nakiedy
        """, [TABELE_SNR[params['rodzaj']], params['symbol'], params['lab']])
    else:
        cols, rows = snr.select("""
            select id, laboratorium, tabela, operacja, klucz, nakiedy, godzina, status, dane from synchronizacje where tabela=%s and klucz->'symbol'=%s
            order by nakiedy
        """, [TABELE_SNR[params['rodzaj']], params['symbol']])
    res.append({
        'title': 'Log synchronizacji w SNR',
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows),
    })
    for row in snr.dict_select("select godzina from synchronizacje where status='OK' order by nakiedy desc limit 1"):
        res.append({'type': 'info', 'text': 'Ostatnia udana synchronizacja czegokolwiek z SNR do wzorów: %s' % str(row['godzina'])})
    max_dc = datetime.datetime(2000, 1, 1, 0, 0, 0)
    for tab in ('platnicy', 'zleceniodawcy'):
        for row in snrkonf.dict_select("select max(dc) as max_dc from " + tab):
            max_dc = max(max_dc, row['max_dc'])
    res.append({'type': 'info',
                'text': 'Ostatnia modyfikacja dowolnego płatnika / zleceniodawcy w bazie SNRKonf: %s' % str(max_dc)})
    return res

def raport_wzory(task_params):
    params = task_params['params']
    res = []
    cnt = CentrumWzorcowa()
    if params['rodzaj'] == 'pracownia':
        sql = "select p.*, s.symbol as system_symbol from %s p left join systemy s on s.id=p.system where p.symbol=?" % TABELE_SNR[params['rodzaj']]
    else:
        sql = "select * from %s where symbol=?" % TABELE_SNR[params['rodzaj']]
    with cnt.connection() as conn:
        cols, rows = conn.raport_z_kolumnami(sql, [params['symbol']])
        if 'platnik' in params['dane_snr'] and params['dane_snr']['platnik']['grupa'] is not None:
            grupa = params['dane_snr']['platnik']['grupa']
            sql = "select * from grupyplatnikow where symbol=? and del=0"
            colsg, rowsg = conn.raport_z_kolumnami(sql, [grupa])
            if len(rowsg) == 0:
                res.append({
                    'type': 'error',
                    'text': 'Nie znaleziono grupy płatników %s w bazie wzorcowej' % (grupa)
                })
            else:
                res.append({
                    'type': 'info',
                    'text': 'Grupa płatników %s znaleziona w bazie wzorcowej' % grupa
                })
    if len(rows) > 0:
        res.append({
            'title': 'Zapisy w bazie wzorcowej',
            'type': 'table',
            'header': cols,
            'data': prepare_for_json(rows)
        })
    else:
        res.append({ 'type': 'warning', 'text': 'Nie znaleziono w bazie wzorcowej' })
    return res

def raport_lab(task_params):
    params = task_params['params']
    res = []
    lab = task_params['target']
    if params['rodzaj'] == 'cena':
        with get_centrum_connection(lab) as conn:
            cols, rows = conn.raport_z_kolumnami("""
                select c.symbol as cennik, cb.cena, cb.del, cb.dc, cb.dd
                from cenybadan cb
                left join badania b on b.id=cb.badanie
                left join cenniki c on c.id=cb.cennik
                where b.symbol=? 
            """, [params['symbol']])
            if len(rows) > 0:
                res.append({
                    'type': 'table',
                    'title': 'Ceny badania %s w bazie %s' % (params['symbol'], lab),
                    'header': cols,
                    'data': prepare_for_json(rows),
                })
            else:
                res.append({
                    'type': 'error',
                    'text': 'Nie znaleziono cen badania %s w bazie %s' % (params['symbol'], lab)
                })
        return res

    if params['rodzaj'] == 'pracownia':
        sql = "select p.*, s.symbol as system_symbol from %s p left join systemy s on s.id=p.system where p.symbol=?" % TABELE_SNR[params['rodzaj']]
    else:
        sql = "select * from %s where symbol=?" % TABELE_SNR[params['rodzaj']]
    with get_centrum_connection(lab) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, [params['symbol']])
        if 'platnik' in params['dane_snr'] and params['dane_snr']['platnik']['grupa'] is not None:
            grupa = params['dane_snr']['platnik']['grupa']
            sql = "select * from grupyplatnikow where symbol=? and del=0"
            colsg, rowsg = conn.raport_z_kolumnami(sql, [grupa])
            if len(rowsg) == 0:
                res.append({
                    'type': 'error',
                    'text': 'Nie znaleziono grupy płatników %s w bazie %s' % (grupa, lab)
                })
    if len(rows) > 0:
        res.append({
            'title': 'Zapisy w bazie %s' % lab,
            'type': 'table',
            'header': cols,
            'data': prepare_for_json(rows)
        })
    else:
        res.append({ 'type': 'warning', 'text': 'Nie znaleziono w bazie %s' % lab })
    return res

def raport_bic(task_params):
    params = task_params['params']
    sql = """
        select s.symbol, 
            case when s.is_bundle then 'T' else 'N' end as "pakiet", 
            case when s.is_marketing_bundle then 'T' else 'N' end as "pakiet marketingowy",
            array_to_string(array_agg(distinct comp.component || case when comp.material is not null then ':' || comp.material else '' end), ', ') as "składowe pakietu",
            pl.symbol as "cennik lab", pl.snr_symbol as "cennik snr", pl.snr_name as "cennik nazwa",
            sp.price as "cena w cenniku", sp.dc as "zmiana ceny w cenniku",
            sip.price as "cena wyliczona", 
            case when sip.available then 'T' else 'N' end as "dostępne w punkcie", 
            sip.unavailability_reason as "powód niedostępności",
            array_to_string(array_agg(distinct cp.symbol), ', ') as punkty
        from services s
        left join service_in_point sip on sip.service=s.symbol
        left join config_collection_points cp on sip.point=cp.symbol and cp.is_active
        left join service_price_lists pl on pl.id=cp.price_list_id
        left join service_prices sp on sp.price_list_id=pl.id and sp.service=s.symbol
        left join service_components comp on comp.bundle=s.symbol
        where s.symbol=%s and cp.lab_symbol=%s
        group by 1,2,3,5,6,7,8,9,10,11,12
    """
    bic = BiCDatasource()
    cols, rows = bic.select(sql, [params['symbol'], params['lab']])
    return {
        'type': 'table',
        'title': 'BiC',
        'header': cols,
        'data': prepare_for_json(rows),
    }