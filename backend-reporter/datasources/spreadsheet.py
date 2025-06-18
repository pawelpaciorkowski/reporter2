import ezodf
import openpyxl
import unicodedata
import re

from helpers import slugify


def find_col(needle, haystack):
    for i, col in enumerate(haystack):
        if col is None or not isinstance(col, str):
            continue
        if slugify(needle) in slugify(col):
            return i
    raise ValueError(needle, 'not found in', haystack)


def worksheet_to_values(ws):
    res = [
        [(cell.value.strip() if isinstance(cell.value, str) else cell.value)
         for cell in row] for row in ws
    ]
    return res


def spreadsheet_to_values(fn):
    if fn.endswith('.xlsx'):
        wb = openpyxl.load_workbook(fn)
        return worksheet_to_values(wb.active)
    elif fn.endswith('.ods'):
        doc = ezodf.opendoc(fn)
        return worksheet_to_values(doc.sheets[0].rows())
    else:
        raise Exception('Unknown file type', fn)
