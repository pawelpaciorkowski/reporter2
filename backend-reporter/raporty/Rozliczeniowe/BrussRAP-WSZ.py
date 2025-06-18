TEMPLATE = "eksport_marcel"

MENU_ENTRY = "Bruss - raport na płatników z Centrum"



SQL = """
select
 PP.Symbol as "Punkt pobrań - symbol",
 PP.Nazwa  as "Punkt pobrań - nazwa",
 GPP.Symbol as "Grupa punktów pobrań - symbol",
 GPP.Nazwa  as "Grupa punktów pobrań - nazwa",
 PL.Symbol as "Płatnik - symbol",
 PL.Nazwa  as "Płatnik - nazwa",
 PL.NIP as "Płatnik - NIP",
 GPL.Symbol as "Grupa płatników - symbol",
 GPL.Nazwa  as "Grupa płatników - nazwa",
 BAD.Symbol as "Badanie - symbol",
 BAD.Nazwa  as "Badanie - nazwa",
 BAD.KOD    as "Badanie - kod ICD",
 GBAD.Symbol as "Grupa badań - symbol",
 GBAD.Nazwa  as "Grupa badań - nazwa",
 MAT.Symbol as "Materiał - symbol",
 MAT.Nazwa  as "Materiał - nazwa",
 W.Platne as "Płatne",
 W.Pakiet as "Pakiet",
 W.Cena   as "Cena",
 SW.Symbol as "Stawka VAT",
 count(w.id) as "Ilość",
 sum(w.Cena) as "Wartość",
 extract(year from w.ROZLICZONE) as "Rok rozliczenia",
 extract(month from w.ROZLICZONE) as "Miesiąc rozliczenia"
from
 Wykonania W
 left outer join Zlecenia Z on W.Zlecenie = Z.ID
 left outer join Oddzialy PP on Z.Oddzial = PP.ID
 left outer join GrupyOddzialow GPP on PP.Grupa = GPP.ID
 left outer join Platnicy PL on W.Platnik = PL.ID
 left outer join GrupyPlatnikow GPL on PL.Grupa = GPL.ID
 left outer join Pacjenci PAC on W.Pacjent = PAC.ID
 left outer join Pobyty POB on Z.Pobyt = POB.ID
 left outer join Lekarze L on Z.Lekarz = L.ID
 left outer join Badania BAD on W.Badanie = BAD.ID
 left outer join GrupyBadan GBAD on BAD.Grupa = GBAD.ID
 left outer join Materialy MAT on W.Material = MAT.ID
 left outer join Pracownicy PR on PR.ID = W.PC
 left outer join StatusyPacjentow STA on PAC.StatusPacjenta = STA.ID
 left join STAWKIVAT sw on sw.id=w.STAWKAVAT
where
 W.Rozliczone between :"D$Data początkowa Rozliczeń" and :"D$Data końcowa Rozliczeń" and
 W.Platne = 1 and W.Anulowane is Null
group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,23,24
order by
 pl.symbol,
 BAD.Symbol,
 MAT.Symbol
"""