from typing import List

from datasources.postgres import PostgresDatasource
from helpers import log


class PreorderRepositoryError(Exception):
    pass


class PreordersRepository:
    def __init__(self, datasource: PostgresDatasource):
        self.datasource = datasource

    def get_preorder(self, code: str) -> dict:
        sql = 'select id, kod_zlecenia, ic_system from zlecenia where kod_zlecenia = %s'
        preorder = self.datasource.dict_select(sql, (code,))
        if not preorder:
            raise PreorderRepositoryError("Nie znaleziono zlecenia")
        return preorder[0]

    def prolong_preorder(self, preorder: dict, date: str):
        sql = ''' update zlecenia set data_waznosci = %s where kod_zlecenia = %s returning 1'''
        code = preorder["kod_zlecenia"]
        prolonged = self.datasource.dict_select(sql, (date, code))
        if len(prolonged) == 1:
            self.datasource.commit()
            log('external_preorders', preorder['id'], 'prezlecenia_zmiana_daty',
                'date_change', preorder, {"new_date": date})
        else:
            self.datasource.rollback()
            raise PreorderRepositoryError('Błąd podczas przedłużania zlecenia')

    def prolong_preorders(self, preorders: List[dict], date: str):
        sql = '''update zlecenia set data_waznosci = %s where kod_zlecenia in %s returning 1'''
        codes = tuple(preorder['kod_zlecenia'] for preorder in preorders)
        print(sql, date, codes)
        prolonged = self.datasource.dict_select(sql, (date,codes))
        if len(prolonged) == len(codes):
            self.datasource.commit()
            log('external_preorders', preorders[0]['id'], 'prezlecenia_zmiana_daty',
                'date_change', preorders, {"new_date": date})
        else:
            self.datasource.rollback()
            raise PreorderRepositoryError('Błąd podczas przedłużania prezleceń')

    def get_preorders(self, codes: List[dict]) -> List[dict]:
        sql = 'select id, kod_zlecenia, ic_system from zlecenia where kod_zlecenia in %s and ic_system is null and ts_rej is null'
        preorders = self.datasource.dict_select(sql, (tuple(codes),))
        if not preorders:
            raise PreorderRepositoryError("Nie znaleziono zleceń")
        return preorders

    def delete_preorders(self, preorders: List[dict]):
        sql = ''' delete from zlecenia where kod_zlecenia in %s returning 1'''
        codes = tuple(preorder["kod_zlecenia"] for preorder in preorders)
        deleted = self.datasource.dict_select(sql, (codes,))

        if len(codes) == len(deleted):
            self.datasource.commit()
            log('external_preorders', preorders[0]['id'], 'prezlecenia_zmiana_daty', 'delete',
                preorders, {"delete": True})
        else:
            self.datasource.rollback()
            raise PreorderRepositoryError('Błąd podczas usuwania zleceń')


