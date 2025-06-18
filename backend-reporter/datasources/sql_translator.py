import re


class FBtoPSQLTranslator:

    def __init__(self, sql):

        self.query_type = None
        self.columns = None
        self.source_table = None
        self.conditions = None
        self.new_query_as_list = []

        # self.raw_query = sql.lower()
        self.raw_query = sql
        self.new_query = self.raw_query.replace('\n', ' ')
        self.new_query = self.new_query.replace('\t', ' ')
        self.replace_list()
        self.set_new_query_as_list()

        self.replace_questionmark()
        self.replace_first()

        self.set_query_type()
        self.set_columns()
        self.set_source_table_and_conditions()

    def psql_query(self):
        """Return query translated to psql"""

        lst = [
            self.query_type,
            ', '.join(i for i in self.columns),
            'from',
            self.source_table,
            ' '.join(i for i in self.conditions),
        ]
        joined = '\n'.join(lst)
        return self.placeholder_to_uppercase(joined)

    @staticmethod
    def double_percent_sign(sql_list):
        for indx, i in enumerate(sql_list):
            if '%' in i and i != '%s':
                first = i.find('%')
                second = i.find('%', first+1)
                new_1 = i[:]
                if second > 0:
                    new_1 = i[:second] + '%' + i[second:]
                new_1 = new_1[:first] + '%' + new_1[first:]
                sql_list[indx] = new_1
        return sql_list

    @staticmethod
    def placeholder_to_uppercase(sql):
        new_sql = []
        for i in sql.split(' '):
            if len(i) > 2:
                if i[0] == '$' and i[-1] == '$' \
                        or i[1] == '$' and i[-2] == '$' \
                        or i[1] == '$' and i[-1] == '$' \
                        or i[0] == '$' and i[-2] == '$':
                    new_sql.append(i.upper())
                else:
                    new_sql.append(i)
            else:
                new_sql.append(i)
        return ' '.join(new_sql)

    def set_query_type(self):
        self.query_type = self.new_query_as_list[0]

    def replace_questionmark(self):
        # TODO Dodać obsługę  ?)

        #for single ?
        indx_lits = [i for i, val in enumerate(self.new_query_as_list) if val == '?']
        for i in indx_lits:
            if len(self.new_query_as_list) > i+1:
                if not self.new_query_as_list[i + 1] in ('"', "'") \
                        and not self.new_query_as_list[i - 1] in ('"', "'") \
                        and not self.new_query_as_list[i - 1][0] in ('"', "'") \
                        and not self.new_query_as_list[i - 1][-1] in ('"', "'"):
                    self.new_query_as_list[i] = '%s'
            else:
                self.new_query_as_list[i] = '%s'

        # for concatenated ?
        indx_lits_words = [i for i, val in enumerate(self.new_query_as_list) if '?' in val]
        for i in indx_lits_words:
            curent_string = self.new_query_as_list[i]

            if curent_string.count('?') > 0:
                self.new_query_as_list[i] = curent_string.replace('?', '%s')

            if curent_string[curent_string.find('?') - 1] == '=':
                self.new_query_as_list[i] = curent_string.replace('?', '%s')

    def set_columns(self):
        to_omit = 'select'
        start_index = self.new_query_as_list.index(to_omit) + 1
        end_index = self.new_query_as_list.index('from')
        joined = ' '.join(self.new_query_as_list[start_index:end_index])
        columns = joined.split(',')
        new_cols = []
        for col in columns:
            if ',' in col:
                splited = col.split(',')
                for i in splited:
                    if i != '':
                        new_cols.append(i)
            else:
                if col != '':
                    new_cols.append(col)
        self.columns = new_cols

    def set_source_table_and_conditions(self):
        additional = ['outer', 'left', 'right', 'inner', 'limit']
        start_index = self.new_query_as_list.index('from') + 1
        splited = self.new_query_as_list[start_index:]
        if len(splited) > 1:
            if splited[1] == 'as':
                self.conditions = splited[3:]
                self.source_table = ' '.join([splited[0], splited[1], splited[2]])
            elif splited[1] not in additional:
                self.conditions = splited[2:]
                self.source_table = ' '.join([splited[0], splited[1]])
        else:
            self.conditions = splited[1:]
            self.source_table = splited[0]

    def replace_list(self):
        self.new_query = self.new_query.replace('list', 'string_agg')
        self.new_query = self.new_query.replace('minvalue', 'least')
        self.new_query = self.new_query.replace('maxvalue', 'greatest')
        # TODO: inne funkcje: minvalue -> least, maxvalue -> greatest

        self.handle_list_to_agg()

    def handle_list_to_agg(self):
        """Add delimiter for string_agg function"""

        occurrences = [m.start() for m in re.finditer('string_agg', self.new_query)]
        for o in sorted(occurrences, reverse=True):
            end_bracket = self.new_query.find(')', o)
            self.new_query = self.new_query[:end_bracket] \
                             + ", ','" + self.new_query[end_bracket:]

    def set_new_query_as_list(self):
        to_lower = [
            'select', 'from', 'on', 'update', 'delete', 'insert',
            'first', 'outer', 'left', 'right', 'inner', 'limit'
        ]
        splited = self.new_query.split(' ')
        clean_query_list = self.remove_empty(splited)
        doubled_percent = self.double_percent_sign(clean_query_list)
        new_list = []
        for i in doubled_percent:
            if i.lower() in to_lower:
                new_list.append(i.lower())
            else:
                new_list.append(i)
        self.new_query_as_list = new_list

    @staticmethod
    def remove_empty(splited):
        new_list = [i for i in splited if i not in ('', '\n')]
        return new_list

    def replace_first(self):

        query = self.new_query_as_list
        if 'first' in query and self.new_query_as_list.index('first') < 4:
            first_index = self.new_query_as_list.index('first')
            next_value = self.new_query_as_list[first_index + 1]

            try:
                next_value_int = int(next_value)
                if isinstance(next_value_int, int):
                    del query[first_index + 1]
                    del query[first_index]
                    query.append(f' limit {next_value_int}')
                    self.new_query_as_list = query

            except ValueError:
                print(f'after first must be a number not {next_value}')


# test cases
if __name__ == '__main__':
    sql1 = ' select first 10 test, id  from wykonania w left join ccc c on c.id w.id ' \
           'where  aa  = ? and w.id in ( ? , ? ) and dd = "test ? test" and cc = "testy?" and w.test = "test ? "' \
           ' group by 12 ' \
           'order by 12'

    sql2 = '''
    select w.id, w.wykonanie, w.platnik, w.zleceniodawca, w.platnikzleceniodawcy, w.nettodlaplatnika,
                    pl.nip
                from wykonania w
                left join platnicy pl on pl.id=w.platnik
                where w.laboratorium=%s and w.datarozliczeniowa between %s and %s and w.wykonanie in ($IDENTS$)
    
    '''

    sql3 = '''
     select  
      pm.id as lab_id,
        (pm.del+m.del+b.del+p.del) as lab_del,
        maxvalue(pm.dc, m.dc, b.dc) as lab_dc,
        trim(b.Symbol) as BADANIE, 
        b.CzasMaksymalny as czas_max, 
        trim(m.Symbol) as METODA,
        m.NAZWA as METODA_NAZWA,gg
        trim(p.symbol) as pracownia
                
    FROM PowiazaniaMetod pm 
    left outer join Badania b on b.id = pm.badanie and b.del = 0 
    left outer join Metody m on m.id = pm.metoda and m.del = 0 
    left outer join Systemy s on s.id = pm.system and s.del = 0 
    left outer join Pracownie p on p.id = m.pracownia and p.del = 0 
    WHERE 
        s.SYMBOL=? 
        and test in (?,?) and pm.del=0 and m.del=0 and b.del=0 and p.del=0
        and pm.dowolnytypzlecenia=1 and pm.dowolnarejestracja=1 and pm.dowolnyoddzial=1 and pm.dowolnyplatnik=1 and pm.dowolnymaterial=1
    
    
    '''
    sql4 = '''select *, b,c from a'''
    sql5 = '''select * from badania where dc > ?'''
    sql6 = '''
    select
    *
    from
    zlecenia where
    datarejestracji between %s and %s  limit 10
'''
    sql7 = '''select * from test where (a = ?)'''
    q= FBtoPSQLTranslator(sql7)
    print(q.psql_query())
