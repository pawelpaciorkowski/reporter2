from abc import ABC
from raporty.Rozliczeniowe.zestawieniaSklep.utils.Query import QueryData
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportTitle import TitleGenerator


class ReportData(ABC):

    def __init__(self, query_data: QueryData, title_generator: TitleGenerator):
        self._query_data = query_data
        self._title_generator = title_generator

    @property
    def title(self) -> str:
        raise NotImplementedError()

    @staticmethod
    def row_to_display(row) -> list:
        raise NotImplementedError()

    def report_rows(self) -> list:
        return [self.row_to_display(row) for row in self._query_data.data]

    @staticmethod
    def str_as_decimal_format(number):
        if number is not None:
            f_number = float(number)
            return '{:.2f}'.format(f_number)
        return '0.00'


