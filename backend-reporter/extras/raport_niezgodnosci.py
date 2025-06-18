import os.path
import tempfile

import json

from typing import Any, Dict
from copy import copy

import datetime
from abc import ABC, abstractmethod
from datetime import time
import weasyprint

from datasources.centrum import CentrumConnection
from helpers import get_centrum_connection, empty, prepare_for_json
from helpers.strings import comma_seq, db_escape_string
from helpers.validators import validate_symbol
from outlib.xlsx import ReportXlsx
from outlib.pdf import ReportPdf, PAPER_SIZES, HTML_HEAD, HTML_FOOT
from outlib.email import Email
from datasources.snrkonf import SNRKonf
from datasources.spreadsheet import spreadsheet_to_values
from tasks import TaskGroup

"""
cols = ['płatnik', 'zleceniodawca', 'raport rano', 'raport rano godzina', 'raport wieczór', 'raport wieczór godzina',
        'emaile', 'braki materiału', 'błędy', 'wartości krytyczne', 'drobnoustroje alarmowe', 'weryfikacje',
        'wysyłać pusty raport']
"""

USTAWIENIA_BOOL = ['raport rano', 'raport wieczór', 'braki materiału', 'błędy', 'wartości krytyczne',
                   'drobnoustroje alarmowe', 'weryfikacje', 'wysyłać pusty raport']


class SekcjaRaportu(ABC):
    tytul_krotki = None
    ustawienie = None

    tab_glowne_pl = ['wykonania w', 'platnicy pl on pl.id=w.platnik', 'zlecenia zl on zl.id=w.zlecenie',
                     'oddzialy o on o.id=zl.oddzial', 'badania bad on bad.id=w.badanie',
                     'bledywykonania bl on bl.id=w.bladwykonania',
                     'pacjenci pac on pac.id=zl.pacjent', "materialy mat on mat.id=w.material",
                     'grupybadan gb on gb.id=bad.grupa']
    tab_glowne_zl = ['zlecenia zl', 'oddzialy o on o.id=zl.oddzial', 'wykonania w on zl.id=w.zlecenie',
                     'platnicy pl on pl.id=w.platnik', 'badania bad on bad.id=w.badanie',
                     'bledywykonania bl on bl.id=w.bladwykonania',
                     'pacjenci pac on pac.id=zl.pacjent', "materialy mat on mat.id=w.material",
                     'grupybadan gb on gb.id=bad.grupa']
    tab_wyniki = ['wyniki y on y.wykonanie=w.id', 'normy n on n.id=y.norma', 'parametry par on par.id=y.parametr']
    kol_glowne_pl = ['trim(pl.symbol) as symbol', 'zl.id as zid', 'w.datarejestracji as data',
                     'zl.godzinarejestracji as godz', 'zl.numer', 'o.nazwa as zleceniodawca',
                     "(pac.Nazwisko || ' ' || pac.Imiona) as PACJENT",
                     "coalesce(cast(pac.PESEL as varchar(12)),'') as PESEL"]
    kol_glowne_zl = ['trim(o.symbol) as symbol', 'zl.id as zid', 'w.datarejestracji as data',
                     'zl.godzinarejestracji as godz', 'zl.numer', 'o.nazwa as zleceniodawca',
                     "(pac.Nazwisko || ' ' || pac.Imiona) as PACJENT",
                     "coalesce(cast(pac.PESEL as varchar(12)),'') as PESEL"]
    kol_badanie = ['trim(bad.symbol) as badanie_symbol', 'bad.nazwa as badanie_nazwa']
    kol_wyniki = ['y.wyniktekstowy']
    badania_pg = "array_to_string(array_agg(trim(bad.symbol)), ', ') as BADANIA"
    badania_fb = "list(trim(bad.symbol), ', ') as BADANIA"

    @property
    def kol_badania(self):
        if self.baza_pg:
            return self.badania_pg
        else:
            return self.badania_fb

    @property
    def warunek_zatwierdzen(self):
        if self.baza_pg:
            if self.pora == "rano":
                return "w.zatwierdzone between (current_timestamp - interval '32 hours') and current_timestamp"
            else:
                return "w.zatwierdzone between (current_timestamp - interval '24 hours') and current_timestamp"
        else:
            if self.pora == "rano":
                data = datetime.datetime.now() - datetime.timedelta(hours=32)
            else:
                data = datetime.datetime.now() - datetime.timedelta(hours=24)
            return "w.zatwierdzone > '" + data.strftime("%Y-%m-%d %H:%M:%S") + "'"

    def __init__(self, pora: str, baza_pg: bool,
                 platnicy: Dict[str, Dict[str, Any]], zleceniodawcy: Dict[str, Dict[str, Any]]):
        self.pora = pora
        self.baza_pg = baza_pg
        self.platnicy = []
        self.zleceniodawcy = []
        self.dane = {'platnicy': {}, 'zleceniodawcy': {}}
        for config_dict, symbol_list in [
            (platnicy, self.platnicy), (zleceniodawcy, self.zleceniodawcy),
        ]:
            for symbol, row in config_dict.items():
                symbol = symbol.upper().strip()
                if row[self.ustawienie]:
                    if symbol not in symbol_list:
                        symbol_list.append(symbol)

    def zbierz_dane(self, conn: CentrumConnection):
        if len(self.platnicy):
            sql, sql_params = self.sql_with_params_platnicy
            # print(sql, sql_params)
            for row in conn.raport_slownikowy(sql, sql_params):
                symbol = row['symbol'].strip()
                if symbol not in self.dane['platnicy']:
                    self.dane['platnicy'][symbol] = []
                self.dane['platnicy'][symbol].append(row)
        if len(self.zleceniodawcy):
            sql, sql_params = self.sql_with_params_zleceniodawcy
            # print(sql, sql_params)
            for row in conn.raport_slownikowy(sql, sql_params):
                symbol = row['symbol'].strip()
                if symbol not in self.dane['zleceniodawcy']:
                    self.dane['zleceniodawcy'][symbol] = []
                self.dane['zleceniodawcy'][symbol].append(row)
        return self.dane

    @classmethod
    def podsumuj(cls, dane):
        count = 0
        for fld in ('platnicy', 'zleceniodawcy'):
            for k, v in dane[fld].items():
                count += len(v)
        if count > 0:
            return f"{count} x {cls.tytul_krotki}"
        return None

    @classmethod
    def sekcja(cls, dane, pora):
        wiersze = []
        for fld in ('platnicy', 'zleceniodawcy'):
            for k, v in dane[fld].items():
                for row in v:
                    wiersze.append(cls.tresc_wiersz(row))
        if len(wiersze) > 0:
            tresc = [cls.tresc_naglowek(pora)]
            tresc += wiersze
            tresc += [ cls.tresc_koniec() ]
        else:
            tresc = [cls.tresc_brak_niezgodnosci(pora)]
        return '\n'.join(tresc)

    @property
    @abstractmethod
    def sql_with_params_platnicy(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def sql_with_params_zleceniodawcy(self):
        raise NotImplementedError

    @classmethod
    def tresc_naglowek(cls, pora):
        res = f'<h2>{cls.tresc_tytul(pora)}</h2>'
        res += '<table class="reportTable"><theader><tr>'
        for title, _ in cls.tresc_kolumny():
            res += '<th>%s</th>' % title
        res += '</tr></theader><tbody>'
        return res

    @classmethod
    @abstractmethod
    def tresc_tytul(cls, pora):
        return f'{cls.tytul_krotki}; {pora}'

    @classmethod
    def tresc_wiersz(cls, row):
        res = '<tr>'
        for _, fld in cls.tresc_kolumny():
            value = ''
            if '$' in fld:
                for k, v in row.items():
                    dk = '$' + k
                    if dk in fld:
                        v = str(v) if v is not None else ''
                        fld = fld.replace(dk, v)
                value = fld
            else:
                value = row.get(fld)
            if value is not None:
                value = str(value)
            else:
                value = ''
            res += '<td>%s</td>' % value
        res += '</tr>'
        return res

    @classmethod
    def tresc_koniec(cls):
        return '</tbody></table>'

    @classmethod
    def tresc_brak_niezgodnosci(cls, pora):
        return f'<p>{cls.tresc_tytul(pora)} - brak niezgodności; {pora}</p>'

    @classmethod
    @abstractmethod
    def tresc_kolumny(cls):
        ...

class BrakiMaterialu(SekcjaRaportu):

    @classmethod
    def tresc_tytul(cls, pora):
        return f'Brak materiału - {pora}'

    @classmethod
    def tresc_kolumny(cls):
        return [
            ('Symbol', 'symbol'),
            ('Pacjent', 'pacjent'),
            ('Nr/data zlecenia', '$numer / $data'),
        ]

    tytul_krotki = 'brak materiału'
    ustawienie = 'braki materiału'

    @property
    def sql_with_params_platnicy(self):
        kolumny = copy(self.kol_glowne_pl)
        kolumny.append(self.kol_badania)
        tabele = copy(self.tab_glowne_pl)
        sql = ["select", ", ".join(kolumny), "from"]
        sql.append(" left join ".join(tabele))
        where = []
        if self.pora == "rano":
            where.append(
                "w.datarejestracji='YESTERDAY' and (zl.godzinarejestracji<'TODAY' or zl.godzinarejestracji is null)")
        else:
            where.append("w.datarejestracji='TODAY' and zl.numer is not null and w.dystrybucja is null")
        where.append('bad.pakiet=0')
        where.append('pl.symbol in (%s)' % ', '.join("'%s'" % db_escape_string(symbol) for symbol in self.platnicy))
        where.append("w.anulowane is null and gb.symbol <> 'TECHNIC'")
        sql.append(" where ")
        sql.append(" and ".join(where))
        sql.append("group by " + comma_seq(1, len(self.kol_glowne_pl)))
        sql.append("order by 1")
        sql_params = []
        return " ".join(sql), sql_params

    @property
    def sql_with_params_zleceniodawcy(self):
        kolumny = copy(self.kol_glowne_zl)
        kolumny.append(self.kol_badania)
        tabele = copy(self.tab_glowne_zl)
        sql = ["select", ", ".join(kolumny), "from"]
        sql.append(" left join ".join(tabele))
        where = []
        if self.pora == "rano":
            where.append(
                "w.datarejestracji='YESTERDAY' and (zl.godzinarejestracji<'TODAY' or zl.godzinarejestracji is null)")
        else:
            where.append("w.datarejestracji='TODAY' and zl.numer is not null and w.dystrybucja is null")
        where.append('bad.pakiet=0')
        where.append('o.symbol in (%s)' % ', '.join("'%s'" % db_escape_string(symbol) for symbol in self.zleceniodawcy))
        where.append("w.anulowane is null and gb.symbol <> 'TECHNIC'")
        sql.append(" where ")
        sql.append(" and ".join(where))
        sql.append("group by " + comma_seq(1, len(self.kol_glowne_zl)))
        sql.append("order by 1")
        sql_params = []
        return " ".join(sql), sql_params


class BledyWykonania(SekcjaRaportu):
    @classmethod
    def tresc_kolumny(cls):
        return [
            ('Symbol', 'symbol'),
            ('Pacjent', 'pacjent'),
            ('Nr/data zlecenia', '$numer / $data'),
        ]

    @classmethod
    def tresc_tytul(cls, pora):
        return f'Błędy wykonania - {pora}'

    tytul_krotki = 'błędy wykonania'
    ustawienie = 'błędy'

    @property
    def sql_with_params_platnicy(self):
        kolumny = copy(self.kol_glowne_pl)
        kolumny.append(self.kol_badania)
        tabele = copy(self.tab_glowne_pl)
        sql = ["select", ", ".join(kolumny), "from"]
        sql.append(" left join ".join(tabele))
        where = []
        where.append(self.warunek_zatwierdzen)
        where.append("w.bladwykonania is not null and bl.symbol not in ('ZLEC', 'OSAD-N', 'ROZMAZ')")
        where.append('bad.pakiet=0')
        where.append('o.symbol in (%s)' % ', '.join("'%s'" % db_escape_string(symbol) for symbol in self.platnicy))
        where.append("w.anulowane is null and gb.symbol <> 'TECHNIC'")
        sql.append(" where ")
        sql.append(" and ".join(where))
        sql.append("group by " + comma_seq(1, len(self.kol_glowne_pl)))
        sql.append("order by 1")
        sql_params = []
        return " ".join(sql), sql_params

    @property
    def sql_with_params_zleceniodawcy(self):
        kolumny = copy(self.kol_glowne_zl)
        kolumny.append(self.kol_badania)
        tabele = copy(self.tab_glowne_zl)
        sql = ["select", ", ".join(kolumny), "from"]
        sql.append(" left join ".join(tabele))
        where = []
        where.append(self.warunek_zatwierdzen)
        where.append("w.bladwykonania is not null and bl.symbol not in ('ZLEC', 'OSAD-N', 'ROZMAZ')")
        where.append('bad.pakiet=0')
        where.append('o.symbol in (%s)' % ', '.join("'%s'" % db_escape_string(symbol) for symbol in self.zleceniodawcy))
        where.append("w.anulowane is null and gb.symbol <> 'TECHNIC'")
        sql.append(" where ")
        sql.append(" and ".join(where))
        sql.append("group by " + comma_seq(1, len(self.kol_glowne_zl)))
        sql.append("order by 1")
        sql_params = []
        return " ".join(sql), sql_params


class WartosciKrytyczne(SekcjaRaportu):
    @classmethod
    def tresc_kolumny(cls):
        pass

    @classmethod
    def tresc_tytul(cls, pora):
        return f'Wartości krytyczne - {pora}'

    tytul_krotki = 'wartości krytyczne wyników badań'
    ustawienie = 'wartości krytyczne'

    @property
    def sql_with_params_platnicy(self):
        kolumny = copy(self.kol_glowne_pl)
        kolumny += copy(self.kol_badanie)
        kolumny += copy(self.kol_wyniki)
        tabele = copy(self.tab_glowne_pl)
        tabele += copy(self.tab_wyniki)
        sql = ["select", ", ".join(kolumny), "from"]
        sql.append(" left join ".join(tabele))
        where = []
        where.append(self.warunek_zatwierdzen)
        where.append('bad.pakiet=0')
        where.append('pl.symbol in (%s)' % ', '.join("'%s'" % db_escape_string(symbol) for symbol in self.platnicy))
        where.append("w.anulowane is null and gb.symbol <> 'TECHNIC' and w.bladwykonania is null and y.ukryty=0")
        where.append('y.flagakrytycznych is not null and y.flagakrytycznych > 0')
        where.append("par.symbol not in ('MCH', 'MCHC', 'LIC%')")
        sql.append(" where ")
        sql.append(" and ".join(where))
        sql.append("order by o.nazwa")
        sql_params = []
        return " ".join(sql), sql_params

    @property
    def sql_with_params_zleceniodawcy(self):
        kolumny = copy(self.kol_glowne_zl)
        kolumny += copy(self.kol_badanie)
        kolumny += copy(self.kol_wyniki)
        tabele = copy(self.tab_glowne_zl)
        tabele += copy(self.tab_wyniki)
        sql = ["select", ", ".join(kolumny), "from"]
        sql.append(" left join ".join(tabele))
        where = []
        where.append(self.warunek_zatwierdzen)
        where.append('bad.pakiet=0')
        where.append('o.symbol in (%s)' % ', '.join("'%s'" % db_escape_string(symbol) for symbol in self.zleceniodawcy))
        where.append("w.anulowane is null and gb.symbol <> 'TECHNIC' and w.bladwykonania is null and y.ukryty=0")
        where.append('y.flagakrytycznych is not null and y.flagakrytycznych > 0')
        where.append("par.symbol not in ('MCH', 'MCHC', 'LIC%')")
        sql.append(" where ")
        sql.append(" and ".join(where))
        sql.append("order by o.nazwa")
        sql_params = []
        return " ".join(sql), sql_params


class DrobnoustrojeAlarmowe(SekcjaRaportu):
    @property
    def sql_with_params_platnicy(self):
        pass

    @property
    def sql_with_params_zleceniodawcy(self):
        pass

    @classmethod
    def tresc_tytul(cls, pora):
        pass

    @classmethod
    def tresc_kolumny(cls):
        pass

    tytul_krotki = 'drobnoustroje alarmowe'
    ustawienie = 'drobnoustroje alarmowe'


class Weryfikacje(SekcjaRaportu):
    @property
    def sql_with_params_platnicy(self):
        pass

    @property
    def sql_with_params_zleceniodawcy(self):
        pass

    @classmethod
    def tresc_tytul(cls, pora):
        pass

    @classmethod
    def tresc_kolumny(cls):
        pass

    tytul_krotki = 'dorejestrowane badania weryfikacyjne'
    ustawienie = 'weryfikacje'


class RaportNiezgodnosci():
    klasy_sekcji = [
        BrakiMaterialu, BledyWykonania, WartosciKrytyczne,  # DrobnoustrojeAlarmowe, Weryfikacje
    ]

    def __init__(self):
        self.config = None
        self.pora = None
        self.platnicy = None
        self.zleceniodawcy = None
        self.laboratoria = None
        self.single_lab = None

    def load_config(self, fn):
        self.config = []
        config = spreadsheet_to_values(fn)
        header = [str(v).lower() for v in config[0]]
        for row in config[1:]:
            config_item = dict(zip(header, [v if not empty(v) else None for v in row]))
            emaile = config_item['emaile'].replace(',', ' ').replace(';', ' ').split(' ')
            config_item['emaile'] = [email.strip() for email in emaile if '@' in email]
            for fld in USTAWIENIA_BOOL:
                config_item[fld] = fld in config_item and not empty(config_item[fld]) and str(
                    config_item[fld]).lower().startswith('t')
            for fld in ('raport rano godzina', 'raport wieczór godzina'):
                fld_enabled = fld.replace(' godzina', '')
                if not config_item[fld_enabled]:
                    config_item[fld] = None
                if config_item[fld] is not None:
                    config_item[fld] = config_item[fld].strftime('%H:%M')
            self.config.append(config_item)

    def configure_for_single_lab(self, lab, pora, platnicy, zleceniodawcy):
        self.single_lab = lab
        self.pora = pora
        self.platnicy = platnicy
        self.zleceniodawcy = zleceniodawcy

    def weryfikuj_generuj_cron(self):
        self.assign_labs(z_platnikow_zleceniodawcow=False)

    def set_time(self, report_time):
        if isinstance(report_time, datetime.datetime):
            report_time = report_time.strftime('%H:%M')
        self.platnicy = {}
        self.zleceniodawcy = {}
        for pora in ('rano', 'wieczór'):
            for row in self.config:
                fld_godzina = "raport %s godzina" % pora
                if row[fld_godzina] == report_time:
                    if self.pora is None:
                        self.pora = pora
                    else:
                        if self.pora != pora:
                            raise RuntimeError("niejednoznaczna pora", report_time)
                    if not empty(row['zleceniodawca']):
                        self.zleceniodawcy[row['zleceniodawca'].upper().strip()] = row
                    elif not empty(row['płatnik']):
                        self.platnicy[row['płatnik'].upper().strip()] = row
                    else:
                        raise RuntimeError("Brak płatnika i zleceniodawcy")

    def assign_labs(self, z_platnikow_zleceniodawcow=False):
        if z_platnikow_zleceniodawcow:
            zrodlo = list(self.platnicy.values()) + list(self.zleceniodawcy.values())
        else:
            zrodlo = self.config
        self.laboratoria = {}
        platnicy = {}
        zleceniodawcy = {}
        for row in zrodlo:
            if not empty(row['płatnik']):
                validate_symbol(row['płatnik'])
                platnicy[row['płatnik']] = None
            if not empty(row['zleceniodawca']):
                validate_symbol(row['zleceniodawca'])
                zleceniodawcy[row['zleceniodawca']] = None
        snr = SNRKonf()
        if len(platnicy) > 0:
            for row in snr.dict_select("select * from platnicywlaboratoriach where symbol in %s",
                                       [tuple(platnicy.keys())]):
                symbol = row['symbol'][:7]
                lab = row['laboratorium'][:7]
                if lab not in self.laboratoria:
                    self.laboratoria[lab] = {'płatnicy': [], 'zleceniodawcy': []}
                self.laboratoria[lab]['płatnicy'].append(symbol)
                platnicy[symbol] = row['platnik']
        if len(zleceniodawcy) > 0:
            for row in snr.dict_select("select * from zleceniodawcywlaboratoriach where symbol in %s",
                                       [tuple(zleceniodawcy.keys())]):
                symbol = row['symbol'][:7]
                lab = row['laboratorium'][:7]
                if lab not in self.laboratoria:
                    self.laboratoria[lab] = {'płatnicy': [], 'zleceniodawcy': []}
                self.laboratoria[lab]['zleceniodawcy'].append(symbol)
                zleceniodawcy[symbol] = row['zleceniodawca']
        for k, v in platnicy.items():
            if v is None:
                raise RuntimeError("Nieznany płatnik", k)
        for k, v in zleceniodawcy.items():
            if v is None:
                raise RuntimeError("Nieznany zleceniodawca", k)

    def run_reports(self):
        params = {
            'pora': self.pora,
            'laboratoria': self.laboratoria,
            'płatnicy': self.platnicy,
            'zleceniodawcy': self.zleceniodawcy,
        }
        task_group = TaskGroup('extras.raport_niezgodnosci', params)
        for lab in self.laboratoria.keys():
            task_group.create_task({
                'type': 'centrum',
                'priority': 1,
                'target': lab,
                'params': params,
                'function': 'raport_lab',
                'retries': 5,
            })
        task_group.save()

    def collect_data(self):
        res = {}
        if self.single_lab is None:
            raise RuntimeError("Uruchamiać dla pojedynczego labu")
        with get_centrum_connection(self.single_lab) as conn:
            self.sekcje = [klasa(
                pora=self.pora, baza_pg=conn.db_engine == "postgres",
                platnicy=self.platnicy, zleceniodawcy=self.zleceniodawcy,
            ) for klasa in self.klasy_sekcji]
            for sekcja in self.sekcje:
                sekcja_res = sekcja.zbierz_dane(conn)
                res[sekcja.tytul_krotki] = sekcja_res
        return res

    def send_reports(self, data):
        emaile = {}
        for symbol, row in self.platnicy.items():
            key = (','.join(sorted(row['emaile']))).lower()
            if key not in emaile:
                emaile[key] = {'zleceniodawcy': set(), 'platnicy': set(), 'pusty': False}
            emaile[key]['platnicy'].add(symbol)
            if row['wysyłać pusty raport']:
                emaile[key]['pusty'] = True
        for symbol, row in self.zleceniodawcy.items():
            key = (','.join(sorted(row['emaile']))).lower()
            if key not in emaile:
                emaile[key] = {'zleceniodawcy': set(), 'platnicy': set(), 'pusty': False}
            emaile[key]['zleceniodawcy'].add(symbol)
            if row['wysyłać pusty raport']:
                emaile[key]['pusty'] = True
        sender = Email()
        for email, ust in emaile.items():
            print(email)
            print('  ', ust)
            podsumowania = []
            sekcje = []
            for klasa in self.klasy_sekcji:
                dane_klasy = self.filter_data(data[klasa.tytul_krotki], ust)
                podsumowanie = klasa.podsumuj(dane_klasy)
                if podsumowanie is not None:
                    podsumowania.append(podsumowanie)
                sekcje.append(klasa.sekcja(dane_klasy, self.pora))
            print('\n'.join(podsumowania))
            if len(podsumowania) > 0:
                tresc = '\n'.join(podsumowania)
            else:
                tresc = 'Brak niezgodności'

            tresc += f'\n\nMail docelowo do {email}'
            with tempfile.TemporaryDirectory() as tmpdir:
                attachment = self.generate_attachment(tmpdir, sekcje)
                sender.send(['adam.morawski@alab.com.pl'], 'Raport niezgodności', tresc, attachments=[
                    attachment
                ])

    def filter_data(self, data, settings):
        res = {}
        for fld in ('platnicy', 'zleceniodawcy'):
            res[fld] = {}
            for k, v in data[fld].items():
                if k in settings[fld]:
                    res[fld][k] = v
        return res

    def generate_attachment(self, tmpdir, sekcje):
        fn = os.path.join(tmpdir, 'raport_niezgodnosci.pdf')
        report = ReportPdf({
            'results': [{'type': 'html', 'html': sekcja} for sekcja in sekcje],
            'errors': []
        }, title = 'Raport niezgodności', password = 'alabpdf')
        report.render_to_file(fn)
        return fn


def raport_lab(task_params):
    params = task_params['params']
    lab = task_params['target']
    lab_config = params['laboratoria'][lab]
    fn = f'/tmp/rn_{lab}.json'
    platnicy = {}
    zleceniodawcy = {}
    for symbol, row in params['płatnicy'].items():
        if row['płatnik'] in lab_config['płatnicy']:
            platnicy[symbol] = row
    for symbol, row in params['zleceniodawcy'].items():
        if row['zleceniodawca'] in lab_config['zleceniodawcy']:
            zleceniodawcy[symbol] = row
    rn = RaportNiezgodnosci()
    rn.configure_for_single_lab(lab, params['pora'], platnicy, zleceniodawcy)
    if not os.path.exists(fn):
        res = rn.collect_data()
        with open(fn, 'w') as f:
            json.dump(prepare_for_json(res), f)
    else:
        with open(fn, 'r') as f:
            res = json.load(f)
    rn.send_reports(res)
