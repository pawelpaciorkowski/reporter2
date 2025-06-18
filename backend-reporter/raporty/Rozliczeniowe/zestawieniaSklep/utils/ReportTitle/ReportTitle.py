from abc import ABC, abstractmethod
import datetime


class TitleGenerator(ABC):

    @staticmethod
    @abstractmethod
    def generate_title(*args, **kwargs) -> str:
        raise NotImplementedError()

    @staticmethod
    def add_leading_zero(number: int) -> str:
        if number < 10:
            return f'0{number}'
        return str(number)

    @staticmethod
    def str_date(date: datetime) -> str:
        day = TitleGenerator.add_leading_zero(date.day)
        month = TitleGenerator.add_leading_zero(date.month)
        return f'{day}.{month}.{date.year}'




