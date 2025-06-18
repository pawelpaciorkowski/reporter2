import datetime

from raporty.Rozliczeniowe.zestawieniaSklep.utils.ReportTitle import \
    TitleGenerator


class PromotionCodesTitle(TitleGenerator):

    @staticmethod
    def generate_title() -> str:
        return f'Zestawienie kodów rabatowych'


