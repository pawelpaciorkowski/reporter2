import socket
import fdb
import psycopg2
from .sql_translator import FBtoPSQLTranslator

# 2022-02-20 CZERNIA przestawiona na bazę bieżącą zawsze. stare ustawienia: "CZERNIA"	"192.168.5.105"	"Raporty"

def monkey_patch_fdb():
    """
    Funkcja b2u z fdb.fbcore zmodyfikowana tak aby w razie błędu dekodowania
    zwrócić null, a nie się wywalić
    """
    import fdb

    def b2u_patched(st, charset):
        if charset:
            try:
                return st.decode(charset)
            except UnicodeDecodeError:
                return None
        else:
            return st

    fdb.fbcore.b2u = b2u_patched


monkey_patch_fdb()


class CentrumManager(object):
    def __init__(self, config=None, adres=None, alias=None, baza=None, engine=None):
        self.adres = adres
        self.alias = alias
        self.engine = engine

    def get_connection(self):
        if self.engine == "firebird":
            return Centrum(adres=self.adres, alias=self.alias)
        if self.engine == "postgres":
            return CentrumPostgres(adres=self.adres, alias=self.alias)


class CentrumConnectionError(Exception):
    def __init__(self, msg, system, variant):
        self.msg = msg
        self.system = system
        self.variant = variant


class CentrumConnection(object):
    def __init__(self, conn, system, alias):
        self.conn = conn
        self.system = system
        self.alias = alias
        self.cur = None
        self.set_db_enine()

    def translate_sql(self, sql, sql_pg=None):
        if self.db_engine == "postgres":
            if sql_pg is None:
                sql_translator = FBtoPSQLTranslator(sql)
                return sql_translator.psql_query()
            return sql_pg
        return sql

    def set_db_enine(self):
        if "psycopg2" in str(self.conn.__class__):
            self.db_engine = "postgres"
        elif "fdb.fbcore" in str(self.conn.__class__):
            self.db_engine = "firebird"
        else:
            self.db_engine = None

    def __enter__(self):
        self.cur = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.cur.close()
            self.conn.commit()
        except:
            pass
        self.cur = None

    def raport_z_kolumnami(
        self, sql, params=None, limit=None, timeout=None, sql_pg=None
    ):
        # TODO timeout
        # TODO wersja streamująca (yieldująca) wiersze
        if self.cur is None:
            raise Exception("Tylko wewnątrz with!")
        column_names = None
        rows = []
        if params is None:
            params = ()
        new_sql = self.translate_sql(sql, sql_pg)
        self.cur.execute(new_sql, params)
        column_names = [column[0].lower() for column in self.cur.description]
        row_num = 0
        for row in self.cur:
            rows.append(list(row))
            row_num += 1
            if limit is not None and row_num == limit:
                break
        return column_names, rows

    def raport_slownikowy(self, sql, params=None, limit=None, timeout=None, sql_pg=None):
        # new_sql = self.translate_sql(sql) - raport_z_kolumnami już sobie tłumaczy sqla
        cols, rows = self.raport_z_kolumnami(sql, params=params, limit=limit, timeout=timeout, sql_pg=sql_pg)
        res = []
        for row in rows:
            row_res = {}
            for k, v in zip(cols, row):
                row_res[k] = v
            res.append(row_res)
        return res

    def raport_z_kolumnami_chunked(self, sql, params=None, chunk_size=None, sql_pg=None):
        # TODO timeout
        # TODO wersja streamująca (yieldująca) wiersze
        if self.cur is None:
            raise Exception("Tylko wewnątrz with!")
        if chunk_size is None:
            raise Exception("Podaj rozmiar chunka lub użyj funkcji bez _chunk")
        column_names = None
        if params is None:
            params = ()
        new_sql = self.translate_sql(sql, sql_pg)
        self.cur.execute(new_sql, params)
        column_names = [column[0].lower() for column in self.cur.description]
        chunk = []
        current_chunk_size = 0
        for row in self.cur:
            chunk.append(row)
            current_chunk_size += 1
            if current_chunk_size == chunk_size:
                yield column_names, chunk
                chunk = []
                current_chunk_size = 0
        if current_chunk_size > 0:
            yield column_names, chunk

    def raport_slownikowy_chunked(self, sql, params=None, chunk_size=None, sql_pg=None):
        for cols, rows in self.raport_z_kolumnami_chunked(sql, params, chunk_size, sql_pg=sql_pg):
            res = []
            for row in rows:
                row_res = {}
                for k, v in zip(cols, row):
                    row_res[k] = v
                res.append(row_res)
            yield res


class CentrumPostgres(object):
    def __init__(self, config=None, adres=None, alias=None, baza=None):
        self.dns = None
        self.pg = True
        if config is not None:
            self.config = config
            self.adres = config.adres
            self.alias = config.alias
            self.system = config.src_system
        else:
            self.adres = adres
            self.alias = alias
            self.system = None
        self.conn = None
        self.system_config = None

        self.set_dns()

    def set_dns(self):
        self.dns = f"""dbname='{self.alias}'
            user='centrum_ro' 
            password='ro' 
            host='{self.adres}' 
            port=5432
            application_name='ALAB Reporter'"""

    def ping(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = socket.create_connection((self.adres, 5432), timeout=5)
            if result is not None:
                result.close()
                return True
            return False
        except socket.timeout:
            return False
        except ConnectionRefusedError:
            return False

    def connect(self):
        if self.conn is not None:
            return
        self.conn = psycopg2.connect(self.dns)

    def get_cursor(self, for_write=False):
        if for_write:
            raise NotImplementedError()
        self.connect()
        return self.conn.cursor()

    def connection(self):
        self.connect()
        return CentrumConnection(self.conn, self.system, self.alias)

    def get_system_config(self):
        if self.system_config is None:
            cur = self.get_cursor()
            cur.execute(
                "select w.*, s.symbol as symbolsystemu, s.nazwa as nazwasystemu from wygladidostosowanie w left join systemy s on s.id=w.system where nazwakomputera='^__^__^' and nazwadrukarki='^__^__^'"
            )
            column_names = [column[0].upper() for column in cur.description]
            row = cur.fetchone()
            res = dict(zip(column_names, row))
            self.system_nazwa = res["NAZWASYSTEMU"] or ""
            self.system_symbol = res["SYMBOLSYSTEMU"] or ""
            self.system_config = {}
            for line in res["PARAMETRY"].split("\r\n"):
                if len(line) > 3 and "=" in line:
                    line = line.split("=", 1)
                    self.system_config[line[0]] = line[1]
            self.system_config["system_nazwa"] = self.system_nazwa.strip()
            self.system_config["system_symbol"] = self.system_symbol.strip()
        return self.system_config


class Centrum(object):
    def __init__(self, config=None, adres=None, alias=None, baza=None):
        self.pg = False
        if config is not None:
            self.config = config
            self.adres = config.adres
            self.alias = config.alias
            self.system = config.src_system
        else:
            self.adres = adres
            self.alias = alias
            self.system = None
        self.conn = None
        self.system_config = None

    def ping(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = socket.create_connection((self.adres, 3050), timeout=5)
            if result is not None:
                result.close()
                return True
            return False
        except socket.timeout:
            return False
        except ConnectionRefusedError:
            return False

    def connect(self):
        if self.conn is not None:
            return
        self.conn = fdb.connect(
            host=self.adres,
            database=self.alias,
            user="sysdba",
            password="MZSz2004",
            charset="WIN1250",
        )
        self.conn.default_tpb = [
            fdb.isc_tpb_read,
            fdb.isc_tpb_read_committed,
            fdb.isc_tpb_rec_version,
            fdb.isc_tpb_nowait,
        ]  # pierwsze było isc_write

    def get_cursor(self, for_write=False):
        if for_write:
            raise NotImplementedError()
        self.connect()
        return self.conn.cursor()

    def connection(self):
        self.connect()
        return CentrumConnection(self.conn, self.system, self.alias)

    def get_system_config(self):
        if self.system_config is None:
            cur = self.get_cursor()
            cur.execute(
                "select w.*, trim(s.symbol) as symbolsystemu, s.nazwa as nazwasystemu from wygladidostosowanie w left join systemy s on s.id=w.system where nazwakomputera='^__^__^' and nazwadrukarki='^__^__^'"
            )
            res = dict(cur.fetchonemap())
            self.system_nazwa = res["NAZWASYSTEMU"] or ""
            self.system_symbol = res["SYMBOLSYSTEMU"] or ""
            self.system_config = {}
            for line in res["PARAMETRY"].split("\r\n"):
                if len(line) > 3 and "=" in line:
                    line = line.split("=", 1)
                    self.system_config[line[0]] = line[1]
            self.system_config["system_nazwa"] = self.system_nazwa.strip()
            self.system_config["system_symbol"] = self.system_symbol.strip()
        return self.system_config


class CentrumWzorcowa(Centrum):
    def __init__(self):
        Centrum.__init__(self, adres="2.0.0.1", alias="Wzorcowa")
        # Centrum.__init__(self, adres="10.1.1.190", alias="Wzorcowa")
