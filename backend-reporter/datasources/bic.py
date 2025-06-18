from .postgres import PostgresDatasource
from config import Config


class BiCDatasource(PostgresDatasource):
    def __init__(self, read_write=False):
        PostgresDatasource.__init__(self, Config.DATABASE_BIC, read_write=False)

    def get_collection_points_for_labs(self, labs):
        if 'KOPERNIKA' in labs:
            labs.append('KOPERNI')
        labs = tuple(labs)
        res = {}
        for row in self.dict_select("select lab_symbol, symbol, name from config_collection_points where lab_symbol in %s", [labs]):
            if row['lab_symbol'] not in res:
                res[row['lab_symbol']] = {}
            res[row['lab_symbol']][row['symbol']] = row['name']
        return res

    def mark_migration_to_postgres(self, symbol: str, db_name: str):
        symbol = symbol[:7]
        for row in self.dict_select("select * from config_labs where symbol=%s", [symbol]):
            if not row['db_pg']:
                print("Zmiana rodzaju bazy w bic")
                self.update('config_labs', {'id': row['id']}, {
                    'db_pg': True,
                    'db': 'pg:%s:%s' % (row['vpn'], db_name)
                })
                self.commit()