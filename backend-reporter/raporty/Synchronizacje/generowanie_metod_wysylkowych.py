from typing import Optional

from outlib.synchdat import SynchDat, DatCol, DatColHeader, DatTable


class GenerowanieMetodWysylkowych:
    def __init__(self):
        self.nazwy_metod = {}
        self.aparaty_metod = {}
        self.metody_badan = []
        self.powiazania_metod = []
        self.byly_dni_tygodnia = False

    def dodaj_metode_wysylkowa(self, symbol: str, nazwa: str, aparat: Optional[str]):
        if symbol in self.nazwy_metod:
            raise ValueError("Powtórzona metoda", symbol)
        if aparat is None:
            aparat = 'X-WYSYL'
        self.aparaty_metod[symbol] = aparat
        self.nazwy_metod[symbol] = nazwa

    def dodaj_metode_dla_badania(self, badanie: str, metoda: str):
        if (metoda, badanie) in self.metody_badan:
            return
        self.metody_badan.append((metoda, badanie))

    def dodaj_powiazanie_metody(self, badanie: str, metoda: str,
                                system: Optional[str] = None,
                                platnik: Optional[str] = None, oddzial: Optional[str] = None,
                                dni_tygodnia: Optional[str] = None,
                                typ_zlecenia: Optional[str] = None):
        # if metoda not in self.nazwy_metod:
            # raise ValueError("Nieznana matoda", metoda)
        if metoda in self.nazwy_metod:
            self.dodaj_metode_dla_badania(badanie, metoda)
        self.powiazania_metod.append(
            (badanie, metoda, system, platnik, oddzial, dni_tygodnia, typ_zlecenia)
        )
        if dni_tygodnia is not None:
            self.byly_dni_tygodnia = True

    def render_dat(self) -> bytes:
        dat = SynchDat()
        table_metody = DatTable(name='Metody', header=DatColHeader([
            DatCol('Pochodna', is_key=True, hidden=True),
            DatCol('Symbol', is_key=True),
            DatCol('Badanie', foreign_table='Badania', is_key=True),
            DatCol('Nazwa'),
            DatCol('Kod'),
            DatCol('Pracownia', foreign_table='Pracownie'),
            DatCol('Aparat', foreign_table='Aparaty'),
            DatCol('Koszt'),
            DatCol('Punkty'),
            DatCol('BadanieZrodlowe', foreign_table='Badania', negative_cond='', is_key=True),
            DatCol('MetodaZrodlowa', foreign_table='Metody',
                   remote_reference=DatCol('Badanie', foreign_table='Badania')),
            DatCol('Serwis'),
            DatCol('NiePrzelaczac'),
            DatCol('Grupa')
        ]))
        table_parametry_w_metodach = DatTable(name='ParametryWMetodach', header=DatColHeader([
            DatCol('Metoda', foreign_table='Metody', remote_reference=DatCol(
                'Badanie', foreign_table='Badania'
            ), is_key=True),
            DatCol('Parametr', foreign_table='Parametry', remote_reference=DatCol(
                'Metoda', foreign_table='Metody', remote_reference=DatCol(
                    'Badanie', foreign_table='Badania'
                )
            ), is_key=True),
            DatCol('Dorejestrowywany'),
            DatCol('Kolejnosc'),
            DatCol('Format'),
        ]))
        table_powiazania_metod = DatTable(name='PowiazaniaMetod', header=DatColHeader([
            DatCol('Badanie', foreign_table='Badania', is_key=True),
            DatCol('DowolnyTypZlecenia', is_key=True),
            DatCol('TypZlecenia', foreign_table='TypyZlecen', is_key=True),
            DatCol('DowolnaRejestracja', is_key=True),
            DatCol('Rejestracja', foreign_table='Rejestracje', is_key=True),
            DatCol('DowolnySystem', is_key=True),
            DatCol('System', foreign_table='Systemy', is_key=True),
            DatCol('Metoda', foreign_table='Metody',
                   remote_reference=DatCol('Badanie', foreign_table='Badania')),
            DatCol('InnaPracownia'),
            DatCol('Pracownia', foreign_table='Pracownie'),
            DatCol('DoRozliczen', is_key=True),
            DatCol('DowolnyMaterial', is_key=True),
            DatCol('Material', foreign_table='Materialy', is_key=True),
            DatCol('DowolnyOddzial', is_key=True),
            DatCol('Oddzial', foreign_table='Oddzialy', is_key=True),
            DatCol('DowolnyPlatnik', is_key=True),
            DatCol('Platnik', foreign_table='Platnicy', is_key=True),
            DatCol('DniTygodnia', is_key=True),
        ]))
        # TODO: dodać jeśli dni tygodnia
        for metoda, badanie in self.metody_badan:
            table_metody.add_row({
                'pochodna': 1, 'symbol': metoda, 'Badanie': badanie,
                'Nazwa': self.nazwy_metod[metoda],
                'Pracownia': metoda, 'aparat': self.aparaty_metod[metoda],
                'BadanieZrodlowe': 'WYSYLKA', 'MetodaZrodlowa': ('WYSYLKA', 'WYSYLKA'), 'NiePrzelaczac': 0,
            })
            table_parametry_w_metodach.add_row([
                (metoda, badanie), ('WYSYLKA', ('WYSYLKA', 'WYSYLKA')), 0, 0, None
            ])
        for (badanie, metoda, system, platnik, oddzial, dni_tygodnia, typ_zlecenia) in self.powiazania_metod:
            table_powiazania_metod.add_row({
                'Badanie': badanie, 'Metoda': (metoda, badanie),
                'DowolnyTypZlecenia': 0 if typ_zlecenia is not None else 1,
                'DowolnaRejestracja': 1,
                'DowolnySystem': 0 if system is not None else 1, 'System': system,
                'DowolnyPlatnik': 0 if platnik is not None else 1, 'Platnik': platnik,
                'DowolnyOddzial': 0 if oddzial is not None else 1, 'Oddzial': oddzial,
                'InnaPracownia': 0, 'DoRozliczen': 0, 'DowolnyMaterial': 1,
                'DniTygodnia': dni_tygodnia, 'TypZlecenia': typ_zlecenia,
            })
        dat.add_table(table_metody)
        dat.add_table(table_parametry_w_metodach)
        dat.add_table(table_powiazania_metod)
        return dat.render_encoded()
