from datasources.postgres import PostgresDatasource


class WynikiStats(PostgresDatasource):
    def __init__(self, read_write=False):
        if read_write:
            PostgresDatasource.__init__(self,
                                    "dbname='wyniki' user='postgres' host='2.0.203.153' port=5432",
                                    read_write=True)
        else:
            PostgresDatasource.__init__(self,
                                    "dbname='wyniki' user='wyniki' password='wyniki' host='2.0.203.153' port=5432",
                                    read_write=False)

