import re
from datetime import datetime, date, time

ILLEGAL_CHARACTERS_RE = re.compile(r'[\000-\010]|[\013-\014]|[\016-\037]')

class RaportStandalone:
    def __init__(self, **kwargs):
        self.reset()

    def reset(self):
        self.cols = None
        self.col_mods = {}
        self.rows = []

    def set_columns(self, cols):
        self.cols = cols

    def add_rows(self, rows):
        for row in rows:
            self.rows.append(row)

    def add_row(self, row):
        self.rows.append(row)

    def set_col_titles(self, **kwargs):
        for c, t in kwargs.items():
            if c not in self.col_mods:
                self.col_mods[c] = {}
            self.col_mods[c]['title'] = t

    def to_string(self, value):
        return str(value)

    def to_excel(self, value):
        if value is None:
            return ''
        if isinstance(value, datetime) or isinstance(value, date) or isinstance(value, time):
            return str(value)
        if isinstance(value, list):
            return '[' + ','.join([self.to_excel(val) for val in value]) + ']'
        if isinstance(value, str):
            return re.sub(ILLEGAL_CHARACTERS_RE, '', value)
        return value

    def prepare(self):
        if self.cols is None:
            raise Exception('Brak kolumn')
        self.col_titles = []
        for col in self.cols:
            try:
                self.col_titles.append(self.col_mods[col]['title'])
            except:
                self.col_titles.append(col)
