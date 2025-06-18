from datasources.snr import SNR
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, NumberInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json, empty
from helpers.validators import validate_date_range, validate_symbol
from tasks import TaskGroup, Task
import datetime

MENU_ENTRY = "Brak podpisu - Zawodzie międzylab"

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY + " (wg znaczników wydruku)", panel=VBox(
    InfoText(
        text="""Raport z niepodpisanych badań na Zawodziu, analogiczny do raportu mailowego "Brak podpisu",
            z wysyłek międzylab ze wskazanych labów, wg płatnika międzylaboratoryjnego
        """),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    TextInput(field='zleceniodawca', title='Pojedynczy zleceniodawca (symbol)')
))

SQL_PLATNICY = """
    select l1.symbol as lab1, l2.symbol as lab2, 
        l1.hs->'symbolplatnika' as symbol_platnika_lab1,
        l2.hs->'przedrosteksymbolu' as przedrostek_symbolu_lab2,
        (l2.hs->'przedrosteksymbolu') || (l1.hs->'symbolplatnika') as oczekiwany_platnik_lab1_w_lab2,
        case when pwl.id is not null then 'T' else '' end as symbol_istnieje,
        pl.nazwa as nazwa_platnika,
        pl.id as id_platnika
    from laboratoria l1
    join laboratoria l2 on 1=1
    left join platnicywlaboratoriach pwl on pwl.symbol=(l2.hs->'przedrosteksymbolu') || (l1.hs->'symbolplatnika') and not pwl.del and pwl.laboratorium=l2.symbol
    left join platnicy pl on pl.id=pwl.platnik
    where not l1.del and not l2.del and l1.aktywne and l2.aktywne
        and l1.id != l2.id and l2.symbol='ZAWODZI'
    order by 1, 2
"""

SQL = """
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
                    left outer JOIN Oddzialy PP on Z.Oddzial = PP.ID
                    left outer JOIN Platnicy PL on Z.Platnik = PL.ID
                    left outer JOIN Pacjenci PC on PC.ID = Z.PACJENT
                    left outer JOIN TypyZlecen T ON T.ID = Z.TypZlecenia
                    left outer JOIN Badania B ON B.ID = W.Badanie
                    left outer JOIN Pracownie P ON P.ID = W.PRACOWNIA
                    left outer JOIN GRUPYPRACOWNI GP on GP.ID = P.GRUPA
                    left outer JOIN GrupyBadan GB on GB.id = B.GRUPA
                    left outer JOIN GRUPYPLATNIKOW GPL on GPL.ID = PL.GRUPA
                    left outer join Lekarze L on Z.Lekarz = L.ID
                    left outer JOIN Pracownicy PR on PR.ID = Z.PC
                    left outer join wyniki wy on wy.wykonanie = w.id
            WHERE
                    W.DataRejestracji >= cast(addHour(current_timestamp, -744) as date) and
                    W.Wydrukowane is null and b.pakiet = '0' 
                    and $WARUNEK$
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
            (cast(array_to_string(array_agg(trim(Symbol)), ' ') as varchar(2000))) as BADANIA
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
                    left outer JOIN Oddzialy PP on Z.Oddzial = PP.ID
                    left outer JOIN Platnicy PL on Z.Platnik = PL.ID
                    left outer JOIN Pacjenci PC on PC.ID = Z.PACJENT
                    left outer JOIN TypyZlecen T ON T.ID = Z.TypZlecenia
                    left outer JOIN Badania B ON B.ID = W.Badanie
                    left outer JOIN Pracownie P ON P.ID = W.PRACOWNIA
                    left outer JOIN GRUPYPRACOWNI GP on GP.ID = P.GRUPA
                    left outer JOIN GrupyBadan GB on GB.id = B.GRUPA
                    left outer JOIN GRUPYPLATNIKOW GPL on GPL.ID = PL.GRUPA
                    left outer join Lekarze L on Z.Lekarz = L.ID
                    left outer JOIN Pracownicy PR on PR.ID = Z.PC
                    left outer join wyniki wy on wy.wykonanie = w.id
            WHERE
                    W.DataRejestracji >= cast(current_timestamp - interval '744h' as date) and
                    W.Wydrukowane is null and b.pakiet = '0' 
                    and $WARUNEK$
                    and W.Zatwierdzone < %s and T.SYMBOL NOT IN ('K', 'KZ', 'KW')
                    and W.Pracownia in (select prac.id from pracownie prac left join grupypracowni gprac on gprac.id=prac.grupa where (gprac.symbol='WEWN' or prac.symbol in ('X-LIMBA', 'X-LIMSL', 'X-VOLKM')) and prac.symbol <> 'XROZL')
                    and b.symbol not in ('OCENA', 'IDE-SAN', 'MORF5DI', 'NOSICIE', 'BIALPRO', 'SURWLAS', 'DZM', 'POS-VIT', 'RCKIK', 'KARTA', 'ALER45', 'ALER-SC', 'ALE22GG', 'ALE22G4', 'ALE87GG', 'ALE87G4', 'AL261GG', 'AL261G4', 'IZOLDNA', 'H-HE5', 'H-HE10', 'H-APES', 'H-SKRAW', 'ALER44G', 'ALE44G4', 'ALER-SC', 'ALE22G4', 'ALE22GG', 'ALE87G4', 'ALE87GG', 'ALER276', 'AL261G4', 'KONALEX')  and b.SYMBOL not like '%%OPR-%%' 
                    and w.BLADWYKONANIA is null and w.PLATNE = 1 and W.anulowane is null and gb.SYMBOL not in ('TECHNIC', 'DOPLATY', 'INNE', 'SEROL') 
                    and w.WYSLANEZLECENIE is null and ((GPL.Symbol not like '%%KONT%%' and PL.Nazwa not like '%%Serwis%%') or w.platnik is null)
                    and not exists (select id from wykonania where zlecenie=W.zlecenie and badanie=w.badanie and material=w.material and powtorka='1')
                    and wy.ukryty = '0' and wy.wyniktekstowy is not null
                    Group by z.id, W.DataRejestracji, W.Zatwierdzone, Z.Numer, PP.Symbol, Pc.Nazwisko, Pc.imiona, Pc.pesel, B.Symbol, z.kodkreskowy
            ) unique_alias_1
    group by ID, DATA, NUMER, ZATW, PP, Pacjent, PESEL, KOD
    ORDER BY Data, Numer;
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    platnicy = []
    for lab in params['laboratoria']:
        if lab == 'ZAWODZI':
            raise ValidationError("Na Zawodziu nie są rejestrowane zlecenia wysyłkowe z Zawodzia...")
    snr = SNR()
    for row in snr.dict_select(SQL_PLATNICY):
        if row['lab1'][:7] in params['laboratoria']:
            if row['symbol_istnieje'] != 'T':
                raise ValidationError("Brak płatnika wewnętrznego %s na Zawodziu" % row['lab1'])
            platnicy.append(row['oczekiwany_platnik_lab1_w_lab2'])
    params['platnicy'] = platnicy
    if not empty(params['zleceniodawca']):
        params['zleceniodawca'] = params['zleceniodawca'].upper().strip()
        validate_symbol(params['zleceniodawca'])
    else:
        params['zleceniodawca'] = None
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'centrum',
        'priority': 1,
        'target': 'ZAWODZI',
        'params': params,
        'function': 'raport_pojedynczy'
    }
    report.create_task(task)
    report.save()
    return report


def raport_pojedynczy(task_params):
    params = task_params['params']
    res = []
    sql = SQL
    sql_pg = SQL_POSTGRES
    zatwierdzone = datetime.datetime.now() - datetime.timedelta(minutes=60)
    sql_params = []
    warunek = []
    warunek.append('pl.symbol in %s')
    sql_params.append(tuple(params['platnicy']))
    info_text = 'Raport z bazy %s, dla płatników %s' % (task_params['target'], ', '.join(params['platnicy']))
    if params['zleceniodawca'] is not None:
        info_text += ', zleceniodawca: ' + params['zleceniodawca']
        warunek.append('pp.symbol=%s')
        sql_params.append(params['zleceniodawca'])
    sql_params.append(zatwierdzone)
    res.append({
        'type': 'info',
        'text': info_text
    })

    sql = sql.replace('$WARUNEK$', ' and '.join(warunek))
    sql_pg = sql_pg.replace('$WARUNEK$', ' and '.join(warunek))
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_params, sql_pg=sql_pg)
    header = 'ID,Data rej.,Numer,Zatwierdzone,Zleceniodawca,Pacjent,PESEL,Kod kreskwoy,Badania'.split(',')
    res.append({
        'type': 'table',
        'header': header,
        'data': prepare_for_json(rows)
    })
    return res
