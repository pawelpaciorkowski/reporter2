from .postgres import PostgresDatasource
from config import Config


class MKurierDatasource(PostgresDatasource):
    def __init__(self, read_write=False):
        PostgresDatasource.__init__(self, Config.DATABASE_MKURIER, read_write=read_write)
