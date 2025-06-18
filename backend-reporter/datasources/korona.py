from .postgres import PostgresDatasource

DSN = "dbname='korona' user='postgres' host='10.1.252.230' port=5432"


class KoronaDatasource(PostgresDatasource):
    def __init__(self, read_write=False):
        PostgresDatasource.__init__(self, dsn=DSN, read_write=read_write)
