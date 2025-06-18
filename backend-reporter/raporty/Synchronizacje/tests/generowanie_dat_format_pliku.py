import os
from outlib.synchdat import SynchDat, DatCol, DatColHeader, DatTable

HEADER_ONLY= """*Symbol
*Badanie@Badania
Nazwa
Kod
Pracownia@Pracownie
Aparat@Aparaty
Koszt
Punkty
*BadanieZrodlowe@Badania-
MetodaZrodlowa@Metody&Metody.Badanie@Badania
Serwis
NiePrzelaczac
Grupa"""

def test_table_header():
    hdr = DatColHeader([
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
    ])
    assert hdr.render() == HEADER_ONLY

def test_pelny_dat():
    with open(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'testowy_dat_metody_wysylkowe.dat'
    ), 'rb') as f:
        target_content = f.read().strip()
    dat = SynchDat()
    dat.add_table(DatTable(name="Metody", header=DatColHeader([
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
    ]), data=[
        {
            'pochodna': 1, 'symbol': 'X-TARWS', 'Badanie': 'AN-ACIP',
            'Nazwa': 'Wysyłka do Tarnobrzegu - Szpital Wojewódzki - ALAB',
            'Pracownia': 'X-TARWS', 'aparat': 'X-WYSYL',
            'BadanieZrodlowe': 'WYSYLKA', 'MetodaZrodlowa': ('WYSYLKA', 'WYSYLKA'), 'NiePrzelaczac': 0,
        },
        {
            'pochodna': 1, 'symbol': 'X-TARWS', 'Badanie': 'AN-ACIR',
            'Nazwa': 'Wysyłka do Tarnobrzegu - Szpital Wojewódzki - ALAB',
            'Pracownia': 'X-TARWS', 'aparat': 'X-WYSYL',
            'BadanieZrodlowe': 'WYSYLKA', 'MetodaZrodlowa': ('WYSYLKA', 'WYSYLKA'), 'NiePrzelaczac': 0,
        },
    ]))

    dat.add_table(DatTable(name='ParametryWMetodach', header=DatColHeader([
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
    ]), data_rows=[
        [('X-TARWS', 'AN-ACIP'), ('WYSYLKA', ('WYSYLKA', 'WYSYLKA')), 0, 0, None],
        [('X-TARWS', 'AN-ACIR'), ('WYSYLKA', ('WYSYLKA', 'WYSYLKA')), 0, 0, None],
    ]))

    dat.add_table(DatTable(name='PowiazaniaMetod', header=DatColHeader([
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
    ]), data=[
        { 'badanie': 'AN-ACIP', 'DowolnyTypZlecenia': 1, 'DowolnaRejestracja': 1, 'DowolnySystem': 0,
          'system': 'CHELM', 'metoda': ('X-TARWS', 'AN-ACIP'), 'InnaPracownia': 0, 'DoRozliczen': 0,
          'DowolnyMaterial': 1, 'DowolnyOddzial': 1, 'DowolnyPlatnik': 1},
        {'badanie': 'AN-ACIR', 'DowolnyTypZlecenia': 1, 'DowolnaRejestracja': 1, 'DowolnySystem': 0,
         'system': 'CHELM', 'metoda': ('X-TARWS', 'AN-ACIR'), 'InnaPracownia': 0, 'DoRozliczen': 0,
         'DowolnyMaterial': 1, 'DowolnyOddzial': 1, 'DowolnyPlatnik': 1},
    ]))

    assert dat.render_encoded().decode('cp1250').strip() == target_content.decode('cp1250')
