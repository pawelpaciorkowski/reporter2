from helpers import prepare_for_json
from .postgres import PostgresDatasource
from config import Config
import json

class ReporterDatasource(PostgresDatasource):
    def __init__(self, read_write=False):
        self.read_write = read_write
        cfg = Config()
        PostgresDatasource.__init__(self, cfg.DATABASE, read_write=read_write)

    def select_with_names_and_types(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        columns = [c.name for c in cur.description]
        types = [c.type_code for c in cur.description]
        rows = cur.fetchall()
        return columns, types, rows

    def get_regular_and_json_columns(self, table_name):
        regular = []
        json = None
        for cn, ct in self.get_table_columns(table_name).items():
            if ct == 'json':
                json = cn
            else:
                regular.append(cn)
        return regular, json

    def select_and_unwrap(self, sql, params=None):
        res = []
        columns, types, rows = self.select_with_names_and_types(sql, params)
        for row in rows:
            res_row = {}
            for cn, fld, tc in zip(columns, row, types):
                # print(fld, tc)
                if tc == 114:
                    for k, v in fld.items():
                        if k not in res_row:
                            res_row[k] = v
                else:
                    res_row[cn] = fld
            res.append(res_row)
        return res

    def save_change_log(self, user_login, obj_type, obj_id, oper, desc, value_before, value_after, params=None, commit=True):
        """
        select * from log_zmiany
        -- obj_type, obj_id, typ, opis, wartosc_przed, wartosc_po, parametry, changing_party
        """
        self.insert('log_zmiany', {
            'changing_party': user_login,
            'obj_type': obj_type,
            'obj_id': obj_id,
            'typ': oper,
            'opis': desc,
            'wartosc_przed': json.dumps(prepare_for_json(value_before)),
            'wartosc_po': json.dumps(prepare_for_json(value_after)),
            'parametry': json.dumps(prepare_for_json(params)),

        })
        if commit:
            self.commit()

    def insert_with_log(self, user_login, table, values, desc=None, oper=None):
        if oper is None:
            oper = 'INSERT'
        cols = self.get_table_columns(table)
        nvalues = {}
        jvalues = {}
        for k, v in values.items():
            if k in cols and cols[k] not in ['json']:
                nvalues[k] = v
            else:
                jvalues[k] = v
        if len(list(jvalues.keys())) > 0:
            for cn, ct in cols.items():
                if ct in ['json']:
                    nvalues[cn] = json.dumps(prepare_for_json(jvalues))
                    break
        res = self.insert(table, nvalues)
        self.save_change_log(user_login, table, res, oper, desc, None, nvalues, commit=False)
        self.commit()
        return res

    def update_with_log(self, user_login, table, id, values, desc=None, oper=None):
        if oper is None:
            oper = 'UPDATE'
        columns, types, rows = self.select_with_names_and_types("select * from %s where id=%%s" % table, [id])
        if len(rows) == 0:
            raise ValueError("Not found")
        old_values = rows[0]
        normal_cols = []
        json_cols = []
        json_fields = {}
        for i, t in enumerate(types):
            if t == 114:
                json_cols.append(columns[i])
                for k, v in old_values[i].items():
                    json_fields[k] = columns[i]
            else:
                normal_cols.append(columns[i])
        nvalues = {}
        log_old_values = {}
        log_new_values = {}
        for k, v in values.items():
            log_new_values[k] = v
            is_json = k not in normal_cols
            if is_json:
                json_col = None
                if k in json_fields:
                    json_col = json_fields[k]
                else:
                    json_col = json_cols[0]
                if json_col not in nvalues:
                    for i, cn in enumerate(columns):
                        if cn == json_col:
                            nvalues[json_col] = old_values[i]
                            break
                log_old_values[k] = nvalues[json_col].get(k)
                nvalues[json_col][k] = v
            else:
                for i, cn in enumerate(columns):
                    if cn == k:
                        log_old_values[k] = old_values[i]
                nvalues[k] = v
        sql = "update %s set " % table
        fields = []
        params = []
        for k, v in nvalues.items():
            fields.append(k)
            if isinstance(v, dict):
                params.append(json.dumps(prepare_for_json(v)))
            else:
                params.append(v)
        sql += ", ".join("%s=%%s" % cn for cn in fields)
        sql += " where id=%s"
        params.append(id)
        self.execute(sql, params)
        self.save_change_log(user_login, table, id, oper, desc, log_old_values, log_new_values, commit=False)
        self.commit()

    def delete_with_log(self, user_login, table, id, desc=None, oper=None):
        if oper is None:
            oper = 'DELETE'
        self.execute("update %s set del=true where id=%%s" % table, [id])
        self.save_change_log(user_login, table, id, oper, desc, None, None, commit=False)
        self.commit()

    def undelete_with_log(self, user_login, table, id, desc=None, oper=None):
        if oper is None:
            oper = 'UNDELETE'
        self.execute("update %s set del=false where id=%%s" % table, [id])
        self.save_change_log(user_login, table, id, oper, desc, None, None, commit=False)
        self.commit()

    def get_log_for(self, obj_type, obj_id):
        return self.dict_select("""select typ, opis, wartosc_przed, wartosc_po, parametry, ts, changing_party
                                    from log_zmiany where obj_type=%s and obj_id=%s""", [obj_type, obj_id])


class ReporterExtraDatasource(PostgresDatasource):
    def __init__(self, read_write=False):
        try:
            dsn = Config.DATABASE_EXTRA
        except:
            dsn = Config.DATABASE.replace('dbname=reporter', 'dbname=reporter_extra')
        PostgresDatasource.__init__(self, dsn=dsn, read_write=read_write)
