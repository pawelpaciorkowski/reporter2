from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, NumberInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
import datetime


SQL = """
    select 
            ID, DATA, NUMER, ZATW, PP, Pacjent, PESEL, KOD, 'TODO', 'TODO'
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
                    left outer JOIN Pacjenci PC on PC.ID = Z.PACJENT
                    left outer JOIN TypyZlecen T ON T.ID = Z.TypZlecenia
                    left outer JOIN Badania B ON B.ID = W.Badanie
                    left outer JOIN Pracownie P ON P.ID = W.PRACOWNIA
                    left outer JOIN GRUPYPRACOWNI GP on GP.ID = P.GRUPA
                    left outer JOIN GrupyBadan GB on GB.id = B.GRUPA
                    left outer JOIN Oddzialy PP on Z.Oddzial = PP.ID
                    left outer JOIN Platnicy PL on W.Platnik = PL.ID
                    left outer JOIN GRUPYPLATNIKOW GPL on GPL.ID = PL.GRUPA
                    left outer join Lekarze L on Z.Lekarz = L.ID
                    left outer JOIN Pracownicy PR on PR.ID = Z.PC
                    left outer join wyniki wy on wy.wykonanie = w.id
            WHERE
                    W.DataRejestracji >= cast(addHour(current_timestamp, -744) as date) and
                    W.Wydrukowane is null and b.pakiet = '0' 
                    and W.Zatwierdzone < ? and T.SYMBOL NOT IN ('K', 'KZ', 'KW')
                    and W.Pracownia in (select prac.id from pracownie prac left join grupypracowni gprac on gprac.id=prac.grupa where (gprac.symbol='WEWN' or prac.symbol in ('X-LIMBA', 'X-LIMSL', 'X-VOLKM')) and prac.symbol <> 'XROZL')
                    and b.symbol not in ('OCENA', 'IDE-SAN', 'MORF5DI', 'NOSICIE', 'BIALPRO', 'SURWLAS', 'DZM', 'POS-VIT', 'RCKIK', 'KARTA', 'ALER45', 'ALER-SC', 'ALE22GG', 'ALE22G4', 'ALE87GG', 'ALE87G4', 'AL261GG', 'AL261G4', 'IZOLDNA', 'H-HE5', 'H-HE10', 'H-APES', 'H-SKRAW', 'ALER44G', 'ALE44G4', 'ALER-SC', 'ALE22G4', 'ALE22GG', 'ALE87G4', 'ALE87GG', 'ALER276', 'AL261G4', 'CANPOCP', 'CANPOCA', 'CANPOCN', 'KONALEX', 'RAPAMYC', 'POJEMN')  and b.SYMBOL not like '%OPR-%' 
                    and w.BLADWYKONANIA is null and w.PLATNE = 1 and W.anulowane is null and gb.SYMBOL not in ('TECHNIC', 'DOPLATY', 'INNE', 'SEROL') 
                    and w.WYSLANEZLECENIE is null and ((GPL.Symbol not like '%KONT%' and PL.Nazwa not like '%Serwis%') or w.platnik is null)
                    and not exists (select id from wykonania where zlecenie=W.zlecenie and badanie=w.badanie and material=w.material and powtorka='1')
                    and wy.ukryty = '0' and wy.wyniktekstowy is not null
                    Group by z.id, W.DataRejestracji, W.Zatwierdzone, Z.Numer, PP.Symbol, Pc.Nazwisko, Pc.imiona, Pc.pesel, B.Symbol, z.kodkreskowy
            )
    group by ID, DATA, NUMER, ZATW, PP, Pacjent, PESEL, KOD
    ORDER BY Data, Numer;
    """

SQL_POSTGRES = """
    select 
            ID, DATA, NUMER, ZATW, PP, Pacjent, PESEL, KOD,
            (cast(array_to_string(array_agg(trim(Symbol)), ' ') as varchar(2000))) as BADANIA, Pracownia, Formularze
    from (
            SELECT
                    Z.id AS ID,
                    W.DataRejestracji AS DATA,
                    Z.Numer AS NUMER,
                    z.kodkreskowy as KOD,
                    W.Zatwierdzone AS ZATW,
                    PP.Symbol as PP,
                    trim(p.symbol) as Pracownia,
                    array_to_string(array_agg(distinct trim(f.symbol)), ', ') as formularze,
                    (PC.Nazwisko || ' ' || PC.Imiona) as PACJENT,
                    coalesce(cast(PC.PESEL as varchar(12)),'') as PESEL,
                    B.symbol
            FROM Wykonania w
                    left join zlecenia z on z.id=w.zlecenie
                    left JOIN Pacjenci PC on PC.ID = Z.PACJENT
                    left JOIN TypyZlecen T ON T.ID = Z.TypZlecenia
                    left JOIN Badania B ON B.ID = W.Badanie
                    left JOIN Pracownie P ON P.ID = W.PRACOWNIA
                    left JOIN GRUPYPRACOWNI GP on GP.ID = P.GRUPA
                    left JOIN GrupyBadan GB on GB.id = B.GRUPA
                    left JOIN Oddzialy PP on Z.Oddzial = PP.ID
                    left JOIN Platnicy PL on W.Platnik = PL.ID
                    left JOIN GRUPYPLATNIKOW GPL on GPL.ID = PL.GRUPA
                    left join Lekarze L on Z.Lekarz = L.ID
                    left JOIN Pracownicy PR on PR.ID = Z.PC
                    left join wyniki wy on wy.wykonanie = w.id
                    left join badaniawformularzach bwf on bwf.badanie=b.id and bwf.del=0
                    left join formularze f on f.id=bwf.formularz 
            WHERE
                    W.DataRejestracji >= cast(current_timestamp - interval '744h' as date) and
                    W.Wydrukowane is null and b.pakiet = '0' 
                    and W.Zatwierdzone < %s and T.SYMBOL NOT IN ('K', 'KZ', 'KW')
                    and W.Pracownia in (select prac.id from pracownie prac left join grupypracowni gprac on gprac.id=prac.grupa where (gprac.symbol='WEWN' or prac.symbol in ('X-LIMBA', 'X-LIMSL', 'X-VOLKM')) and prac.symbol <> 'XROZL')
                    and b.symbol not in ('OCENA', 'IDE-SAN', 'MORF5DI', 'NOSICIE', 'BIALPRO', 'SURWLAS', 'DZM', 'POS-VIT', 'RCKIK', 'KARTA', 'ALER45', 'ALER-SC', 'ALE22GG', 'ALE22G4', 'ALE87GG', 'ALE87G4', 'AL261GG', 'AL261G4', 'IZOLDNA', 'H-HE5', 'H-HE10', 'H-APES', 'H-SKRAW', 'ALER44G', 'ALE44G4', 'ALER-SC', 'ALE22G4', 'ALE22GG', 'ALE87G4', 'ALE87GG', 'ALER276', 'AL261G4', 'KONALEX')  and b.SYMBOL not like '%%OPR-%%' 
                    and w.BLADWYKONANIA is null and w.PLATNE = 1 and W.anulowane is null and gb.SYMBOL not in ('TECHNIC', 'DOPLATY', 'INNE', 'SEROL') 
                    and w.WYSLANEZLECENIE is null and ((GPL.Symbol not like '%%KONT%%' and PL.Nazwa not like '%%Serwis%%') or w.platnik is null)
                    and not exists (select id from wykonania where zlecenie=W.zlecenie and badanie=w.badanie and material=w.material and powtorka='1')
                    and wy.ukryty = '0' and wy.wyniktekstowy is not null
                    Group by z.id, W.DataRejestracji, W.Zatwierdzone, Z.Numer, PP.Symbol, Pc.Nazwisko, Pc.imiona, Pc.pesel, B.Symbol, z.kodkreskowy, p.symbol
            ) unique_alias_1
    group by ID, DATA, NUMER, ZATW, PP, Pacjent, PESEL, KOD, Pracownia, Formularze
    ORDER BY Data, Numer;
"""

MENU_ENTRY = "Brak podpisu"

ADD_TO_ROLE = ['L-PRAC']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY + " (wg znaczników wydruku)", panel=VBox(
    InfoText(
        text="""Raport z niepodpisanych badań analogiczny do mailowego, z możliwością ustawienia jak stare mają być zatwierdzone wykonania brane pod uwagę.
        
        """),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    NumberInput(field='minuty', title='Zatwierdzone co najmniej minut temu', default=60),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    if params['minuty'] is None:
        raise ValidationError("Nie podano wieku najstarszych zatwierdzonych")
    if params['minuty'] < 0 or params['minuty'] > 60 * 24 * 5:
        raise ValidationError("Nieprawidłowe minuty")
    params['zatwierdzone'] = datetime.datetime.now() - datetime.timedelta(minutes=params['minuty'])
    params['zatwierdzone'] = params['zatwierdzone'].strftime('%Y-%m-%d %H:%M:%S')
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
    header = 'ID,Data rej.,Numer,Zatwierdzone,Zleceniodawca,Pacjent,PESEL,Kod kreskowy,Badania,Pracownia,Formularze'.split(',')
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(SQL, [params['zatwierdzone']], sql_pg=SQL_POSTGRES)
    return [{
        'type': 'table',
        'header': header,
        'data': prepare_for_json(rows)
    }]
