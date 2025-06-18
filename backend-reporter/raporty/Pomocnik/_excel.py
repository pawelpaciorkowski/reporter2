import os
import base64
from copy import copy

import openpyxl
import openpyxl.workbook

from dialog import ValidationError
from helpers import random_path

LITERY = [c for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ']
KOLUMNY = copy(LITERY)

for l1 in LITERY:
    for l2 in LITERY:
        KOLUMNY.append(l1 + l2)

class ExcelError(Exception):
    pass

def kolumny_szukania(val):
    if val is None:
        raise ValidationError("Nie podano kolumn szukania")
    res = []
    for sv in val.upper().split(' '):
        if sv == '':
            continue
        if sv in KOLUMNY:
            res.append(KOLUMNY.index(sv))
        else:
            raise ValidationError("Nieprawidłowa kolumna: %s" % sv)
    if len(res) == 0:
        raise ValidationError("Brak kolumn szukania")
    return res


def kolumny_wypelnij(params):
    res = {}
    for k, v in params.items():
        if k.startswith('wyp_'):
            if v is None:
                continue
            v = v.upper().strip()
            if v == '':
                continue
            pole = k[4:]
            if v in KOLUMNY:
                res[pole] = KOLUMNY.index(v)
            else:
                raise ValidationError("Nieprawidłowa kolumna: %s" % v)
    if len(res.keys()) == 0:
        raise ValidationError("Brak kolumn do wypełnienia")
    return res


class ExcelCompleter:
    def __init__(self, field_data):
        self.field_data = field_data
        self.rows = None
        self.res_rows = None
        self.filename = None
        self.local_filename = None
        self.max_row_len = 0

    def __enter__(self):
        self.filename = self.field_data['filename'].lower()
        if not self.filename.endswith('.xlsx'):
            raise ExcelError("Prześlij plik XLSX")
        self.local_filename = random_path('reporter', 'xlsx')
        with open(self.local_filename, 'wb') as f:
            f.write(base64.b64decode(self.field_data['content']))
        try:
            wb: openpyxl.workbook.Workbook = openpyxl.load_workbook(self.local_filename)
        except Exception as e:
            raise ExcelError("Nie udało się załadować pliku: %s" % str(e))
        if len(wb.worksheets) != 1:
            raise ExcelError("Plik zawiera %d arkuszy. Prześlij plik z jednym arkuszem" % len(wb.worksheets))
        self.rows = []
        for row in wb.active:
            row = [cell.value for cell in row]
            if all([v is None for v in row]):
                continue
            self.max_row_len = max(self.max_row_len, len(row))
            self.rows.append(row)
        if len(self.rows) > 2000:
            raise ExcelError("Arkusz zawiera ponad 2000 wierszy - nie wyszukuję ze względów wydajnościowych.")
        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.local_filename is not None and os.path.exists(self.local_filename):
            os.unlink(self.local_filename)


    def do_match(self, on_search, kol_szukaj, kol_wypelnij, on_value=None):
        if self.rows is None or self.res_rows is not None:
            raise RuntimeError("Niewłaściwy moment")
        wypelnij_rev = {}
        required_fields = []
        for pole, kolumna in kol_wypelnij.items():
            self.max_row_len = max(self.max_row_len, kolumna+1)
            wypelnij_rev[kolumna] = pole
            required_fields.append(pole)
        self.res_rows = []
        for row in self.rows:
            search_res = None
            # if len(self.res_rows) > 50:
            #     break # TODO do testów, wywalić
            query = ' '.join([str(row[i]) for i in kol_szukaj if row[i] is not None and str(row[i]).strip() != ''])
            if len(query) >= 2:
                search_res = on_search(query, required_fields)
            res_row = []
            for i in range(self.max_row_len):
                if i in wypelnij_rev:
                    if search_res is not None:
                        res_row.append(search_res.get(wypelnij_rev[i], ''))
                    else:
                        res_row.append({'value': '---', 'background': '#ff0000'})
                else:
                    if i < len(row):
                        res_row.append(row[i])
                    else:
                        res_row.append('')
            if on_value is not None:
                for i, fld in wypelnij_rev.items():
                    if res_row[i] is not None and not isinstance(res_row[i], dict):
                        replacement = on_value(fld, res_row[i])
                        if replacement is not None:
                            if not isinstance(replacement, list):
                                replacement = [replacement]
                            while len(res_row) < i + len(replacement):
                                res_row.append('')
                            for j, val in enumerate(replacement):
                                res_row[i+j] = val
            self.res_rows.append(res_row)


