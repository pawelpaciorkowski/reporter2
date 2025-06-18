import datetime
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportTitle import \
    MonthlyTitleGenerator, DailyTitleGenerator


def test_add_leading_zero():
    assert '01' == MonthlyTitleGenerator.add_leading_zero(1)
    assert '10' == MonthlyTitleGenerator.add_leading_zero(10)


def test_calculate_xx():
    assert '08' == MonthlyTitleGenerator.calculate_xx(4, 2020)
    assert '16' == MonthlyTitleGenerator.calculate_xx(12, 2020)


def test_numer_zestawienia():
    date1 = datetime.datetime.strptime('2016-11-30', '%Y-%m-%d')
    date2 = datetime.datetime.strptime('2020-12-31', '%Y-%m-%d')
    date3 = datetime.datetime.strptime('2020-04-30', '%Y-%m-%d')
    assert 'SR-0011/11/2016' == MonthlyTitleGenerator.generate_number(date1)
    assert 'SR-0016/12/2020' == MonthlyTitleGenerator.generate_number(date2)
    assert 'SR-0008/04/2020' == MonthlyTitleGenerator.generate_number(date3)


def test_data_zastawienia():
    date1 = datetime.datetime.strptime('2016-11-30', '%Y-%m-%d')
    date2 = datetime.datetime.strptime('2020-12-31', '%Y-%m-%d')
    date3 = datetime.datetime.strptime('2020-04-30', '%Y-%m-%d')
    assert '30.11.2016' == MonthlyTitleGenerator.str_date(date1)
    assert '31.12.2020' == MonthlyTitleGenerator.str_date(date2)
    assert '30.04.2020' == MonthlyTitleGenerator.str_date(date3)


def test_tytul_zestawienia():
    date1 = '2016-11-30'
    date2 = '2020-12-31'
    date3 = '2020-04-30'
    assert 'Zestawienie miesięczne nr SR-0011/11/2016 z dnia 30.11.2016' == MonthlyTitleGenerator.generate_title(date1)
    assert 'Zestawienie miesięczne nr SR-0016/12/2020 z dnia 31.12.2020' == MonthlyTitleGenerator.generate_title(date2)
    assert 'Zestawienie miesięczne nr SR-0008/04/2020 z dnia 30.04.2020' == MonthlyTitleGenerator.generate_title(date3)


class TestDaily:
    def test_numer_zestawienia(self):
        date1 = datetime.datetime.strptime('2021-01-13', '%Y-%m-%d')
        assert 'SRD-1839/13/01/2021' == DailyTitleGenerator.generate_number(date1)

    def test_tytul_zestawienia(self):
        date1 = '2021-01-13'
        assert 'Zestawienie dzienne nr SRD-1839/13/01/2021 z dnia 13.01.2021' == DailyTitleGenerator.generate_title(date1)
