TEMPLATE = "eksport_marcel"

MENU_ENTRY = "Kody zleceń zleceniodawcy"

HELP = "Eksport wg dat rejestracji, po symbolu w bazie"

SQL = """
select zl.datarejestracji as "Data", zl.numer as "Numer", zl.kodkreskowy as "Kod kreskowy",
    count(w.id) as "Ilość wykonań",
    sum(case when w.zatwierdzone is not null and w.bladwykonania is null then 1 else 0 end) as "Zatw bez błędów",
    sum(case when w.zatwierdzone is not null and w.bladwykonania is not null then 1 else 0 end) as "Błędy wykonania"
from zlecenia zl
left join oddzialy o on o.id=zl.oddzial
left join wykonania w on w.zlecenie=zl.id
where zl.datarejestracji between :"D$Data od" and :"D$Data do" and o.symbol=:"$Zleceniodawca" 
and zl.anulowane is null group by 1, 2, 3 order by 1, 2
"""
