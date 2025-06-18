import datetime
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportTitle import \
    TitleGenerator


class DailyTitleGenerator(TitleGenerator):
    PREFIX = 'SRD-'
    SUBTRACTION_DATE = datetime.datetime(2015, 11, 14)

    @staticmethod
    def generate_title(date: str) -> str:
        date = datetime.datetime.strptime(date, '%Y-%m-%d')
        nr_zestawienia = DailyTitleGenerator.generate_number(date)
        d_zestawienia = DailyTitleGenerator.str_date(date)
        return f'Zestawienie dzienne nr {nr_zestawienia} z dnia {d_zestawienia}'

    @staticmethod
    def generate_number(date: datetime) -> str:
        yyyy = date.year
        mm = date.month
        dd = date.day
        xx = DailyTitleGenerator.calculate_xx(date)
        xx_len = len(xx)
        if xx_len < 4:
            xx = (4-xx_len) * '0' + xx
        str_mm = TitleGenerator.add_leading_zero(mm)
        str_dd = TitleGenerator.add_leading_zero(dd)
        return f'{DailyTitleGenerator.PREFIX}{xx}/{str_dd}/{str_mm}/{yyyy}'

    @staticmethod
    def calculate_xx(end_date: datetime) -> str:
        xx = end_date - DailyTitleGenerator.SUBTRACTION_DATE
        days = xx.days - 48
        return TitleGenerator.add_leading_zero(days)


