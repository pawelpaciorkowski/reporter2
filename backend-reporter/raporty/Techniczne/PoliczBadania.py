from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError, Switch, Preset
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty

# TODO: jeśli zaznaczone tylko błędy wykonania to pozwolić cały rok

# prio 1

# IleBledowLaboratorium, IleKontroliLaboratorium,
# IleBadanWDanejGodzinie, IleBadanWDanejGodzinie_Okres, IleBadanWDanejGodzinieSerologia
# IleZlecenWDanejGodzinie

# RaportAparaty?

MENU_ENTRY = 'Policz badania'
REQUIRE_ROLE = ['L-KIER', 'C-FIN', 'C-ROZL', 'C-DS']
ADD_TO_ROLE = ['L-REJ', 'L-PRAC']

PODZIALY = {
    'brak': 'Brak podziału',
    'platnicy': 'Płatnicy',
    'grupyplatnikow': 'Grupy płatników',
    'zleceniodawcy': 'Zleceniodawcy',
    'typyzlecen': 'Typy zleceń',
    'pracownie': 'Pracownie',
    'metody': 'Metody',
    'aparaty': 'Aparaty',
    'rejestracje': 'Punkty rejestracji',
    'pracrej': 'Pracownicy rejestracji',
    'grupybadan': 'Grupy badań',
    'badania': 'Badania',
    'bledy': 'Błędy wykonania',
    # 'powody': 'Powody anulowania',
    'miesiace': 'Miesiące',
    'dni': 'Dni',
    'godziny': 'Godziny',
    'platne': 'Czy płatne?',
}

PODZIALY_SQL = {
    'platnicy': "(platnik || ' - ' || platnik_nazwa)",
    'grupyplatnikow': "(grupaplatnika || ' - ' || grupaplatnika_nazwa)",
    'zleceniodawcy': "(zleceniodawca || ' - ' || zleceniodawca_nazwa)",
    'typyzlecen': "(typzlecenia || ' - ' || typzlecenia_nazwa)",
    'pracownie': "(pracownia || ' - ' || pracownia_nazwa)",
    'aparaty': "(aparat || ' - ' || aparat_nazwa)",
    'rejestracje': "(rejestracja || ' - ' || rejestracja_nazwa)",
    'pracrej': "(pracrej_login || ' - ' || pracrej_nazwisko)",
    'metody': "(metoda || ' - ' || metoda_nazwa)",
    'grupybadan': "(grupabadan || ' - ' || grupabadan_nazwa)",
    'badania': "(badanie || ' - ' || badanie_nazwa)",
    'bledy': "(blad || ' - ' || blad_nazwa)",
    # 'powody': "(powodanulowania || ' - ' || powodanulowania_nazwa)",
    'miesiace': "(extract(month from czas))",
    'dni': "(cast(czas as date))",
    'godziny': "(extract(hour from czas))",
    'platne': "platne"
}

RODZAJE_DAT = {'rej': 'Rejestracji', 'dystr': 'Przyjęcia materiału', 'zatw': 'Zatwierdzenia',
               'rozl': 'Rozliczeniowa'}

PRESETS = [
    ("Ile błędów w laboratorium", {
        'rodzajdat': 'zatw',
        'tylkokontr': False, 'bezkontr': False,
        'beztechn': False, 'bezdopl': False,
        'tylkobl': True, 'bezbl': False,
        'tylkozatw': False, 'bezzatw': False,
        'tylkopak': False, 'bezpak': False,
        'tylkopl': False, 'tylkokoszt': False, 'bezrozl': True,
        'tylkohl7': False, 'bezhl7': False,
        'bezgpa': False, 'lokalneaparaty': False,
        'zliczajzlec': False, 'wykresgodz': True,
        'podzial1': 'bledy', 'podzial2': 'brak', 'podzial3': 'brak',
    }),
    ("Ile kontroli w laboratorium", {
        'rodzajdat': 'zatw',
        'tylkokontr': True, 'bezkontr': False,
        'beztechn': False, 'bezdopl': False,
        'tylkobl': False, 'bezbl': False,
        'tylkozatw': False, 'bezzatw': False,
        'tylkopak': False, 'bezpak': False,
        'tylkopl': False, 'tylkokoszt': False, 'bezrozl': True,
        'tylkohl7': False, 'bezhl7': False,
        'bezgpa': False, 'lokalneaparaty': False,
        'zliczajzlec': False, 'wykresgodz': True,
        'podzial1': 'brak', 'podzial2': 'brak', 'podzial3': 'brak',
    }),
    ("Ile badań w danej godzinie", {
        'rodzajdat': 'dystr',
        'tylkokontr': False, 'bezkontr': True,
        'beztechn': True, 'bezdopl': False,
        'tylkobl': False, 'bezbl': False,
        'tylkozatw': False, 'bezzatw': False,
        'tylkopak': False, 'bezpak': False,
        'tylkopl': False, 'tylkokoszt': False, 'bezrozl': True,
        'tylkohl7': False, 'bezhl7': False,
        'bezgpa': False, 'lokalneaparaty': False,
        'zliczajzlec': False, 'wykresgodz': True,
        'podzial1': 'brak', 'podzial2': 'brak', 'podzial3': 'brak',
    }),
    ("Ile zleceń w danej godzinie", {
        'rodzajdat': 'rej',
        'tylkokontr': False, 'bezkontr': True,
        'beztechn': True, 'bezdopl': False,
        'tylkobl': False, 'bezbl': False,
        'tylkozatw': False, 'bezzatw': False,
        'tylkopak': False, 'bezpak': False,
        'tylkopl': False, 'tylkokoszt': False, 'bezrozl': True,
        'tylkohl7': False, 'bezhl7': False,
        'bezgpa': False, 'lokalneaparaty': False,
        'zliczajzlec': True, 'wykresgodz': True,
        'podzial1': 'brak', 'podzial2': 'brak', 'podzial3': 'brak',
    }),
]

LAUNCH_DIALOG = Dialog(title="Policz badania / zlecenia", panel=HBox(
    VBox(
        LabSelector(field="laboratorium", title="Laboratorium", multiselect=False, pokaz_nieaktywne=True),
        InfoText(text="""Zakres raportu. W przypadku filtrowania po płatnikach lub zleceniodawcach
                         lub zliczania błędów wykonania maksymalny
                         zakres raportu wynosi rok, bez filtrowania - 3 miesiące.
                         Dla zakresu obejmującego 1 dzień możliwe jest przeglądanie zleceń,
                         a dla bazy Stępińska - wybór bazy bieżącej zamiast raportowej."""),
        HBox(
            VBox(
                HBox(DateInput(field='dataod', title='Data początkowa', default='T')),
                HBox(DateInput(field='datado', title='Data końcowa', default='T')),
            ),
            Radio(field="rodzajdat", values=RODZAJE_DAT, default='zatw'),
        ),
        InfoText(text="Filtrowanie"),
        HBox(
            Switch(field="tylkokontr", title="Tylko kontrole"),
            Switch(field="bezkontr", title="Bez kontrolnych"),
        ),
        HBox(
            Switch(field="beztechn", title="Bez technicznych", default=True),
            Switch(field="bezdopl", title="Bez dopłat i innych"),
        ),
        HBox(
            Switch(field="tylkobl", title="Tylko błędy wykonania"),
            Switch(field="bezbl", title="Bez błędów wykonania")
        ),
        HBox(
            Switch(field="tylkozatw", title="Tylko zatwierdzone"),
            Switch(field="bezzatw", title="Tylko niezatwierdzone"),
        ),
        HBox(
            Switch(field="tylkopak", title="Tylko pakiety"),
            Switch(field="bezpak", title="Bez pakietów"),
        ),
        HBox(
            Switch(field="tylkopl", title="Tylko płatne"),
            Switch(field="tylkokoszt", title="Tylko na koszt labu"),
            Switch(field="bezrozl", title="Bez pracowni rozliczeniowych", default=True),
        ),
        HBox(
            Switch(field="tylkohl7", title="Tylko zlecone po HL7"),
            Switch(field="bezhl7", title="Bez zleconych po HL7"),
        ),
        HBox(
            Switch(field="bezgpa", title="Bez grupy pracowni ALAB"),
            Switch(field="lokalneaparaty", title="Tylko lokalne aparaty"),
        ),
        HBox(
            TextInput(field="symbolp", title="Symbol płatnika"),
            TextInput(field="symbolz", title="Symbol zleceniodawcy"),
        ),
        HBox(
            TextInput(field="symbolb", title="Pojedyncze badanie"),
            TextInput(field="symbolpr", title="Symbol pracowni"),
        ),
        InfoText(text="Prezentacja danych"),
        Switch(field="zliczajzlec", title="Zliczaj całe zlecenia (a nie pojedyncze wykonania)"),
        Switch(field="wykresgodz", title="Pokaż rozkład godzinowy"),
        # Switch(field="kodykreskowe", title="Dołącz kody kreskowe"),
        HBox(
            Select(field="podzial1", title="Podział 1", values=PODZIALY),
            Select(field="podzial2", title="Podział 2", values=PODZIALY),
            Select(field="podzial3", title="Podział 3", values=PODZIALY),
        ),
        Switch(field="flat", title="Płaska tabelka")
    ),
    VBox(
        InfoText(text="Okresy predefiniowane:"),
        Preset(text="Dziś", preset={'dataod': 'T', 'datado': 'T'}),
        Preset(text="Wczoraj", preset={'dataod': '-1D', 'datado': '-1D'}),
        Preset(text="Ostatni tydzień", preset={'dataod': '-7D', 'datado': '-1D'}),
        Preset(text="Zeszły miesiąc", preset={'dataod': 'PZM', 'datado': 'KZM'}),
        InfoText(text="Ustawienia predefiniowane:"),
        *(map(lambda p: Preset(text=p[0], preset=p[1]), PRESETS))
    )
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if empty(params['symbolp']) and empty(params['symbolz']) and not params['tylkobl']:
        validate_date_range(params['dataod'], params['datado'], max_days=96)
    else:
        validate_date_range(params['dataod'], params['datado'], max_days=366)
    if params['tylkokontr'] and params['bezkontr']:
        raise ValidationError('Tylko kontrolne i bez kontrolnych?')
    if params['tylkobl'] and params['bezbl']:
        raise ValidationError('Tylko błędne i bez błędów?')
    if params['tylkozatw'] and params['bezzatw']:
        raise ValidationError('Tylko zatwierdzone i tylko niezatwierdzone?')
    if params['bezzatw'] and params['rodzajdat'] == 'zatw':
        raise ValidationError('Bez zatwierdzonych, wg dat zatwierdzenia?')
    if params['tylkopl'] and params['tylkokoszt']:
        raise ValidationError('Tylko płatne i na koszt labu?')
    if params['tylkopak'] and params['bezpak']:
        raise ValidationError('Tylko pakiety i bez pakietów?')
    if params['tylkohl7'] and params['bezhl7']:
        raise ValidationError('Tylko HL7 i bez HL7?')
    if params['wykresgodz']:
        if params['rodzajdat'] in ['rozl']:
            raise ValidationError('Dla dat rozliczeniowych nie ma sensu rozkład godzinowy.')
    if not empty(params['symbolp']) and len(params['symbolp']) > 7:
        raise ValidationError('Za długi symbol płatnika - max 7 znaków')
    if not empty(params['symbolz']) and len(params['symbolz']) > 7:
        raise ValidationError('Za długi symbol zleceniodawcy - max 7 znaków')
    podzialy = []
    for fld in ('podzial1', 'podzial2', 'podzial3'):
        if params[fld] is not None and params[fld] != 'brak' and params[fld] not in podzialy:
            podzialy.append(params[fld])
    params['podzialy'] = podzialy
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
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
    # TODO: jeśli są jakieś symbole to sprawdzić i dorzucić identyfikatory
    lacznie = 'zleceń' if params['zliczajzlec'] else 'wykonań'
    res = []
    if not empty(params['symbolp']) \
            or not empty(params['symbolz']) \
            or not empty(params['symbolb']) \
            or not empty(params['symbolpr']):
        with get_centrum_connection(task_params['target'], fresh=True) as conn:
            if not empty(params['symbolp']):
                cols, rows = conn.raport_z_kolumnami("select id, symbol, nazwa from platnicy where symbol=? and del=0",
                                                     [params['symbolp']])
                if len(rows) > 0:
                    params['platnik_id'] = rows[0][0]
                    res.append({'type': 'info', 'text': 'Tylko płatnik %s - %s' % (rows[0][1], rows[0][2])})
                else:
                    return {'type': 'error', 'text': 'Nie znaleziono płatnika'}
            if not empty(params['symbolz']):
                cols, rows = conn.raport_z_kolumnami("""select o.id, o.symbol, o.nazwa, o.platnik, pl.symbol
                                                        from oddzialy o
                                                        left join platnicy pl on pl.id=o.platnik 
                                                        where o.symbol=? and o.del=0""",
                                                     [params['symbolz']])
                if len(rows) > 0:
                    params['oddzial_id'] = rows[0][0]
                    params['oddzial_platnik_id'] = rows[0][3]
                    if 'GOT' in rows[0][4]:
                        params['oddzial_platnik_got'] = True
                    else:
                        params['oddzial_platnik_got'] = False
                    res.append({'type': 'info', 'text': 'Tylko zleceniodawca %s - %s' % (rows[0][1], rows[0][2])})
                else:
                    return {'type': 'error', 'text': 'Nie znaleziono zleceniodawcy'}
            if not empty(params['symbolb']):
                cols, rows = conn.raport_z_kolumnami("select id, symbol, nazwa from badania where symbol=? and del=0",
                                                     [params['symbolb']])
                if len(rows) > 0:
                    params['badanie_id'] = rows[0][0]
                    res.append({'type': 'info', 'text': 'Tylko badanie %s - %s' % (rows[0][1], rows[0][2])})
                else:
                    return {'type': 'error', 'text': 'Nie znaleziono badania'}

            if not empty(params['symbolpr']):
                cols, rows = conn.raport_z_kolumnami(
                    "select id, symbol, nazwa from pracownie where symbol=? and del=0",
                    [params['symbolpr']])
                if len(rows) > 0:
                    params['pracownia_id'] = rows[0][0]
                    res.append({'type': 'info', 'text': 'Tylko pracownie %s - %s' % (
                        rows[0][1], rows[0][2])})
                else:
                    return {'type': 'error', 'text': 'Nie znaleziono pracowni'}
    linki_podgladu = params['dataod'] == params['datado']
    sql, sql_params = zbuduj_zapytanie(params)
    # res.append({
    #     'type': 'table',
    #     'header': ['zapytanie', 'parametry'],
    #     'data': [
    #         [{'fontstyle': 'm', 'value': sql}, repr(sql_params)]
    #     ]
    # })
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        godziny = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        kol_godziny = -1
        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
    for i, c in enumerate(cols):
        if c == 'godzina':
            kol_godziny = i
    if kol_godziny != -1:
        rows_zbiorczo = []
        for row in rows:
            godziny[int(row[kol_godziny])] += row[0]
            subrow = row[:-1]
            if len(rows_zbiorczo) == 0:
                rows_zbiorczo.append(subrow)
            else:
                rozne = False
                for i in range(1, len(row) - 1):
                    if row[i] != rows_zbiorczo[-1][i]:
                        rozne = True
                if rozne:
                    rows_zbiorczo.append(subrow)
                else:
                    rows_zbiorczo[-1][0] += subrow[0]
        if len(rows_zbiorczo) == 0:
            rows_zbiorczo = []
    else:
        rows_zbiorczo = rows
    # res.append({
    #     'type': 'table',
    #     'header': cols,
    #     'data': prepare_for_json(rows_zbiorczo)
    # })
    if params['flat'] and len(params['podzialy']) > 1:
        header = ['Ilość'] + [PODZIALY[podz] for podz in params['podzialy']]
        return {
            'type': 'table',
            'header': header,
            'data': prepare_for_json(rows_zbiorczo)
        }
    elif len(params['podzialy']) == 0:
        ilosc = 0
        if rows_zbiorczo:
            res.append({'type': 'info', 'text': 'Łącznie %d %s' % (
                rows_zbiorczo[0][0], lacznie)})
        else:
            res.append(
                {'type': 'info', 'text': 'Łącznie %d %s' % (ilosc, lacznie)})

    elif len(params['podzialy']) == 1:
        ilosc = 0
        for row in rows_zbiorczo:
            ilosc += row[0]
        if ilosc:
            res.append({
                'type': 'table',
                'header': ['Ilość', PODZIALY[params['podzialy'][0]]],
                'data': rows_zbiorczo
            })
        res.append({'type': 'info', 'text': 'Łącznie %d %s' % (
            ilosc, lacznie)})
    else:
        ilosc = 0
        podtabelki = len(params['podzialy']) == 3
        if podtabelki:
            podpodzialy = params['podzialy'][1:]
            biezaca_tabelka = None
            biezace_wiersze = []
            for wiersz in rows_zbiorczo:
                nazwa = wiersz[1] or 'BRAK'
                if nazwa != biezaca_tabelka:
                    if len(biezace_wiersze) > 0:
                        ilosc, tabelka = zrob_tabelke(biezace_wiersze, podpodzialy)
                        tabelka['title'] = biezaca_tabelka
                        res.append(tabelka)
                        res.append({'type': 'info', 'text': '%s - łącznie %d %s' % (biezaca_tabelka, ilosc, lacznie)})
                    biezaca_tabelka = nazwa
                    biezace_wiersze = []
                biezace_wiersze.append([wiersz[0]] + wiersz[2:])
            if len(biezace_wiersze) > 0:
                ilosc, tabelka = zrob_tabelke(biezace_wiersze, podpodzialy)
                tabelka['title'] = biezaca_tabelka
                res.append(tabelka)
                res.append({'type': 'info', 'text': '%s - łącznie %d %s' % (biezaca_tabelka, ilosc, lacznie)})
            else:
                res.append({'type': 'info',
                            'text': 'Łącznie %d %s' % (ilosc, lacznie)})
        else:
            if len(rows_zbiorczo) > 0:
                ilosc, tabelka = zrob_tabelke(rows_zbiorczo, params['podzialy'])
                res.append(tabelka)
            res.append({'type': 'info', 'text': 'Łącznie %d %s' % (ilosc, lacznie)})
    if kol_godziny != -1:
        res.append({
            'type': 'diagram',
            'subtype': 'bars',
            'title': 'Rozkład godzinowy',
            'x_axis_title': 'Godzina %s' % RODZAJE_DAT[params['rodzajdat']],
            'y_axis_title': 'Ilość badań',
            'data': [[i, v] for i, v in enumerate(godziny)]
        })

    return prepare_for_json(res)


def zbuduj_zapytanie(params):
    pierwsze_wykonania = True
    sql_wew = """
        select w.id as wykonanie, w.zlecenie,
            w.kodkreskowy as kodwykonania, zl.kodkreskowy as kodzlecenia,
            pl.symbol as platnik, pl.nazwa as platnik_nazwa,
            gpl.symbol as grupaplatnika, gpl.nazwa as grupaplatnika_nazwa,
            o.symbol as zleceniodawca, o.nazwa as zleceniodawca_nazwa,
            bl.symbol as blad, bl.nazwa as blad_nazwa,
            pa.symbol as powodanulowania, pa.nazwa as powodanulowania_nazwa,
            tz.symbol as typzlecenia, tz.nazwa as typzlecenia_nazwa,
            pr.symbol as pracownia, pr.nazwa as pracownia_nazwa,
            gpr.symbol as grupapracowni, gpr.nazwa as grupapracowni_nazwa,
            met.symbol as metoda, met.nazwa as metoda_nazwa,
            rej.symbol as rejestracja, rej.nazwa as rejestracja_nazwa,
            prrej.logowanie as pracrej_login, prrej.nazwisko as pracrej_nazwisko,
            ap.symbol as aparat, ap.nazwa as aparat_nazwa, trim(aps.symbol) as aparat_system,
            b.symbol as badanie, b.nazwa as badanie_nazwa,
            gb.symbol as grupabadan, gb.nazwa as grupabadan_nazwa,
            case when w.platne=1 then 'T' else 'N' end as platne
            $KOLUMNY_WEW$
            
        $KOLEJNOSC_SELECTA$
        left join platnicy pl on pl.id=w.platnik
        left join grupyplatnikow gpl on gpl.id=pl.grupa
        left join oddzialy o on o.id=zl.oddzial
        left join bledywykonania bl on bl.id=w.bladwykonania
        left join powodyanulowania pa on pa.id=w.powodanulowania
        left join typyzlecen tz on tz.id=zl.typzlecenia
        left join pracownie pr on pr.id=w.pracownia
        left join grupypracowni gpr on gpr.id=pr.grupa
        left join metody met on met.id=w.metoda
        left join aparaty ap on ap.id=w.aparat
        left join systemy aps on aps.id=ap.system
        left join rejestracje rej on rej.id=zl.rejestracja
        left join pracownicy prrej on prrej.id=zl.pracownikodrejestracji
        left join badania b on b.id=w.badanie
        left join grupybadan gb on gb.id=b.grupa
        where 
    """
    kolejnosc_selecta = """        from wykonania w 
        left join zlecenia zl on zl.id=w.zlecenie"""
    kolumny_wew = []
    warunki_wew = []
    params_wew = []
    params_zew = []
    group_by = []
    order_by = []
    warunek_tylko_daty = False
    if params['rodzajdat'] == 'rej':
        warunki_wew.append('(zl.datarejestracji between ? and ? )')
        kolumny_wew.append('coalesce(w.godzinarejestracji, cast(zl.datarejestracji as timestamp)) as czas')
        kolejnosc_selecta = """        from zlecenia zl
            left join wykonania w on w.zlecenie=zl.id"""
        pierwsze_wykonania = False
        warunek_tylko_daty = True
    elif params['rodzajdat'] == 'dystr':
        warunki_wew.append('(w.dystrybucja between ? and ? )')
        kolumny_wew.append('w.dystrybucja as czas')
    elif params['rodzajdat'] == 'zatw':
        warunki_wew.append('(w.zatwierdzone between ? and ? )')
        kolumny_wew.append('w.zatwierdzone as czas')
    elif params['rodzajdat'] == 'rozl':
        warunki_wew.append('(w.rozliczone between ? and ? )')
        kolumny_wew.append('w.rozliczone as czas')
        warunek_tylko_daty = True
    else:
        raise ValidationError('Nieznany rodzaj dat %s' % params['rodzajdat'])
    if warunek_tylko_daty:
        params_wew += [params['dataod'], params['datado']]
    else:
        params_wew += [params['dataod'] + ' 0:00:00', params['datado'] + ' 23:59:59']
    if params['lokalneaparaty']:
        warunki_wew.append('aps.symbol=?')
        params_wew.append(params['laboratorium'])
    sql_wew = sql_wew.replace('$KOLEJNOSC_SELECTA$', kolejnosc_selecta)

    if len(kolumny_wew) > 0:
        sql_wew = sql_wew.replace('$KOLUMNY_WEW$', ', '.join([''] + kolumny_wew))
    else:
        sql_wew = sql_wew.replace('$KOLUMNY_WEW$', '')
    # TODO warunek na nieanulowane powinien być wyłączalny
    warunki_wew.append('w.anulowane is null')
    if params['tylkobl']:
        warunki_wew.append('w.bladwykonania is not null')
    if params['bezbl']:
        warunki_wew.append('w.bladwykonania is null')
    if params['tylkopak']:
        warunki_wew.append('b.pakiet=1')
    if params['bezpak']:
        warunki_wew.append('b.pakiet=0')
    if params['tylkozatw']:
        warunki_wew.append('w.zatwierdzone is not null')
    if params['bezzatw']:
        warunki_wew.append('w.zatwierdzone is null')
    if params['tylkokontr']:
        warunki_wew.append("""(tz.symbol in ('K', 'KW') or zl.oddzial in (
            select id from oddzialy where trim(o.symbol) like '%-KW' or trim(o.symbol) like '%-KZ'))""")
    if params['bezkontr']:
        warunki_wew.append("""((tz.symbol not in ('K', 'KW') or tz.symbol is null) and zl.oddzial not in (
            select id from oddzialy where trim(o.symbol) like '%-KW' or trim(o.symbol) like '%-KZ'))""")
    if params['beztechn']:
        warunki_wew.append("(gb.symbol != 'TECHNIC' or gb.symbol is null)")
    if params['bezdopl']:
        warunki_wew.append("(gb.symbol not in ('DOPLATY', 'INNE') or gb.symbol is null)")
    if params['tylkopl']:
        warunki_wew.append('w.platne=1')
    if params['tylkokoszt']:
        warunki_wew.append('w.platne=0')
        warunki_wew.append('w.koszty=1')
    if params['tylkohl7']:
        if params['zliczajzlec']:
            warunki_wew.append('exists (select id from zleceniazewnetrzne zleze where zleze.zlecenie=zl.id)')
        else:
            warunki_wew.append('exists (select id from wykonaniazewnetrzne wykze where wykze.wykonanie=w.id)')
    if params['bezhl7']:
        if params['zliczajzlec']:
            warunki_wew.append('not exists (select id from zleceniazewnetrzne zleze where zleze.zlecenie=zl.id)')
        else:
            warunki_wew.append('not exists (select id from wykonaniazewnetrzne wykze where wykze.wykonanie=w.id)')
    if params['bezrozl']:
        warunki_wew.append(
            "(w.pracownia is null or w.pracownia not in (select id from pracownie where symbol in ('Z-ROZL', 'XROZL')))")
    if params['bezgpa']:
        warunki_wew.append("(gpr.symbol is null or gpr.symbol != 'ALAB')")
    if 'platnik_id' in params:
        if pierwsze_wykonania:
            warunki_wew.append('w.platnik = ?')
        else:
            warunki_wew.append('zl.platnik = ?')
        params_wew.append(params['platnik_id'])
    if 'oddzial_id' in params:
        if pierwsze_wykonania:
            if not params['oddzial_platnik_got']:
                warunki_wew.append('w.platnik = ?')
                params_wew.append(params['oddzial_platnik_id'])
            warunki_wew.append('zl.oddzial = ?')
            params_wew.append(params['oddzial_id'])
        else:
            warunki_wew.append('zl.oddzial = ?')
            params_wew.append(params['oddzial_id'])
    if 'pracownia_id' in params:
        warunki_wew.append('w.pracownia = ?')
        params_wew.append(params['pracownia_id'])

    if 'badanie_id' in params:
        warunki_wew.append('w.badanie = ?')
        params_wew.append(params['badanie_id'])

    sql_wew += '        ' + '\n            and '.join(warunki_wew)

    zew_kolumny = []
    if params['zliczajzlec']:
        zew_kolumny.append("count(distinct zlecenie) as ilosc")
    else:
        zew_kolumny.append("count(wykonanie) as ilosc")
    for podzial in params['podzialy']:
        kolumna = PODZIALY_SQL[podzial]
        zew_kolumny.append('%s as %s' % (kolumna, podzial))
        group_by.append(kolumna)
        order_by.append(kolumna)
    if params['wykresgodz']:
        kolumna = '(extract(hour from czas))'
        zew_kolumny.append('%s as godzina' % kolumna)
        group_by.append(kolumna)
        order_by.append(kolumna)
    # if params['kodykreskowe']:
    #     if params['zliczajzlec']:
    #         zew_kolumny.append('list(distinct kodzlecenia) as kodykreskowe')
    #     else:
    #         zew_kolumny.append('list(distinct kodwykonania) as kodykreskowe')

    sql = "select %s from (\n%s\n) as wew " % (', '.join(zew_kolumny), sql_wew)
    if len(group_by) > 0:
        sql += '\ngroup by %s' % ', '.join(group_by)
    if len(order_by) > 0:
        sql += '\norder by %s' % ', '.join(order_by)

    return sql, params_wew + params_zew


def zrob_tabelke(wiersze, podzialy):
    ilosc = 0
    poziomo_tytuly = {}
    poziomo_symbole = []
    poziomo = []
    data = []
    data_row = None
    last_row_value = None
    for wiersz in wiersze:
        ilosc += wiersz[0]
        nazwa_kr, nazwa_dl, nazwa_calosc = rozbij_krotkie_dlugie(wiersz[2])
        if nazwa_calosc not in poziomo:
            poziomo.append(nazwa_calosc)
            poziomo_symbole.append(nazwa_kr)
            poziomo_tytuly[nazwa_kr] = nazwa_dl
    indeksy_symboli = {}
    for i, symbol in enumerate(poziomo_symbole):
        indeksy_symboli[symbol] = i
    # poziomo_symbole.sort()
    for wiersz in wiersze:
        nazwa_kr, nazwa_dl, nazwa_calosc = rozbij_krotkie_dlugie(wiersz[1])
        if data_row is None or nazwa_calosc != last_row_value:
            if data_row is not None:
                data.append(data_row)
            last_row_value = nazwa_calosc
            data_row = [{'value': nazwa_kr, 'hint': nazwa_dl, 'fontstyle': 'b'}] + ['' for _ in poziomo_symbole]
        nazwa_kr, nazwa_dl, nazwa_calosc = rozbij_krotkie_dlugie(wiersz[2])
        data_row[indeksy_symboli[nazwa_kr] + 1] = {
            'value': wiersz[0], # jeśli kody kreskowe to wiersz[3]
            'hint': '%s / %s' % (wiersz[1], wiersz[2]),
        }
    if data_row is not None:
        data.append(data_row)
    header = [[
        {'title': PODZIALY[podzialy[0]], 'rowspan': 2, 'fontstyle': 'b'},
        {'title': PODZIALY[podzialy[1]], 'fontstyle': 'b', 'colspan': len(poziomo_tytuly)}
    ],
        [{'title': symbol, 'hint': poziomo_tytuly[symbol], 'fontstyle': 'b'} for symbol in poziomo_symbole]]
    tab = {
        'type': 'table',
        'header': header,
        'data': data,
    }
    return ilosc, tab


def rozbij_krotkie_dlugie(wartosc):
    if wartosc is None:
        wartosc = 'BRAK'
    if isinstance(wartosc, str) and ' - ' in wartosc:
        wartosc_t = wartosc.split(' - ')
        kr = wartosc_t[0]
        dl = wartosc_t[1]
        calosc = wartosc
    else:
        kr = dl = calosc = str(wartosc)
    return kr, dl, calosc


"""
RaportAparaty:
 - daty rozliczeniowe
 - lab
 - płatne/bezpłatne/płatne i bezpłatne
 
Tab1: poziomo aparaty, pionowo badania, na przecięciu ilość
Tab2: legenda aparatów symbol/nazwa


IleBledowLaboratorium:
 - daty
 - lab
 - dod podział: nie / płatnicy / oddziały
 - zliczanie błędów w badaniach / zleceniach

Tab: symbol, nazwa, ilość błędów; poza błędami też wykonane bez błędów i wszystkie


IleKontroliLaboratorium:
- daty
- lab


Tab: (podział na pracownie + w sumie na aparatach)
symbol, nazwa badania, grupa badań, symbol i nazwa aparatu,
ilość wszystkich oznaczeń, ilość płatnych, ilość powtórek
w tym kontrolnych (ilość, % względem wszystkich)
kontrole wewnętrzne (ilość, % względem wszystkich)
kontrole zewnętrzne (ilość, % względem wszystkich)

Wykres:
procentowy udział kontroli względem wszystkich badań, w osi poziomej aparaty


IleBadanWDanejGodzinie
- data (pojedyncza)

Wykaz ilościowy do ilu badań został przyjęty materiał w danej godzinie.
Wykaz zawiera badania płatne wykonywane na lokalnych pracowniach
Na czas przygotowywania raportów dla MZ uwzględnia tylko szpitale (???)

Tabela + Wykres Ilość / godzina 


IleBadanWDanejGodzinie_Okres
Wykaz Ilościowy do Ilu badań został przyjęty materiał w danej godzinie
Wykaz zawiera badania płatne wykonywane na lokalnych pracowniach
- 2 daty + lab (godziny przjęcia)

Tabelka z godzinami w kolumnach i datami w wierszach, ilpości na przecięciu


IleBadanWdanejGodzinieSerologia
- data zleceń
- lab
- wykluczyć grupę płatników (nie / szpital / zoz / alab)

Wykresy:
- rozkład wykonanych badań w poszczególnych godzinach
- rozkład wykonanych badań CITO w poszczególnych godzinach  
- rozkład wykonanych badań grup krwi w poszczególnych godzinach
- rozkład wykonanych badań prób krzyżowych w poszczególnych godzinach

IleZlecenWDanejGodzinie
- data zleceń
- lab

Tabelka: poziomo godziny, pionowo podział
Skaner / Centrum / HL7 / kanały internetowe


--- raczej nie do tego raportu

IleZlecenPunktyPobran
- daty
- lab
- zahaczka "tylko wykaz zleceń na potrzeby obliczenia rentowności" 

Zahaczka nie:

Tab 1
symbol i nazwa pp, dalej ilości zleceń w kolejnych dniach z przedziału

Tab 2
wykaz ile zleceń dla danego płatnika zarejestrował punkt rejstrujące się samodzielnie przez iCentrum w okresie od 01-09-2019 do 03-09-2019

Symbol i nazwa płatnika, potem idzie punktami pobrań ilość zleceń, ilość badań, wartość
+ w sumie

Tab 3
wykaz ile zleceń dla danego płatnika zarejestrował punkt poprzez moduł dystrybucji HL7 w okresie od 01-09-2019 do 03-09-2019
tabelka j.w.

Tabelka 4
wykaz wartości sprzedaży gotówkowej w ramach zleceń zarejestrowanych przez iCentrum w punkcie pobrań od 01-09-2019 do 03-09-2019 z uwzględnieniem średniej ceny paragonu
symbol i nazwa PP, ilość badań, ilość zleceń, wartość, średnia cena paragonu

Tab 5
Wykaz ile pakietów gotówkowych zarejestrowano przez iCentrum w punkcie pobrań od 01-09-2019 do 03-09-2019 z podziałem na poszczególne dni
symbol, nazwa pp, potem dniami ilość i wartość
Podsumowanie - ile pakieów + wartość



Zahaczka tak:
Tab 1
wykaz ile zleceń dla danego płatnika zarejestrował punkt rejstrujące się samodzielnie przez iCentrum w okresie od 
symbol pp, symbol i nazwa płatnika, ilość zleceń, badań, wartość

Tab 2
wykaz ile zleceń dla danego płatnika zarejestrował punkt poprzez moduł dystrybucji HL7 w okresie od 01-09-2019 do 
dane j.w.

Tab 3:
sprzedaż danego PP w podziale na grupy płatników w okresie od 01-09-2019 do 03-09-2019
Symbol i nazwa pp, symbol grupy płatników, ilość zleceń, ilość badań, wartośćma


StatystykaPacjentGotowkowy
- zakres dat
- lab

Analiza zleconych usług oraz ich wartości w poszczególnych grupach wiekowych
jako ilośc badań liczone są zarówno pakiety jak i składniki pakietów.

Tab 1:
Symbol i nazwa PP, Grupa Wiekowa, potem płciami ilość zleceń, badań i wartość
(widać że idzie po zleceniodawcach a nie po samych punktach)


Tab 2:
Analiza ile razy dany pacjent był u nas na pobraniu w okresie od 01-09-2019 do 03-09-2019
Pacjenci bez peselu nie są uwzględniani

Ilość wizyt jedna ... osiem, więcej niż osiem, w sumie

Tab 3
Analiza jakie badania kupowali pacjenci w poszczególnych miesiącach zadanego okresu od 01-09-2019 do 03-09-2019

Symbol, nazwa badania, ilość _w miesiącu_



"""
