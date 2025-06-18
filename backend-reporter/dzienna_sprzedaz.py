import sys
from datetime import date, datetime, timedelta
from datasources.nocka import NockaDatasource
from helpers.kalendarz import Kalendarz


SQL_INSERT = """
with rows AS (
insert into dzienna_sprzedaz 
select
    pac.pacjent,
    zlec.lab,
    zlec.lab_zlecenie_data,
    zlec.lab_cena is not null as lab_gotowka,
    zlec.lab_znacznik_dystrybucja,
    zlec.kanal,
    zlec.platnik_zlecenia,
    zlec.zleceniodawca,
    count(distinct zlec.lab || zlec.lab_zlecenie::varchar) as ile_zlecen,
    sum(zlec.ile_wykonan) as ile_wykonan,
    sum(zlec.lab_cena) as wartosc_gotowki
from
    (
    select
        wp.lab,
        wp.lab_zlecenie,
        wp.lab_zlecenie_data,
        wp.lab_zlecenie_nr,
        wp.platnik_zlecenia,
        wp.zleceniodawca,
        wp.kanal,
        wp.lab_znacznik_dystrybucja,
        count(wp.id) as ile_wykonan,
        sum(wp.lab_cena) as lab_cena
    from
        wykonania_pelne wp
    where
        wp.lab_zlecenie_data = %s
        and (wp.kanal is not null or wp.lab_znacznik_dystrybucja)
    group by
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8) zlec
left join pacjenci pac on
    pac.lab = zlec.lab
    and pac.lab_zlecenie = zlec.lab_zlecenie
group by
    1,
    2,
    3,
    4,
    5,
    6,
    7,
    8
returning 1)
select count(*) from rows
"""

SQL_DELETE = """
with rows as (
delete from dzienna_sprzedaz  where lab_zlecenie_data = %s returning 1)
select count(*) from rows
"""

class DziennaSprzedazManager:

    def __init__(self) -> None:
        self.db = NockaDatasource(read_write=True)

    def _log_information(self, command: str, count:int, date: str):
        print(f'{command} \t{count:,} \t {date}')

    def insert_daily_data(self, date: str):
        db_response = self.db.dict_select(SQL_INSERT,(date,))
        self.db.commit()
        self._log_information('insert', db_response[0]["count"], date)
        return db_response

    def _delete_daily_date(self, date:str):
        db_response = self.db.dict_select(SQL_DELETE,(date,))
        self.db.commit()
        self._log_information('delete', db_response[0]["count"], date)
        return db_response


if __name__ == '__main__':
    # try:
    #     date = sys.argv[1]
    # except IndexError:
    #     print('Podaj date jako patametr - yyyy-mm-dd')
    #     exit()

    date = str(datetime.today() - timedelta(days=1))
    dsm = DziennaSprzedazManager()
    dsm._delete_daily_date(date)
    dsm.insert_daily_data(date)

    # for d in range(31):
    #     day = '0%s' % (d + 1) if d < 10 else d+1
    #     date_day = str(date[:-2]) + str(day)
    #     dsm._delete_daily_date(date_day)
    #     dsm.insert_daily_data(date_day)
    #     print('\n')

    kal = Kalendarz()
    for d in kal.zakres_dat(kal.data('-14D'), kal.data('-1D')):
    # for d in kal.zakres_dat(kal.data('2023-01-01'), kal.data('2023-03-05')):
        print(d)
        dsm = DziennaSprzedazManager()
        dsm._delete_daily_date(d)
        dsm.insert_daily_data(d)

