from datasources.postgres import PostgresDatasource
db = PostgresDatasource("dbname='reporter' user='postgres' host='127.0.0.1' port=5433")

def zapisz_zdarzenie(typ, opis=None, serwer=None, zlaczka=None, status=None):
    pass

