import pytest
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportData.ReportPoKlientach import *
from datetime import date


def test_User():
    user = User(1, 'test name')
    assert user.user_id == 1
    assert user.user_name == 'test name'


def test_Order_creation():
    user = User(1, 'test name')
    order = Order(user, 1, date.today())
    assert order.order_number == 1
    assert order.order_item_sum == 0
    assert order.order_item_count == 0
    assert order.order_date == date.today()


def test_Order_add_single():
    user = User(1, 'test name')
    order_item = OrderItem(1, 1, 12.5, 15.5, 1, date.today())
    order = Order(user, 1, date.today())
    order.add_item(order_item)
    assert order.order_item_count == 1
    assert order.order_item_sum == 15.50


def test_Order_add_many():
    user = User(1, 'test name')
    order_item = OrderItem(1, 1, 12.5, 15.5, 1, date.today())
    order_item2 = OrderItem(1, 1, 12.5, 15.5, 1, date.today())
    order = Order(user, 1, date.today())
    order.add_item(order_item)
    order.add_item(order_item2)
    assert order.order_item_count == 2
    assert order.order_item_sum == 31


def test_Order_add_with_different_order_number_error():
    with pytest.raises(ValueError):
        user = User(1, 'test name')
        order_item = OrderItem(2, 1, 12.5, 15.5, 1, date.today())
        order = Order(user, 1, date.today())
        order.add_item(order_item)


def test_ReportRow():
    user = User(1, 'test name')
    order_item = OrderItem(1, 1, 12.5, 15.5, 1, date.today())
    order_item2 = OrderItem(1, 1, 12.5, 15.5, 1, date.today())
    order = Order(user, 1, date.today())
    order.add_item(order_item)
    order.add_item(order_item2)
    row = ReportRow(user)
    row.add_order(order)
    assert row.order_count == 1
    assert row.order_sum == 31


def test_ReportRow_add_dupicated_order_error():
    with pytest.raises(ValueError):
        user = User(1, 'test name')
        order_item = OrderItem(1, 1, 12.5, 15.5, 1, date.today())
        order_item2 = OrderItem(1, 1, 12.5, 15.5, 1, date.today())
        order = Order(user, 1, date.today())
        order.add_item(order_item)
        order.add_item(order_item2)
        row = ReportRow(user)
        row.add_order(order)
        row.add_order(order)


def test_ReportRow_get_all_order_numbers():
    user = User(1, 'test name')
    order_item = OrderItem(1, 1, 12.5, 15.5, 1, date.today())
    order_item2 = OrderItem(1, 1, 12.5, 15.5, 1, date.today())
    order = Order(user, 1, date.today())
    order2 = Order(user, 2, date.today())
    order.add_item(order_item)
    order.add_item(order_item2)
    row = ReportRow(user)
    row.add_order(order)
    row.add_order(order2)
    assert row.get_all_order_numbers() == [1, 2]


def test_ReportRow_is_order_exsts():
    user = User(1, 'test name')
    order_item = OrderItem(1, 1, 12.5, 15.5, 1, date.today())
    order_item2 = OrderItem(1, 1, 12.5, 15.5, 1, date.today())
    order = Order(user, 1, date.today())
    order2 = Order(user, 2, date.today())
    order.add_item(order_item)
    order.add_item(order_item2)
    row = ReportRow(user)
    row.add_order(order)
    row.add_order(order2)

    assert row.is_order_exists(1) is True
    assert row.is_order_exists(99) is False


def test_ReportRow_get_order():
    user = User(1, 'test name')
    order_item = OrderItem(1, 1, 12.5, 15.5, 1, date.today())
    order_item2 = OrderItem(1, 1, 12.5, 15.5, 1, date.today())
    order = Order(user, 1, date.today())
    order2 = Order(user, 2, date.today())
    order.add_item(order_item)
    order.add_item(order_item2)
    row = ReportRow(user)
    row.add_order(order)
    row.add_order(order2)

    assert row.get_order(1) == order


def test_ReportData_is_user_existing():

    user = User(1, 'test name')
    user2 = User(2, 'test name')
    order_item = OrderItem(1, 1, 12.5, 15.5, 1, date.today())
    report = ReportDataClient()
    report.add_row(user, order_item)
    assert report._is_user_exists(user) is True
    assert report._is_user_exists(user2) is False


def test_ReportData_get_row_with_order():

    user = User(1, 'test name')
    user2 = User(2, 'test name')
    order_item = OrderItem(1, 1, 12.5, 15.5, 1, date.today())
    order = Order(user, 1, date.today())
    row = ReportRow(user)
    row.add_order(order)
    order_item2 = OrderItem(2, 1, 12.5, 15.5, 1, date.today())
    report = ReportDataClient()
    report.add_row(user, order_item)
    report.add_row(user2, order_item2)
    assert report.get_row_with_order(1) == row
    assert report.get_row_with_order(99) is None


def test_ReportData__check_order_number():

    user = User(1, 'test name')
    order_item = OrderItem(1, 2, 12.5, 15.5, 1, date.today())
    report = ReportDataClient()
    report.add_row(user, order_item)
    assert report._check_order_number(2) is False
    assert report._check_order_number(1) is True


def test_ReportData():
    user = User(1, 'test name')
    order_item = OrderItem(1, 1, 12.5, 15.5, 1, date.today())
    report = ReportDataClient()
    report.add_row(user, order_item)
    assert report.row_count == 1
    assert report.row_sum == 15.5