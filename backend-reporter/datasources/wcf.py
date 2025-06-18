from config import Config
from .postgres import PostgresDatasource

class WCFDatasource(PostgresDatasource):
    def __init__(self, read_write=False):
        cfg = Config()
        PostgresDatasource.__init__(self, cfg.DATABASE_WCF,
                                    read_write=read_write)