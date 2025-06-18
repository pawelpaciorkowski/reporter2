import base64
import json

from .base import Field
from helpers import Kalendarz


class TextInput(Field):
    pass


class NumberInput(TextInput):
    pass


class DateTimeInput(TextInput):
    def get_default_value(self):
        res = TextInput.get_default_value(self)
        if res is not None:
            kal = Kalendarz()
            return kal.data_godz(res)
        return res

    def load_own_value(self, value):
        kal = Kalendarz()
        if value is None or value == '':
            return None
        return kal.data_godz(value)


class DateInput(DateTimeInput):
    def get_default_value(self):
        res = TextInput.get_default_value(self)
        if res is not None:
            kal = Kalendarz()
            return kal.data(res)
        return res

    def load_own_value(self, value):
        kal = Kalendarz()
        if value is None or value == '':
            return None
        return kal.data(value)


class FileInput(TextInput):
    def load_own_value(self, value):
        if value is None:
            return None
        elif isinstance(value, dict):
            return value
        else:
            res = json.loads(value)
            return res


class TimeInput(DateTimeInput):
    pass


class EmailInput(TextInput):
    pass


class Select(Field):
    def _prettify_params_value(self, params):
        res = Field._prettify_params_value(self, params)
        if res is not None and res in self.init_kwargs.get('values', {}):
            return self.init_kwargs['values'][res]
        else:
            return res

    def load_own_value(self, value):
        possible_values = list(self.init_kwargs.get('values', {}).keys())
        if value is None or value not in possible_values:
            if len(possible_values) > 0:
                return possible_values[0]
            else:
                return None
        else:
            return value


class Radio(Select):
    pass


class MultiSelect(Field):
    pass


class Switch(Field):
    def _prettify_params_value(self, params):
        res = Field._prettify_params_value(self, params)
        return 'Tak' if res else 'Nie'

    def load_own_value(self, value):
        if value is None or not value:
            return False
        return True
