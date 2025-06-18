import sqlite3
import database
db = database.db


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

db_bazy = sqlite3.connect('./bazy.db')
db_bazy.row_factory = dict_factory
cur_bazy = db_bazy.cursor()

cur_bazy.execute("select * from bazy where adres!='192.168.5.100';")
for row in cur_bazy.fetchall():
    print(row)
    db.execute("""update laboratoria
        set aktywne=%s, wewnetrzne=%s, zewnetrzne=%s, zewnetrzne_got=%s,
        replikacja=%s, pracownia_domyslna=%s, laboratorium=%s, marcel=%s,
        kolejnosc=%s, kolejnosc_marcel=%s where symbol=%s""", [
        row['aktywne']==1, row['wewnetrzne']==1, row['zewnetrzne']==1, row['zewnetrzne_got']==1,
        row['replikacja']==1, row['pracownia_domyslna']==1, row['laboratorium']==1, row['marcel']==1,
        row['kolejnosc'], row['kolejnosc_marcel'], row['system']
    ])
db.commit()