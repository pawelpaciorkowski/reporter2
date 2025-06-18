from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportData import ReportData


class ReportPoBadaniachIPakietach(ReportData):

    @property
    def title(self):
        return self._title_generator.generate_title(
            date_from=self._query_data.params['dataod'],
            date_to=self._query_data.params['datado'],
            scope=self._query_data.params['product_type'])

    def report_rows(self) -> list:
        return [self.row_to_display(row) for row in self._query_data.data if row['suma']]

    @staticmethod
    def row_to_display(row_data) -> list:

        return [
            row_data['symbol'],
            row_data['title'],
            ReportPoBadaniachIPakietach.str_as_decimal_format(row_data['suma']),
        ]
