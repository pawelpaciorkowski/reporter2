import datetime
from decimal import Decimal


def prepare_for_json(data):
    if isinstance(data, list):
        return [prepare_for_json(x) for x in data]
    elif isinstance(data, tuple):
        return tuple([prepare_for_json(x) for x in data])
    elif isinstance(data, dict):
        res = {}
        for k, v in data.items():
            res[k] = prepare_for_json(v)
        return res
    elif isinstance(data, datetime.datetime):
        return data.strftime('%Y-%m-%d %H:%M')
    elif isinstance(data, datetime.date):
        return data.strftime('%Y-%m-%d')
    elif isinstance(data, Decimal):
        return float(data) # "%.02f" % data
    elif isinstance(data, bytes):
        return data.decode()
    else:
        return data