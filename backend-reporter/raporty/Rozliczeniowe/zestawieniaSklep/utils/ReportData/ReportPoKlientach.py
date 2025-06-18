from typing import List
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportData import ReportData
from raporty.Rozliczeniowe.zestawieniaSklep.utils.Query import QueryData
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportTitle import \
    TitleGenerator
from dataclasses import dataclass
import datetime
from pprint import pprint


@dataclass
class User:
    user_id: int
    user_name: str

    @staticmethod
    def prepare_user_name(name, surname):
        if not name:
            name = ''
        if not surname:
            surname = ''
        return name + ' ' + surname


@dataclass
class OrderItem:
    order_number: int
    order_item_id: int
    unit_price: float
    total_price: float
    quantity: int
    create_date: datetime
    order_item_type: str
    extra_service: str
    extra_service_quantity: int
    extra_service_price: float
    discount_code: str


class Order:

    def __init__(
            self, user: User, order_number: int,
            order_date: datetime) -> None:
        self._order_item_list = []
        self.order_item_count = 0
        self.order_item_sum = 0
        self.user = user
        self.order_number = order_number
        self.order_date = order_date
        self._has_extra_service = False
        self._added_extra_service = None
        self.discount_code = None

    def _validate_order_item(self, item: OrderItem) -> None:
        if not item.order_number == self.order_number:
            raise ValueError('Order number is not matching')

    def _set_extra_service(self, item: OrderItem):
        if item.extra_service is not None:
            self._has_extra_service = True

    def _set_discount_code(self, item: OrderItem):
        if item.discount_code is not None:
            self.discount_code = item.discount_code

    def _add_extra_service(self, item: OrderItem):
        if self._has_extra_service and not self._added_extra_service:
            self.order_item_sum += \
                item.extra_service_price*item.extra_service_quantity
            self._added_extra_service = True

    def add_item(self, item: OrderItem) -> None:
        self._validate_order_item(item)
        self._order_item_list.append(item)
        self._set_extra_service(item)
        self._set_discount_code(item)
        self.order_item_count += 1
        self.order_item_sum += item.total_price
        self._add_extra_service(item)


@dataclass
class ReportRow:
    def __init__(self, user: User) -> None:
        self.order_list = []
        self.order_count = 0
        self.order_sum = 0
        self.user = user

    def get_all_order_numbers(self) -> List[int]:
        return [order.order_number for order in self.order_list]

    def _validate_order(self, order_number: int) -> None:
        if order_number in self.get_all_order_numbers():
            raise ValueError("Orders cannot be duplicated")

    def is_order_exists(self, order_number: int) -> bool:
        for order in self.order_list:
            if order.order_number == order_number:
                return True
        return False

    def is_user_exists(self, user: User) -> bool:
        for order in self.order_list:
            if order.user == user:
                return True
        return False

    def get_order(self, order_number: int) -> Order:
        for order in self.order_list:
            if order.order_number == order_number:
                return order

    def add_order(self, order: Order) -> None:
        self._validate_order(order.order_number)
        self.order_list.append(order)
        self.order_count += 1
        self.order_sum += order.order_item_sum

    def add_item_to_order(self, order: Order, item: OrderItem) -> None:
        order.add_item(item)
        self.order_sum += item.total_price


class ReportDataClient:
    def __init__(self):
        self.rows = []
        self.row_count = 0
        self.row_sum = 0

    def add_row(self, user: User, item: OrderItem) -> None:

        if self._is_user_exists(user) \
                and self._check_order_number(item.order_number):
            row = self.get_row_with_order(item.order_number)
            order = row.get_order(item.order_number)
            row.add_item_to_order(order, item)
            self.row_sum += row.order_sum

        if self._is_user_exists(user) \
                and not self._check_order_number(item.order_number):
            row = self.get_row_with_user(user)
            if row:
                order = Order(user, item.order_number, item.create_date)
                order.add_item(item)
                row.add_order(order)
                self.row_sum += row.order_sum

        if not self._is_user_exists(user) \
                and not self._check_order_number(item.order_number):
            order = Order(user, item.order_number, item.create_date)
            order.add_item(item)
            row = ReportRow(user)
            row.add_order(order)
            self.rows.append(row)
            self.row_count += 1
            self.row_sum += row.order_sum

    def get_row_with_order(self, order_number: int) -> ReportRow:
        for row in self.rows:
            if row.is_order_exists(order_number):
                return row

    def get_row_with_user(self, user: User) -> ReportRow:
        for row in self.rows:
            if row.is_user_exists(user):
                return row

    def _check_order_number(self, order_number: int) -> bool:
        for row in self.rows:
            if row.is_order_exists(order_number):
                return True
        return False

    def _is_user_exists(self, user: User) -> bool:
        for row in self.rows:
            if row.user.user_id == user.user_id:
                return True
        return False


class ReportPoKlientach(ReportData):

    USER_FIELDS = [
        'user_id',
        'name',
        'surname',
    ]
    SINGLE_ORDER_FIELDS = [
        'order_number',
        'price',
        'create_date',
        'discount_code',
        'quantity'
    ]

    def __init__(
            self,
            query_data: QueryData,
            title_generator: TitleGenerator) -> None:
        super().__init__(query_data, title_generator)
        self._orders_by_client = {}
        self._report_rows = []
        self._report = None

    @property
    def title(self) -> str:
        return 'Zestawienie po klientach'

    @staticmethod
    def row_to_display(row: ReportRow) -> list:

        display_row = [
            row.user.user_id, row.user.user_name,
            row.order_sum, row.order_count]

        for order in row.order_list:
            display_row.append(order.order_number)
            display_row.append(order.order_item_sum),
            display_row.append(order.order_date),
            display_row.append(order.discount_code),
            display_row.append(order.order_item_count)
        return display_row

    def _group_orders_by_user(self) -> None:
        self._report = ReportDataClient()
        for row in self._query_data.data:
            user = User(
                row['user_id'],
                User.prepare_user_name(row['name'], row['surname']))

            order_item = OrderItem(
                row['order_number'], row['order_item_id'],
                row['unit_price__number'], row['total_price__number'],
                row['quantity'], row['create_date'],
                row['type'], row['extra_service'],
                row['extra_ilosc'], row['extra_wartosc'],
                row['voucher'])

            self._report.add_row(user, order_item)

    def report_rows(self) -> list:
        self._group_orders_by_user()
        resp = [self.row_to_display(row) for row in self._report.rows]
        return resp
