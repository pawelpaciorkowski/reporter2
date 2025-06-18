from config import Config
from datasources.mssql import MSSQLDatasource

INSERT_LAB_SQL = '''
INSERT INTO LabCostCenters (Symbol, Name, Number, Active) VALUES (%s, %s, %s, 1)
'''

SELECT_LAB_SQL = '''
SELECT * FROM LabCostCenters WHERE Symbol=%s AND Active=1;
'''

SELECT_PAYMENT_OWNERS_IDS_SQL = '''
SELECT ExternalId from PaymentOwners
'''

UPDATE_USER_PAYMENT_OWNER_LINK_SQL = '''
UPDATE PaymentOwners
SET SalesRepresentativeId=%s
WHERE ExternalId=%s;
'''


class EFakturaDatasource(MSSQLDatasource):
    def __init__(self):
        cfg = Config()
        MSSQLDatasource.__init__(self, cfg.DATABASE_EFAKTURA)

    def lab_not_in_db(self, symbol: str):
        cols, rows = self.select(SELECT_LAB_SQL, [symbol])
        return len(rows) == 0

    def add_lab_to_db(self, symbol: str, name: str, mpk: str):
        self.execute(INSERT_LAB_SQL, [symbol, name, mpk])

    def get_payment_owners_ids(self):
        return self.select('''SELECT ExternalId from PaymentOwners''')[1]
    
    def get_users_email(self):
        return self.select('''SELECT Email FROM Users''')[1]
    
    def get_user_id_by_email(self, email: str):
        return self.select('''SELECT UserId FROM Users Where Email=%s and IsActive=1''', [email])[1][0][0]

    def update_user_payment_owner_link(self, user_id: int, k_number: str):
        print('Aktualizuje powiązanie przedstawiciela {} z użytkownikiem o id {} ...'.format(k_number, user_id))
        # self.execute(UPDATE_USER_PAYMENT_OWNER_LINK_SQL, [user_id, k_number])
