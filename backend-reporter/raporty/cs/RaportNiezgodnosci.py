import copy

from datasources.snrkonf import SNRKonf
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError, Switch
from datasources.nocka import NockaDatasource, nocka_sprawdz_kompletnosc  # noqa # pylint: disable=unused-import
from helpers import prepare_for_json, Kalendarz, empty, list_from_space_separated, get_centrum_connection
from helpers.helpers import remove_first_cols, group_by_first_cols
from helpers.validators import validate_date_range, validate_symbol
from tasks import TaskGroup, Task

MENU_ENTRY = 'Raport niezgodności'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="""Raport niezgodności, podobny do wysyłanych do klientów na mail. Rozszerzone możliwości wyboru warunków filtrowania i źródła danych.
        Wybór zakresu dat dotyczy wyników krytycznych i badań zabłędowanych (wg dat zatwierdzenia). NIE DOTYCZY niedostarczonych materiałów - w tym przypadku brany jest pod uwagę warunek bieżący/następny dzień.
        Zagrożony termin wykonania wyliczany jest zawsze na bieżący moment, wg czasów we wskazanej bazie (a nie np w innej bazie z której przyszły zlecenia).
        Wybranie "Zleceniodawcy płatnika" pozwala wyciągać raporty po zleceniodawcach, co zadziała również dla badań wysyłkowych, mimo podania w filtrze płatnika. 
        Max 5 laboratoriów."""),
    DateInput(field='dataod', title='Data początkowa', default='-1D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria', pokaz_nieaktywne=True),
    TextInput(field='platnik_symbol', title='Płatnik (symbol)'),
    TextInput(field='platnik_nip', title='Płatnik (NIP)'),
    TextInput(field='zleceniodawcy', title='Zleceniodawcy (symbole)'),
    Switch(field='zleceniodawcy_platnika', title='Zleceniodawcy płatnika (wysyłki)'),
    Switch(field='sekcja_braki', title='sekcja: Braki materiałów', default=True),
    Switch(field='sekcja_braki_biezacy',
           title='\u00a0\u00a0 - braki materiałów - bieżący dzień rejestracji (a nie poprzedni)', default=False),
    Switch(field='sekcja_bledy', title='sekcja: Błędy wykonania', default=True),
    Switch(field='sekcja_krytyczne', title='sekcja: Wyniki krytyczne', default=False),
    Switch(field='sekcja_pat', title='sekcja: Patogeny alarmowe', default=False),
    Switch(field='sekcja_cyt', title='sekcja: Cytologia - BLOKADA', default=False),
    Switch(field='sekcja_wer', title='sekcja: Do weryfikacji', default=False),
    Switch(field='sekcja_nieter', title='sekcja: Nieterminowe', default=False),
    Switch(field='dane_pacjentow', title='Dołącz dane pacjentów (a nie tylko zleceń)'),
    Switch(field='info_no_problem', title='Informuj o braku problemów')
))

SQL_KOLUMNY_WSPOLNE = """
    select zl.id, zl.datarejestracji, zl.numer, zl.kodkreskowy, trim(o.symbol) || ' - ' || o.nazwa as zleceniodawca
"""

SQL_KOLUMNY_PACJENT = """
    , pac.nazwisko || ' ' || pac.imiona as pacjent, coalesce(cast(pac.PESEL as varchar(12)),'') as pesel
"""

SQL_KOLUMNY_BADANIA_FB = """
    , list(trim(bad.symbol)) as badania
"""

SQL_KOLUMNY_BADANIA_PG = """
    , array_to_string(array_agg(trim(bad.symbol)), ', ') as badania
"""

SQL_KOLUMNA_CZAS_MAX = """
    , min(Bad.CzasMaksymalny/24) as "czas max"
"""

SQL_TABLES = """
    from wykonania w
    left join zlecenia zl on zl.id=w.zlecenie 
    left join oddzialy o on o.id=zl.oddzial
    left join platnicy pl on pl.id=zl.platnik
    left join badania bad on bad.id=w.badanie
    left join pacjenci pac on pac.id=zl.pacjent
    left join bledywykonania bl on bl.id=w.bladwykonania
    left join grupybadan gb on gb.id=bad.grupa
"""

SQL_TABLES_WYNIKI = """
    left join wyniki wyn on wyn.wykonanie=w.id
    left join parametry par on par.id=wyn.parametr
    left join normy nor on nor.id=wyn.norma
"""

WARUNEK_PLATNICY = """where pl.symbol in ($SYMBOLE$)"""

WARUNEK_ODDZIALY = """where o.symbol in ($SYMBOLE$)"""

WARUNEK_ZATWIERDZENIE = """
    and w.zatwierdzone between ? and ?
"""

WARUNEK_BRAKI = """
    and w.datarejestracji='YESTERDAY' and (zl.godzinarejestracji < 'TODAY' or zl.godzinarejestracji is null) and w.dystrybucja is null
"""

WARUNEK_BRAKI_BIEZACY_DZIEN = """
    and w.datarejestracji='TODAY' and zl.numer is not null and w.dystrybucja is null
"""

WARUNEK_BLEDY = """
    and w.bladwykonania is not null and bl.symbol <> 'ZLEC'
"""

WARUNEK_WSPOLNE = """
    and bad.pakiet=0 and w.anulowane is null and gb.symbol <> 'TECHNIC'
"""

WARUNEK_NIETERMINOWE_FB = """
    and (GB.Symbol not in ('HISTOPA', 'HIS-ALA') or GB.Symbol is null)
    and AddMinute(W.Dystrybucja, Bad.CzasMaksymalny*0.8*60) <= current_timestamp
    and (Bad.Symbol not in ('TBC-AU', 'TBC-PBK', 'TBC-ANS', 'TBC-ANT', 'TBC-GEN', 'TBC-ID', 'TBC-IDA', 'TBC-IDN', 'TBC-PR') or AddMinute(W.Dystrybucja, Bad.CzasMaksymalny*0.95*60) <= current_timestamp)
    and w.zatwierdzone is null 
"""

WARUNEK_NIETERMINOWE_PG = """
    and (GB.Symbol not in ('HISTOPA', 'HIS-ALA') or GB.Symbol is null)
    and W.Dystrybucja + Bad.CzasMaksymalny*0.8*60 * interval '1 minute' <= current_timestamp
    and (Bad.Symbol not in ('TBC-AU', 'TBC-PBK', 'TBC-ANS', 'TBC-ANT', 'TBC-GEN', 'TBC-ID', 'TBC-IDA', 'TBC-IDN', 'TBC-PR') or W.Dystrybucja + Bad.CzasMaksymalny*0.95*60 * interval '1 minute' <= current_timestamp)
    and w.zatwierdzone is null
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    if len(params['laboratoria']) > 5:
        raise ValidationError("Max 5 laboratoriów !!!")
    if params['sekcja_krytyczne']:
        raise ValidationError("Krytyczne niezaimplementowane!")
    if params['sekcja_pat']:
        raise ValidationError("Patogeny alarmowe niezaimplementowane!")
    if params['sekcja_cyt']:
        raise ValidationError("Cytologia BLOKADA niezaimplementowane!")
    if params['sekcja_wer']:
        raise ValidationError("Wyniki do weryfikacji niezaimplementowane!")
    validate_date_range(params['dataod'], params['datado'], 7)
    if not empty(params['platnik_symbol']):
        validate_symbol(params['platnik_symbol'])
        if not empty(params['platnik_nip']):
            raise ValidationError("Podaj albo symbol albo NIP płatnika")

    snr = SNRKonf()
    platnicy = None
    platnicy_w_laboratoriach = None
    if not empty(params['platnik_symbol']):
        rows = snr.dict_select("select platnik from platnicywlaboratoriach where symbol=%s and not del",
                               [params['platnik_symbol']])
        if len(rows) == 0:
            raise ValidationError("Nie znaleziono płatnika")
        else:
            platnicy = [rows[0]['platnik']]
    if not empty(params['platnik_nip']):
        rows = snr.dict_select("select id from platnicy where nip=%s and not del")
        if len(rows) == 0:
            raise ValidationError("Nie znaleziono płatnika")
        else:
            platnicy = [row['id'] for row in rows]
            if len(platnicy) > 20:
                raise ValidationError("Znaleziono ponad 20 pasujących płatników")
    params['zleceniodawcy'] = list_from_space_separated(params['zleceniodawcy'], upper=True, also_comma=True,
                                                        also_semicolon=True, unique=True)
    if len(params['zleceniodawcy']) > 0:
        if params['zleceniodawcy_platnika']:
            raise ValidationError("Bez sensu.")
        if platnicy is not None:
            raise ValidationError("Albo płatnik albo symbole zleceniodawców")
        if len(params['zleceniodawcy']) > 20:
            raise ValidationError("Max 20 zleceniodawców")
        for zlec in params['zleceniodawcy']:
            validate_symbol(zlec)
        params['_oddzialy'] = params['zleceniodawcy']
    elif params['zleceniodawcy_platnika']:
        params['_oddzialy'] = [row['symbol'] for row in snr.dict_select("""
            select zwl.symbol from platnicy pl
            left join zleceniodawcy zl on zl.platnik=pl.id and not zl.del
            left join zleceniodawcywlaboratoriach zwl on zwl.zleceniodawca=zl.id and not zwl.del
            where pl.id in %s
        """, [tuple(platnicy)])]
        for sym in params['_oddzialy']:
            validate_symbol(sym)
    elif platnicy is not None:
        params['_oddzialy'] = None
        platnicy_w_laboratoriach = {}
        for row in snr.dict_select("""
            select pwl.laboratorium, pwl.symbol
            from platnicywlaboratoriach pwl 
            where pwl.platnik in %s and not pwl.del
        """, [tuple(platnicy)]):
            lab = row['laboratorium'][:7]
            if lab not in platnicy_w_laboratoriach:
                platnicy_w_laboratoriach[lab] = []
            validate_symbol(row['symbol'])
            platnicy_w_laboratoriach[lab].append(row['symbol'])
    else:
        raise ValidationError("Brak warunku na płatnika / zleceniodawcę.")

    for lab in params['laboratoria']:
        task_params = copy.deepcopy(params)
        if platnicy_w_laboratoriach is not None:
            if lab not in platnicy_w_laboratoriach:
                raise ValidationError("Brak symboli płatników w labie %s" % lab)
            task_params['_platnicy'] = platnicy_w_laboratoriach[lab]
        else:
            task_params['_platnicy'] = None
        if params['sekcja_braki'] or params['sekcja_bledy']:
            task = {
                "type": "centrum",
                "priority": 1,
                "target": lab,
                "params": task_params,
                "function": "raport_braki_bledy",
            }
            report.create_task(task)
        if params['sekcja_nieter']:
            task = {
                "type": "centrum",
                "priority": 1,
                "target": lab,
                "params": task_params,
                "function": "raport_nieterminowe",
            }
            report.create_task(task)
    if len(report.tasks) == 0:
        raise ValidationError("Nic do zrobienia.")
    report.save()
    return report

def warunek_podmiotow(params):
    if params['_platnicy'] is not None:
        return WARUNEK_PLATNICY.replace('$SYMBOLE$', ','.join(["'%s'" % sym for sym in params['_platnicy']]))
    elif params['_oddzialy'] is not None:
        return WARUNEK_ODDZIALY.replace('$SYMBOLE$', ','.join(["'%s'" % sym for sym in params['_oddzialy']]))
    else:
        raise RuntimeError("Brak warunku", params)


def raport_braki_bledy(task_params):
    params = task_params['params']
    lab = task_params['target']
    res = []
    sql_common = SQL_KOLUMNY_WSPOLNE
    ile_kol = 5
    if params['dane_pacjentow']:
        sql_common += SQL_KOLUMNY_PACJENT
        ile_kol += 2
    sql_common += SQL_KOLUMNY_BADANIA_FB
    sql_common += SQL_TABLES
    sql_common += warunek_podmiotow(params)
    sql_common += ' $WHERE$ ' + WARUNEK_WSPOLNE
    sql_common += group_by_first_cols(ile_kol)
    with get_centrum_connection(lab, fresh=True) as conn:
        if params['sekcja_braki']:
            if params['sekcja_braki_biezacy']:
                sql = sql_common.replace('$WHERE$', WARUNEK_BRAKI_BIEZACY_DZIEN)
            else:
                sql = sql_common.replace('$WHERE$', WARUNEK_BRAKI)
            sql_pg = sql.replace(SQL_KOLUMNY_BADANIA_FB, SQL_KOLUMNY_BADANIA_PG)
            cols, rows = conn.raport_z_kolumnami(sql, sql_pg=sql_pg)
            if len(rows) > 0:
                res.append({
                    'type': 'table',
                    'title': '%s - brak materiału' % lab,
                    'header': cols,
                    'data': prepare_for_json(rows)
                })
            elif params['info_no_problem']:
                res.append({'type': 'info', 'text': '%s - Brak nieprzyjętych materiałów' % lab})
        if params['sekcja_bledy']:
            sql = sql_common.replace('$WHERE$', WARUNEK_ZATWIERDZENIE + WARUNEK_BLEDY)
            sql = sql.replace('from wykonania w', ', trim(bl.symbol) || \' - \' || bl.nazwa as "błąd"\nfrom wykonania w')
            sql += ',%d' % (ile_kol + 2)
            sql_params = [params['dataod'], params['datado']]
            sql_pg = sql.replace(SQL_KOLUMNY_BADANIA_FB, SQL_KOLUMNY_BADANIA_PG).replace('?', '%s')
            cols, rows = conn.raport_z_kolumnami(sql, sql_params, sql_pg=sql_pg)
            if len(rows) > 0:
                res.append({
                    'type': 'table',
                    'title': '%s - błędy wykonania' % lab,
                    'header': cols,
                    'data': prepare_for_json(rows)
                })
            elif params['info_no_problem']:
                res.append({'type': 'info', 'text': '%s - Brak błędów wykonania' % lab})
    return res


def raport_nieterminowe(task_params):
    params = task_params['params']
    lab = task_params['target']
    res = []
    sql = SQL_KOLUMNY_WSPOLNE
    ile_kol = 5
    sql_params = []
    if params['dane_pacjentow']:
        sql += SQL_KOLUMNY_PACJENT
        ile_kol += 2
    sql += SQL_KOLUMNY_BADANIA_FB + SQL_KOLUMNA_CZAS_MAX
    sql += SQL_TABLES
    sql += warunek_podmiotow(params)
    sql += WARUNEK_NIETERMINOWE_FB
    sql += WARUNEK_WSPOLNE
    sql += group_by_first_cols(ile_kol)
    print(sql)
    print(sql_params)
    sql_pg = sql.replace(SQL_KOLUMNY_BADANIA_FB, SQL_KOLUMNY_BADANIA_PG).replace(WARUNEK_NIETERMINOWE_FB, WARUNEK_NIETERMINOWE_PG)
    with get_centrum_connection(lab) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_params, sql_pg=sql_pg)
    cols, rows = remove_first_cols(cols, rows, 1)
    if len(rows) > 0:
        res.append({
            'type': 'table',
            'title': '%s - zagrożony termin wykonania' % lab,
            'header': cols,
            'data': prepare_for_json(rows)
        })
    elif params['info_no_problem']:
        res.append({'type': 'info', 'text': '%s - Brak badań z zagrożonym terminem wykonania' % lab})

    return res


def raport_wyniki(task_params):
    pass
