from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
import datetime

NEWS = [
    ("2024-11-07", """
        * raport możliwy do wykonania także z laboratoriów nieaktywnych (m.in. baza Limbach)
        * dodana możliwość filtrowania tylko zleceń nieposiadających żadnych sprawozdań
    """)
]

# TODO 1: wziąć pod uwagę przede wszystkim raport wysyłany mailem
# TODO 2: dołożyć kod kreskowy i zewnętrzny identyfikator (prośba histopatów)
# TODO 3: zdjąć wykluczenie cytologii albo zrobić na to oddzielną zahaczkę (prośba histopatów)

# dorzucić ilość dokumentów w zleceniu

SQL = """
   select 
            DATA, NUMER, KOD, Identyfikator, Aparat, ZATW, TypZlecenia, Platnik, PP, Pacjent, Lekarz,
            (cast(list(trim(Symbol), ' ') as varchar(2000))) as BADANIA,
            count(wwz.id) as wydruki
    from (
            SELECT
                    Z.id AS ID,
                    W.DataRejestracji AS DATA,
                    Z.ZewnetrznyIdentyfikator as identyfikator,
                    AP.Symbol as Aparat,
                    T.Symbol as TypZlecenia,
                    Z.Numer AS NUMER,
                    z.kodkreskowy as KOD,
                    W.Zatwierdzone AS ZATW,
                    PP.Symbol as PP,
                    Pl.Symbol as Platnik,
                    (coalesce(PC.Nazwisko, '') || ' ' || coalesce(PC.Imiona, '') || ' PESEL: ' || coalesce(cast(PC.PESEL as varchar(12)),'')) as PACJENT,
                    (coalesce(L.Nazwisko, '') || ' ' || coalesce(L.Imiona, '')) as Lekarz,
                    B.symbol
            FROM Wykonania w
                    left join zlecenia z on z.id=w.zlecenie
                    left join Pacjenci PC on PC.ID = Z.PACJENT
                    left join TypyZlecen T ON T.ID = Z.TypZlecenia
                    left join Badania B ON B.ID = W.Badanie
                    left join Pracownie P ON P.ID = W.PRACOWNIA
                    left join GRUPYPRACOWNI GP on GP.ID = P.GRUPA
                    left join GrupyBadan GB on GB.id = B.GRUPA
                    left join Oddzialy PP on Z.Oddzial = PP.ID
                    left join Platnicy PL on W.Platnik = PL.ID
                    left join GRUPYPLATNIKOW GPL on GPL.ID = PL.GRUPA
                    left join Lekarze L on Z.Lekarz = L.ID
                    left join Pracownicy PR on PR.ID = Z.PC
                    left join wyniki wy on wy.wykonanie = w.id
                    left join aparaty ap on ap.id=w.aparat
            WHERE
                    W.DataRejestracji between ? and ? 
                    and (W.Wydrukowane is null or not exists (select id from WYDRUKIWZLECENIACH wwz where wwz.ZLECENIE=w.zlecenie)) 
                    and b.pakiet = '0' 
                    and W.Zatwierdzone < 'TODAY' and T.SYMBOL NOT IN ('K', 'KZ', 'KW')
                    and W.Pracownia in (select prac.id from pracownie prac left join grupypracowni gprac on gprac.id=prac.grupa where (gprac.symbol='WEWN' or prac.symbol in ('X-LIMBA', 'X-LIMSL', 'X-VOLKM')) and prac.symbol <> 'XROZL')
                    and b.symbol not in ('OCENA', 'IDE-SAN', 'MORF5DI', 'NOSICIE', 'BIALPRO', 'SURWLAS', 'DZM', 'POS-VIT', 'RCKIK', 'KARTA', 'ALER45', 'ALER-SC', 'ALE22GG', 'ALE22G4', 'ALE87GG', 'ALE87G4', 'AL261GG', 'AL261G4', 'IZOLDNA', 'H-HE5', 'H-HE10', 'H-APES', 'H-SKRAW', 'ALER44G', 'ALE44G4', 'ALER-SC', 'ALE22G4', 'ALE22GG', 'ALE87G4', 'ALE87GG', 'ALER276', 'AL261G4')  and b.SYMBOL not like '%OPR-%' 
                    and w.BLADWYKONANIA is null and w.PLATNE = 1 and W.anulowane is null and gb.SYMBOL not in ('TECHNIC', 'DOPLATY', 'INNE', 'SEROL') 
                    and w.WYSLANEZLECENIE is null and ((GPL.Symbol not like '%KONT%' and PL.Nazwa not like '%Serwis%') or w.platnik is null)
                    and not exists (select id from wykonania where zlecenie=W.zlecenie and badanie=w.badanie and material=w.material and powtorka='1')
                    and wy.ukryty = '0' and wy.wyniktekstowy is not null
            ) raport
    left join wydrukiwzleceniach wwz on wwz.zlecenie=raport.id and wwz.del = 0
    group by 1,2,3,4,5,6,7,8,9,10,11
    ORDER BY Data, Numer;
"""

MENU_ENTRY = "Zlecenia niepodpisane"

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="Wykaz zleceń nie podpisanych (wyniki zatwierdzone w dniu dzisiejszym nie są uwzględniane), filtr wg dat rejestracji."),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', pokaz_nieaktywne=True),
    DateInput(field='dataod', title='Data początkowa', default='-31D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
    Switch(field='bezdoc', title='Tylko zlecenia bez dokumentów sprawozdań'),
    # HBox(
    #     VBox(
    #         Switch(field="bezhistopa", title="Bez Histopatologii"),
    #         Switch(field="tylkohist", title="Tylko Histopatologia"),
    #     ),
    #     VBox(
    #         Switch(field="bezbakter", title="Bez Bakteriologii"),
    #         Switch(field="tylkobakter", title="Tylko Bakteriologia"),
    #     )
    # )
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    # if params['bezhistopa'] and params['tylkohist']:
    #     raise ValidationError('Bez histopatologii i tylko histopatologia?')
    # if params['bezbakter'] and params['tylkobakter']:
    #     raise ValidationError('Bez bakteriologii i tylko bakteriologia?')
    validate_date_range(params['dataod'], params['datado'], 90)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_pojedynczy'
    }
    report.create_task(task)
    report.save()
    return report


def raport_pojedynczy(task_params):
    params = task_params['params']
    sql = SQL
    if params['bezdoc']:
        sql = sql.replace('ORDER BY', 'having count(wwz.id) = 0 ORDER BY')
    header = 'Data Rejestracji,Numer,Kod kreskowy,Nr zewnętrzny,Aparat,Data Zatwierdzenia,Typ Zlecenia,Płatnik,Zleceniodawca,Pacjent,Lekarz,Badania,Ile dok. w zleceniu'.split(
        ',')
    with get_centrum_connection(task_params['target']) as conn: # TODO: czy ma być fresh?
        cols, rows = conn.raport_z_kolumnami(sql, [params['dataod'], params['datado']])
    return [{
        'type': 'table',
        'header': header,
        'data': prepare_for_json(rows)
    }]


"""
zapytania z oryginalnego raportu

górna tabelka:
   $sql  = "SELECT distinct 
	W.DataRejestracji AS DATAR,
	W.Zatwierdzone AS ZATW,
	Z.Numer AS NR,
	T.Symbol AS TZ,
	PL.SYMBOL as PL,
	PP.Symbol as PP,
	(PC.Nazwisko || ' ' || PC.Imiona || ' ' || coalesce(cast(PC.PESEL as varchar(20)),'')) as PACJENT,  
	(L.Nazwisko || ' ' || L.Imiona) AS LEKARZ,
	(cast(list(trim(B.Symbol), ' ') as varchar(2000))) as BADANIA
FROM Wykonania W
JOIN Zlecenia Z ON Z.ID = W.Zlecenie
left join Pacjenci PC on PC.ID = Z.PACJENT
left join TypyZlecen T ON T.ID = Z.TypZlecenia
left join Badania B ON B.ID = W.Badanie
left join Pracownie P ON P.ID = W.PRACOWNIA
left join GRUPYPRACOWNI GP on GP.ID = P.GRUPA
left join GrupyBadan GB on GB.id = B.GRUPA
left join Oddzialy PP on Z.Oddzial = PP.ID
left join Platnicy PL on W.Platnik = PL.ID
left join  GRUPYPLATNIKOW GPL on GPL.ID = PL.GRUPA
left join Lekarze L on Z.Lekarz = L.ID
left join Pracownicy PR on PR.ID = Z.PC
left join ksiegi ks on ks.id=z.ksiega
join (
select z.id  ZlecenieBezPliku, WZ.Zlecenie 
FROM Zlecenia Z left join WYDRUKIWZLECENIACH WZ 
on Z.ID = WZ.Zlecenie where 
Z.DataRejestracji  between " . "'{$od}'" . " AND " . "'{$do}'" . "
group by Z.id, WZ.Zlecenie ) as ZBP on ZBP.ZlecenieBezPliku = Z.id 
WHERE
 ZBP.Zlecenie  is null and p.symbol not in ('X-MAINZ')
 and W.DataRejestracji BETWEEN " . "'{$od}'" . " AND " . "'{$do}'" . " AND b.symbol not in ('CYTOLOG', 'NOSICIE', 'MKAT-DM', 'CMV-PCR', 'HLAB27', 'BIALPRO', 'SURWLAS', 'DZM', 'POS-VIT', 'RCKIK', 'KARTA', 'ALER45', 'IZOLDNA') and b.nazwa not like '%Barwienie%' and b.SYMBOL not like '%OPR-%' and 
  W.Zatwierdzone < 'TODAY' and T.SYMBOL NOT IN ('K', 'KZ', 'KW') and gb.SYMBOL not in ('TECHNIC', 'DOPLATY', 'INNE', 'SEROL') and ";
if 	($_GET['tylkohistopa'] == 'tak') {
	$sql .= "KS.klasa = 'C' and ";
} else if ($_GET['tylkobakter'] == 'tak') {
	$sql .= "KS.klasa = 'B' and ";
} else {	
	if ($_GET['histopa'] == 'tak') {
		$sql .= "( KS.klasa <> 'C' or Z.ksiega is null ) and ";
	}	
	if ($_GET['bakter'] == 'tak') {
		$sql .= "( KS.klasa <> 'B' or Z.ksiega is null ) and ";
	}		
}
if 	($platnik != '') {
	$platnik = strtoupper($platnik);
	$sql.= "Pl.symbol like '%" . "{$platnik}" . "%' and ";
}
$sql .= "b.pakiet = 0 and b.SYMBOL not like '%OPR-%'
  and (GP.SYMBOL in ('WEWN', 'ALAB') or P.Symbol = 'X-LIMBA' )
  and w.BLADWYKONANIA is null and w.PLATNE = 1 and W.anulowane is null
  and w.WYSLANEZLECENIE is null and GPL.Symbol not like '%KONT%' and PL.Nazwa not like '%Serwis%'
Group by w.DataRejestracji, W.Zatwierdzone, Z.Numer, T.symbol, Pl.symbol, PP.Symbol, Pc.Nazwisko, Pc.imiona, Pc.pesel, L.Nazwisko, L.Imiona
ORDER BY W.DataRejestracji, Z.Numer; ";



dolna tabelka:
$sqlNW = "select ID, DATAR, NR, ZATW, TZ, PL, PP, PACJENT, LEKARZ, 
(cast(list(trim(Symbol), ' ') as varchar(2000))) as BADANIA
from (
  SELECT distinct 
	Z.id AS ID,
	W.DataRejestracji AS DATAR,
	W.Zatwierdzone AS ZATW,
	Z.Numer AS NR,
	T.Symbol AS TZ,
	PL.SYMBOL as PL,
	PP.Symbol as PP,
	(PC.Nazwisko || ' ' || PC.Imiona || ' ' || coalesce(cast(PC.PESEL as varchar(20)),'')) as PACJENT,  
	(L.Nazwisko || ' ' || L.Imiona) AS LEKARZ,
	B.Symbol
FROM Wykonania W
left join Zlecenia Z ON Z.ID = W.Zlecenie
left join Pacjenci PC on PC.ID = Z.PACJENT
left join TypyZlecen T ON T.ID = Z.TypZlecenia
left join Badania B ON B.ID = W.Badanie
left join Pracownie P ON P.ID = W.PRACOWNIA
left join GRUPYPRACOWNI GP on GP.ID = P.GRUPA
left join GrupyBadan GB on GB.id = B.GRUPA
left join Oddzialy PP on Z.Oddzial = PP.ID
left join Platnicy PL on W.Platnik = PL.ID
left join  GRUPYPLATNIKOW GPL on GPL.ID = PL.GRUPA
left join Lekarze L on Z.Lekarz = L.ID
left join Pracownicy PR on PR.ID = Z.PC
left join wyniki wy on wy.wykonanie = w.id
left join ksiegi ks on ks.id=z.ksiega
WHERE
 W.DataRejestracji BETWEEN " . "'{$od}'" . " AND " . "'{$do}'" . "
 AND W.Wydrukowane is null and b.pakiet = '0' and p.symbol not in ('X-MAINZ') and
 not exists (select id from wykonania where DataRejestracji BETWEEN " . "'{$od}'" . " AND " . "'{$do}'" . " and zlecenie=W.zlecenie and badanie=w.badanie and material=w.material and powtorka='1') and
  W.Zatwierdzone < 'TODAY' and T.SYMBOL NOT IN ('K', 'KZ', 'KW') 
  and b.nazwa not like '%opłata%' and b.symbol not in ('MORF5DI', 'CYTOLOG', 'NOSICIE', 'MKAT-DM', 'CMV-PCR', 'HLAB27', 'BIALPRO', 'SURWLAS', 'DZM', 'POS-VIT', 'RCKIK', 'KARTA', 'ALER45', 'IZOLDNA')  and b.SYMBOL not like '%OPR-%' 
  and w.BLADWYKONANIA is null and w.PLATNE = 1 and W.anulowane is null
  and gb.SYMBOL not in ('TECHNIC', 'DOPLATY', 'INNE', 'SEROL') and ";
if 	($_GET['tylkohistopa'] == 'tak') {
	$sqlNW .= "KS.klasa = 'C' and ";
} else if ($_GET['tylkobakter'] == 'tak') {
	$sqlNW .= "KS.klasa = 'B' and ";
} else {	
	if ($_GET['histopa'] == 'tak') {
		$sqlNW .= "( KS.klasa <> 'C' or Z.ksiega is null ) and ";
	}	
	if ($_GET['bakter'] == 'tak') {
		$sqlNW .= "( KS.klasa <> 'B' or Z.ksiega is null ) and ";
	}		
}
if 	($platnik != '') {
	$platnik = strtoupper($platnik);
	$sqlNW .= "Pl.symbol like '%" . "{$platnik}" . "%' and ";
}
$sqlNW .= "w.WYSLANEZLECENIE is null and GPL.Symbol not like '%KONT%' and PL.Nazwa not like '%Serwis%'
  and wy.ukryty = '0' and (GP.SYMBOL in ('WEWN', 'ALAB') or P.Symbol = 'X-LIMBA' )
Group by z.id, w.DataRejestracji, W.Zatwierdzone, Z.Numer, T.symbol, Pl.symbol, PP.Symbol, Pc.Nazwisko, Pc.imiona, Pc.pesel, L.Nazwisko, L.Imiona, B.Symbol
)
group by ID, DATAR, NR, ZATW, TZ, PL, PP, PACJENT, LEKARZ
ORDER BY DATAR, NR; ";


tabelka górna:
filtr po dacie rejestracji, zatwierdzone nie dzisiaj, nie kontrolne, techniczne, dopłaty serologiczne itd
wykonania.wyslanezlecenie is null
join ze "zleceniami bez pliku" -  zlecenia z wydrukamiwzleceniach???
ale zleceniebezpliku.zlecenie musi być null

tabelka dolna:
wykonania.wydrukowane is null




Zapytania z raportu mailowego:

   select 
            ID, DATA, NUMER, ZATW, PP, Pacjent, PESEL, KOD,
            (cast(list(trim(Symbol), ' ') as varchar(2000))) as BADANIA
    from (
            SELECT
                    Z.id AS ID,
                    W.DataRejestracji AS DATA,
                    Z.Numer AS NUMER,
                    z.kodkreskowy as KOD,
                    W.Zatwierdzone AS ZATW,
                    PP.Symbol as PP,
                    (PC.Nazwisko || ' ' || PC.Imiona) as PACJENT,
                    coalesce(cast(PC.PESEL as varchar(12)),'') as PESEL,
                    B.symbol
            FROM Wykonania w
                    left join zlecenia z on z.id=w.zlecenie
                    left join Pacjenci PC on PC.ID = Z.PACJENT
                    left join TypyZlecen T ON T.ID = Z.TypZlecenia
                    left join Badania B ON B.ID = W.Badanie
                    left join Pracownie P ON P.ID = W.PRACOWNIA
                    left join GRUPYPRACOWNI GP on GP.ID = P.GRUPA
                    left join GrupyBadan GB on GB.id = B.GRUPA
                    left join Oddzialy PP on Z.Oddzial = PP.ID
                    left join Platnicy PL on W.Platnik = PL.ID
                    left join GRUPYPLATNIKOW GPL on GPL.ID = PL.GRUPA
                    left join Lekarze L on Z.Lekarz = L.ID
                    left join Pracownicy PR on PR.ID = Z.PC
                    left join wyniki wy on wy.wykonanie = w.id
            WHERE
                    W.DataRejestracji >= cast(addHour(current_timestamp, -744) as date) and
                    W.Wydrukowane is null and b.pakiet = '0' 
                    and W.Zatwierdzone < 'TODAY' and T.SYMBOL NOT IN ('K', 'KZ', 'KW')
                    and W.Pracownia in (select prac.id from pracownie prac left join grupypracowni gprac on gprac.id=prac.grupa where (gprac.symbol='WEWN' or prac.symbol in ('X-LIMBA', 'X-LIMSL', 'X-VOLKM')) and prac.symbol <> 'XROZL')
                    and b.symbol not in ('OCENA', 'IDE-SAN', 'MORF5DI', 'NOSICIE', 'BIALPRO', 'SURWLAS', 'DZM', 'POS-VIT', 'RCKIK', 'KARTA', 'ALER45', 'ALER-SC', 'ALE22GG', 'ALE22G4', 'ALE87GG', 'ALE87G4', 'AL261GG', 'AL261G4', 'IZOLDNA', 'H-HE5', 'H-HE10', 'H-APES', 'H-SKRAW', 'ALER44G', 'ALE44G4', 'ALER-SC', 'ALE22G4', 'ALE22GG', 'ALE87G4', 'ALE87GG', 'ALER276', 'AL261G4')  and b.SYMBOL not like '%OPR-%' 
                    and w.BLADWYKONANIA is null and w.PLATNE = 1 and W.anulowane is null and gb.SYMBOL not in ('TECHNIC', 'DOPLATY', 'INNE', 'SEROL') 
                    and w.WYSLANEZLECENIE is null and ((GPL.Symbol not like '%KONT%' and PL.Nazwa not like '%Serwis%') or w.platnik is null)
                    and not exists (select id from wykonania where zlecenie=W.zlecenie and badanie=w.badanie and material=w.material and powtorka='1')
                    and wy.ukryty = '0' and wy.wyniktekstowy is not null
                    Group by z.id, W.DataRejestracji, W.Zatwierdzone, Z.Numer, PP.Symbol, Pc.Nazwisko, Pc.imiona, Pc.pesel, B.Symbol, z.kodkreskowy
            )
    group by ID, DATA, NUMER, ZATW, PP, Pacjent, PESEL, KOD
    ORDER BY Data, Numer;



"""
