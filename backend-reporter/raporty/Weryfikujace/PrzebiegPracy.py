import time

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError, Switch
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty, odpiotrkuj

MENU_ENTRY = 'Przebieg pracy'

ADD_TO_ROLE = ['L-REJ']

"""

Sprawdzanie obciążenia raportami:
    select z.opis, o.nazwisko, count(z.id)
    from log_zdarzenia z
    left join osoby o on o.id=z.obj_id
    where z.typ='REPGEN' and z.ts >= '2020-10-17'
    group by 1,2
    order by 3 desc limit 20

"""

SQL_KOD_LAB = """
    SELECT z.id as zlecenie, w.id as wykonanie, z.DATAREJESTRACJI as DR, z.NUMER as NR, 
        z.PELENNUMERKSIEGI as PNK, Z.KODKRESKOWY,
        o.SYMBOL as OS, o.NAZWA as ONA, p.SYMBOL as PS, p.NAZWA as PN,
        kan.symbol as KANS, kan.nazwa as KANN,
        (PA.Nazwisko || ' ' || PA.Imiona ) as PAC,
        PA.PESEL as PAP,
        b.symbol as BS, b.nazwa as BN,
        a.symbol as APS, pr.symbol as PRA,		
        z.GODZINAREJESTRACJI as ZUTW, z.dc as ZDOZ, 
        w.DYSTRYBUCJA as DYS,	
        nullif(minvalue(coalesce(min(W.dc), '2100-01-01'), coalesce(min(HW.dc), '2100-01-01')), '2100-01-01') as WDOZ,
        w.WYKONANE as WYK, w.ZATWIERDZONE as ZATW, w.platne, w.anulowane, w.powtorka,
        nullif(minvalue(coalesce(min(W.Wydrukowane), '2100-01-01'), coalesce(min(HW.Wydrukowane), '2100-01-01')), '2100-01-01') as PPOD,
        nullif(maxvalue(coalesce(max(W.Wydrukowane), '1900-01-01'), coalesce(max(HW.Wydrukowane), '1900-01-01')), '1900-01-01') as OPOD,
        count(distinct(WZ.id)) as ILEPOD,
        list(distinct wyz.numer) as HL7,
        min(coalesce(wy.ukryty,0)) as ukryty
    from zlecenia z
        left OUTER JOIN wykonania w on z.id=w.ZLECENIE
        left outer join wykonaniazewnetrzne wyz on wyz.wykonanie=w.id
        left outer join ODDZIALY o on o.id=z.ODDZIAL
        left outer join PLATNICY p on p.id=z.PLATNIK
        left OUTER JOIN HSTWYKONANIA hw on hw.del=w.id
        left OUTER JOIN badania b on b.id=w.BADANIE
        left OUTER JOIN GRUPYBADAN gb on gb.id=b.GRUPA
        left OUTER JOIN WYDRUKIWZLECENIACH wz ON WZ.ZLECENIE = Z.ID
        left OUTER JOIN Wyniki wy on wy.WYKONANIE=w.id
        left outer join aparaty a on a.id=w.aparat
        left outer join pracownie pr on pr.id=w.pracownia
        left outer join pacjenci pa on pa.id=z.pacjent
        left outer join pracownicy pracrej on pracrej.id=z.pracownikodrejestracji
        left outer join kanaly kan on kan.id=pracrej.kanalinternetowy
    where z.kodkreskowy like ? 
        and (gb.SYMBOL <>'TECHNIC' or b.GRUPA is null) and w.PLATNE='1' and wy.ukryty = '0' 
        group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,23,24,25,26,27
        order by z.DATAREJESTRACJI, z.numer, b.symbol;"""

SQL_KOD_LAB_WYK = """
    SELECT z.id as zlecenie, w.id as wykonanie, z.DATAREJESTRACJI as DR, z.NUMER as NR, 
        z.PELENNUMERKSIEGI as PNK, Z.KODKRESKOWY,
        o.SYMBOL as OS, o.NAZWA as ONA, p.SYMBOL as PS, p.NAZWA as PN,
        kan.symbol as KANS, kan.nazwa as KANN,
        (PA.Nazwisko || ' ' || PA.Imiona ) as PAC,
        PA.PESEL as PAP,
        b.symbol as BS, b.nazwa as BN,
        a.symbol as APS, pr.symbol as PRA,		
        z.GODZINAREJESTRACJI as ZUTW, z.dc as ZDOZ, 
        w.DYSTRYBUCJA as DYS,	
        nullif(minvalue(coalesce(min(W.dc), '2100-01-01'), coalesce(min(HW.dc), '2100-01-01')), '2100-01-01') as WDOZ,
        w.WYKONANE as WYK, w.ZATWIERDZONE as ZATW, w.platne, w.anulowane, w.powtorka,
        nullif(minvalue(coalesce(min(W.Wydrukowane), '2100-01-01'), coalesce(min(HW.Wydrukowane), '2100-01-01')), '2100-01-01') as PPOD,
        nullif(maxvalue(coalesce(max(W.Wydrukowane), '1900-01-01'), coalesce(max(HW.Wydrukowane), '1900-01-01')), '1900-01-01') as OPOD,
        count(distinct(WZ.id)) as ILEPOD,
        list(distinct wyz.numer) as HL7,
        min(coalesce(wy.ukryty,0)) as ukryty
    from wykonania w
        left OUTER JOIN zlecenia z on z.id=w.ZLECENIE
        left outer join wykonaniazewnetrzne wyz on wyz.wykonanie=w.id
        left outer join ODDZIALY o on o.id=z.ODDZIAL
        left outer join PLATNICY p on p.id=z.PLATNIK
        left OUTER JOIN HSTWYKONANIA hw on hw.del=w.id
        left OUTER JOIN badania b on b.id=w.BADANIE
        left OUTER JOIN GRUPYBADAN gb on gb.id=b.GRUPA
        left OUTER JOIN WYDRUKIWZLECENIACH wz ON WZ.ZLECENIE = Z.ID
        left OUTER JOIN Wyniki wy on wy.WYKONANIE=w.id
        left outer join aparaty a on a.id=w.aparat
        left outer join pracownie pr on pr.id=w.pracownia
        left outer join pacjenci pa on pa.id=z.pacjent
        left outer join pracownicy pracrej on pracrej.id=z.pracownikodrejestracji
        left outer join kanaly kan on kan.id=pracrej.kanalinternetowy
    where w.kodkreskowy like ? 
        and (gb.SYMBOL <>'TECHNIC' or b.GRUPA is null) and w.PLATNE='1' and wy.ukryty = '0' 
        group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,23,24,25,26,27
        order by z.DATAREJESTRACJI, z.numer, b.symbol;"""

SQL_NR_DATA = """
    SELECT z.id as zlecenie, w.id as wykonanie, z.DATAREJESTRACJI as DR, z.NUMER as NR, 
        z.PELENNUMERKSIEGI as PNK, Z.KODKRESKOWY,
        o.SYMBOL as OS, o.NAZWA as ONA, p.SYMBOL as PS, p.NAZWA as PN,
        kan.symbol as KANS, kan.nazwa as KANN,
        (PA.Nazwisko || ' ' || PA.Imiona ) as PAC,
        PA.PESEL as PAP,
        b.symbol as BS, b.nazwa as BN,
        a.symbol as APS, pr.symbol as PRA,		
        z.GODZINAREJESTRACJI as ZUTW, z.dc as ZDOZ, 
        w.DYSTRYBUCJA as DYS,		
        nullif(minvalue(coalesce(min(W.dc), '2100-01-01'), coalesce(min(HW.dc), '2100-01-01')), '2100-01-01') as WDOZ,
        w.WYKONANE as WYK, w.ZATWIERDZONE as ZATW, w.platne, w.anulowane, w.powtorka,
        nullif(minvalue(coalesce(min(W.Wydrukowane), '2100-01-01'), coalesce(min(HW.Wydrukowane), '2100-01-01')), '2100-01-01') as PPOD,
        nullif(maxvalue(coalesce(max(W.Wydrukowane), '1900-01-01'), coalesce(max(HW.Wydrukowane), '1900-01-01')), '1900-01-01') as OPOD,
        count(distinct(WZ.id)) as ILEPOD,
        list(distinct wyz.numer) as HL7,
        min(coalesce(wy.ukryty,0)) as ukryty
    from zlecenia z
        left OUTER JOIN wykonania w on z.id=w.ZLECENIE
        left outer join wykonaniazewnetrzne wyz on wyz.wykonanie=w.id
        left outer join ODDZIALY o on o.id=z.ODDZIAL
        left outer join PLATNICY p on p.id=z.PLATNIK
        left OUTER JOIN HSTWYKONANIA hw on hw.del=w.id
        left OUTER JOIN badania b on b.id=w.BADANIE
        left OUTER JOIN GRUPYBADAN gb on gb.id=b.GRUPA
        left OUTER JOIN WYDRUKIWZLECENIACH wz ON WZ.ZLECENIE = Z.ID
        left OUTER JOIN Wyniki wy on wy.WYKONANIE=w.id
        left outer join aparaty a on a.id=w.aparat
        left outer join pracownie pr on pr.id=w.pracownia
        left outer join pacjenci pa on pa.id=z.pacjent
        left outer join pracownicy pracrej on pracrej.id=z.pracownikodrejestracji
        left outer join kanaly kan on kan.id=pracrej.kanalinternetowy
    where z.numer = ? and z.datarejestracji = ?
        and (gb.SYMBOL <>'TECHNIC' or b.GRUPA is null) and w.PLATNE='1' and wy.ukryty = '0'
        group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,23,24,25,26,27
        order by z.DATAREJESTRACJI, z.numer, b.symbol;"""

SQL_PESEL = """
    SELECT z.id as zlecenie, w.id as wykonanie, z.DATAREJESTRACJI as DR, z.NUMER as NR, 
        z.PELENNUMERKSIEGI as PNK, Z.KODKRESKOWY,
        o.SYMBOL as OS, o.NAZWA as ONA, p.SYMBOL as PS, p.NAZWA as PN,
        kan.symbol as KANS, kan.nazwa as KANN,
        (PA.Nazwisko || ' ' || PA.Imiona ) as PAC,
        PA.PESEL as PAP,
        b.symbol as BS, b.nazwa as BN,
        a.symbol as APS, pr.symbol as PRA,		
        z.GODZINAREJESTRACJI as ZUTW, z.dc as ZDOZ, 
        w.DYSTRYBUCJA as DYS,		
        nullif(minvalue(coalesce(min(W.dc), '2100-01-01'), coalesce(min(HW.dc), '2100-01-01')), '2100-01-01') as WDOZ,
        w.WYKONANE as WYK, w.ZATWIERDZONE as ZATW, w.platne, w.anulowane, w.powtorka,
        nullif(minvalue(coalesce(min(W.Wydrukowane), '2100-01-01'), coalesce(min(HW.Wydrukowane), '2100-01-01')), '2100-01-01') as PPOD,
        nullif(maxvalue(coalesce(max(W.Wydrukowane), '1900-01-01'), coalesce(max(HW.Wydrukowane), '1900-01-01')), '1900-01-01') as OPOD,
        count(distinct(WZ.id)) as ILEPOD,
        list(distinct wyz.numer) as HL7,
        min(coalesce(wy.ukryty,0)) as ukryty
    from 
        pacjenci pa
        left join zlecenia z on pa.id=z.pacjent
        left OUTER JOIN wykonania w on z.id=w.ZLECENIE
        left outer join wykonaniazewnetrzne wyz on wyz.wykonanie=w.id
        left outer join ODDZIALY o on o.id=z.ODDZIAL
        left outer join PLATNICY p on p.id=z.PLATNIK
        left OUTER JOIN HSTWYKONANIA hw on hw.del=w.id
        left OUTER JOIN badania b on b.id=w.BADANIE
        left OUTER JOIN GRUPYBADAN gb on gb.id=b.GRUPA
        left OUTER JOIN WYDRUKIWZLECENIACH wz ON WZ.ZLECENIE = Z.ID
        left OUTER JOIN Wyniki wy on wy.WYKONANIE=w.id
        left outer join aparaty a on a.id=w.aparat
        left outer join pracownie pr on pr.id=w.pracownia
        left outer join pracownicy pracrej on pracrej.id=z.pracownikodrejestracji
        left outer join kanaly kan on kan.id=pracrej.kanalinternetowy
    where pa.pesel = ?
        and (gb.SYMBOL <>'TECHNIC' or b.GRUPA is null) and w.PLATNE='1' and wy.ukryty = '0'
        group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,23,24,25,26,27
        order by z.DATAREJESTRACJI, z.numer, b.symbol;"""

SQL_ZBIORCZY = """
    SELECT z.DATAREJESTRACJI as DR, z.NUMER as NR, 
        z.PELENNUMERKSIEGI as PNK, Z.KODKRESKOWY,
        o.SYMBOL as OS, o.NAZWA as ONA, p.SYMBOL as PS, p.NAZWA as PN,
        kan.symbol as KANS, kan.nazwa as KANN,
        (PA.Nazwisko || ' ' || PA.Imiona ) as PAC,
        PA.PESEL as PAP,
        b.symbol as BS, b.nazwa as BN,
        a.symbol as APS, pr.symbol as PRA,		
        z.GODZINAREJESTRACJI as ZUTW, z.dc as ZDOZ, 
        w.DYSTRYBUCJA as DYS,		
        nullif(minvalue(coalesce(min(W.dc), '2100-01-01'), coalesce(min(HW.dc), '2100-01-01')), '2100-01-01') as WDOZ,
        w.WYKONANE as WYK, w.ZATWIERDZONE as ZATW, w.platne, w.anulowane, w.powtorka,
        nullif(minvalue(coalesce(min(W.Wydrukowane), '2100-01-01'), coalesce(min(HW.Wydrukowane), '2100-01-01')), '2100-01-01') as PPOD,
        nullif(maxvalue(coalesce(max(W.Wydrukowane), '1900-01-01'), coalesce(max(HW.Wydrukowane), '1900-01-01')), '1900-01-01') as OPOD,
        count(distinct(WZ.id)) as ILEPOD,
        list(distinct wyz.numer) as HL7,
        min(coalesce(wy.ukryty,0)) as ukryty
    from zlecenia z
        left OUTER JOIN wykonania w on z.id=w.ZLECENIE
        left outer join wykonaniazewnetrzne wyz on wyz.wykonanie=w.id
        left outer join ODDZIALY o on o.id=z.ODDZIAL
        left outer join PLATNICY p on p.id=z.PLATNIK
        left OUTER JOIN HSTWYKONANIA hw on hw.del=w.id
        left OUTER JOIN badania b on b.id=w.BADANIE
        left OUTER JOIN GRUPYBADAN gb on gb.id=b.GRUPA
        left OUTER JOIN WYDRUKIWZLECENIACH wz ON WZ.ZLECENIE = Z.ID
        left OUTER JOIN Wyniki wy on wy.WYKONANIE=w.id
        left outer join aparaty a on a.id=w.aparat
        left outer join pracownie pr on pr.id=w.pracownia
        left outer join pacjenci pa on pa.id=z.pacjent
        left outer join pracownicy pracrej on pracrej.id=z.pracownikodrejestracji
        left outer join kanaly kan on kan.id=pracrej.kanalinternetowy
    where z.DATAREJESTRACJI between ? and ?
        and $WARUNEK_PODMIOTU$
        and (gb.SYMBOL <>'TECHNIC' or b.GRUPA is null) and w.PLATNE='1' and wy.ukryty = '0'
    group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,21,22,23,24,25
    order by z.DATAREJESTRACJI, z.numer, b.symbol ;"""

SQL_ZLECENIA_HL7 = """
    select zl.datarejestracji as "Data rejestracji", zl.numer as "Numer w Centrum", 
        zz.przyszlozzewnatrz, zz.poszlodocentrum, zz.przyszlozcentrum, zz.poszlonazewnatrz, zz.status, zz.numer as "numer zewnętrzny",
        zz.parametry 
    from zleceniazewnetrzne zz
    left join zlecenia zl on zl.id=zz.zlecenie 
    where zz.zlecenie in ($IDENTS$)
"""

SQL_WYKONANIA_HL7 = """
    select zl.datarejestracji as "Data rejestracji", zl.numer as "Numer w Centrum", 
        wz.badanie, wz.material, w.dystrybucja, w.godzina as "pobranie", w.zatwierdzone, w.anulowane, bl.symbol as "błąd",
        wz.przyszlozcentrum, wz.poszlonazewnatrz, wz.przyjetewcentrum, wz.przyjetenazewnatrz, wz.status, wz.numer as "numer zewnętrzny",
            wz.wynik as "wysłany wynik", wz.parametry
    from wykonaniazewnetrzne wz
    left join wykonania w on w.id=wz.wykonanie
    left join zlecenia zl on zl.id=w.zlecenie
    left join bledywykonania bl on bl.id=w.bladwykonania
    
    where wz.wykonanie in ($IDENTS$)
"""

SQL_WYDRUKI = """
    select zl.datarejestracji as "Data rejestracji", zl.numer as "Numer",
        wwz.plik as "Plik", wwz.odebrany, wwz.odebral, wwz.wydrukowany, wwz.wyslany, wwz.podpisany,
        wwzz.wyslanyhl7 as "wysłany hl7", wwzz.system as "wysłany do systemu",
        wcwz.plik as "Plik CDA", wcwz.podpisany as "Podpisany CDA", wcwz.Wyslany as "Wysłany CDA", wcwz.Podpisany as "Podpisany CDA",
        wcwz.potwierdzony as "Potwierdzony CDA",
        wcwzz.wyslanyhl7 as "CDA wysłany hl7", wcwzz.system as "CDA wysłany do systemu"
    from wydrukiwzleceniach wwz
    left join wydrukiwzleceniachzewnetrzne wwzz on wwzz.wydrukwzleceniu=wwz.id
    left join wydrukicdawzleceniach wcwz on wcwz.wydruk=wwz.id
    left join WYDRUKICDAWZLECENIACHZEWNETRZNE wcwzz on wcwzz.wydrukcdawzleceniu=wcwz.id
    
    left join zlecenia zl on zl.id=wwz.zlecenie
    where wwz.zlecenie in ($IDENTS$)
"""

SQL_WYDRUKI_PODST1 = """
    select zl.datarejestracji as "Data rejestracji", zl.numer as "Numer",
        wwz.plik as "Plik", wwz.odebrany, wwz.odebral, wwz.wydrukowany, wwz.wyslany, wwz.podpisany, wwz.wyslanyhl7
    from wydrukiwzleceniach wwz

    left join zlecenia zl on zl.id=wwz.zlecenie
    where wwz.zlecenie in ($IDENTS$)     
"""

SQL_WYDRUKI_PODST2 = """
    select zl.datarejestracji as "Data rejestracji", zl.numer as "Numer",
        wwz.plik as "Plik", wwz.odebrany, wwz.odebral, wwz.wydrukowany, wwz.wyslany, wwz.podpisany
    from wydrukiwzleceniach wwz

    left join zlecenia zl on zl.id=wwz.zlecenie
    where wwz.zlecenie in ($IDENTS$)
"""

# TODO: sprawdzać kolumny w bazie i w zależności czy np jest WYKONANIA.GODZINAREJESTRACJI dokładać do zapytania albo nie;
# w bazie CZERNIA kolumna jest, a w bazie HISTOPA nie ma


LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    TabbedView(field='tab', desc_title='Typ raportu', children=[
        Tab(title='Raport zbiorczy', value='zbiorczy',
            panel=VBox(
                InfoText(
                    text='Proszę wybrać laboratorium, a następnie wskazać płatnika lub zleceniodawcę oraz zakres dat rejestracji, dla których zostanie wykonany raport'),
                LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', pokaz_nieaktywne=True),
                # PlatnikSearch(field='platnik', title='Płatnik'),
                # ZleceniodawcaSearch(field='zleceniodawca', title='Zleceniodawca'),
                TextInput(field='symbolp', title='Symbol płatnika'),
                TextInput(field='symbolz', title='Symbol zleceniodawcy'),
                DateInput(field='dataod', title='Data początkowa', default='-7D'),
                DateInput(field='datado', title='Data końcowa', default='-1D'),
            )
            ),
        Tab(title='Wybrane zlecenie', default=True, value='zlecenie',
            panel=VBox(
                InfoText(
                    text='Proszę wybrać laboratorium/laboratoria oraz podać kod kreskowy, pesel lub numer i datę zlecenia do sprawdzenia'),
                LabSelector(multiselect=True, selectall=True, field='laboratoria', title='Laboratoria',
                            pokaz_nieaktywne=True),
                TextInput(field='kodkreskowy', title='Kod kreskowy', helper='min 9 cyfr', autofocus=True,
                          validate=lambda x: len(x) >= 9),
                Switch(field='kodwykonania', title='Szukaj po kodzie wykonania, a nie zlecenia', validate=lambda x: len(x) >= 9),
                HBox(
                    VBox(TextInput(field='numerzl', title='Numer i data zlecenia', desc_title='Numer zlecenia')),
                    DateInput(field='datazl', desc_title='Data zlecenia', can_clear=True)
                ),
                TextInput(field='pesel', title='PESEL'),
                Switch(field='hl7wydr', title="Info o HL7 i wydrukach"),
            )
            )
    ]),
    Switch(field='pokaz_bezplatne', title="Pokaż bezpłatne i ukryte")
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['tab'] == 'zbiorczy':
        if params['laboratorium'] is None:
            raise ValidationError('Nie wybrano laboratorium')
        validate_date_range(params['dataod'], params['datado'], 31)
        for fld in ('symbolp', 'symbolz'):
            if params[fld] is None:
                params[fld] = ''
        if params['symbolp'].strip() == '' and params['symbolz'].strip() == '':
            raise ValidationError('Nie podano symbolu ani płatnika ani zleceniodawcy')
        task = {
            'type': 'centrum',
            'priority': 1,
            'target': params['laboratorium'],
            'params': params,
            'function': 'raport_zbiorczy'
        }
        report.create_task(task)
    elif params['tab'] == 'zlecenie':
        if not empty(params['kodkreskowy']):
            if not empty(params['numerzl']) or not empty(params['pesel']):
                raise ValidationError('Podaj kod kreskowy albo numer i datę zlecenia albo nr pesel')
            if len(params['kodkreskowy']) < 9:
                raise ValidationError('Podaj co najmniej 9 znaków kodu kreskowego')
            if len(params['laboratoria']) > 5:
                raise ValidationError(
                    'Wybierz co najwyżej 5 laboratoriów. Jeśli chcesz poszukać kodu we wszystkich laboratoriach, skorzystaj z raportu Szukaj kodu')
            if params['hl7wydr'] and len(params['laboratoria']) > 1:
                raise ValidationError("Info o HL7 i wydrukach - tylko 1 lab!")
            params['datazl'] = None
            params['_szukaj'] = 'kod'
        elif not empty(params['pesel']):
            if len(params['laboratoria']) > 5:
                raise ValidationError(
                    'Wybierz co najwyżej 5 laboratoriów')
            if len(params['pesel']) != 11:
                raise ValidationError(
                    'Nr PESEL 11 cyfr'
                )
            params['_szukaj'] = 'pesel'
        else:
            if empty(params['numerzl']) or empty(params['datazl']):
                raise ValidationError('Podaj kod kreskowy albo datę i numer zlecenia')
            if len(params['laboratoria']) != 1:
                raise ValidationError(
                    'W przypadku szukania po numerze i dacie zlecenia wskaż dokładnie jedno laboratorium')
            params['_szukaj'] = 'datanr'
        if len(params['laboratoria']) == 0:
            raise ValidationError('Nie wybrano żadnego laboratorium')
        for lab in params['laboratoria']:
            lab_task = {
                'type': 'centrum',
                'priority': 0 if not params['hl7wydr'] else 1,
                'target': lab,
                'params': params,
                'function': 'raport_kod_lab',
            }
            report.create_task(lab_task)
    report.save()
    return report


def raport_zbiorczy(task_params):
    params = task_params['params']
    system = task_params['target']
    oddnia = params['dataod']
    dodnia = params['datado']
    symbolp = params['symbolp'].strip()
    symbolz = params['symbolz'].strip()
    warunki_podmiotu = []
    if symbolp != '':
        with get_centrum_connection(system) as conn:
            for row in conn.raport_slownikowy('select id, symbol, nazwa from platnicy where symbol=? and del=0',
                                              [symbolp]):
                warunki_podmiotu.append('z.platnik=%d' % row['id'])
    if symbolz != '':
        with get_centrum_connection(system) as conn:
            for row in conn.raport_slownikowy('select id, symbol, nazwa from oddzialy where symbol=? and del=0',
                                              [symbolz]):
                warunki_podmiotu.append('z.oddzial=%d' % row['id'])
    if len(warunki_podmiotu) > 0:
        sql = SQL_ZBIORCZY.replace('$WARUNEK_PODMIOTU$', ' and '.join(warunki_podmiotu))
        if params['pokaz_bezplatne']:
            sql = sql.replace("and w.PLATNE='1' and wy.ukryty = '0'", "")
        with get_centrum_connection(system) as conn:
            cols, rows = conn.raport_z_kolumnami(sql, [oddnia, dodnia])
            return rows, []
    else:
        raise ValidationError('Nie znaleziono pasującego płatnika/zleceniodawcy')


def raport_hl7_zlecenia(conn, zlecenia):
    cols, rows = conn.raport_z_kolumnami(SQL_ZLECENIA_HL7.replace('$IDENTS$', ','.join([str(id) for id in zlecenia if id is not None])))
    return {
        'type': 'table',
        'title': 'Zlecenia HL7',
        'header': cols,
        'data': prepare_for_json(rows),
    }


def raport_hl7_wykonania(conn, wykonania):
    cols, rows = conn.raport_z_kolumnami(SQL_WYKONANIA_HL7.replace('$IDENTS$', ','.join([str(id) for id in wykonania if id is not None])))
    return {
        'type': 'table',
        'title': 'Wykonania HL7',
        'header': cols,
        'data': prepare_for_json(rows),
    }


def raport_wydruki(conn, zlecenia):
    try:
        cols, rows = conn.raport_z_kolumnami(SQL_WYDRUKI.replace('$IDENTS$', ','.join([str(id) for id in zlecenia if id is not None])))
    except:
        try:
            cols, rows = conn.raport_z_kolumnami(
                SQL_WYDRUKI_PODST1.replace('$IDENTS$', ','.join([str(id) for id in zlecenia])))
        except:
            cols, rows = conn.raport_z_kolumnami(
                SQL_WYDRUKI_PODST2.replace('$IDENTS$', ','.join([str(id) for id in zlecenia])))
    return {
        'type': 'table',
        'title': 'Wydruki',
        'header': cols,
        'data': prepare_for_json(rows),
    }


def raport_kod_lab(task_params):
    params = task_params['params']
    system = task_params['target']
    sql = None
    sql_params = []
    main_res = None
    aux_res = []
    if params['_szukaj'] == 'kod':
        kodkreskowy = params['kodkreskowy'].replace('=', '')
        if len(kodkreskowy) == 10:
            kodkreskowy = kodkreskowy[:9]
        kodkreskowy += '%'
        if params['kodwykonania']:
            sql = SQL_KOD_LAB_WYK
        else:
            sql = SQL_KOD_LAB
        sql_params.append(kodkreskowy)
    elif params['_szukaj'] == 'datanr':
        sql = SQL_NR_DATA
        sql_params += [params['numerzl'], params['datazl']]
    elif params['_szukaj'] == 'pesel':
        sql = SQL_PESEL
        sql_params.append(params['pesel'])
    if params['pokaz_bezplatne']:
        sql = sql.replace("and w.PLATNE='1' and wy.ukryty = '0'", "")
    with get_centrum_connection(system, fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
        main_res = [row[2:] for row in rows]
        if params['hl7wydr']:
            zlecenia = []
            wykonania = []
            for row in rows:
                if row[0] not in zlecenia:
                    zlecenia.append(row[0])
                if row[1] not in wykonania:
                    wykonania.append(row[1])
            if len(zlecenia) > 0:
                subres = raport_hl7_zlecenia(conn, zlecenia)
                if subres is not None:
                    aux_res.append(subres)
                subres = raport_hl7_wykonania(conn, wykonania)
                if subres is not None:
                    aux_res.append(subres)
                subres = raport_wydruki(conn, zlecenia)
                if subres is not None:
                    aux_res.append(subres)

    return [main_res, aux_res]


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': [
            'xlsx',
            {
                'type': 'pdf',
                'landscape': True,
                'base_font_size': '6pt'
            }
        ]
    }
    nz = []
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            [main_res, aux_res] = result
            if len(main_res) > 0:
                rows = []
                for row in main_res:
                    row = list(row)
                    warnings = []
                    platne = row[22]
                    anulowane = row[23]
                    powtorka = row[24]
                    ukryte = row[29]
                    if str(platne) != '1':
                        warnings.append('wykonanie bezpłatne')
                    if anulowane is not None:
                        warnings.append('wykonanie anulowane ' + anulowane.strftime('%Y-%m-%d %H:%M'))
                    if str(ukryte) == '1':
                        warnings.append('wszystkie wyniki ukryte')
                    if str(powtorka) == '1':
                        warnings.append('powtórka')
                    row = row[:22] + row[25:29] + row[30:]
                    if len(warnings) > 0:
                        row[12] = {
                            'value': '%s\n(%s)' % (row[12], ', '.join(warnings)),
                            'background': '#ff0000',
                        }
                    rows.append(row)
                res['results'].append({
                    'type': 'table',
                    'title': params['target'],
                    'header': 'Data Rejestracji,Numer Zlecenia,Numer księgi,Kod kreskowy,Zleceniodawca Symbol,Zleceniodawca Nazwa,Płatnik Symbol,Płatnik Nazwa,Kanał symbol,Kanał nazwa,Pacjent,Pesel,Badanie Symbol,Badanie Nazwa,Aparat Symbol,Pracownia Symbol,Zlecenie utworzone,Ostatnia modyfikacja,Materiał Przyjęty,Ostania zmiana w badaniu,Data wykonania,Data zatwierdzenia,Pierwszy podpis,Ostatni podpis,Ile dokumentów w zleceniu,Ident. HL7'.split(
                        ','),
                    'data': prepare_for_json(rows)
                })
                res['results'] += aux_res
            else:
                nz.append(params['target'])
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])
    if len(nz) > 0:
        res['results'].append({
            'type': 'info',
            'text': '%s - nie znaleziono' % ', '.join(nz)
        })
    res['progress'] = task_group.progress
    return res
