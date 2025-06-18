import mysql.connector
import re
import json


class MySQLDatasource(object):
    def __init__(self, dsn, read_write=False):
        self.dsn = dsn
        connection_params = self.connection_string_parser(self.dsn)
        self.readonly = self._is_readonly(read_write)
        self.conn = mysql.connector.connect(**connection_params)
        self.session = self.conn.start_transaction(readonly=self.readonly)

    @staticmethod
    def _is_readonly(readwrite):
        if readwrite:
            return False
        return True

    @staticmethod
    def clean_quotas(data):
        if not isinstance(data, str):
            return data
        try:
            if data[0] == '"':
                data = data[1:]
            if data[-1] == '"':
                data = data[:-1]
        except IndexError:
            return data
        return data

    @staticmethod
    def connection_string_parser(dsn):
        splited = dsn.split(' ')
        splited_2 = [param.split('=') for param in splited]
        return {param[0]: param[1] for param in splited_2}

    def cursor(self):
        return self.conn.cursor()

    def sanitize_name(self, name):
        return re.sub(r'[\W]+', '', name.lower())

    def sanitize_hstore(self, value):
        if value is None:
            return 'null'
        else:
            return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'

    def select(self, sql, params=None):
        res = []
        cur = self.cursor()
        cur.execute(sql, params)
        columns = [c[0] for c in cur.description]
        for row in cur:
            res.append(row)
        return columns, res

    def dict_select(self, sql, params=None):
        cols, rows = self.select(sql, params)
        res = []
        for row in rows:
            rres = {}
            for col, val in zip(cols, row):
                rres[col] = self.clean_quotas(val)
            res.append(rres)
        return res

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)

    def insert(self, table, values):
        fields = []
        params = []
        table = self.sanitize_name(table)
        for k, v in values.items():
            fields.append(self.sanitize_name(k))
            if isinstance(v, dict):
                params.append(json.dumps(v))
            else:
                params.append(v)
        sql = "insert into " + table + "("
        sql += ', '.join(fld for fld in fields)
        sql += ") values ("
        sql += ', '.join('%s' for fld in fields)
        sql += ")"
        self.execute(sql, params)
        self.commit()
        for row in self.dict_select(' select last_insert_id() as id;'):
            return row['id']

    def commit(self):
        self.conn.commit()

    def update(self, tabela, klucze, pola):
        if len(klucze.keys()) == 0:
            raise Exception('Brak warunku')
        warunek = []
        zmiany = []
        wartosci = []
        for k, v in pola.items():
            if k not in klucze:
                zmiany.append(k + '=%s')
                wartosci.append(v)
        for k, v in klucze.items():
            warunek.append(k + '=%s')
            wartosci.append(v)
        sql = "update " + tabela + " set " + ','.join(zmiany) + " where " + " and ".join(warunek)
        self.execute(sql, wartosci)
        self.commit()
        for row in self.dict_select(' select last_insert_id() as id;'):
            return row['id']



def test_clean_quotas():
    value1 = '"test"'
    value2 = '"test'
    value3 = 'test"'
    assert MySQLDatasource.clean_quotas(value1) == 'test'
    assert MySQLDatasource.clean_quotas(value2) == 'test'
    assert MySQLDatasource.clean_quotas(value3) == 'test'