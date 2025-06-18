import base64
import datetime
import json
import os
import shutil
import random

import sentry_sdk

from api.common import get_db
from datasources.bic import BiCDatasource
from datasources.reporter import ReporterDatasource
from datasources.snrkonf import SNRKonf
from datasources.spreadsheet import spreadsheet_to_values, find_col
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError, Switch, FileInput
from datasources.centrum import CentrumWzorcowa
from api_access_client import ApiAccessManager
from helpers.validators import validate_symbol
from tasks import TaskGroup, Task
from helpers import prepare_for_json, generate_barcode_img_tag, get_centrum_connection, slugify, get_and_cache, empty, \
    divide_chunks
from helpers.files import random_path
from outlib.xlsx import ReportXlsx
from outlib.email import Email
import random
import string
from outlib.synchdat import SynchDat, DatCol
from raporty.Synchronizacje.generowanie_metod_wysylkowych import GenerowanieMetodWysylkowych

MENU_ENTRY = 'Metody wysyłkowe'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""Wybierz plik XLSX z nowym rozdzielnikiem metod.
        Arkusz powinien mieć 1 zakładkę, 1 linię nagłówka, w niej obowiązkowo kolumnę Badanie (wypełnioną symbolami badań)
        oraz kolumny z rozdzielnikiem metod (symbolami) według poniższego opisu. Inne kolumny będą ignorowane. Symbole metod muszą
        odpowiadać pracowniom wysyłkowym (z grupą ALAB lub ZEWN) założonych w SNR.
        Nagłówek kolumny z rozdzielnikiem może składać się z oddzielonych spacją warunków na lab, płatnika, zleceniodawcę
        lub dni tygodnia. W przypadku podania warunku na płatnika warunek na lab nie jest konieczny - lab będzie wybrany wg symbolu płatnika.
        Przykładowe warunki:
          lab:ZAWODZI
          pł:F-SZPIT
          zl:FALAZAW
          lab:OTWOCK dni:678
          zl:F-ODDZ tz:C
        
        UWAGA! Generator działa na wszystkich wierszach i kolumnach, także ukrytych. Przesyłany dokument nie powinien 
        mieć ukrytych wierszy/kolumn, ale nie jest to weryfikowane. 
        """),
    FileInput(field="plik", title="Plik z metodami"),
    Switch(field="czysc", title="Czyść dotychczasowe bardziej szczegółowe powiązania metod")
))


def start_report(params, user_login):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['plik'] is None:
        raise ValidationError("Wybierz plik")
    if params['czysc']:
        raise ValidationError("Nie umiem czyścić powiązań :(")
    tmp_fn = random_path(prefix='reporter', extension='.xlsx')
    header_badanie = None
    header_powiazania = {}
    errors = []
    warnings = []
    infos = []
    spr_laby = []
    spr_platnicy = []
    spr_zleceniodawcy = []
    spr_typyzlecen = []
    spr_badania = []
    spr_metody = []
    spr_typyzlecen = []

    metody_do_zrobienia = {}
    powiazania_do_zrobienia = []
    laby_platnikow = {}
    laby_zleceniodawcow = {}
    nazwy_metod = {}
    powiazania_do_labow = {}
    aparaty = {}
    wysylki_miedzylab = {}

    def add_error(text: str):
        if text not in errors:
            errors.append(text)

    def add_warning(text: str):
        if text not in warnings:
            warnings.append(text)

    def add_info(text: str):
        if text not in infos:
            infos.append(text)

    try:
        with open(tmp_fn, 'wb') as f:
            f.write(base64.b64decode(params['plik']['content']))
        values = spreadsheet_to_values(tmp_fn)
        header = [v.upper().strip() if v is not None else '' for v in values[0]]
        rows = values[1:]
        for i, col in enumerate(header):
            if col in ('BADANIE', 'BADANIA'):
                if header_badanie is not None:
                    raise ValidationError("Powtórzona kolumna z badaniami")
                header_badanie = i
            if col != '':
                powiazania = []
                for substr in col.split(' '):
                    if ':' in substr:
                        substr_t = substr.split(':')
                        if substr_t[0] == 'DNI':
                            for c in substr_t[1]:
                                if c not in '12345678':
                                    errors.append('Nieprawidłowy opis dni: %s' % substr)
                            powiazania.append(('dni', substr_t[1]))
                        elif substr_t[0] == 'PŁ':
                            try:
                                validate_symbol(substr_t[1])
                                if substr_t[1] not in spr_platnicy:
                                    spr_platnicy.append(substr_t[1])
                                powiazania.append(('płatnik', substr_t[1]))
                            except:
                                add_error('Nieprawidłowy symbol płatnika: %s' % substr)
                        elif substr_t[0] == 'ZL':
                                try:
                                    validate_symbol(substr_t[1])
                                    if substr_t[1] not in spr_zleceniodawcy:
                                        spr_zleceniodawcy.append(substr_t[1])
                                    powiazania.append(('zleceniodawca', substr_t[1]))
                                except:
                                    add_error('Nieprawidłowy symbol zleceniodawcy: %s' % substr)
                        elif substr_t[0] == 'TZ':
                            try:
                                validate_symbol(substr_t[1])
                                if substr_t[1] not in spr_typyzlecen:
                                    spr_typyzlecen.append(substr_t[1])
                                powiazania.append(('typzlecenia', substr_t[1]))
                            except:
                                add_error('Nieprawodłowy typ zlecenia %s' % substr)
                        elif substr_t[0] == 'LAB':
                            try:
                                validate_symbol(substr_t[1])
                                if substr_t[1] not in spr_laby:
                                    spr_laby.append(substr_t[1])
                                powiazania.append(('lab', substr_t[1]))
                            except:
                                add_error('Nieprawidłowy symbol labu: %s' % substr)
                        # TYpy zleceń na razie nie
                        # elif substr_t[0] == 'TZ':
                        #     try:
                        #         validate_symbol(substr_t[1])
                        #         if substr_t[1] not in spr_typyzlecen:
                        #             spr_typyzlecen.append(substr_t[1])
                        #         powiazania.append(('typzlecenia', substr_t[1]))
                        #     except:
                        #         add_error('Nieprawidłowy typ zlecenia: %s' % substr)
                        else:
                            add_warning("Niezrozumiały warunek w kolumnie %s" % col)
                if len(powiazania) > 0:
                    header_powiazania[i] = powiazania
        for row_no, row in enumerate(rows):
            badanie = None
            for i, val in enumerate(row):
                if val is None:
                    continue
                val = str(val).strip()
                if i == header_badanie:
                    try:
                        validate_symbol(val)
                        badanie = val
                        if val not in spr_badania:
                            spr_badania.append(val)
                        else:
                            add_error("Powtórzony symbol badania %s" % val)
                    except:
                        add_error("Nieprawidłowy symbol badania %s" % val)
            for i, val in enumerate(row):
                if empty(val):
                    continue
                if i in header_powiazania:
                    try:
                        validate_symbol(val)
                        if val not in spr_metody:
                            spr_metody.append(val)
                        if badanie is None:
                            add_error("Brak badania dla wiersza %d" % (row_no + 2))
                        else:
                            powiazania_do_zrobienia.append(
                                (badanie, header_powiazania[i], val)
                            )
                            if badanie not in metody_do_zrobienia:
                                metody_do_zrobienia[badanie] = []
                            if val not in metody_do_zrobienia[badanie]:
                                metody_do_zrobienia[badanie].append(val)
                    except:
                        add_error("Nieprawidłowy symbol metody %s" % val)
        bic = BiCDatasource()
        snr = SNRKonf()
        if len(spr_badania) > 0:
            badania_sa = set()
            for chunk in divide_chunks(spr_badania, 100):
                for row in bic.dict_select("select * from services where symbol in %s", [tuple(chunk)]):
                    if row['is_bundle']:
                        add_error("%s jest pakietem!" % row['symbol'])
                    else:
                        badania_sa.add(row['symbol'])
            for bad in spr_badania:
                if bad not in badania_sa:
                    add_error("Brak badania o symbolu %s" % bad)
        else:
            add_error("Brak badań")
        if len(spr_metody) > 0:
            sa_metody = set()
            for chunk in divide_chunks(spr_metody, 100):
                # for row in bic.dict_select("""
                #     select symbol, value as nazwa, params->>'lab' as lab, params->>'zewn' as zewn
                #     from dictionaries
                #     where dict='XMETODY' and symbol in %s
                # """, [tuple(chunk)]):
                #     nazwy_metod[row['symbol']] = row['nazwa']
                #     sa_metody.add(row['symbol'])
                for row in snr.dict_select("""
                    select symbol, nazwa, hs->'system' as lab, hs->'aparat' as aparat, p.hs->'grupa' as grupa
                    from pozycjekatalogow p 
                    where p.katalog ='PRACOWNIE' and p.hs->'grupa' in ('ALAB', 'ZEWN') and not p.del
                    and (p.wszystkielaboratoria or coalesce(p.wybranelaboratoria, '') != '')
                    and symbol in %s
                """, [tuple(chunk)]):
                    if row['lab'] is None:
                        if row['grupa'] != 'ZEWN':
                            errors.append("Metoda %s nie ma skonfigurowanego systemu" % row['symbol'])
                    else:
                        try:
                            lab_int = int(row['lab'])
                            if str(lab_int) == str(row['lab']):
                                errors.append("Metoda %s nie ma skonfigurowanego systemu" % row['symbol'])
                        except:
                            pass
                    if row['grupa'] == 'ALAB':
                        wysylki_miedzylab[row['symbol']] = row['lab']
                    nazwy_metod[row['symbol']] = row['nazwa']
                    sa_metody.add(row['symbol'])
                    if not empty(row['aparat']):
                        aparaty[row['symbol']] = row['aparat']
            for met in spr_metody:
                if met not in sa_metody:
                    add_error("Brak pracowni wysyłkowej %s w SNR!" % met)

        else:
            add_error("Brak metod")
        if len(spr_platnicy) > 0:
            for chunk in divide_chunks(spr_platnicy, 100):
                for row in snr.dict_select("""
                    select laboratorium, symbol from platnicywlaboratoriach
                    where not del and symbol in %s
                """, [tuple(chunk)]):
                    if row['laboratorium'] not in spr_laby:
                        spr_laby.append(row['laboratorium'])
                    if row['symbol'] not in laby_platnikow:
                        laby_platnikow[row['symbol']] = []
                    laby_platnikow[row['symbol']].append(row['laboratorium'])
            for pl in spr_platnicy:
                if pl not in laby_platnikow:
                    add_error("Brak płatnika %s w SNR!" % pl)
        if len(spr_zleceniodawcy) > 0:
            for chunk in divide_chunks(spr_zleceniodawcy, 100):
                for row in snr.dict_select("""
                    select laboratorium, symbol from zleceniodawcywlaboratoriach
                    where not del and symbol in %s
                """, [tuple(chunk)]):
                    if row['laboratorium'] not in spr_laby:
                        spr_laby.append(row['laboratorium'])
                    if row['symbol'] not in laby_zleceniodawcow:
                        laby_zleceniodawcow[row['symbol']] = []
                    laby_zleceniodawcow[row['symbol']].append(row['laboratorium'])
            for pl in spr_zleceniodawcy:
                if pl not in laby_zleceniodawcow:
                    add_error("Brak zleceniodawcy %s w SNR!" % pl)
        byly_laby = set()
        if len(spr_laby) > 0:
            for row in snr.dict_select("Select * from laboratoria where not del"):
                row['symbol'] = row['symbol'][:7]
                if row['symbol'] in spr_laby:
                    byly_laby.add(row['symbol'])
                    if not row['aktywne']:
                        add_error("Laboratorium %s nieaktywne w SNR!" % row['symbol'])
                    if row['vpn'] is None:
                        add_error("Laboratorium %s - brak VPN w SNR, prawdopodobnie lab niemarcelowy!" % row['symbol'])
        else:
            add_error("Brak laboratoriów do rozesłania powiązań")
        for lab in spr_laby:
            if lab not in byly_laby:
                add_error("Nieznane laboratorium %s" % lab)
        for badanie, powiazania, metoda in powiazania_do_zrobienia:
            lab = None
            for (typ, pow) in powiazania:
                if typ == 'lab':
                    if lab not in (None, pow):
                        add_error("Niejednoznaczne powiązanie do labu - %s" % repr(powiazania))
                    else:
                        lab = pow
                elif typ == 'płatnik':
                    nlab = laby_platnikow.get(pow)
                    if nlab is None:
                        add_error("Brak labu dla płatnika %s" % pow)
                    elif lab not in (nlab, None):
                        add_error("Niejednoznaczne powiązanie do labu - %s" % repr(powiazania))
                    else:
                        lab = nlab
                elif typ == 'zleceniodawca':
                    nlab = laby_zleceniodawcow.get(pow)
                    if nlab is None:
                        add_error("Brak labu dla zleceniodawcy %s" % pow)
                    elif lab not in (nlab, None):
                        add_error("Niejednoznaczne powiązanie do labu - %s" % repr(powiazania))
                    else:
                        lab = nlab
            if lab is not None:
                if isinstance(lab, list):
                    laby = lab
                else:
                    laby = [lab]
                for lab in laby:
                    if metoda in wysylki_miedzylab:
                        if lab == wysylki_miedzylab[metoda]:
                            add_error("Metoda %s - wysyłka do labu %s z labu %s?" % (metoda, wysylki_miedzylab[metoda], lab))
                    if lab not in powiazania_do_labow:
                        powiazania_do_labow[lab] = []
                    powiazania_do_labow[lab].append(
                        (badanie, powiazania, metoda)
                    )
        if len(errors) > 0:
            task = {
                'type': 'ick',
                'priority': 1,
                'params': {
                    'errors': errors,
                },
                'function': 'raport_errors'
            }
        else:
            task = {
                'type': 'ick',
                'priority': 1,
                'params': {
                    'infos': infos,
                    'warnings': warnings,
                    'nazwy_metod': nazwy_metod,
                    'powiazania': powiazania_do_labow,
                    'aparaty': aparaty,
                },
                'function': 'raport_generuj'
            }
        report.create_task(task)
        report.save()
        return report
    finally:
        try:
            os.unlink(tmp_fn)
        except:
            pass


def raport_errors(task_params):
    params = task_params['params']
    res = []
    for err in params['errors']:
        res.append({
            'type': 'error',
            'text': err
        })
    return res


def raport_generuj(task_params):
    params = task_params['params']
    # with open('/tmp/mw_params.json', 'w') as f:
    #     json.dump(params, f)
    res = []
    for text in params['warnings']:
        res.append({
            'type': 'warning',
            'text': text
        })
    for text in params['infos']:
        res.append({
            'type': 'info',
            'text': text
        })
    gen = GenerowanieMetodWysylkowych()
    for symbol, nazwa in params['nazwy_metod'].items():
        if symbol not in ('X-LIMBA', 'X-VOLKM', 'X-DESAU'):
            gen.dodaj_metode_wysylkowa(symbol, nazwa, params['aparaty'].get(symbol))
    for lab, powiazania_badan in params['powiazania'].items():
        for badanie, powiazania, metoda in powiazania_badan:
            platnik = None
            oddzial = None
            dni = None
            tz = None
            for rodzaj, pow in powiazania:
                if rodzaj == 'lab':
                    continue
                if rodzaj == 'płatnik':
                    platnik = pow
                if rodzaj == 'zleceniodawca':
                    oddzial = pow
                if rodzaj == 'dni':
                    dni = pow
                if rodzaj == 'typzlecenia':
                    tz = pow
            gen.dodaj_powiazanie_metody(badanie=badanie, metoda=metoda, system=lab,
                                        platnik=platnik, oddzial=oddzial, dni_tygodnia=dni, typ_zlecenia=tz)
    res.append({
        'type': 'download',
        'content': base64.b64encode(gen.render_dat()).decode(),
        'content_type': 'application/octet-stream',
        'filename': 'metody_wysylkowe_%s.dat' % datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S'),
    })
    return res
