from .mysql import MySQLDatasource
from config import Config


class AlabSerwisDatasource(MySQLDatasource):
    def __init__(self, read_write=False):
        self.read_write = read_write
        cfg = Config()
        MySQLDatasource.__init__(
            self, cfg.DATABASE_ALABSERWIS, read_write=read_write)
        self.execute("SET character_set_client = 'utf8'")
