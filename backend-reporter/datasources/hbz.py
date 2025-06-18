from sqlalchemy import create_engine
from config import Config


class HBZ:
    def __init__(self):
        self.engine = create_engine(Config.HBZ_DATABASE)

    def execute(self, sql, params=None):
        if params is None:
            params = []
        return self.engine.execute(sql, *params)

    def select(self, sql, params=None):
        res = []
        for row in self.execute(sql, params):
            res.append(row)
        return res
