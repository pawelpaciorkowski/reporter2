import config
from tasks.db import redis_conn
import requests
import json
import jwt
import time


class MopDatasource:
    def __init__(self):
        cfg = config.Config()
        self.url = cfg.MOP_URL
        self.username = cfg.MOP_CREDENTIALS[0]
        self.password = cfg.MOP_CREDENTIALS[1]
        try:
            self.token = redis_conn.get('mop:token').decode()
        except:
            self.token = None
        if not self.login():
            raise IOError('Brak połączenia z serwisem MoP')

    def headers(self):
        res = {'Accept': 'application/json'}
        if self.token is not None:
            res['Authorization'] = 'bearer %s' % self.token
        return res

    def post(self, url, data):
        full_url = self.url + url
        resp = requests.post(full_url, json=data, headers=self.headers())
        return resp.json()

    def get(self, url):
        full_url = self.url + url
        resp = requests.get(full_url, headers=self.headers(), timeout=120)
        return resp.json()

    def login(self):
        if self.token is not None:
            try:
                dec = jwt.decode(self.token, verify=False)
                if dec['exp'] - 60 < time.time():
                    self.token = None
            except:
                self.token = None
        if self.token is None:
            res = self.post('api/login_check', {
                'username': self.username,
                'password': self.password
            })
            # print(res)
            if 'token' in res:
                self.token = res['token']
                redis_conn.set('mop:token', self.token)
                return True
            else:
                return False
        else:
            return True

    def get_data(self, endpoint):
        return self.get(endpoint)

    def get_cached_data(self, endpoint):
        redis_key = 'mop:cached:%s' % endpoint
        res = redis_conn.get(redis_key)
        if res is not None:
            res = json.loads(res.decode())
        else:
            mop_res = self.get_data(endpoint)
            redis_conn.set(redis_key, json.dumps(mop_res), ex=3600)
        return res
