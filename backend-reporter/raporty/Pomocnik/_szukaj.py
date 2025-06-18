import requests
from config import Config
from datasources.mop import MopDatasource


def _url(path):
    return Config.MS_STRUKTURA_URL.strip('/') + '/' + path.lstrip('/')


def search(query, index, only_tables=None, offset=None, limit=None):
    if offset is None:
        offset = 0
    if limit is None:
        limit = 20
    url = _url('/indexes/%s/search' % index)
    query = ' '.join([word for word in query.split(' ') if word.lower().split() not in ('', 'punkt', 'pobrań', 'pobran', 'alab', 'pp', 'ppalab', 'ul.', 'al.', 'pl.')])
    params = {
        'q': query, 'filter': [],
        'offset': offset, 'limit': limit,
    }
    if only_tables is not None and len(only_tables) > 0:
        params['filter'].append(["table=%s" % tab for tab in only_tables])
    resp = requests.request('POST', url, json=params, headers={
        "Authorization": "Bearer %s" % Config.MS_STRUKTURA_KEY
    })
    return resp.json()


def uogolniaj_query_badania(q):
    q1 = q
    q2 = q1.lower().replace('-', ' ').replace('.', ' ').replace('icd9', '').replace('icd 9', '')
    q3 = q2
    while len(q3) > 0 and q3[0] in '0123456789 ':
        q3 = q3[1:]


    return [q1, q2, q3]


def szukaj_badania_w_labie(lab):
    dane_lab = {}

    def szukaj_badania(query, required_fields):
        hits = None
        print('SZUKAJ BADANIA', lab, query, required_fields)
        for q in uogolniaj_query_badania(query):
            res = search(q, 'badania', limit=10)
            if res is not None and 'hits' in res and len(res['hits']) > 0:
                hits = res['hits']
                break
        if hits is None:
            return None
        hit = None
        for sr in hits:
            if sr.get('service_type') == 'laboratoryTest':
                hit = sr
                break
        if hit is None:
            return None
        symbol = hit['symbol']
        res = {
            'symbol': symbol, 'nazwa': hit['name_pl'],
        }
        if symbol in dane_lab:
            for k, v in dane_lab[symbol]:
                res[k] = v
        return res

    return szukaj_badania


DANE_PUNKTOW = None

def dane_skarbiec(dane, path):
    if isinstance(path, str):
        return dane_skarbiec(dane, path.split('.'))
    if len(path) == 0:
        return dane
    if isinstance(dane, dict) and path[0] in dane and dane[path[0]] is not None:
        return dane_skarbiec(dane[path[0]], path[1:])
    return None

def wszystkie_dane_punktu(dane, required_fields):
    global DANE_PUNKTOW
    if DANE_PUNKTOW is None:
        DANE_PUNKTOW = {}
        mop = MopDatasource()
        dane_punkty = mop.get_cached_data('api/v2/collection-point')
        if dane_punkty is None:
            dane_punkty = mop.get_cached_data('api/v2/collection-point')
        for punkt in dane_punkty:
            symbol = punkt['marcel']
            if symbol is None:
                continue
            if symbol in DANE_PUNKTOW:
                if DANE_PUNKTOW[symbol]['isActive'] and not punkt['isActive']:
                    continue
            DANE_PUNKTOW[symbol] = punkt
    if dane['symbol'] in DANE_PUNKTOW:
        punkt = DANE_PUNKTOW[dane['symbol']]
        if punkt.get('user') is not None:
            dane['koordynator'] = '%s %s' % (punkt['user'].get('name') or '', punkt['user'].get('surname') or '')
            dane['koordynator_email'] = punkt['user'].get('email')
        if punkt.get('user2') is not None:
            dane['dyrektor'] = '%s %s' % (punkt['user2'].get('name') or '', punkt['user2'].get('surname') or '')
            dane['dyrektor_email'] = punkt['user2'].get('email')
        dane['nazwa'] = punkt['name']
        dane['miejscowosc'] = dane_skarbiec(punkt, 'city.name')
        dane['kodpocztowy'] = dane_skarbiec(punkt, 'postalCode')
        dane['ulica'] = dane_skarbiec(punkt, 'street')
        dane['lab_symbol'] = dane_skarbiec(punkt, 'laboratory.symbol')
        dane['region'] = dane_skarbiec(punkt, 'laboratory.region.name')
        dane['mpk'] = dane_skarbiec(punkt, 'mpk')
        dane['klasyfikacja'] = dane_skarbiec(punkt, 'collectionPointClassification.name')
        dane['partner'] = dane_skarbiec(punkt, 'collectionPointPartner.name')
        dane['lokalizacja'] = dane_skarbiec(punkt, 'collectionPointLocation.name')
        dane['typ'] = dane_skarbiec(punkt, 'collectionPointType.name')
        dane['email'] = dane_skarbiec(punkt, 'email')
        dane['telefony'] = ', '.join(phone.get('number') or '' for phone in (punkt.get('phones') or []))
        dane['aktywny'] = 'Aktywny' if punkt.get('isActive') else 'Nieaktywyny'
    return dane


def szukaj_punktu(query, required_fields):
    res = search(query, 'podmioty', only_tables=['punkty'], limit=1)
    if res is None or 'hits' not in res or len(res['hits']) == 0:
        return None
    return wszystkie_dane_punktu(res['hits'][0], required_fields)

def szukaj_punktu_nieaktywne(query, required_fields):
    res = search(query, 'podmioty', only_tables=['punktywszystkie'], limit=1)
    if res is None or 'hits' not in res or len(res['hits']) == 0:
        return None
    return wszystkie_dane_punktu(res['hits'][0], required_fields)
