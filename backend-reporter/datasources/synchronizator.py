from .postgres import PostgresDatasource
from helpers import Kalendarz
from helpers.helpers import get_local_open_vpn_address
from config import Config


class SynchronizatorDatasource(PostgresDatasource):
    def __init__(self):
        PostgresDatasource.__init__(self,
                                    dsn="dbname='synchronizacje' user='sync_ro' password='sync_ro' host='2.0.0.3' port=5432",
                                    read_write=False)
