from semplate import Semplate
import psycopg2

TABLES_SQL = """
    with recursive fk_tree as (
      -- All tables not referencing anything else
      select t.oid as reloid, 
             t.relname as table_name, 
             s.nspname as schema_name,
             null::text as referenced_table_name,
             null::text as referenced_schema_name,
             1 as level
      from pg_class t
        join pg_namespace s on s.oid = t.relnamespace
      where relkind = 'r'
        and not exists (select *
                        from pg_constraint
                        where contype = 'f'
                          and conrelid = t.oid)
        and s.nspname = 'public' -- limit to one schema 
    
      union all 
    
      select ref.oid, 
             ref.relname, 
             rs.nspname,
             p.table_name,
             p.schema_name,
             p.level + 1
      from pg_class ref
        join pg_namespace rs on rs.oid = ref.relnamespace
        join pg_constraint c on c.contype = 'f' and c.conrelid = ref.oid
        join fk_tree p on p.reloid = c.confrelid
    ), all_tables as (
      -- this picks the highest level for each table
      select schema_name, table_name,
             level, 
             row_number() over (partition by schema_name, table_name order by level desc) as last_table_row
      from fk_tree
    )
    select schema_name, table_name, level
    from all_tables at
    where last_table_row = 1
    order by level;
"""

ignoruj_tabele = 'wykonania,przesylki,sesjelogowania,rozliczenia,pozycjerozliczen,faktury,pozycjefaktur,synchronizacje,komunikaty'.split(',')

if __name__ == '__main__':

    spl = Semplate(comment_char='#', section_prefix='##')
    counter = 101
    spl.load('create_set.slonik')
    spl.clear_section('TABLES')
    conn = psycopg2.connect("dbname='rozliczeniowa' user='postgres' host='2.0.4.101' port=5432")
    cur = conn.cursor()
    cur.execute(TABLES_SQL, [])
    for row in cur.fetchall():
        table = row[1]
        if table in ignoruj_tabele or (table.startswith('hst') and table[3:] in ignoruj_tabele):
            continue
        table_res = spl.template('TABLE TEMPLATE', ID=str(counter), TABLE_NAME=table)
        counter += 1
        spl.add_to_section('TABLES', table_res)
    spl.save('create_set.slonik')