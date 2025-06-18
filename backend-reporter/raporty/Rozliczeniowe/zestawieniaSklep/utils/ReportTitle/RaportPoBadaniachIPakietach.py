import datetime

from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportTitle import \
    TitleGenerator


class TestAndBundleTitle(TitleGenerator):

    @staticmethod
    def generate_title(
            date_from: datetime, date_to: datetime, scope: str) -> str:
        return f'Zestawienie po badaniach i pakietach - {scope} w {date_from} - {date_to}'


