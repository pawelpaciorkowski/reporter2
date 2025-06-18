import base64
import datetime
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch, BadanieSearch, Select
from helpers.validators import validate_date_range
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_and_cache, first_or_none, empty

MENU_ENTRY = 'Badanie w laboratorium'

CACHE_TIMEOUT = 7200

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    TextInput(field='badanie', title="Symbol badania"),
))

SQL_BADANIE = """
    select b.*, trim(gb.symbol) as grupa, gb.nazwa as grupa_nazwa,
        trim(prac.symbol) as pracownia, prac.nazwa as pracownia_nazwa,
        trim(gdr.symbol) as gruparej, (coalesce(gdr.nazwa, '') || (case when gdr.bezrejestracjiinternetowej=1 then ' [BEZ REJESTRACJI]' else '' end)) as gruparej_nazwa,
        trim(gdd.symbol) as grupadruk, gdd.nazwa as grupadruk_nazwa,
        trim(ks.symbol) as ksiega, ks.nazwa as ksiega_nazwa
    from badania b
    left join grupybadan gb on gb.id=b.grupa
    left join grupydorejestracji gdr on gdr.id=b.grupadorejestracji
    left join grupydodrukowania gdd on gdd.id=b.grupadodrukowania
    left join pracownie prac on prac.id=b.pracownia
    left join ksiegi ks on ks.id=b.ksiega
    where b.symbol=? and b.del=0
"""

SQL_MWB = """
    select 
        trim(m.symbol) as material, m.nazwa as material_nazwa,
        trim(gdr.symbol) as gruparej, (coalesce(gdr.nazwa, '') || (case when gdr.bezrejestracjiinternetowej=1 then ' [BEZ REJESTRACJI]' else '' end)) as gruparej_nazwa,
        coalesce(cast(gdr.rodzaj as varchar(8)), '') || ' ' || coalesce(gdrr.symbol, '') as gruparej_rodzaj, gdrr.nazwa as gruparej_rodzaj_nazwa,
        trim(gdd.symbol) as grupadruk, gdd.nazwa as grupadruk_nazwa,
        trim(ks.symbol) as ksiega, ks.nazwa as ksiega_nazwa,
        mwb.ukryty, mwb.NIEWYMAGACKODUKRESKOWEGO, mwb.NIEWYMAGACUNIKALNEGO, mwb.PRZENOSICKODZEZLECENIA, mwb.AUTOMATYCZNADYSTRYBUCJA, mwb.CZASMAKSYMALNY
    from materialywbadaniach mwb
    left join materialy m on m.id=mwb.MATERIAL
    left join GRUPYDOREJESTRACJI gdr on gdr.id=mwb.grupa
    left join rodzajegrup gdrr on gdrr.id=gdr.rodzaj
    left join GRUPYDODRUKOWANIA gdd on gdd.id=mwb.GRUPADODRUKOWANIA
    left join ksiegi ks on ks.id=mwb.ksiega
    where mwb.badanie=? and mwb.del=0
    order by mwb.KOLEJNOSC
"""

SQL_ICENTRUM = """
select B.ID, B.Nazwa, B.NazwaAlternatywna, B.Symbol, B.CzasMaksymalny, B.Pakiet, B.ZerowacCeny, B.BezRejestracji, B.BezRejestracjiInternetowej, coalesce(B.Bezplatne, 0) as Bezplatne, coalesce(B.Ukryte, 0) as Ukryte, coalesce(MB.Ukryty, 0) as Ukryte2, 
        GR.ID as Grupa, GR.Symbol as GrupySymbol, GR.Nazwa as GrupyNazwa, GR.Rodzaj as GrupyRodzaj, GR.BezRejestracjiInternetowej as GrupyBezRejestracjiInternetowej, coalesce(GR.Del, 0) as GrupyDel, 
        coalesce(MB.Ksiega, B.Ksiega) as Ksiega, B.OsobneZlecenie as BadaniaOsobneZlecenie, M.OsobneZlecenie as MaterialyOsobneZlecenie, 
        M.ID as Material, M.Nazwa as MaterialyNazwa, M.NazwaAlternatywna as MaterialyNazwaAlternatywna, M.Symbol as MaterialySymbol, MB.Kolejnosc
from Badania B 
        left outer join MaterialyWBadaniach MB on MB.Badanie = B.ID and MB.DEL = 0 
        left outer join Materialy M on M.ID = MB.Material 
        left outer join GrupyDoRejestracji GR on GR.ID = coalesce(MB.Grupa, B.GrupaDoRejestracji) 
        where coalesce(B.Rodzaj, 0) in (0,1,4,8,11, 12) and B.DEL = 0 and B.BezRejestracji = 0 and b.id=? and
        coalesce(B.BezRejestracjiInternetowej, 0) = 0 and coalesce(B.Ukryte, 0) = 0 and 
        coalesce(B.Bezplatne, 0) = 0 and 
        coalesce(MB.Ukryty, 0) = 0
        order by mb.kolejnosc
"""

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if empty(params['badanie']):
        raise ValidationError("Podaj symbol badania")
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego labu")
    params['badanie'] = params['badanie'].upper().strip()
    report = TaskGroup(__PLUGIN__, params)
    for lab in params['laboratoria']:
        lab_task = {
            'type': 'centrum',
            'priority': 0,
            'target': lab,
            'params': params,
            'function': 'raport_lab',
        }
        report.create_task(lab_task)
    report.save()
    return report

TYTULY_POL = {
    'dc': 'Ost. zmiana'
}

def wartosc_pola(fld, val):
    return val

def raport_lab(task_params):
    params = task_params['params']
    symbol = params['badanie']
    lab = task_params['target']
    res = []
    with get_centrum_connection(lab) as conn:
        rows = conn.raport_slownikowy(SQL_BADANIE, [symbol])
        if len(rows) == 0:
            return {
                'type': 'error',
                'text': 'Nie znaleziono badania o podanym symbolu',
            }
        wiersz_badania = rows[0]
        wiersze_info = []
        for fld in ('symbol nazwa nazwaalternatywna kod rodzaj akredytacja pakiet rejestrowac zerowacceny procedura niewymagackodukreskowego niepublikowac serwis dorozliczen bezrejestracji ukryte niewymagacunikalnego przenosickodzezlecenia automatycznadystrybucja rodzaj czasmaksymalny bezrejestracjiinternetowej osobnezlecenie klasy bezplatne podlozaidzialania dc'.split(' ')):
            if fld in wiersz_badania and not empty(wiersz_badania[fld]):
                wiersze_info.append((TYTULY_POL.get(fld, fld), wartosc_pola(fld, wiersz_badania[fld])))
        for fld in ('grupa pracownia gruparej grupadruk ksiega'.split(' ')):
            if fld in wiersz_badania and not empty(wiersz_badania[fld]):
                wiersze_info.append((TYTULY_POL.get(fld, fld), '%s - %s' % (wiersz_badania[fld], wiersz_badania[fld+'_nazwa'])))
        res.append({
            'type': 'vertTable',
            'title': '%s - Badanie' % lab,
            'data': prepare_for_json([{'title': w[0], 'value': str(w[1])} for w in wiersze_info]),
        })
        cols, rows = conn.raport_z_kolumnami(SQL_MWB, [wiersz_badania['id']])
        res.append({
            'type': 'table',
            'title': '%s - Materiały w badaniach' % lab,
            'header': cols,
            'data': prepare_for_json(rows),
        })
        # cols, rows = conn.raport_z_kolumnami(SQL_ICENTRUM, [wiersz_badania['id']])
        # res.append({
        #     'type': 'table',
        #     'title': 'Do icentrum',
        #     'header': cols,
        #     'data': prepare_for_json(rows),
        # })
        
    return res