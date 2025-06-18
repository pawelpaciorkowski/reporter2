from pprint import pprint
from raporty.Rozliczeniowe.zestawieniaSklep.utils.CollectionPoint import \
    CollectionPointMiesieczny
from raporty.Rozliczeniowe.zestawieniaSklep.utils.Order import DailyOrders
from raporty.Rozliczeniowe.zestawieniaSklep.utils.Purchaser import Purchaser, VatPurchaser
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportData import ReportData
from raporty.Rozliczeniowe.zestawieniaSklep.utils.Query import QueryData
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportTitle import TitleGenerator
from raporty.Rozliczeniowe.zestawieniaSklep.utils.Street import \
    StreetMiesieczny


class ReportDzienny(ReportData):

    DISPLAY_CELLS = [
        'title',
        'quantity',
        'discount_code',
        'voucher',
        'item_price',
        'test_symbol'
    ]

    DISPLAY_EXTRA = [
        'extra_title',
        'extra_ilosc',
        'discount_code',
        'voucher',
        'extra_wartosc',
        'extra_service'
    ]

    def __init__(self, query_data: QueryData, title_generator: TitleGenerator):
        super().__init__(query_data, title_generator)
        self._grouped_rows = {}

    def group_rows(self):
        def sort_order(orders: dict) -> dict:
            return dict(sorted(orders.items()))

        def add_extra_service(orders: list, row):
            extra_service = row['extra_service']
            extra_value = row['extra_wartosc']
            extra_quantity = row['extra_ilosc']
            extra_title = row['extra_title']
            order = {
                'quantity': extra_quantity ,
                'discount_code': None,
                'voucher': None,
                'item_price': extra_value,
                'test_symbol': extra_service,
                'title': extra_title
            }
            if order not in orders and order['test_symbol']:
                orders.append(order)
            return orders

        def append_grouped_rows_or_order(rows: dict, order_number: str, row: dict):
            order = {}
            for c in row:
                if not c in self.DISPLAY_CELLS:
                    rows[order_number][c] = row[c]
                else:
                    order[c] = row[c]
            rows = create_order_list(rows, order_number)
            orders = rows[order_number]['orders']
            orders.append(order)
            add_extra_service(orders, row)
            return rows

        def create_order_list(rows: dict, order_nr: str):
            if not rows[order_nr].get('orders'):
                rows[order_nr]['orders'] = []
            return rows

        def create_dict_for_order_number(rows: dict, order_number: str) :
            if not rows.get(order_number):
                rows[order_number] = {}
            return rows

        def group_rows():
            grouped_rows = self._grouped_rows
            for row in self._query_data.data:
                order_number = row['order_number']
                if not order_number:
                    continue
                grouped_rows = create_dict_for_order_number(
                    grouped_rows, order_number)

                grouped_rows = append_grouped_rows_or_order(
                    grouped_rows, order_number, row)
            return grouped_rows

        self._grouped_rows = sort_order(group_rows())

    def report_rows(self) -> list:
        self.group_rows()
        resp = [self.row_to_display(self._grouped_rows[row]) for row in self._grouped_rows]
        resp.append(self._add_summary())
        return resp

    def report_rows_no_merge(self) -> list:
        return [self.row_to_display_no_colspan(row) for row in self._query_data.data]

    def summary_rows(self):
        data = self.summary_table()
        rows = [[
            data[row]['cp'],
            data[row]['mpk'],
            data[row]['net_sum']] for row in data]
        sum_net = sum([data[row]['net_sum'] for row in data])
        rows.append(['', '', sum_net])
        return rows

    def summary_table(self):
        res = {}

        for row_data in self._query_data.data:
            collection_point = ReportDzienny.get_collection_point(row_data)
            row = {
                'cp': collection_point.report_representation(),
                'mpk': collection_point.mpk,
                'net_sum': 0
            }
            if collection_point.mpk not in res:
                res[collection_point.mpk] = row

            if row_data['item_price']:
                res[collection_point.mpk]['net_sum'] += row_data['item_price']

        return res

    def _add_summary(self):
        data = self._grouped_rows
        order_count = len(data)
        gross_sum = sum([data[d]['sum'] for d in data])
        quantity_sum = 0
        item_price_sum = 0
        for d in data:
            for o in data[d]['orders']:
                quantity_sum += o['quantity']
                item_price_sum += o['item_price']
        return [
            {'value': f'Liczba zamówień: {order_count}', 'colspan':6},
            {'value': gross_sum},
            {'value': ''},
            {'value': ''},
            {'value': ''},
            {'value': ''},
            {'value': ''},
            {'value': quantity_sum},
            {'value': item_price_sum},
        ]

    @property
    def title(self):
        end_date = self._query_data.params['datado']
        return self._title_generator.generate_title(end_date)

    @staticmethod
    def cell_dict(value, rowspan=0):
        if rowspan:
            return {"value": value, "rowspan": rowspan}
        return {"value": value}

    @staticmethod
    def row_to_display_no_colspan(row_data) -> list:

        collection_point = ReportDzienny.get_collection_point(row_data)
        purchaser = ReportDzienny.get_purchaser(row_data)
        for_whom = row_data['for_whom']
        vat_invoice = row_data['vat_invoice']
        if for_whom == 'self':
            for_whom = ''
        else:
            for_whom = ReportDzienny.get_patient(row_data).report_representation()

        if vat_invoice == 0:
            vat_invoice = ''
        else:
            vat_invoice = VatPurchaser(**row_data).report_representation()

        return [
            row_data['order_number'],
            row_data['nr_zes'],
            collection_point.mpk,
            collection_point.report_representation(),
            purchaser.report_representation(),
            for_whom,
            ReportDzienny.str_as_decimal_format(row_data['sum']),
            vat_invoice,
            row_data['payment'],
            row_data['promotion_code'],
            row_data['test_symbol'],
            row_data['title'],
            row_data['quantity'],
            row_data['item_price'],
        ]

    @staticmethod
    def row_to_display(row_data) -> list:
        collection_point = ReportDzienny.get_collection_point(row_data)
        purchaser = ReportDzienny.get_purchaser(row_data)
        rowspan = len(row_data['orders'])
        orders = DailyOrders(row_data['orders'])
        for_whom = row_data['for_whom']
        if for_whom == 'self':
            for_whom = ''
        else:
            for_whom = ReportDzienny.get_patient(row_data).report_representation()
        vat_invoice = row_data['vat_invoice']
        if for_whom == 'self':
            for_whom = ''
        if vat_invoice == 0:
            vat_invoice = ''
        else:
            vat_invoice = VatPurchaser(**row_data).report_representation()
        if purchaser.get_name() is not None:
            purchaser_display = purchaser.report_representation()
        elif purchaser.get_name() is None and vat_invoice:
            purchaser_display = vat_invoice
        else:
            purchaser_display = ReportDzienny.get_patient(row_data).report_representation()

        return [
            ReportDzienny.cell_dict(row_data['order_number'], rowspan),
            ReportDzienny.cell_dict(row_data['nr_zes'], rowspan),
            ReportDzienny.cell_dict(collection_point.mpk, rowspan),
            ReportDzienny.cell_dict(collection_point.report_representation(), rowspan),
            ReportDzienny.cell_dict(purchaser_display, rowspan),
            ReportDzienny.cell_dict(for_whom, rowspan),
            ReportDzienny.cell_dict(
                ReportDzienny.str_as_decimal_format(
                    row_data['sum']), rowspan),
            ReportDzienny.cell_dict(vat_invoice, rowspan),
            ReportDzienny.cell_dict(row_data['payment'], rowspan),
            ReportDzienny.cell_dict(row_data['promotion_code'], rowspan),
            orders.symbols(),
            orders.titles(),
            orders.quantities(),
            orders.item_prices(),
        ]

    @staticmethod
    def get_purchaser(row_data):
        return Purchaser(
            firstname=row_data['name'],
            surname=row_data['surname'] ,
            telephone=row_data['telephone'],
            email=row_data['mail'],
            pesel=row_data['pesel'])

    @staticmethod
    def get_patient(row_data):
        return Purchaser(
            firstname=row_data['patient_name'],
            surname=row_data['patient_surname'] ,
            telephone=row_data['patient_telephone'],
            email=row_data['mail'],
            pesel=row_data['patient_pesel'])

    @staticmethod
    def get_collection_point(row_data):
        street = StreetMiesieczny(row_data)
        return CollectionPointMiesieczny(
            street=street,
            symbol=row_data['symbol'],
            city=row_data['city'],
            mpk=row_data['mpk'])


