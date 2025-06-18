import pytest

from helpers import Kalendarz, KalendarzException
import datetime


def test_simple_now():
    kal = Kalendarz()
    assert kal.data('T') == datetime.datetime.now().strftime('%Y-%m-%d')


def test_simple_now_time():
    kal = Kalendarz()
    assert kal.data_godz('T') == datetime.datetime.now().strftime('%Y-%m-%d %H:%M')


def test_simple_now_pl():
    kal = Kalendarz()
    kal.polski = True
    assert kal.data('T') == datetime.datetime.now().strftime('%d-%m-%Y')


def test_sama_data_ok():
    kal = Kalendarz()
    assert kal.data('2019-11-30') == '2019-11-30'


def test_sama_data_blad():
    kal = Kalendarz()
    assert kal.data('2019-11-31') is None


def test_sama_data_blad2():
    kal = Kalendarz()
    with pytest.raises(KalendarzException):
        kal.data('2019-11-31', throw_exception=True)


@pytest.mark.parametrize("data", [
    '2019-01-01', '2019-01-06',
    '2019-04-22',
    '2019-05-01', '2019-05-03',
    '2019-06-20', '2019-08-15',
    '2019-11-01', '2019-11-11',
    '2019-12-25', '2019-12-26',
    '2020-04-13', '2020-06-11'

])
def test_dni_wolne(data):
    kal = Kalendarz()
    assert not kal.dzien_roboczy(data)


@pytest.mark.parametrize("test_input,expected", [
    ('T', '2019-12-30'),
    ('W', '2019-12-29'),
    ('J', '2019-12-31'),
    ('+3D', '2020-01-02'),
    ('+2T', '2020-01-13'),
    ('+1R', '2020-12-30'),
    ('+2R', '2021-12-30'),
    ('+3DR', '2020-01-03'),
    ('-3D', '2019-12-27'),
    ('-3DR', '2019-12-23'),
    ('-35D', '2019-11-25'),
    ('PM', '2019-12-01'),
    ('KM', '2019-12-31'),
    ('PZM', '2019-11-01'),
    ('KZM', '2019-11-30')
])
def test_wyliczenia_wzgledne_daty(test_input, expected):
    kal = Kalendarz()
    kal.ustaw_teraz('2019-12-30')
    assert kal.data(test_input, throw_exception=True) == expected


@pytest.mark.parametrize("test_input,expected", [
    ('-3G', '2019-12-30 07:00'),
    ('+30G', '2019-12-31 16:00'),
    ('8:00', '2019-12-30 08:00'),
    ('-5DR 11', '2019-12-19 11:00'),
    ('-5DR 11:17', '2019-12-19 11:17'),
])
def test_z_godzinami(test_input, expected):
    kal = Kalendarz()
    kal.ustaw_teraz('2019-12-30 10:00')
    assert kal.data_godz(test_input, throw_exception=True) == expected


def test_lata_przestepne():
    kal = Kalendarz()
    kal.ustaw_teraz('2019-02-15')
    assert kal.data('KM') == '2019-02-28'
    kal.ustaw_teraz('2020-02-15')
    assert kal.data('KM') == '2020-02-29'
    kal.ustaw_teraz('2000-02-15')
    assert kal.data('KM') == '2000-02-29'
    kal.ustaw_teraz('2100-02-15')
    assert kal.data('KM') == '2100-02-28'
