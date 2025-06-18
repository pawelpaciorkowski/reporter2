from .postgres import PostgresDatasource


class SanepidDatasource(PostgresDatasource):
    def __init__(self, read_write=False):
        PostgresDatasource.__init__(self, "dbname=sanepid user=postgres host=2.0.205.185 port=5482",
                                    read_write=read_write)
