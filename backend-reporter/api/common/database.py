import psycopg2
from psycopg2 import pool
from psycopg2.extras import DictCursor
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED, ISOLATION_LEVEL_READ_UNCOMMITTED
import contextlib
import math
import re
import json
try:
    from flask import current_app, app
except ImportError:
    current_app = app = None


class Database(object):
    def __init__(self, pool):
        self.pool = pool
        self.conn = None

    # def reconnect(self):
    #     self.conn = psycopg2.connect(self.conn_str, cursor_factory=DictCursor)
    #     self.conn.set_session(isolation_level=ISOLATION_LEVEL_READ_UNCOMMITTED, autocommit=True)
    #
    def execute(self, query, params):
        if self.conn is None:
            raise RuntimeError("Użycie poza with")
        ok = False
        cur = self.conn.cursor()
        cur.execute(query, params)
        return cur
        # try:
        #     cur = self.conn.cursor()
        # except psycopg2.InterfaceError:
        #     self.reconnect()
        #     cur = self.conn.cursor()
        # try:
        #     cur.execute(query, params)
        #     ok = True
        # finally:
        #     if not ok:
        #         self.conn.rollback()
        # return cur

    def select(self, query, params=None):
        res = []
        cur = self.execute(query, params)
        for row in cur.fetchall():
            row = dict(row)
            res.append(row)
        cur.close()
        return res

    def sanitize_name(self, name):
        return re.sub(r'[\W]+', '', name.lower())

    def select_from_api(self, table, args):
        page = args.get('page', 1)
        per_page = args.get('per_page', 10)
        offset = (page - 1) * per_page

        sql_query = "select * from %s " % table
        sql_cnt_query = "select count(*) as count from %s " % table
        sql_args = []

        # TODO: inne argumenty filtrujące

        sql_query += " limit %s offset %s"
        sql_args += [per_page, offset]

        result = self.select(sql_query, sql_args)
        total_count = self.select(sql_cnt_query, sql_args[:-2])[0]['count']

        # TODO: tu ma być grupowanie po group_id
        return {
            'page': page,
            'per_page': per_page,
            'pages': math.ceil(total_count / per_page),
            'total': total_count,
            'items': result,
        }

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
        sql += ") returning id"
        for row in self.select(sql, params):
            return row['id']

    def log_change(self, typ, obj_type, obj_id, opis=None, wartosc_przed=None, wartosc_po=None, **parametry):
        self.insert('log_zmiany', {
            'typ': typ,
            'obj_type': obj_type,
            'obj_id': obj_id,
            'opis': opis,
            'wartosc_przed': wartosc_przed,
            'wartosc_po': wartosc_po,
            'parametry': json.dumps(parametry)
        })

    def commit(self):
        pass
        # self.conn.commit()

    def select_from_api_custom(self, sql, args):
        pass  # TODO przy wyliczaniu ilości zastąpić listę pól count(*)

    def __enter__(self):
        self.conn = self.pool.getconn()
        self.conn.set_session(isolation_level=ISOLATION_LEVEL_READ_COMMITTED, autocommit=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pool.putconn(self.conn)
        self.conn = None


_connection_pool = None


def get_db():
    global _connection_pool
    if _connection_pool is None:
        from config import Config
        _connection_pool = psycopg2.pool.SimpleConnectionPool(1, 4, Config.DATABASE, cursor_factory=DictCursor)
    # TODO: pooling itp
    return Database(_connection_pool)
