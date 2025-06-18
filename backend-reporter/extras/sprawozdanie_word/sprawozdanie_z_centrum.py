import os
from contextlib import contextmanager
from typing import Optional
from hashlib import sha256

from datasources.centrum import Centrum, CentrumConnection
from helpers import copy_from_remote
from helpers.crystal_ball.marcel_servers import sciezka_wydruku
from helpers.marcel_pdf_xml import MarcelPdf


class SprawozdanieZCentrum:
    def __init__(self, cnt: Centrum, wwz_id: int):
        self.cnt = cnt
        self.wwz_id = wwz_id
        self.dane_zlecenia = None
        self.naglowek = None
        self.tresc = None
        self.nazwy = {}
        self.data_badania = None
        self.wykonali = []
        self.zatwierdzili = []
        self._load()

    @contextmanager
    def cnt_connection(self):
        with self.cnt.connection() as conn:
            yield conn

    @property
    def report_id(self):
        if self.cnt.system is None or self.wwz_id is None:
            raise ValueError(self.cnt.system, self.wwz_id)
        res = f"{self.cnt.system}:{self.wwz_id}"
        sign = sha256(("Sprawozdanie z Centrum " + res).encode())
        res += ":" + sign.hexdigest()[:8]
        return res


    def _load(self):
        with self.cnt_connection() as conn:
            for row in conn.raport_slownikowy("""
                select a.naglowek from formularze f
                left join adresy a on a.id=f.adres 
                where f.symbol like 'ANGIELS' or f.wywolanie ilike '%angielski%' and f.adres is not null
                order by f.symbol='ANGIELS' desc, f.id desc
            """):
                self.naglowek = row['naglowek'].replace('\r\n', '\n')
                break
            for row in conn.raport_slownikowy("""
                select zl.id, zl.kodkreskowy, pac.nazwisko, pac.imiona, pac.dataurodzenia, pac.adres, pac.numer as pac_numer,  
                    trim(plc.symbol) as plec, zl.zewnetrznyidentyfikator, zl.numer, zl.datarejestracji,
                    lek.nazwisko as lek_nazwisko, lek.imiona as lek_imiona, o.nazwa as zleceniodawca, zl.godzinarejestracji,
                    wwz.plik
                from wydrukiwzleceniach wwz 
                left join zlecenia zl on zl.id=wwz.zlecenie
                left join pacjenci pac on pac.id=zl.pacjent
                left join plci plc on plc.id=pac.plec
                left join lekarze lek on lek.id=zl.lekarz
                left join oddzialy o on o.id=zl.oddzial

                where wwz.id = ?
            """, [self.wwz_id]):
                self.dane_zlecenia = row
                self.wykonania = []
        sciezka_remote = sciezka_wydruku('ZAWODZI', self.dane_zlecenia['datarejestracji'], self.dane_zlecenia['numer'], self.dane_zlecenia['plik'])
        sciezka_local = os.path.join('/tmp', os.path.basename(sciezka_remote))
        if not os.path.exists(sciezka_local):
            # print(sciezka_remote)
            copy_from_remote(self.cnt.adres, sciezka_remote, sciezka_local)
        pdf = MarcelPdf(sciezka_local)
        self.tresc = pdf.get_xml_as_dict()
        # os.unlink(sciezka_local)

        id_parametrow = []
        for sekcja in self.tresc['Sekcje']:
            for probka in sekcja['Próbki']:
                for wykonanie in probka['Wykonania']:
                    for fld, tab in (('Wykonanie', self.wykonali), ('Zatwierdzenie', self.zatwierdzili)):
                        dane_os = wykonanie.get(fld, {}).get('Pracownik')
                        if dane_os is not None:
                            naz = ' '.join([dane_os.get(sfld) for sfld in ('Nazwisko', 'Imiona') if sfld in dane_os]).strip()
                            if naz != '' and naz not in tab:
                                tab.append(naz)
                            # print(self.wykonali, self.zatwierdzili)
                    godz_zatw = wykonanie['Zatwierdzenie'].get('Godzina')
                    if 'T' in godz_zatw:
                        godz_zatw = godz_zatw.split('T')[0]
                        if self.data_badania is None or godz_zatw > self.data_badania:
                            self.data_badania = godz_zatw
                    for wynik in wykonanie['Wyniki']:
                        par = wynik['Parametr']
                        ident = int(par['@id'].split(':')[1])
                        if ident not in id_parametrow:
                            id_parametrow.append(ident)

        sql = """
            select par.id as par_id, met.id as met_id, bad.id as bad_id,
                par.symbol as par_symbol, par.nazwa as par_nazwa, par.nazwaalternatywna as par_nazwaalternatywna,
                met.symbol as met_symbol, met.nazwa as met_nazwa, met.opis as met_opis,
                bad.symbol as bad_symbol, bad.nazwa as bad_nazwa, bad.nazwaalternatywna as bad_nazwaalternatywna
            from parametry par
            left join metody met on met.id=par.metoda
            left join badania bad on bad.id=met.badanie
            where par.id in (%s)
        """ % ', '.join([str(id) for id in id_parametrow])

        with self.cnt_connection() as conn:
            for row in conn.raport_slownikowy(sql):
                for fld in ('bad_id', 'met_id', 'par_id'):
                    self.nazwy[row[fld]] = row

        sql = """
            select id, nazwa, nazwaalternatywna from materialy where del=0
        """

        with self.cnt_connection() as conn:
            for row in conn.raport_slownikowy(sql):
                self.nazwy[row['id']] = row['nazwaalternatywna']


        # TODO usuwać ścieżka local
