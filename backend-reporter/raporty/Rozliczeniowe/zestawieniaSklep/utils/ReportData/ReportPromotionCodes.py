from raporty.Rozliczeniowe.zestawieniaSklep.utils.CollectionPoint import \
    CollectionPointMiesieczny
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportData import ReportData
from raporty.Rozliczeniowe.zestawieniaSklep.utils.Street import \
    StreetMiesieczny


class ReportPromotionCodes(ReportData):

    def report_rows(self) -> list:
        return [self.row_to_display(row) for row in self._query_data.data]

    @property
    def title(self):
        return self._title_generator.generate_title()

    @staticmethod
    def row_to_display(row) -> list:
        return [
            row['code'],
            row['status'],
            row['start_date'],
            row['end_date'],
            row['name'],
            row['order_id'],
            row['order_number'],
            row['user'],
            row['use_date']
        ]



