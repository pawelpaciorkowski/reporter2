import aiohttp
from config import Config
from helpers import empty


class MeiliSearch:
    index_name = None

    def __init__(self):
        self.url = Config.MS_STRUKTURA_URL
        self.key = Config.MS_STRUKTURA_KEY

    async def search(self, query, only_tables=None, offset=None, limit=None):
        if offset is None:
            offset = 0
        if limit is None:
            limit = 20
        url = self._url('/indexes/%s/search' % self.index_name)
        params = {
            'q': query, 'filter': [],
            'offset': offset, 'limit': limit,
        }
        if only_tables is not None and len(only_tables) > 0:
            params['filter'].append(["table=%s" % tab for tab in only_tables])
        async with aiohttp.request('POST', url, json=params, headers={
            "Authorization": "Bearer %s" % self.key
        }) as request:
            resp = await request.json()
            return resp

    def _url(self, path):
        return self.url.strip('/') + '/' + path.lstrip('/')


class PodmiotSearch(MeiliSearch):
    index_name = 'podmioty'


class BadanieSearch(MeiliSearch):
    index_name = 'badania'


async def search_pl(query):
    ps = PodmiotSearch()
    res = []
    results = await ps.search(query, only_tables=['platnicy'], limit=15)
    for hit in results['hits']:
        helper = []
        if not empty(hit.get('umowa')):
            helper.append('umowa: %s' % hit['umowa'])
        if not empty(hit.get('nip')):
            helper.append('nip: %s' % hit['nip'])
        if hit.get('symbole') is not None:
            symbole = hit['symbole'].split(' ')
            if len(symbole) > 3:
                helper.append(' '.join(symbole) + '...')
            else:
                helper.append(' '.join(symbole))
        res.append({
            'title': hit['nazwa'],
            'helper': ', '.join(helper),
            'url': '/raporty/info/oneshot:1platnicy?id=' + hit['id']
        })
    return res


async def search_zl(query):
    ps = PodmiotSearch()
    res = []
    results = await ps.search(query, only_tables=['zleceniodawcy'], limit=15)
    for hit in results['hits']:
        helper = []
        if not empty(hit.get('miejscowosc')) and hit['miejscowosc'] not in hit['nazwa']:
            helper.append(hit['miejscowosc'])
        if hit.get('symbole') is not None:
            symbole = hit['symbole'].split(' ')
            if len(symbole) > 3:
                helper.append(' '.join(symbole) + '...')
            else:
                helper.append(' '.join(symbole))
        res.append({
            'title': hit['nazwa'],
            'helper': ', '.join(helper),
            'url': '/raporty/info/oneshot:2zleceniodawcy?id=' + hit['id']
        })
    return res


async def search_lab(query):
    ps = PodmiotSearch()
    res = []
    results = await ps.search(query, only_tables=['laboratoria'], limit=15)
    for hit in results['hits']:
        helper = [hit.get('symbol')]
        res.append({
            'title': hit['nazwa'],
            'helper': ', '.join(helper),
            'url': '/raporty/info/oneshot:0laboratoria?symbol=' + hit['symbol']
        })
    return res


async def search_pp(query):
    ps = PodmiotSearch()
    res = []
    results = await ps.search(query, only_tables=['punkty'], limit=15)
    for hit in results['hits']:
        helper = []
        if not empty(hit.get('symbol')):
            helper.append(hit['symbol'])
        symbole = hit['symbole'].split(' ')
        if symbole[-1] not in helper:
            helper.append(symbole[-1])
        res.append({
            'title': hit['nazwa'],
            'helper': ', '.join(helper),
            'url': '/raporty/info/oneshot:3punkty?symbol=' + hit['symbol']
        })
    return res


async def search_bad(query):
    bs = BadanieSearch()
    res = []
    results = await bs.search(query)
    for hit in results['hits']:
        helper = [hit['symbol']]
        if hit.get('service_type') == 'registrationBundle':
            helper.append('pakiet do rejestracji')
        elif hit.get('service_type') == 'marketingBundle':
            helper.append('pakiet marketingowy')
        res.append({
            'title': hit['name_pl'],
            'helper': ', '.join(helper),
            'url': '/raporty/info/oneshot:4badania?symbol=' + hit['symbol']
        })
    return res
