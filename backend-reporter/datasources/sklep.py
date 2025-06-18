from .mysql import MySQLDatasource
from config import Config


class SklepDatasource(MySQLDatasource):
    def __init__(self, read_write=False):
        self.read_write = read_write
        cfg = Config()
        MySQLDatasource.__init__(
            self, cfg.DATABASE_SKLEP, read_write=read_write)
