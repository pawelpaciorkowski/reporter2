from abc import ABC
from raporty.Rozliczeniowe.zestawieniaSklep.utils.Street import Street


class CollectionPoint:

    def __init__(self, street: Street, symbol: str,  city: str, mpk: str):
        self._street = street
        self._symbol = symbol
        self._city = city
        self._mpk = mpk

    @property
    def street(self) -> Street:
        return self._street

    @property
    def symbol(self) -> str:
        return self._symbol

    @property
    def city(self) -> str:
        return self._city

    @property
    def mpk(self) -> str:
        return self._mpk

    @staticmethod
    def clear_underline(val):
        if val[0] == '_':
            return val[1:]
        return val

    def dict(self):
        return {self.clear_underline(v): self.__dict__[v] for v in self.__dict__}


class CollectionPointMiesieczny(CollectionPoint):

    def report_representation(self) -> str:
        return f'{self.street.full_street}, {self.city}, Symbol punktu: {self.symbol}'
