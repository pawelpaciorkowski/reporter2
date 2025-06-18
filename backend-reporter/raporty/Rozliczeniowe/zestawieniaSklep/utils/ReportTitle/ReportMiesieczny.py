import datetime
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportTitle.ReportTitle import \
    TitleGenerator


class MonthlyTitleGenerator(TitleGenerator):
    PREFIX = 'SR-00'
    SUBTRACTION_DATE = 2016

    @staticmethod
    def generate_title(date: datetime) -> str:
        date = datetime.datetime.strptime(date, '%Y-%m-%d')
        nr_zestawienia = MonthlyTitleGenerator.generate_number(date)
        d_zestawienia = MonthlyTitleGenerator.str_date(date)
        return f'Zestawienie miesięczne nr {nr_zestawienia} z dnia {d_zestawienia}'

    @staticmethod
    def generate_number(date: datetime) -> str:
        yyyy = date.year
        mm = date.month
        xx = MonthlyTitleGenerator.calculate_xx(mm, yyyy)
        str_mm = MonthlyTitleGenerator.add_leading_zero(mm)
        return f'{MonthlyTitleGenerator.PREFIX}{xx}/{str_mm}/{yyyy}'

    @staticmethod
    def calculate_xx(mm: int, yyyy: int) -> str:
        xx = mm + yyyy - MonthlyTitleGenerator.SUBTRACTION_DATE
        return MonthlyTitleGenerator.add_leading_zero(xx)
