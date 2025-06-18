from config import Config
from .mssql import MSSQLDatasource


class SimpleDatasource(MSSQLDatasource):
    def __init__(self):
        cfg = Config()
        MSSQLDatasource.__init__(self, cfg.DATABASE_SIMPLE)