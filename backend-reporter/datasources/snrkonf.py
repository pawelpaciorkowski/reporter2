from .postgres import PostgresDatasource
from config import Config

import string

# https://github.com/caub/pg-tsquery/blob/master/index.js - javascriptowy parser requesta ludzkiego do ts_query
# https://www.depesz.com/2008/04/22/polish-tsearch-in-83-polski-tsearch-w-postgresie-83/ - dodanie polskiego


class SNRKonf(PostgresDatasource):
    def __init__(self):
        cfg = Config()
        PostgresDatasource.__init__(self, cfg.DATABASE_SNRCONF)

    def laboratoria(self):
        return self.select("select * from laboratoria")

    def struktura(self):
        res = {
            "regiony": self.select("select * from regiony"),
            "laboratoria": self.select("select * from laboratoria"),
            "platnicy": self.select("select * from platnicy"),
            "platnicywlaboratoriach": self.select("select * from platnicywlaboratoriach"),
            "zleceniodawcy": self.select("select * from zleceniodawcy"),
        }
        for k in res:
            res[k] = self.remove_columns(res[k], "tsidx")
        return res

    def escape_symbol(self, value):
        def check_char(ch):
            return ch.isalnum() or ch in ('-', '_')
        return ''.join(filter(check_char, value.upper()))

    def szukaj_podmiotow(self, params):
        SQL = """
            select t.id as id, array_agg(st.symbol) as symbole, t.nazwa as nazwa
            from $TABLENAME$ t
            left join $TABLENAME$wlaboratoriach st on t.id=st.$TABLEKEY$
            where not t.del and not st.del
            and (st.symbol=%s or t.tsidx @@ websearch_to_tsquery(%s)) 
        """

        if params.get('lab_filter') is not None:
            SQL += """ and st.laboratorium in (%s)""" % ','.join(
                "'" + self.escape_symbol(s) + "'" for s in params['lab_filter'])

        SQL += "group by t.id, t.nazwa limit 30"
        SQL = SQL.replace('$TABLENAME$', params['type'])
        SQL = SQL.replace('$TABLEKEY$', {
                          'platnicy': 'platnik', 'zleceniodawcy': 'zleceniodawca'}[params['type']])

        res = []
        for row in self.dict_select(SQL, [params['query'], params['query']]):
            symbole = ', '.join(row['symbole'])
            if len(symbole) > 20:
                symbole = symbole[:20] + '...'
            res.append({
                'value': row['id'],
                'label': "%s (%s)" % (row['nazwa'], symbole)
            })
        return res

    def szukaj_badan(self, query):
        SQL = """
            select b.symbol, b.nazwa, b.hs->'rodzaj' as rodzaj
            from badania b
            where not b.del
            and (b.symbol=%s or b.tsidx @@ websearch_to_tsquery(%s)) 
        """
        res = []
        for row in self.dict_select(SQL, [query, query]):
            dod = []
            if row['rodzaj'] == 'P':
                dod.append('P')
            label = '%s - %s' % (row['symbol'], row['nazwa'])
            if len(dod) > 0:
                label += ' (%s)' % ', '.join(dod)
            res.append({
                'value': row['symbol'],
                'label': label
            })
        return res

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
