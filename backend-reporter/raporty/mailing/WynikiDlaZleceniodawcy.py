import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch
from helpers.validators import validate_date_range, validate_symbol, validate_phone_number
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none, list_from_space_separated, \
    empty, slugify, simple_password, send_sms, send_sms_flush_queue
from helpers.email import encrypt_and_send

MENU_ENTRY = 'Wyniki dla zleceniodawcy'

REQUIRE_ROLE = ['C-ADM']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Eksport wyników wybranych badań dla zleceniodawców - wg dat zatwierdzenia.
        Możliwa wysyłka mailem. Raport do podpięcia pod crona."""),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    TextInput(field='platnik', title='Płatnik (wszyscy zleceniodawcy płatnika trafią do raportu)'),
    TextInput(field='zleceniodawcy', title='Zleceniodawca (symbole oddzielone spacją)'),
    Switch(field='zleceniodawcy_oddzielnie', title='Zleceniodawcy w oddzielnych plikach'),
    TextInput(field='badania', title='Badania (symbole badanie:parametr oddzielone spacją)'),
    DateInput(field='dataod', title='Data początkowa', default='-1D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
    TextInput(field='emails', title='Emaile (oddzielone spacją)'),
    TextInput(field='password', title='Hasło do szyfrowania załącznika (jeśli stałe)'),
    TextInput(field='phones', title='Nry telefonów do wysłania wygenerowanego hasła (oddzielone spacją)'),
))

SQL = """
    select z.datarejestracji, z.KodKreskowy as "Kod Kreskowy", trim(pp.symbol) as "Zleceniodawca",
    pp.nazwa as "Zleceniodawca nazwa",
    (P.Nazwisko || ' ' || P.Imiona) as "Pacjent", p.DATAURODZENIA as "Data urodzenia", p.PESEL as "PESEL",
    trim(B.Symbol) as "Badanie",
    trim(pa.symbol) as "Parametr",
    WY.wyniktekstowy as "Wynik"
    from Wykonania W
    left join Zlecenia Z on Z.id = W.zlecenie
    left join Oddzialy PP on PP.id = Z.oddzial
    left join Platnicy PL on PL.id = W.Platnik
    left join wyniki WY on WY.wykonanie = W.id
    left join badania B on B.id = W.Badanie
    left join parametry PA on pa.id =wy.PARAMETR
    left join pacjenci P on P.id = Z.pacjent
    where
    w.zatwierdzone between ? and ? 
    and z.oddzial in (select id from oddzialy where symbol in ($ODDZIALY$))
    and B.symbol in ($BADANIA$)
    and z.PACJENT is not null and W.BladWykonania is null and W.anulowane is null and wy.WYNIKTEKSTOWY is not null and wy.ukryty = '0'
    order by z.datarejestracji
"""

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if not empty(params['platnik']) and not empty(params['zleceniodawcy']):
        raise ValidationError("Wybierz albo płatnika albo zleceniodawców")
    params['zleceniodawcy'] = list_from_space_separated(params['zleceniodawcy'], also_comma=True, also_semicolon=True, unique=True, upper=True)
    params['badania'] = list_from_space_separated(params['badania'], also_comma=True, also_semicolon=True, unique=True, upper=True)
    params['badania'] = [pos.split(':') for pos in params['badania']]
    params['phones'] = list_from_space_separated(params['phones'], also_comma=True, also_semicolon=True, unique=True)
    for pos in params['badania']:
        if len(pos) != 2:
            raise ValidationError('Nieprawidłowe badanie: %s' % ':'.join(pos))
        validate_symbol(pos[0])
        validate_symbol(pos[1])
    for zlec in params['zleceniodawcy']:
        validate_symbol(zlec)
    if not empty(params['platnik']):
        validate_symbol(params['platnik'])
    params['emails'] = list_from_space_separated(params['emails'], also_comma=True, also_semicolon=True, unique=True)
    for phone in params['phones']:
        validate_phone_number(phone, only_pl=True)
    if len(params['badania']) == 0:
        raise ValidationError("Nie podano żadnego badania")
    if len(params['badania']) > 20:
        raise ValidationError("Max 20 badań")
    if len(params['badania']) == 1 and len(params['zleceniodawcy']) == 1:
        validate_date_range(params['dataod'], params['datado'], 365)
    else:
        validate_date_range(params['dataod'], params['datado'], 7)
    if len(params['zleceniodawcy']) == 0 and empty(params['platnik']):
        raise ValidationError("Nie podano żadnego zleceniodawcy ani płatnika")
    if len(params['zleceniodawcy']) > 20:
        raise ValidationError("Max 20 zleceniodawców")
    if len(params['emails']) > 0:
        if empty(params['password']) and len(params['phones']) == 0:
            raise ValidationError("Raport wysyłany mailem musi być szyfrowany - potrzebne stałe hasło albo nr telefonu")
        if not empty(params['password']) and len(params['password']) < 8:
            raise ValidationError("Hasło co najmniej 8 znaków")
    report = TaskGroup(__PLUGIN__, params)
    lb_task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_lista_wynikow',
    }
    report.create_task(lb_task)
    report.save()
    return report


def raport_lista_wynikow(task_params):
    params = task_params['params']
    same_badania = [pos[0] for pos in params['badania']]
    parametry_badan = {}
    for [bad, par] in params['badania']:
        if bad not in parametry_badan:
            parametry_badan[bad] = set()
        parametry_badan[bad].add(par)
    rep_results = []
    sql = SQL
    sql_params = [
        params['dataod'], str(params['datado']) + ' 23:59:59',
    ]
    if not empty(params['platnik']):
        sql = sql.replace(
            'select id from oddzialy where symbol in ($ODDZIALY$)',
            'select id from oddzialy where platnik=(select id from platnicy where symbol=? and del=0)'
        )
        sql_params.append(params['platnik'])
    else:
        sql = sql.replace('$ODDZIALY$', ','.join(["'%s'" % symbol for symbol in params['zleceniodawcy']]))
    sql = sql.replace('$BADANIA$', ','.join(["'%s'" % symbol for symbol in same_badania]))
    wyniki_zleceniodawcow = {}
    zleceniodawcy_nazwy = {'': 'wyniki'}
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
    for row in rows:
        zlec_symbol = row[2]
        zlec_nazwa = row[3]
        bad = row[7]
        par = row[8]
        if par not in parametry_badan[bad]:
            continue
        target = zlec_symbol if params['zleceniodawcy_oddzielnie'] else ''
        if target not in wyniki_zleceniodawcow:
            wyniki_zleceniodawcow[target] = []
            zleceniodawcy_nazwy[zlec_symbol] = zlec_nazwa
        wyniki_zleceniodawcow[target].append(row)
    if len(params['emails']) > 0:
        results = []
        for target, rows in wyniki_zleceniodawcow.items():
            results.append({
                'type': 'table',
                'header': cols,
                'data': prepare_for_json(rows),
                'filename': '%s_%s.xlsx' % (target, slugify(zleceniodawcy_nazwy[target]))
            })
        send_password = False
        if empty(params['password']):
            params['password'] = simple_password()
            send_password = True
        if len(results) > 0:
            encrypt_and_send(params['emails'], params['password'], results,
                             attachment_filename='wyniki_%s.zip' % datetime.datetime.now().strftime('%Y-%m-%d'),
                             subject='Zestawienie wyników')
            if send_password:
                for phone in params['phones']:
                    send_sms(phone, "Hasło do załącznika: %s" % params['password'], send_now=False)
                send_sms_flush_queue()
            rep_results.append({
                'type': 'info',
                'text': 'Wygenerowano i wysłano'
            })
        else:
            rep_results.append({
                'type': 'info',
                'text': 'Brak wyników'
            })
    for target, rows in wyniki_zleceniodawcow.items():
        rep_results.append({
            'type': 'table',
            'title': "%s - %s" % (target, zleceniodawcy_nazwy[target]),
            'header': cols,
            'data': prepare_for_json(rows),
        })
    return rep_results

