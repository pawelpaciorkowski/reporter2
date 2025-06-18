from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError, Switch, Preset
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, empty  # get_centrum_connection
from datasources.nocka import NockaDatasource

# TODO: jeśli zaznaczone tylko błędy wykonania to pozwolić cały rok

# prio 1

# IleBledowLaboratorium, IleKontroliLaboratorium,
# IleBadanWDanejGodzinie, IleBadanWDanejGodzinie_Okres, IleBadanWDanejGodzinieSerologia
# IleZlecenWDanejGodzinie

# RaportAparaty?

SOURCE_TABLE = 'wykonania_pelne'
MENU_ENTRY = 'Policz badania - NOCKA'
REQUIRE_ROLE = ['ADMIN']

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
    'grupybadan': 'Grupy badań',
    'badania': 'Badania',
    'bledy': 'Błędy wykonania',
    'dni': 'Dni',
    'godziny': 'Godziny',
}

PODZIALY_SQL = {
    'platnicy': "(platnik || ' - ' || platnik_nazwa)",
    'grupyplatnikow': "(grupaplatnika || ' - ' || grupaplatnika_nazwa)",
    'zleceniodawcy': "(zleceniodawca || ' - ' || zleceniodawca_nazwa)",
    'typyzlecen': "(typzlecenia || ' - ' || typzlecenia_nazwa)",
    'pracownie': "(pracownia || ' - ' || pracownia_nazwa)",
    'aparaty': "(aparat || ' - ' || aparat_nazwa)",
    'rejestracje': "(rejestracja || ' - ' || rejestracja_nazwa)",
    'metody': "(metoda || ' - ' || metoda_nazwa)",
    'grupybadan': "(grupabadan || ' - ' || grupabadan_nazwa)",
    'badania': "(badanie || ' - ' || badanie_nazwa)",
    'bledy': "(blad || ' - ' || blad_nazwa)",
    'dni': "(cast(czas as date))",
    'godziny': "(extract(hour from czas))",
}

RODZAJE_DAT = {'rej': 'Rejestracji', 'dystr': 'Przyjęcia materiału', 'zatw': 'Zatwierdzenia',
               'rozl': 'Rozliczeniowa'}

PRESETS = [
    ("Ile błędów w laboratorium", {
        'rodzajdat': 'zatw',
        'fresh': False,
        'tylkokontr': False, 'bezkontr': False,
        'beztechn': False, 'bezdopl': False,
        'tylkobl': True, 'bezbl': False,
        'tylkozatw': False, 'bezzatw': False,
        'tylkopak': False, 'bezpak': False,
        'tylkopl': False, 'bezrozl': True,
        'bezgpa': False,
        'zliczajzlec': False, 'wykresgodz': True,
        'podzial1': 'bledy', 'podzial2': 'brak', 'podzial3': 'brak',
    }),
    ("Ile kontroli w laboratorium", {
        'rodzajdat': 'zatw',
        'fresh': False,
        'tylkokontr': True, 'bezkontr': False,
        'beztechn': False, 'bezdopl': False,
        'tylkobl': False, 'bezbl': False,
        'tylkozatw': False, 'bezzatw': False,
        'tylkopak': False, 'bezpak': False,
        'tylkopl': False, 'bezrozl': True,
        'bezgpa': False,
        'zliczajzlec': False, 'wykresgodz': True,
        'podzial1': 'brak', 'podzial2': 'brak', 'podzial3': 'brak',
    }),
    ("Ile badań w danej godzinie", {
        'rodzajdat': 'dystr',
        'fresh': False,
        'tylkokontr': False, 'bezkontr': True,
        'beztechn': True, 'bezdopl': False,
        'tylkobl': False, 'bezbl': False,
        'tylkozatw': False, 'bezzatw': False,
        'tylkopak': False, 'bezpak': False,
        'tylkopl': False, 'bezrozl': True,
        'bezgpa': False,
        'zliczajzlec': False, 'wykresgodz': True,
        'podzial1': 'brak', 'podzial2': 'brak', 'podzial3': 'brak',
    }),
    ("Ile zleceń w danej godzinie", {
        'rodzajdat': 'rej',
        'fresh': False,
        'tylkokontr': False, 'bezkontr': True,
        'beztechn': True, 'bezdopl': False,
        'tylkobl': False, 'bezbl': False,
        'tylkozatw': False, 'bezzatw': False,
        'tylkopak': False, 'bezpak': False,
        'tylkopl': False, 'bezrozl': True,
        'bezgpa': False,
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
        HBox(
            Switch(field="fresh", title="Bieżąca baza danych (Stępińska, tylko 1 dzień)"),
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
            Switch(field="bezrozl", title="Bez pracowni rozliczeniowych", default=True),
        ),

        # BRAK GRUPY PRACOWNI W TABELI SŁOWNIK
        # HBox(
        #     Switch(field="bezgpa", title="Bez grupy pracowni ALAB"),
        # ),
        HBox(
            TextInput(field="symbolp", title="Symbol płatnika"),
            TextInput(field="symbolz", title="Symbol zleceniodawcy"),
        ),
        HBox(
            TextInput(field="symbolb", title="Pojedyncze badanie"),
        ),
        InfoText(text="Prezentacja danych"),
        Switch(field="zliczajzlec", title="Zliczaj całe zlecenia (a nie pojedyncze wykonania)"),
        Switch(field="wykresgodz", title="Pokaż rozkład godzinowy"),
        # Switch(field="kodykreskowe", title="Dołącz kody kreskowe"),
        HBox(
            Select(field="podzial1", title="Podział 1", values=PODZIALY),
            Select(field="podzial2", title="Podział 2", values=PODZIALY),
            Select(field="podzial3", title="Podział 3", values=PODZIALY),
        )
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
    if params['fresh'] and params['dataod'] != params['datado']:
        raise ValidationError('Dla pobierania danych z bazy bieżącej należy wybrać zakres jednego dnia')
    if params['tylkokontr'] and params['bezkontr']:
        raise ValidationError('Tylko kontrolne i bez kontrolnych?')
    if params['tylkobl'] and params['bezbl']:
        raise ValidationError('Tylko błędne i bez błędów?')
    if params['tylkozatw'] and params['bezzatw']:
        raise ValidationError('Tylko zatwierdzone i tylko niezatwierdzone?')
    if params['bezzatw'] and params['rodzajdat'] == 'zatw':
        raise ValidationError('Bez zatwierdzonych, wg dat zatwierdzenia?')
    if params['tylkopak'] and params['bezpak']:
        raise ValidationError('Tylko pakiety i bez pakietów?')
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
        'type': 'noc',
        'priority': 1,
        'params': params,
        'function': 'raport_nocka'
    }
    report.create_task(task)
    report.save()
    return report


def pobierz_slowniki(symbol, table):
    ds = NockaDatasource()
    sql = f'''SELECT lab_id, symbol, nazwa
        FROM {table} 
        WHERE symbol = {symbol} and del=0 '''
    cols, rows = ds.select(sql)

    return rows


def raport_nocka(task_params):
    ds = NockaDatasource()
    params = task_params['params']

    lacznie = 'zleceń' if params['zliczajzlec'] else 'wykonań'
    res = []

    if not empty(params['symbolp']) or not empty(params['symbolz']) or not empty(params['symbolb']):

        # pobierz dane dla sybolu płatnika
        if not empty(params['symbolp']):
            rows = ds.select('platnicy', [params['symbolp']])
            if len(rows) > 0:
                params['platnik_id'] = rows[0][0]
                res.append({'type': 'info', 'text': 'Tylko płatnik %s - %s' % (rows[0][1], rows[0][2])})
            else:
                return {'type': 'error', 'text': 'Nie znaleziono płatnika'}

        # pobierz dane dla symbolu zleceniodawcy
        if not empty(params['symbolz']):
            rows = ds.select('platnicy', [params['symbolz']])

            if len(rows) > 0:
                params['oddzial_id'] = rows[0][0]
                res.append(
                    {'type': 'info', 'text': 'Tylko zleceniodawca %s - %s' % (rows[0][1], rows[0][2])})
            else:
                return {'type': 'error', 'text': 'Nie znaleziono zleceniodawcy'}

        # pbierz dane dla pojepdyńczego badenia
        if not empty(params['symbolb']):
            rows = ds.select('platnicy', [params['symbolb']])

            if len(rows) > 0:
                params['badanie_id'] = rows[0][0]
                res.append({'type': 'info', 'text': 'Tylko badanie %s - %s' % (rows[0][1], rows[0][2])})
            else:
                return {'type': 'error', 'text': 'Nie znaleziono badania'}


    linki_podgladu = params['dataod'] == params['datado']
    print(params)
    sql, sql_params = zbuduj_zapytanie(params)
    print(sql, sql_params)
    godziny = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    kol_godziny = -1
    cols, rows = ds.select(sql, sql_params)
    for i, c in enumerate(cols):
        if c == 'godzina':
            kol_godziny = i

    if kol_godziny != -1:
        rows_zbiorczo = []
        for row in rows:
            godziny[row[kol_godziny]] += row[0]
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
            rows_zbiorczo = [[0]]
    else:
        rows_zbiorczo = rows

    if len(params['podzialy']) == 0:
        res.append({'type': 'info', 'text': 'Łącznie %d %s' % (rows_zbiorczo[0][0], lacznie)})
    elif len(params['podzialy']) == 1:
        ilosc = 0
        for row in rows_zbiorczo:
            ilosc += row[0]
        res.append({
            'type': 'table',
            'header': ['Ilość', PODZIALY[params['podzialy'][0]]],
            'data': rows_zbiorczo
        })
        res.append({'type': 'info', 'text': 'Łącznie %d %s' % (ilosc, lacznie)})
    else:
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
    sql_wew = f"""
        select w.lab_id as wykonanie, w.lab_zlecenie,
            w.lab_kodkreskowy as kodwykonania, w.lab_zlecenie_kodkreskowy as kodzlecenia,
            w.platnik_zlecenia as platnik, w.platnik_zlecenia_nazwa as platnik_nazwa,
            w.kanal as grupaplatnika, w.kanal_nazwa as grupaplatnika_nazwa,
            w.zleceniodawca as zleceniodawca, w.zleceniodawca_nazwa as zleceniodawca_nazwa,
            w.blad_wykonania as blad, w.blad_wykonania_nazwa as blad_nazwa,
            w.typ_zlecenia as typzlecenia, w.typ_zlecenia_nazwa as typzlecenia_nazwa,
            w.pracownia, w.pracownia_nazwa,
            --symbol as grupapracowni, gpr.nazwa as grupapracowni_nazwa,
            w.metoda, w.metoda_nazwa,
            --rej.symbol as rejestracja, rej.nazwa as rejestracja_nazwa,
            w.aparat, w.aparat_nazwa,
            w.badanie, w.badanie_nazwa,
            w.grupa_badan as grupabadan, w.grupa_badan_nazwa as grupabadan_nazwa
            
            $KOLUMNY_WEW$
        
        from {SOURCE_TABLE} as w 
      
           
        where 
            
    """
    kolumny_wew = []
    warunki_wew = []
    params_wew = []
    params_zew = []
    group_by = []
    order_by = []
    warunek_tylko_daty = False


    # Data rejestracji
    if params['rodzajdat'] == 'rej':
        warunki_wew.append('(w.lab_zlecenie_data between %s and %s)')
        kolumny_wew.append('coalesce(w.lab_wykonanie_godz_rejestracji, cast(zl.lab_zlecenie_data as timestamp)) as czas')
        warunek_tylko_daty = True

    # Data przyjecia materiału
    elif params['rodzajdat'] == 'dystr':
        warunki_wew.append('(w.lab_wykonanie_godz_dystrybucji between %s and %s)')
        kolumny_wew.append('w.lab_wykonanie_godz_dystrybucji  as czas')

    # Data ztwierdzenia
    elif params['rodzajdat'] == 'zatw':
        warunki_wew.append('(w.lab_wykonanie_godz_zatw between %s and %s)')
        kolumny_wew.append('w.lab_wykonanie_godz_zatw as czas')

    # Data rozliczeniowa
    elif params['rodzajdat'] == 'rozl':
        warunki_wew.append('(w.lab_wykonanie_data_rozliczenia between %s and %s)')
        kolumny_wew.append('w.lab_wykonanie_data_rozliczenia as czas')
        warunek_tylko_daty = True
    else:
        raise ValidationError('Nieznany rodzaj dat %s' % params['rodzajdat'])

    # Data to datetime
    if warunek_tylko_daty:
        params_wew += [params['dataod'], params['datado']]
    else:
        params_wew += [params['dataod'] + ' 0:00:00', params['datado'] + ' 23:59:59']

    if len(kolumny_wew) > 0:
        sql_wew = sql_wew.replace('$KOLUMNY_WEW$', ', '.join([''] + kolumny_wew))
    else:
        sql_wew = sql_wew.replace('$KOLUMNY_WEW$', '')

    warunki_wew.append('w.lab_wykonanie_godz_anulowania is null')

    if params['laboratorium']:
        warunki_wew.append('w.lab in ( %s )')
        params_wew.append(params['laboratorium'])
    if params['tylkobl']:
        warunki_wew.append('w.lab_bladwykonania is not null')
    if params['bezbl']:
        warunki_wew.append('w.lab_bladwykonania is null')
    if params['tylkopak']:
        warunki_wew.append('w.lab_pakiet=1')
    if params['bezpak']:
        warunki_wew.append('w.lab_pakiet=0')
    if params['tylkozatw']:
        warunki_wew.append('w.lab_wykonanie_godz_zatw is not null')
    if params['bezzatw']:
        warunki_wew.append('w.lab_wykonanie_godz_zatw is null')

    if params['tylkokontr']:
        warunki_wew.append("""(w.typ_zlecenia in ('K', 'KW')
            )""")

    if params['bezkontr']:
        warunki_wew.append("""((w.typ_zlecenia not in ('K', 'KW') or w.typ_zlecenia is null))""")

    # Bez technicznych
    if params['beztechn']:
        warunki_wew.append("(w.grupa_badan != 'TECHNIC' or w.grupa_badan is null)")

    if params['bezdopl']:
        warunki_wew.append("(w.grupa_badan not in ('DOPLATY', 'INNE') or w.grupa_badan is null)")

    if params['tylkopl']:
        warunki_wew.append('w.lab_platne=1')

    # Bez pracowni rozliczeniowych
    if params['bezrozl']:
        warunki_wew.append(
            """(w.lab_pracownia is null or w.pracownia not in ('Z-ROZL', 'XROZL'))""")

    # BRAK GRUPY PRACOWNI W TABELI SŁOWNIK
    # if params['bezgpa']:
    #     warunki_wew.append("(gpr.symbol is null or gpr.symbol != 'ALAB')")

    if 'platnik_id' in params:
        warunki_wew.append('w.lab_zlecenie_platnik = ?')
        params_wew.append(params['platnik_id'])

    if 'oddzial_id' in params:
        warunki_wew.append('w.lab_oddzial = ?')
        params_wew.append(params['oddzial_id'])

    if 'badanie_id' in params:
        warunki_wew.append('w.lab_badanie = ?')
        params_wew.append(params['badanie_id'])

    sql_wew += '        ' + '\n            and '.join(warunki_wew)

    zew_kolumny = []

    if params['zliczajzlec']:
        zew_kolumny.append("count(distinct lab_zlecenie) as ilosc")
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

    sql = "select %s from (\n%s\n) as foo" % (', '.join(zew_kolumny), sql_wew)
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
            'value': wiersz[0],  # jeśli kody kreskowe to wiersz[3]
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
