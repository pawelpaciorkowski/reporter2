from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty

MENU_ENTRY = 'Zlecenie w bazie'

REQUIRE_ROLE = 'C-ADM'
ADD_TO_ROLE = ['R-MDO', 'L-PRAC']

SQL_ZL_KOD = """
    SELECT z.ID, z.DATAREJESTRACJI as "Data rej.", z.NUMER as "Nr",
        z.system, z.sysid,
        z.GODZINAREJESTRACJI as "Godz. rej.", 
        z.PELENNUMERKSIEGI as "Nr ks.",
        coalesce(o.SYMBOL, '') || ' - ' || coalesce(o.NAZWA, '') as "Zleceniodawca", 
        coalesce(p.SYMBOL, '') || ' - ' || coalesce(p.NAZWA, '') as "Płatnik", 
        (coalesce(PA.Nazwisko, '') || ' ' || coalesce(PA.Imiona, '') || ', ' || coalesce(PA.PESEL, '') ) as "Pacjent",
        (coalesce(L.Nazwisko, '') || ' ' || coalesce(L.Imiona, '')) as "Lekarz",
        z.dc as "dc",
        coalesce(Pr.Logowanie, '') || ' - ' || coalesce(Pr.Nazwisko, '') as "Rejestrator",
        coalesce(Kan.Symbol, '') || ' - ' || coalesce(Kan.Nazwa, '') as "Kanał intern."
    from zlecenia z
        left join ODDZIALY o on o.id=z.ODDZIAL
        left join PLATNICY p on p.id=z.PLATNIK
        left join lekarze l on l.id=z.lekarz
        left join pacjenci pa on pa.id=z.pacjent
        left join pracownicy pr on pr.id=z.pracownikodrejestracji
        left join kanaly kan on kan.id=pr.kanalinternetowy
    where (z.kodkreskowy like ?) or z.id in (select zlecenie from wykonania where kodkreskowy=?) 
        order by z.DATAREJESTRACJI, z.numer"""

SQL_ZL_DATA_NR = """
    SELECT z.ID, z.DATAREJESTRACJI as "Data rej.", z.NUMER as "Nr",
        z.system, z.sysid,
        z.GODZINAREJESTRACJI as "Godz. rej.", 
        z.PELENNUMERKSIEGI as "Nr ks.",
        coalesce(o.SYMBOL, '') || ' - ' || coalesce(o.NAZWA, '') as "Zleceniodawca", 
        coalesce(p.SYMBOL, '') || ' - ' || coalesce(p.NAZWA, '') as "Płatnik", 
        (coalesce(PA.Nazwisko, '') || ' ' || coalesce(PA.Imiona, '') || ', ' || coalesce(PA.PESEL, '') ) as "Pacjent",
        (coalesce(L.Nazwisko, '') || ' ' || coalesce(L.Imiona, '')) as "Lekarz",
        z.dc as "dc",
        coalesce(Pr.Logowanie, '') || ' - ' || coalesce(Pr.Nazwisko, '') as "Rejestrator",
        coalesce(Kan.Symbol, '') || ' - ' || coalesce(Kan.Nazwa, '') as "Kanał intern."
    from zlecenia z
        left join ODDZIALY o on o.id=z.ODDZIAL
        left join PLATNICY p on p.id=z.PLATNIK
        left join lekarze l on l.id=z.lekarz
        left join pacjenci pa on pa.id=z.pacjent
        left join pracownicy pr on pr.id=z.pracownikodrejestracji
        left join kanaly kan on kan.id=pr.kanalinternetowy
    where z.datarejestracji=? and z.numer=?
        order by z.DATAREJESTRACJI, z.numer"""

SQL_WYDRUKI = """
    select
        wwz.dc,
        coalesce(Pr.Logowanie, '') || ' - ' || coalesce(Pr.Nazwisko, '') as "Prac. ost. zm.",
        wwz.del,
        wwz.odebrany,
        wwz.odebral,
        wwz.plik,
        wwz.wydrukowany,
        coalesce(Prw.Logowanie, '') || ' - ' || coalesce(Prw.Nazwisko, '') as "Prac. wydr.",
        wwz.wydrukowany2,
        coalesce(Prw2.Logowanie, '') || ' - ' || coalesce(Prw2.Nazwisko, '') as "Prac. wydr. 2",
        wwz.wyslany,
        wwz.podpisany,
        wwz.odwolanywydrukowany,
        wwz.wyslanyhl7
    from WYDRUKIWZLECENIACH wwz
    left join pracownicy pr on pr.id=wwz.PC
    left join pracownicy prw on prw.id=wwz.PRACOWNIKODWYDRUKOWANIA
    left join pracownicy prw2 on prw2.id=wwz.PRACOWNIKODWYDRUKOWANIA2
    where wwz.zlecenie=?
    order by wwz.id
"""

SQL_WYKONANIA = """
    select 
        w.id,
        bad.symbol,
        bad.nazwa,
        mat.symbol,
        w.KODKRESKOWY,
        w.dc as "Ost. zm.",
        coalesce(Pr.Logowanie, '') || ' - ' || coalesce(Pr.Nazwisko, '') as "Prac ost. zm.",
        prac.symbol as "Pracownia",
        ap.symbol as "Aparat",
        bl.symbol as "Błąd",
        w.ANULOWANE as "Anulowane",
        coalesce(Pra.Logowanie, '') || ' - ' || coalesce(Pra.Nazwisko, '') as "Prac anul.",
        pa.Symbol as "Pow. anul.",
        w.liczbapowtorzen as "L. powt.",
        w.POWTORKA as "Powtórka",
        w.dorejestrowane as "Dorej.",
        w.platne as "Płatne",
        w.cena as "Cena",
        pak.symbol as "Pakiet",
        w.GODZINA as "Godz. pobr.",
        w.DYSTRYBUCJA as "Godz. przyj.",
        w.wykonane as "Wykonane",
        coalesce(Prw.Logowanie, '') || ' - ' || coalesce(Prw.Nazwisko, '') as "Prac wyk.",
        w.zatwierdzone as "Zatwierdzone",
        coalesce(Prz.Logowanie, '') || ' - ' || coalesce(Prz.Nazwisko, '') as "Prac zatw.",
        w.ROZLICZONE as "Rozliczone",
        w.WYSLANEROZLICZENIE as "Wysł. rozl.",
        w.Wydrukowane as "Wydrukowane"
        
    from wykonania w
    left join badania bad on bad.id=w.BADANIE
    left join materialy mat on mat.id=w.MATERIAL
    left join wykonania wp on wp.id=w.PAKIET
    left join badania pak on pak.id=wp.BADANIE
    left join POWODYANULOWANIA pa on pa.id=w.POWODANULOWANIA
    left join BLEDYWYKONANIA bl on bl.id=w.BLADWYKONANIA
    left join pracownicy pr on pr.id=w.pc
    left join pracownicy pra on pra.id=w.PRACOWNIKODANULOWANIA
    left join pracownicy prw on prw.id=w.PRACOWNIKODWYKONANIA
    left join pracownicy prz on prz.id=w.PRACOWNIKODZATWIERDZENIA
    left join pracownie prac on prac.id=w.pracownia
    left join aparaty ap on ap.id=w.APARAT
    
    where w.zlecenie=?
    order by w.id
"""

SQL_WYNIKI = """
    select
    
        y.dc as "Ost. zm",
        y.del,
        
        par.symbol || ' - ' || par.nazwa as "Parametr",
        y.WYNIKLICZBOWY as "Wynik liczbowy",
        par.FORMAT as "Format.",
        y.WYNIKTEKSTOWY as "Wynik tekstowy",
        y.opis as "Opis"
        
        -- y.*
        
        
    from wyniki y
    left join parametry par on par.id=y.PARAMETR
    
    where y.zlecenie=? and y.wykonanie=?
    order by y.id
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Proszę wybrać laboratorium/laboratoria oraz podać kod kreskowy lub numer i datę zlecenia do sprawdzenia'),
    LabSelector(multiselect=False, selectall=True, field='laboratorium', title='Laboratorium', pokaz_nieaktywne=True),
    TextInput(field='kodkreskowy', title='Kod kreskowy', helper='min 9 cyfr', autofocus=True,
              validate=lambda x: len(x) >= 9),
    HBox(
        VBox(TextInput(field='numerzl', title='Numer i data zlecenia', desc_title='Numer zlecenia')),
        DateInput(field='datazl', desc_title='Data zlecenia', can_clear=True)
    )
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if not empty(params['kodkreskowy']):
        if not empty(params['numerzl']):
            raise ValidationError('Podaj kod kreskowy albo numer i datę zlecenia')
        if len(params['kodkreskowy']) < 9:
            raise ValidationError('Podaj co najmniej 9 znaków kodu kreskowego')
        params['datazl'] = None
        params['_szukaj'] = 'kod'
    else:
        if empty(params['numerzl']) or empty(params['datazl']):
            raise ValidationError('Podaj kod kreskowy albo datę i numer zlecenia')
        params['_szukaj'] = 'datanr'
    if params['laboratorium'] is None:
        raise ValidationError('Nie wybrano laboratorium')
    lab_task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_lab',
    }
    report.create_task(lab_task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']
    system = task_params['target']
    res = []

    with get_centrum_connection(system, fresh=True) as conn:
        if params['_szukaj'] == 'kod':
            kodkreskowy = params['kodkreskowy'].replace('=', '')
            cols, rows = conn.raport_z_kolumnami(SQL_ZL_KOD, [kodkreskowy[:9] + '%', kodkreskowy])
        elif params['_szukaj'] == 'datanr':
            cols, rows = conn.raport_z_kolumnami(SQL_ZL_DATA_NR, [params['datazl'], params['numerzl']])
        cols = cols[5:]
        for row in rows:
            id = row[0]
            data = row[1]
            nr = row[2]
            system = row[3]
            sys_id = row[4]
            row = row[5:]
            title = "ZLECENIE %d / %s (%d)" % (nr, data, id)
            if sys_id != id:
                title += " (%s:%d)" % (system, sys_id)
            res.append({
                'type': 'table',
                'title': title,
                'header': cols,
                'data': [row],
            })
            colswwz, rowswwz = conn.raport_z_kolumnami(SQL_WYDRUKI, [id])
            res.append({
                'type': 'table',
                'title': ' - wydruki w zleceniach',
                'header': colswwz,
                'data': rowswwz
            })
            colsw, rowsw = conn.raport_z_kolumnami(SQL_WYKONANIA, [id])
            colsw = colsw[4:]
            for roww in rowsw:
                w_id = roww[0]
                bad = roww[1]
                bad_n = roww[2]
                mat = roww[3]
                kod = roww[4]
                title = " - %s - %s" % (bad_n, bad.strip())
                if mat is not None:
                    title += ":" + mat.strip()
                if kod is not None:
                    title += ", " + kod
                res.append({
                    'type': 'table',
                    'title': title,
                    'header': colsw,
                    'data': [roww[4:]],
                })
                colsy, rowsy = conn.raport_z_kolumnami(SQL_WYNIKI, [id, w_id])
                res.append({
                    'type': 'table',
                    'header': colsy,
                    'data': rowsy,
                })
            # TODO: wykonania, wyniki
    return {
        'errors': [],
        'results': prepare_for_json(res),
        'actions': [
            'xlsx',
            {
                'type': 'pdf',
                'landscape': True,
                'base_font_size': '6pt'
            }
        ]
    }
