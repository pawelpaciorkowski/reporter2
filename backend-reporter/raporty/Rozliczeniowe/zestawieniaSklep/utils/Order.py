from raporty.Rozliczeniowe.zestawieniaSklep.utils.Query import QueryData
from datasources.sklep import SklepDatasource


class Order:

    def __init__(
            self, symbol: str, name: str, quantity: str, unit_price: str,
            vat: str, gross_price: str, voucher: str, discount_percentage: str,
            discount_code: str, use_date: str):
        self._symbol = symbol
        self._name = name
        self._quantity = quantity
        self._unit_price = unit_price
        self._vat = vat
        self._gross_price = gross_price
        self._voucher = voucher
        self._discount_percentage = discount_percentage
        self._discount_code = discount_code
        self._use_date = use_date


class DailyOrders:

    def __init__(self, orders: dict):
        self._symbols = [o['test_symbol'] for o in orders]
        self._titles = [o['title'] for o in orders]
        self._quantities = [o['quantity'] for o in orders]
        self._discount_codes = [o['discount_code'] for o in orders]
        self._vouchers = [o['voucher'] for o in orders]
        self._item_prices = [o['item_price'] for o in orders]

    def symbols(self):
        return self._symbols

    def titles(self):
        return self._titles

    def quantities(self):
        return self._quantities

    def discount_codes(self):
        return self._discount_codes

    def vouchers(self):
        return self._vouchers

    def item_prices(self):
        return self._item_prices
