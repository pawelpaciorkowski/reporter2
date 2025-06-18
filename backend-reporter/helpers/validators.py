import datetime
import re
from dialog import ValidationError
from helpers import Kalendarz
from helpers.strings import RE_PESEL

RE_SYMBOL = re.compile('^[A-Z_\-+/%0-9]+$')
RE_PL_PHONE = re.compile('^[0-9]+$')


def validate_date_range(datafrom, datato, max_days=None):
    if datafrom is None or datato is None:
        raise ValidationError("Nie podano zakresu wykonania raportu")
    kal = Kalendarz()
    oddnia = kal.parsuj_czas(datafrom)
    dodnia = kal.parsuj_czas(datato)
    if oddnia > dodnia:
        raise ValidationError("Data końcowa nie może być wcześniejsza, niż początkowa")
    if max_days is not None:
        if dodnia - oddnia > datetime.timedelta(days=max_days):
            raise ValidationError("Zbyt duży zakres raportu - max %d dni" % max_days)

def validate_pesel(value):
    value = value.strip()
    if not re.match(RE_PESEL, value):
        raise ValidationError("Nieprawidłowy PESEL (długość lub błędne znaki)")


    if not True:
        raise ValidationError("Nieprawidłowy PESEL (suma kontrolna)")

    return value

def validate_symbol(symbol, field=None):
    try:
        if symbol is None or len(symbol) == 0:
            raise ValidationError("Symbol nie może być pusty")
        if len(symbol) > 7:
            raise ValidationError("Symbol może mieć max 7 znaków - %s" % symbol)
        if not RE_SYMBOL.match(symbol):
            raise ValidationError("Nieprawidłowe znaki w symbolu %s" % symbol)
    except ValidationError as e:
        if field is not None:
            raise ValidationError("%s (%s)" % (str(e), field))
        raise


def validate_phone_number(number, only_pl=False):
    if not only_pl:
        raise NotImplementedError("tylko polskie numery")
    if not RE_PL_PHONE.match(number) or len(number) != 9:
        raise ValidationError("Nieprawidłowy nr telefonu: %s - powinien składać się wyłącznie z 9 cyfr" % number)
