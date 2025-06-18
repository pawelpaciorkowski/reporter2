import json
from helpers import prepare_for_json
from datasources.reporter import ReporterDatasource

MENU_ENTRY = 'Ostatnie zdarzenia'

REQUIRE_ROLE = ['C-ALL']
GUI_MODE = 'one_shot'

SQL = """
    select l.ts, l.typ, l.opis, o.nazwisko, l.parametry
    from log_zdarzenia l
    left join osoby o on o.id=l.obj_id
    where l.obj_type='osoba' and l.typ in ('REPGEN', 'REPVIEW')
    order by l.id desc
    limit 50
"""


def shorten(data):
    if isinstance(data, dict):
        return dict((k, shorten(v)) for k, v in data.items())
    elif isinstance(data, list):
        return [shorten(item) for item in data]
    elif isinstance(data, str):
        if len(data) > 100:
            return data[:100] + '..'
    return data


def get_content(user_login):
    rep = ReporterDatasource()
    rows = []
    _, src_rows = rep.select(SQL)
    for row in src_rows:
        row = list(row)
        row[4] = json.dumps(shorten(row[4]))
        rows.append(row)
    return [
        {
            'type': 'table',
            'title': 'Ostatnie zdarzenia',
            'header': 'Timestamp,Zdarzenie,Opis,Osoba,Parametry'.split(','),
            'data': prepare_for_json(rows)
        }
    ]
