from .postgres import PostgresDatasource


class IccDatasource(PostgresDatasource):
    def __init__(self, read_write=False):
        PostgresDatasource.__init__(self, "dbname='ic_centrala' user='postgres' host='2.0.1.101' port=5432",
                                    read_write=read_write)


class IckDatasource(PostgresDatasource):
    def __init__(self, read_write=False):
        PostgresDatasource.__init__(self, "dbname='ic_komunikator' user='postgres' host='2.0.1.101' port=5432",
                                    read_write=read_write)

    def select(self, query, params=None):
        cols, rows = PostgresDatasource.select(self, query, params)
        rrows = []
        for row in rows:
            rrow = []
            for val in row:
                if isinstance(val, str):
                    try:
                        val = val.encode('latin2').decode('utf-8')
                    except:
                        pass
                rrow.append(val)
            rrows.append(rrow)
        return cols, rrows

    def _recode_params(self, params):
        def recode_value(v):
            if isinstance(v, str):
                return v.encode('utf-8').decode('latin2')
            else:
                return v

        if params is None:
            return None
        if isinstance(params, list):
            res = []
            for v in params:
                res.append(recode_value(v))
            return res
        elif isinstance(params, dict):
            res = {}
            for k, v in params.items():
                res[k] = recode_value(v)
            return res

    def insert(self, table, values):
        return PostgresDatasource.insert(self, table, self._recode_params(values))
