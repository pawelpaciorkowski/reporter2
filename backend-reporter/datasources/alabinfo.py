from .postgres import PostgresDatasource


class AlabInfoDatasource(PostgresDatasource):
    def __init__(self, read_write=False):
        PostgresDatasource.__init__(self, "dbname=alabinfo user=postgres host=2.0.3.49 password=kapljca port=5432",
                                    read_write=read_write)
