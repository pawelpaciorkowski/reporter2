import os
import sqlite3
from datasources.reporter import ReporterDatasource

FILENAME = './bazy.db'
SCHEMA = """
    CREATE TABLE bazy (
        id integer primary key,
        baza varchar(255),
        nazwa varchar(255),
        system varchar(255),
        system_snr varchar(255),
        adres varchar(255),
        alias varchar(255),
        replikacja integer,
        aktywne integer,
        wewnetrzne integer,
        zewnetrzne integer,
        zewnetrzne_got integer,
        pracownia_domyslna integer,
        marcel integer,
        kolejnosc integer,
        kolejnosc_marcel integer, 
        laboratorium integer
    );
"""

if __name__ == '__main__':
    rep = ReporterDatasource()
    if os.path.exists(FILENAME):
        os.unlink(FILENAME)
    conn = sqlite3.connect(FILENAME)
    c = conn.cursor()
    c.execute(SCHEMA)

    for row in rep.dict_select("select * from laboratoria where adres_fresh is not null order by kolejnosc"):
        c.execute("""insert into bazy(baza, nazwa, system, system_snr, adres, alias, replikacja, aktywne, wewnetrzne,
                        zewnetrzne, zewnetrzne_got, pracownia_domyslna, marcel, kolejnosc, kolejnosc_marcel, laboratorium)
                    values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", [
            "%s:%s" % (row['adres'], row['baza']),
            row['nazwa'],
            row['symbol'],
            row['symbol_snr'],
            row['adres'],
            row['baza'],
            1 if row['replikacja'] else 0,
            1 if row['aktywne'] else 0,
            1 if row['wewnetrzne'] else 0,
            1 if row['zewnetrzne'] else 0,
            1 if row['zewnetrzne_got'] else 0,
            1 if row['pracownia_domyslna'] else 0,
            1 if row['marcel'] else 0,
            row['kolejnosc'],
            row['kolejnosc_marcel'],
            1 if row['laboratorium'] else 0,
        ])

    conn.commit()
    conn.close()