TEMPLATE = "eksport_marcel"

MENU_ENTRY = "Zliczanie ilości na zatwierdzających - wg d. rozl."

SQL = """
select symbol, pls, pln, zls, zln, numer || ' / ' || datarejestracji as "Numer zlecenia", zewnetrznyidentyfikator as "Numer zewnętrzny", ZATW as "Osoba zatwierdzająca", WYNIKTEKSTOWY as "ILE BLOCZKÓW", count(*) as "W Ilu Badaniach" from
(
select distinct z.id, pl.symbol as pls, pl.nazwa as pln, o.symbol as zls, o.nazwa as zln, 
    wy.WYNIKTEKSTOWY, m.symbol as mat1
from wykonania w
join zlecenia z on z.id = w.ZLECENIE
join badania b on w.BADANIE = b.id
join wyniki wy on wy.WYKONANIE = w.id
join parametry p on p.id = wy.PARAMETR
join materialy m on m.id =w.MATERIAL
left outer join platnicy pl on pl.id =z.platnik
left join oddzialy o on o.id=z.oddzial
where
w.rozliczone BETWEEN :"D$Data od" and :"D$Data do" and
b.SYMBOL = 'H-WYSYL' and p.symbol = 'IL-KASE'
and (wy.WYNIKTEKSTOWY is not null or trim(wy.WYNIKTEKSTOWY) <> '') and wy.WYNIKLICZBOWY < '1000000'
) as z1
JOIN
(select distinct z.id, z.numer, z.DATAREJESTRACJI, z.ZEWNETRZNYIDENTYFIKATOR, b.symbol, m.SYMBOL as mat, pr.NAZWISKO as ZATW
from wykonania w
join zlecenia z on z.id = w.ZLECENIE
join badania b on w.BADANIE = b.id
join materialy m on m.id =w.MATERIAL
left outer join PRACOWNICY pr on pr.id = w.PRACOWNIKODZATWIERDZENIA
where w.rozliczone BETWEEN :"D$Data od" and :"D$Data do" and b.SYMBOL <> 'H-WYSYL' and b.dorozliczen = '0'
) z2 on z1.Id = z2.id
where z1.mat1 = z2.mat
group by symbol, WYNIKTEKSTOWY, numer, datarejestracji, zewnetrznyidentyfikator, zatw, pls, pln, zls, zln
"""
