import requests
from .postgres import PostgresDatasource
from config import Config


class GJWAPI:
    def __init__(self):
        self.token = None
        self._login()

    def get(self, url):
        full_url = Config.GJW_URL + url
        print(full_url)
        req = requests.get(url=full_url, headers=self._headers())
        if req.status_code == 200:
            return req.json()
        else:
            raise Exception(req.text)

    def post(self, url, data):
        full_url = Config.GJW_URL + url
        req = requests.post(url=full_url, json=data, headers=self._headers())
        return req.json()

    def _login(self):
        res = self.post('auth/login', Config.GJW_CREDENTIALS)
        if 'token' in res:
            self.token = res['token']

    def _headers(self):
        res = {}
        if self.token is not None:
            res['Authorization'] = 'Bearer %s' % self.token
        return res


class GJW(PostgresDatasource):
    def __init__(self, read_write=False):
        PostgresDatasource.__init__(self, Config.DATABASE_GJW, read_write=read_write)
