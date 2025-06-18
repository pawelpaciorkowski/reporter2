TEMPLATE = "eksport_marcel"

MENU_ENTRY = "Histopatologia wg daty wykonania"

SQL = """
    select WYNIKTEKSTOWY, symbol, nazwisko, count(*) as liczba from
    (
    select distinct z.id, wy.WYNIKTEKSTOWY
    from zlecenia z
    join wykonania w on z.id = w.ZLECENIE
    join badania b on w.BADANIE = b.id
    join wyniki wy  on wy.WYKONANIE = w.id
    join parametry p on p.id = wy.PARAMETR
    where
    w.rozliczone BETWEEN :"D$Data początkowa" AND :"D$Data końcowa" and w.datarejestracji >= '2014-01-01' and
    b.SYMBOL = 'H-WYSYL' and p.symbol = 'WYK-OPI'
    and (wy.WYNIKTEKSTOWY is not null or trim(wy.WYNIKTEKSTOWY) <> '')
    ) as z1
    JOIN
    (select distinct z.id, b.symbol, pr.nazwisko
    from zlecenia z
    join wykonania w on z.id = w.ZLECENIE
    join badania b on w.BADANIE = b.id
    join pracownicy pr on w.pracownikodzatwierdzenia = pr.id
    where w.rozliczone BETWEEN :"D$Data początkowa" AND :"D$Data końcowa" and w.datarejestracji >= '2014-01-01' and b.SYMBOL <> 'H-WYSYL'
    )  z2 on z1.Id = z2.id
    group by WYNIKTEKSTOWY, symbol, nazwisko
"""