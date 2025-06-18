from raporty.Rozliczeniowe.zestawieniaSklep.utils.CollectionPoint import \
    CollectionPointMiesieczny
from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportData import ReportData
from raporty.Rozliczeniowe.zestawieniaSklep.utils.Street import \
    StreetMiesieczny


class ReportMiesieczny(ReportData):

    def _add_sum_row(self):
        total_sum = 0
        for row in self._query_data.data:
            total_sum += row['suma_cen']
        return ['', '', total_sum, '', total_sum, total_sum]

    def report_rows(self) -> list:
        rows = [self.row_to_display(row) for row in self._query_data.data if row['mpk'] is not None]
        rows.append(self._add_sum_row())
        return rows

    @property
    def title(self):
        end_date = self._query_data.params['datado']
        return self._title_generator.generate_title(end_date)

    @staticmethod
    def row_to_display(row_data) -> list:
        mpk = row_data['mpk']
        street = StreetMiesieczny(row_data)
        collection_point = CollectionPointMiesieczny(
            street=street,
            symbol=row_data['symbol'],
            city=row_data['city'],
            mpk=mpk)
        return [
            mpk,
            collection_point.report_representation(),
            ReportMiesieczny.str_as_decimal_format(row_data['suma_cen']),

            # WORKAROUND - brak możliwości połączenia zamówień
            # z informacja odnośnie stawki VAT w zaimportowanch
            # zamówieniach ze starego sklepu TO CHANGE
            ReportMiesieczny.str_as_decimal_format(None),
            # ReportDataMiesieczny.str_as_decimal_format(row_data['suma_vat']),
            # ReportDataMiesieczny.str_as_decimal_format(row_data['suma_brutto']),
            ReportMiesieczny.str_as_decimal_format(row_data['suma_cen']),
            ReportMiesieczny.str_as_decimal_format(row_data['suma_cen']),
        ]


