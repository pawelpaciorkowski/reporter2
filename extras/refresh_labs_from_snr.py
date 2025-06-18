import psycopg2
import requests
import xml.etree.cElementTree as etree
import database
db = database.db



def flat_xml_to_dict(row):
    res = {}
    for elem in list(row):
        res[elem.tag] = elem.text
    return res


def remove_add_lists(old_l, new_l):
    rem_l = []
    add_l = []
    for elem in old_l:
        if elem not in new_l:
            rem_l.append(elem)
    for elem in new_l:
        if elem not in old_l:
            add_l.append(elem)
    return rem_l, add_l


res = requests.post('http://2.0.4.101:8080/MarcelWebServices/jsonwsp', json={
    'methodname': 'Datasource',
    'args': {
        'client': {'id': 'rozliczeniowa', 'key': 'rozliczeniowa', 'info': '<xxx />'},
        'datasource': 'Laboratoria',
        'service': 'select',
        'params': '',
        'cacheMD5': '',
    }
})

res = res.json()
res = res['result']['result']

xml = etree.fromstring(res)

laby_snr = {}
laby_istniejace = {}

for row in list(xml):
    lab = flat_xml_to_dict(row)
    laby_snr[lab['symbol']] = lab

for row in db.dict_select("select * from laboratoria"):
    laby_istniejace[row['symbol']] = row

usun, dodaj = remove_add_lists(laby_istniejace.keys(), laby_snr.keys())
for symbol in usun:
    pass  # TODO
for symbol in dodaj:
    lab = laby_snr[symbol]
    nid = db.insert('laboratoria', {
        'symbol': symbol,
        'symbol_snr': symbol,
        'nazwa': lab['nazwa'],
        'adres': lab['vpn'],
        'adres_fresh': lab['vpn'],
        'baza': 'Centrum',
        'baza_fresh': 'Centrum',
        'centrum_kosztow': lab.get('centrumrozliczeniowe'),
    })
    print(nid)
db.commit()

# TODO: porównywanie zmian
