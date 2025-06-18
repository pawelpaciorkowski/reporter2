import sqlalchemy as sa


class MSSQLDatasource(object):
    def __init__(self, dsn):
        self.dsn = dsn
        self.engine = sa.create_engine(dsn)

    def execute(self, sql, params=None):
        if params is None:
            params = []
        return self.engine.execute(sql, *params)

    def select(self, sql, params=None):
        rows = []
        executed = self.execute(sql, params)
        cols = list(executed.keys())
        for row in executed:
            rows.append(list(row))
        return cols, rows

    def dict_select(self, sql, params=None):
        cols, rows = self.select(sql, params)
        res = []
        for row in rows:
            res.append(dict(zip(cols, row)))
        return res