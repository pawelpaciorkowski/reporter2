from .postgres import PostgresDatasource
from config import Config


class PPAlabUpstreamDatasource(PostgresDatasource):
    def __init__(self, read_write=False):
        PostgresDatasource.__init__(self, Config.DATABASE_PPALAB_UPSTREAM, read_write=read_write)
