from typing import List

from helpers import log
from .postgres import PostgresDatasource
from config import Config


class VoucherProlongError(Exception):
    pass


class VoucherDeactivationError(Exception):
    pass


class VouchersDatasource(PostgresDatasource):
    def __init__(self, read_write=False):
        cfg = Config()
        PostgresDatasource.__init__(
            self,
            cfg.DATABASE_VOUCHERS,
            read_write=read_write)

    def deactivate_vouchers(self, vouchers: List[dict]):
        barcodes = tuple([voucher['barcode'] for voucher in vouchers])
        try:
            self.execute(
                    "update vouchers_voucher set is_active = false where barcode in %s",
                    (barcodes,))
            self.commit()
            log('external_vouchers', vouchers[0]['id'], 'vouchers_deaktywacja',
                'delete', vouchers, {"delete": True})
        except:
            raise VoucherDeactivationError("Błąd podczas deaktywacji w aplikacji Vouchery")

    def deactivate_generation(self, generation_id: int, vouchers: List[dict]):
        try:
            self.execute(
                "update vouchers_vouchergeneration set deleted = true where id = %s",
                (generation_id,))
            self.commit()

            log('external_vouchers', generation_id, 'vouchers_deaktywacja_generacji',
                'delete', vouchers, {"delete": True})
        except:
            raise VoucherDeactivationError("Błąd podczas deaktywacji generacji w aplikacji Vouchery")

    def prolong_voucher(self, voucher: dict, date: str):
        barcode = voucher['barcode']
        try:
            self.execute(
                "update vouchers_voucher set date_to = %s where barcode = %s",
                (date, barcode))
            self.commit()
            log('external_vouchers', voucher['id'], 'vouchers_zmiana_daty',
                'date_change', voucher, {"new_date": date})
        except:
            raise Exception("Błąd podczas przedłużenia ważności w aplikacji Vouchery")

    def prolong_vouchers(self, vouchers: List[dict], date: str):
        sql = "update vouchers_voucher set date_to = %s where barcode in %s"
        barcodes = tuple([voucher['barcode'] for voucher in vouchers])
        try:
            self.execute(sql, (date, barcodes))
            self.commit()
            log('external_vouchers', vouchers[0]['id'], 'vouchers_zmiana_daty',
                'date_change', vouchers, {"new_date": date})
        except:
            raise Exception("Błąd podczas przedłużenia ważności w aplikacji Vouchery")

    def get_vouchers_by_generation(self, generation_id: int) -> List[dict]:
        try:
            return self.dict_select("select * from vouchers_voucher where generation_id = %s", (generation_id,))
        except:
            raise VoucherProlongError("Błąd podczas pobierania voucherów")

    def get_voucher(self, code: str) -> dict:
        try:
            return self.dict_select("select * from vouchers_voucher where barcode = %s", (code,))
        except:
            raise VoucherProlongError("Błąd podczas pobierania voucherów")

    def get_vouchers(self, codes: List[str]) -> List[dict]:
        # try:
        codes_tuple = tuple(codes)
        return self.dict_select("select * from vouchers_voucher where barcode in %s", (codes_tuple,))
        # except:
        #     raise VoucherProlongError("Błąd podczas pobierania voucherów")
