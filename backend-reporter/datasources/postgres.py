import psycopg2
import re
import json

INSERT_CHUNK_SIZE = 100


class PostgresDatasource(object):
    def __init__(self, dsn, read_write=False):
        self.dsn = dsn
        self.read_write = read_write
        self.table_columns = {}
        self.conn = psycopg2.connect(dsn)

    def cursor(self):
        return self.conn.cursor()

    def select(self, sql, params=None):
        res = []
        cur = self.cursor()
        cur.execute(sql, params)
        columns = [c.name for c in cur.description]
        for row in cur.fetchall():
            res.append(row)
        return columns, res

    def preview_query(self, sql, params=None) -> str:
        cur = self.cursor()
        return str(cur.mogrify(sql, params))

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)

    def dict_select(self, sql, params=None):
        cols, rows = self.select(sql, params)
        res = []
        for row in rows:
            rres = {}
            for col, val in zip(cols, row):
                rres[col] = val
            res.append(rres)
        return res

    def remove_columns(self, inp, *cols_to_remove):
        in_cols, in_rows = inp
        cols = []
        rows = []
        copy_cols = []
        for col in in_cols:
            if col not in cols_to_remove:
                cols.append(col)
                copy_cols.append(True)
            else:
                copy_cols.append(False)
        for in_row in in_rows:
            row = []
            for i, val in enumerate(in_row):
                if copy_cols[i]:
                    row.append(val)
            rows.append(row)
        return cols, rows

    def get_table_columns(self, table):
        if table not in self.table_columns:
            cols, rows = self.select("""select
              a.attname,
              pg_catalog.format_type(a.atttypid, a.atttypmod)
            from pg_catalog.pg_attribute a
            where
              a.attnum > 0
              and not a.attisdropped
              and a.attrelid = (
                select c.oid
                from pg_catalog.pg_class c
                left join pg_catalog.pg_namespace n on n.oid = c.relnamespace
                where c.relname = %s
                  and pg_catalog.pg_table_is_visible(c.oid)
              )""", [table])
            res = {}
            for row in rows:
                res[row[0]] = row[1]
                self.table_columns[table] = res
        return self.table_columns.get(table)

    def sanitize_name(self, name):
        return re.sub(r'[\W]+', '', name.lower())

    def sanitize_hstore(self, value):
        if value is None:
            return 'null'
        else:
            return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'

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
        for row in self.dict_select(sql, params):
            return row['id']

    def multi_insert(self, table, values_list):
        def divide_chunks(data, chunk_size=64):
            chunks = []
            chunk = []
            for elem in data:
                if len(chunk) == chunk_size:
                    chunks.append(chunk)
                    chunk = []
                chunk.append(elem)
            if (len(chunk)) > 0:
                chunks.append(chunk)
            return chunks

        if len(values_list) == 0:
            return
        if len(values_list) > INSERT_CHUNK_SIZE:
            for chunk in divide_chunks(values_list, INSERT_CHUNK_SIZE):
                self.multi_insert(table, chunk)
            return
        fields = []
        params = []
        table = self.sanitize_name(table)
        for values in values_list:
            for k, v in values.items():
                fld_name = self.sanitize_name(k)
                if fld_name not in fields:
                    fields.append(fld_name)
        for values in values_list:
            params += [values.get(fld_name) for fld_name in fields]
        sql_sub_values = "(" + ', '.join('%s' for fld in fields) + ")"
        sql = "insert into " + table + "("
        sql += ', '.join(fld for fld in fields)
        sql += ") values "
        sql += ', '.join(sql_sub_values for _ in values_list)
        self.execute(sql, params)

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

    def multi_update(self, tabela, wiersze):
        # TODO: zoptymalizować żeby szło jednym zapytaniem
        for (klucze, pola) in wiersze:
            self.update(tabela, klucze, pola)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()
