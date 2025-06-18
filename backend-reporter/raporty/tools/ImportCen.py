import base64
import datetime
import os

import time
import hashlib
from api.auth import login_required
from datasources.snr import SNR
from datasources.spreadsheet import spreadsheet_to_values
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError, Switch, FileInput
from helpers.validators import validate_date_range, validate_symbol
from datasources.reporter import ReporterExtraDatasource
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty, odpiotrkuj, list_from_space_separated, random_path

MENU_ENTRY = 'Import cen do SNR'

REQUIRE_ROLE = ['C-ADM']

FIELDS_IN_FILE = {
    'lab': 'Laboratorium',
    'cennik': 'Cennik',
    'numerk': 'Numer K',
    'nip': 'NIP',
    'umowa': 'Umowa',
}

SQL_CENNIKI_GOTOWKOWE = """
    select id, laboratorium, hs->'symbolwlaboratorium' as symbol 
    from cenniki c 
    where symbol is not null and laboratorium is not null and not del and not wycofany and not zablokowany
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""
Import cen z arkusza XLSX. Plik musi zawierać dokładnie 1 arkusz. W arkuszu muszą się znajdować co najmniej kolumny Badanie i Cena.
Na właściwy cennik wskazują pola:
 - Laboratorium i Cennik (symbole) - dla cenników gotówkowych
 - Numer K lub NIP i Umowa (identyfikator umowy/aneksu/PU) - dla cenników klientów
Pola te mogą być albo wypełnione poniżej (import wszystkich cen w jedno miejsce) albo jako kolumny w arkuszu (jednorazowy import do wielu cenników).
Jest też możliwość importu cen do wszystkich cenników gotówkowych (aktywnych).

Uruchomienie raportu bez wpisania kodu potwierdzenia wyświetli tylko jakie zmiany zostałyby naniesione i poda kod potwierdzenia.
Aby faktycznie nanieść zmiany na cenniki należy przekleić podany kod potwierdzenia.
    """),
    FileInput(field="plik", title="Plik z cenami"),
    HBox(
        TextInput(field="lab", title="Gotówka: Laboratorium"),
        TextInput(field="cennik", title="Cennik"),
        Switch(field="gotowki", title="Wszystkie cenniki gotówkowe")
    ),
    HBox(
        TextInput(field="numerk", title="Klient: Numer K"),
        TextInput(field="nip", title="lub NIP"),
        TextInput(field="umowa", title="Umowa"),
    ),
    TextInput(field='confirm', title='Kod potwierdzenia'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['plik'] is None:
        raise ValidationError("Wybierz plik")
    cenniki_gotowkowe = []
    if params['gotowki']:
        wszystkie_gotowki = True
        if not empty(params['cennik']) or not empty(params['numerk']) or not empty(params['nip']) or not empty(
                params['umowa']):
            raise ValidationError("Przy imporcie do gotówek nie wypełniaj innych pól wskazujących na cennik.")
        snr = SNR()
        for row in snr.dict_select(SQL_CENNIKI_GOTOWKOWE):
            cenniki_gotowkowe.append(f'GOT^{row["laboratorium"].strip()}^{row["symbol"].strip()}')
    else:
        wszystkie_gotowki = False
    tmp_fn = random_path(prefix='reporter', extension='.xlsx')
    ceny = {}
    try:
        with open(tmp_fn, 'wb') as f:
            f.write(base64.b64decode(params['plik']['content']))
        values = spreadsheet_to_values(tmp_fn)
        header = [v.lower().strip() if v is not None else '' for v in values[0]]
        for fld in ['Badanie', 'Cena']:
            if fld.lower() not in header:
                raise ValidationError(f"Brak kolumny {fld}")
        for form_fld, col in FIELDS_IN_FILE.items():
            if not empty(params[form_fld]) and col.lower() in header:
                raise ValidationError(f"Pole {col} zostało jednocześnie wypełnione w okienku i ma kolumnę w pliku")
            if wszystkie_gotowki and col.lower() in header:
                raise ValidationError(
                    f"Przy imporcie do gotówek nie wypełniaj innych pól wskazujących na cennik (kolumna {col} w arkuszu).")
        rows = values[1:]
        for i, row in enumerate(rows):
            nr_wiersza = i + 2
            opis_wiersza = f"Wiersz {nr_wiersza} ({', '.join([str(v) for v in row])})"
            row_dict = dict(zip(header, row))
            if empty(row_dict['badanie']):
                raise ValidationError(f"{opis_wiersza} - brak badania")
            if empty(row_dict['cena']):
                raise ValidationError(f"{opis_wiersza} - brak ceny")
            badanie = row_dict['badanie']
            for form_fld, col in FIELDS_IN_FILE.items():
                if not empty(params[form_fld]):
                    row_dict[form_fld] = params[form_fld]
                else:
                    row_dict[form_fld] = row_dict.get(col.lower())
            if not empty(row_dict['lab']) and not empty(row_dict['cennik']):
                for fld in ('numerk', 'nip', 'umowa'):
                    if not empty(row_dict[fld]):
                        raise ValidationError(
                            f"{opis_wiersza} ma niepuste pola wskazujące i na cennik gotówkowy i kliencki")
                cennik = f"GOT^{row_dict['lab'].strip()}^{row_dict['cennik'].strip()}"
            elif (not empty(row_dict['numerk']) or not empty(row_dict['nip'])) and not empty(row_dict['umowa']):
                for fld in ('lab', 'cennik'):
                    if not empty(row_dict[fld]):
                        raise ValidationError(
                            f"{opis_wiersza} ma niepuste pola wskazujące i na cennik gotówkowy i kliencki")
                cennik = f"KL^{(row_dict['numerk'] or '').strip()}^{(row_dict['nip'] or '').strip()}^{row_dict['umowa'].strip()}"
            elif not wszystkie_gotowki:
                raise ValidationError(
                    f"{opis_wiersza} nie wskazuje jednoznacznie ani na cennik gotówkowy ani na kliencki")
            if wszystkie_gotowki:
                cenniki = cenniki_gotowkowe
            else:
                cenniki = [cennik]
            for cennik in cenniki:
                if cennik not in ceny:
                    ceny[cennik] = {}
                if badanie in ceny[cennik]:
                    raise ValidationError(f"{opis_wiersza} - powtórzona cena tego samego badania w tym samym cenniku")
                ceny[cennik][badanie] = float(row_dict['cena'])
    finally:
        try:
            os.unlink(tmp_fn)
        except:
            pass
    print(ceny)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': {
            'ceny': ceny,
            'confirm': params['confirm'],
        },
        'function': 'raport_generuj'
    }
    report.create_task(task)
    report.save()
    return report


def cenniki_got(snr, lab, symbol_cennika):
    return snr.dict_select("""
        select * from cenniki c where not del and laboratorium=%s and hs->'symbolwlaboratorium' = %s
    """, [lab, symbol_cennika])


def umowy_kl(snr, numer_k, nip, umowa):
    sql = """
        select u.*, pl.nazwa as nazwa_platnika, pl.nip as nip_platnika, pl.hs->'umowa' as numer_k 
        from umowy u
        left join platnicy pl on pl.id=u.platnik 
        where 
    """
    params = []
    where = ['not u.del']
    if not empty(numer_k):
        where.append("pl.hs->'umowa'=%s")
        params.append(numer_k)
    if not empty(nip):
        where.append("pl.nip=%s")
        params.append(nip)
    where.append('u.identyfikatorwrejestrze=%s')
    params.append(umowa)
    sql += ' and '.join(where)
    return snr.dict_select(sql, params)


def ceny_badan_aktualne(snr, id_cennika, id_umowy, badania):
    res = {}
    sql = """
        select * from ceny where 
    """
    where = ['not del', 'badanie in %s']
    params = [tuple(badania)]
    if id_cennika is not None:
        where.append('cennik=%s')
        params.append(id_cennika)
    else:
        where.append('cennik is null')
    if id_umowy is not None:
        where.append('umowa=%s')
        params.append(id_umowy)
    else:
        where.append('umowa is null')
    sql += ' and '.join(where)
    for row in snr.dict_select(sql, params):
        if row['badanie'] in res:
            raise RuntimeError("Niejednoznaczna cena badania", row)
        res[row['badanie']] = (row['id'], row['cenadlaplatnika'], row['nazwa'])
    return res


def raport_generuj(task_params):
    params = task_params['params']
    res = []
    bledy = []
    zmiany = []  # oper, id ceny, symbol cennika, id umowy, badanie, nazwa, cenadlaplatnika
    opisy_zmian = []
    wszystkie_badania = []
    nazwy_badan = {}
    snr = SNR()
    for cennik, ceny_badan in params['ceny'].items():
        id_cennika = id_umowy = opis_cennika = None
        cennik = cennik.split('^')
        for bad in ceny_badan:
            if bad not in wszystkie_badania:
                wszystkie_badania.append(bad)
        if cennik[0] == 'GOT':
            lab = cennik[1]
            if lab == 'KOPERNI':
                lab = 'KOPERNIKA'
            symbol_cennika = cennik[2]
            cenniki = cenniki_got(snr, lab, symbol_cennika)
            if len(cenniki) == 0:
                bledy.append(f"Brak cennika gotówkowego dla lab {lab} symbol {symbol_cennika}")
            elif len(cenniki) > 1:
                bledy.append(f"Niejednoznaczny cennik gotówkowy dla lab {lab} symbol {symbol_cennika}")
            else:
                id_cennika = cenniki[0]['symbol']
                opis_cennika = f"{lab} - {cenniki[0]['nazwa']}"
        elif cennik[0] == 'KL':
            numer_k = cennik[1]
            nip = cennik[2]
            umowa = cennik[3]
            umowy = umowy_kl(snr, numer_k, nip, umowa)
            if len(umowy) == 0:
                bledy.append(f"Brak cennika klienckiego dla {numer_k} {nip} {umowa}")
            elif len(umowy) > 1:
                bledy.append(f"Niejednoznaczny cennik kliencki dla {numer_k} {nip} {umowa}")
            else:
                id_umowy = umowy[0]['id']
                opis_cennika = f"{umowy[0]['nazwa_klienta']} - {umowy[0]['rejestr']} {umowy[0]['identyfikatorwrejestrze']}"
        else:
            raise RuntimeError("Nieprawidłowy cennik", cennik)
        opisy_zmian_cennika = []
        aktualne = ceny_badan_aktualne(snr, id_cennika, id_umowy, ceny_badan.keys())
        for badanie, cena in ceny_badan.items():
            if badanie in aktualne:
                id_ceny, stara_cena, nazwa = aktualne[badanie]
            else:
                id_ceny = stara_cena = nazwa = None
            if stara_cena is not None:
                if stara_cena != cena:
                    # TODO jeszcze jakoś pobranie nazwy z arkusza na przyszłość
                    opisy_zmian_cennika.append(f"{badanie} [{stara_cena} -> {cena}]")
                    zmiany.append(['UPDATE', id_ceny, None, None, None, None, cena])
            else:
                opisy_zmian_cennika.append(f"{badanie} [nowe {cena}]")
                zmiany.append(['INSERT', None, id_cennika, id_umowy, badanie, None, cena])
        # TODO zebrać
        if len(opisy_zmian_cennika) > 0:
            opisy_zmian.append(f"{opis_cennika}: {', '.join(opisy_zmian_cennika)}")
    for row in snr.dict_select("select symbol, nazwa from badania where symbol in %s and not del",
                               [tuple(wszystkie_badania)]):
        nazwy_badan[row['symbol']] = row['nazwa']
    if len(nazwy_badan.keys()) != len(wszystkie_badania):
        bledy.append(f"Brak badań {', '.join([bad for bad in wszystkie_badania if bad not in nazwy_badan])}")
    if len(bledy) > 0:
        for blad in bledy:
            res.append({'type': 'error', 'text': blad})
        return res
    for opis in opisy_zmian:
        res.append({'type': 'info', 'text': opis})
    zmiany_txt = '\n'.join(sorted([
        '\t'.join([str(val) for val in zmiana])
        for zmiana in zmiany
    ]))
    kod_potwierdzenia = hashlib.sha1(zmiany_txt.encode()).hexdigest()
    if not empty(params['confirm']):
        if params['confirm'].strip() == kod_potwierdzenia:
            for [oper, id_ceny, symbol_cennika, id_umowy, badanie, nazwa, cenadlaplatnika] in zmiany:
                if oper == 'INSERT':
                    if nazwa is None:
                        nazwa = nazwy_badan[badanie]
                    snr.execute("""insert into ceny(pc, cennik, umowa, badanie, 
                            materialy, typyzlecen, analizatory, nazwa, cenadlaplatnika) 
                            values('ADMIN', %s, %s, %s, '', '', '', %s, %s)""",
                                [symbol_cennika, id_umowy, badanie, nazwa, cenadlaplatnika])
                elif oper == 'UPDATE':
                    if id_ceny is None:
                        raise RuntimeError("brak id ceny")
                    snr.execute("""update ceny set cenadlaplatnika=%s, pc='ADMIN' where id=%s""",
                                [cenadlaplatnika, id_ceny])
                else:
                    raise RuntimeError("Nieznana operacja", oper)
            snr.commit()
        else:
            res.append({'type': 'error', 'text': 'Nieprawidłowy kod potwierdzenia - nie nanoszę zmian'})
    res.append({'type': 'info', 'text': f'Kod potwierdzenia: {kod_potwierdzenia}'})
    return res
