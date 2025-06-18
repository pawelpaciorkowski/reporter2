import json
from typing import List

from .postgres import PostgresDatasource
from config import Config


class RepublikaDatasource(PostgresDatasource):
    def __init__(self):
        cfg = Config()
        PostgresDatasource.__init__(self, cfg.DATABASE_REPUBLIKA)

    def orders_for_barcode(self, kod, dokladne=False) -> List[str]:
        if dokladne:
            sql = """
                select distinct entity_id 
                from republika_index where index_name='barcode' and value=%s and entity_name='Order'
            """
            sql_params = [kod]
        else:
            sql = """
                select distinct entity_id 
                from republika_index where index_name='barcode' and left(value, 9)=%s and entity_name='Order'
            """
            sql_params = [kod.replace('=', '').strip()[:9]]
        res = []
        for row in self.dict_select(sql, sql_params):
            res.append(row['entity_id'])
        return res

    def get_order(self, order_id: str, anonymize: bool = True):
        rows = self.dict_select("select * from republika_stream_events where order_id=%s order by id", [order_id])
        events = {}
        if len(rows) == 0:
            return None
        id_pracownikow = set()
        for row in rows:
            ed = row['event_data']
            if ed.get('pracownik') is not None:
                id_pracownikow.add(ed['pracownik'])
            events[row['id']] = row
            if row['event_type'] == 'CntZewZlecenieBind':
                for zew_row in self.dict_select(
                        "select * from republika_stream_events where entity_name=%s and entity_id=%s order by id",
                        [row['entity_name'], row['entity_id']]):
                    events[zew_row['id']] = zew_row
            if row['event_type'] == 'CntZlecDaneRejestracyjne' and anonymize:
                if 'pacjent' in row['event_data'] and row['event_data']['pacjent'] is not None:
                    for fld in ('imiona', 'nazwisko', 'pesel'):
                        if row['event_data']['pacjent'].get(fld) not in (None, ''):
                            row['event_data']['pacjent'][fld] = row['event_data']['pacjent'][fld][0] + '...'
        pracownicy = {}
        for row in self.dict_select("select * from pracownicy where rpl_src_system || ':' || (id::varchar) in %s", [
            tuple(id_pracownikow)
        ]):
            ident = '%s:%d' % (row['rpl_src_system'], row['id'])
            pracownicy[ident] = row['nazwisko']
        all_events = []
        for id in sorted(events.keys()):
            event = events[id]
            all_events.append(event)
        return {
            'events': all_events,
            'lookup': {
                'pracownicy': pracownicy,
            },
        }
