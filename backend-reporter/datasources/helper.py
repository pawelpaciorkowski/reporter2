import os
import sqlite3
from config import Config


class HelperDb:
    def __init__(self, fn):
        self.fn = os.path.join(Config.HELPER_DATABASES, fn)
        self.conn = sqlite3.connect(self.fn)

    def select(self, sql, params=None):
        if params is None:
            params = []
        cur = self.conn.cursor()
        cur.execute(sql, params)
        cols = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        return cols, rows

    def dict_select(self, sql, params=None):
        cols, rows = self.select(sql, params)
        res = []
        for row in rows:
            rres = {}
            for (fld, val) in zip(cols, row):
                rres[fld] = val
            res.append(rres)
        return res
