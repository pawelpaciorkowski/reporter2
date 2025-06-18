from pprint import pprint
from dialog import Dialog, VBox, LabSelector, InfoText, DateInput, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup
from helpers import prepare_for_json  # get_centrum_connection
from datasources.nocka import NockaDatasource

MENU_ENTRY = 'Ile zleceń dla płatnika - iCentrum - NOCKA'

REQUIRE_ROLE = ['C-FIN', 'C-CS', 'PP-S', 'C-PP']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport ile zleceń dla danego płatnika zarejestrowały punkty pobra rejestrujące się samodzielnie przez iCentrum'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa', default='-7D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
))

SQL_SP = """
    SELECT 
        lab as SYMBOL
        ,kanal as NAZWA
        ,platnik_zlecenia as PLATNIKS
        ,platnik_zlecenia_nazwa as PLATNIK
        ,kanal_nazwa as GPL
        ,count(distinct lab_zlecenie_sysid) as ILOSC
        ,count(lab_id) as BAD
        ,sum(lab_cena) as WART
        ,cast(string_agg(distinct lab_zlecenie::text, ';') as varchar(32765)) as LISTA

    FROM public.wykonania_pelne
    where 
        lab in %s 
        and lab_zlecenie_data between %s and %s
        and lab_pracownik_rejestracji is not null
        and lab_kanal is not null
        and lab_wykonanie_godz_anulowania is null
        and lab_platne = '1'
        and (grupa_badan != 'TECHNIC' or grupa_badan is null)
    group by 
        platnik_zlecenia
        ,platnik_zlecenia_nazwa
        ,kanal_nazwa
        ,lab
        ,kanal
    order by 
        lab
        ,kanal 
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)

    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")

    validate_date_range(params['dataod'], params['datado'], 31)
    for lab in params['laboratoria']:
        lab_task = {
            'type': 'noc',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'zbierz_lab',
        }
        report.create_task(lab_task)
    report.save()
    return report


def zbierz_lab(task_params):
    ds = NockaDatasource()
    params = task_params['params']
    oddnia = params['dataod']
    dodnia = params['datado']
    res = []
    sql = SQL_SP
    sql_params = [tuple(params['laboratoria']), oddnia, dodnia]
    cols, rows = ds.select(sql, sql_params)
    for row in rows:
        res.append([task_params['target']] + list(row))
    return res


def check(table, key, row, row_number):
    """

    :param table:
    :param key:
    :param row:
    :param row_number:
    :return:
    """
    nxt = next((i for i in table if i[key] == prepare_for_json(row[row_number])), None)
    if nxt is None:
        return True
    return False


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': ['xlsx']
    }
    nocka = NockaDatasource()
    wiersze = []
    wierszeg = []
    TabSkadPacjent = []
    TabPlatnicySP = []
    TabGrupa = []
    TabKanalyGrupa = []

    for job_id, params, status, result in task_group.get_tasks_results():
        pprint(result)
        if status == 'finished' and result is not None:
            for row in result:
                # print('dostepne w row :', params)
                lab = params['target']

                # Print Row
                # pprint({
                #     '0': row[0],
                #     '1': row[1],
                #     '2': row[2],
                #     '3': row[3],
                #     '4': row[4],
                #     '5': row[5],
                # })

                # Check na PLATNIK
                if check(TabPlatnicySP, 'symbol', row, 3):
                    TabPlatnicySP.append({
                        'lab': prepare_for_json(row[0]),
                        'symbol': prepare_for_json(row[3]),
                        'nazwa': prepare_for_json(row[4])})

                # Check na NAZWA -> kanal
                if check(TabKanalyGrupa, 'symbol', row, 2):
                    TabKanalyGrupa.append({
                        'lab': prepare_for_json(row[0]),
                        'symbol': prepare_for_json(row[2]),
                        'nazwa': prepare_for_json(row[5])})

                if check(TabGrupa, 'Gpl', row, 5):
                    TabGrupa.append({'Gpl': prepare_for_json(row[5])})

                sqlSNR = """select sum(w.snr_nettodlaplatnika) as wart 
                            from wykonania_pelne W 
                            where W.lab_zlecenie_data between '%s' and '%s' 
                            and w.lab = '%s' 
                            and w.lab_zlecenie in (%s) 
                            and  W.lab_platne; """ % (
                    params['params']['dataod'],
                    params['params']['datado'],
                    lab,
                    row[9].replace(';', ','))
                _, rows = nocka.select(sqlSNR)

                wartosc = 0
                if row[8] is None:
                    print(sqlSNR)
                    wartosc = rows[0][0]
                else:
                    wartosc = row[8]

                TabSkadPacjent.append({
                    'lab': prepare_for_json(row[0]),
                    'Symbol': prepare_for_json(row[2]),
                    'Platnik': prepare_for_json(row[3]),
                    'Ilosc': prepare_for_json(row[6]),
                    'Badania': prepare_for_json(row[7]),
                    'Wartosc': prepare_for_json(wartosc)})

        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])

    # pprint('#############################################')
    # pprint(TabPlatnicySP[:5])
    # pprint(TabKanalyGrupa[:5])
    # pprint(TabGrupa[:5])
    # pprint(TabSkadPacjent[:5])

    # Tabela 1 start
    for platnik in TabPlatnicySP:
        linia = []
        for kanal in TabKanalyGrupa:

            dane = next(
                (i for i in TabSkadPacjent if i['Platnik'] == platnik['symbol'] and i['Symbol'] == kanal['symbol']),
                {'lab': kanal['lab'],
                 'Symbol': kanal['symbol'],
                 'Platnik': platnik['symbol'],
                 'Ilosc': '',
                 'Badania': '',
                 'Wartosc': ''})

            if dane is not None:
                # linia.append(list(dane.values())[2])
                linia.append(list(dane.values())[3])
                linia.append(list(dane.values())[4])
                linia.append(list(dane.values())[5])

        wiersze.append(list(platnik.values()) + linia)

    suma = ['', 'W SUMIE', 'W sumie']

    #####################

    for kanal in TabKanalyGrupa:
        iloscZlecen = 0
        iloscBadan = 0
        wartosc = 0
        for i in TabSkadPacjent:
            if i['Symbol'] == kanal['symbol']:
                iloscZlecen = iloscZlecen + int(i['Ilosc'])
                iloscBadan = iloscBadan + int(i['Badania'])
                if i['Wartosc'] != '' and i['Wartosc'] is not None:
                    wartosc = wartosc + float(i['Wartosc'])
        suma.append(iloscZlecen)
        suma.append(iloscBadan)
        suma.append((format(float(wartosc), '7.2f')))
    wiersze.append(suma)

    header = ['Laboratorium', 'Symbol', 'Nazwa płatnika']
    for platnik in TabPlatnicySP:
        header.append({'title': platnik['symbol'], 'colspan': 3})
    # Tabela 1 end

    # Tabela 2 start
    for platnik in TabPlatnicySP:
        if 'GOTO' in platnik['symbol']:
            for kanal in TabKanalyGrupa:
                daneg = next(
                    (i for i in TabSkadPacjent if i['Platnik'] == platnik['symbol'] and i['Symbol'] == kanal['symbol']),
                    None)

                if daneg is not None:
                    linia = [kanal['lab'], kanal['symbol'], kanal['nazwa']]
                    # linia.append(list(daneg.values())[2])
                    linia.append(list(daneg.values())[3])
                    linia.append(list(daneg.values())[4])
                    linia.append(list(daneg.values())[5])
                    srednia = format(float(list(daneg.values())[5]) / float(list(daneg.values())[3]), '7.2f')
                    linia.append(srednia)
                    wierszeg.append(linia)


    # HEADERY
    headerFull = []
    headerlist = []
    header = []

    # Dodaj podstawowe headery dla tabeli 1
    header.append({'title': 'Laboratorium', 'rowspan': 2, 'fontstyle': 'b'})
    header.append({'title': 'Symbol płatnika', 'rowspan': 2, 'fontstyle': 'b'})
    header.append({'title': 'Nazwa płatnika', 'rowspan': 2, 'fontstyle': 'b'})

    # Dodaj kolumny w tabeli 1 (GPL/Symbol Punktu Pobran)
    for kanal in TabKanalyGrupa:
        header.append({'title': kanal['symbol'], 'rowspan': 1, 'colspan': 3, 'fontstyle': 'b'})

    headerFull.append(header)

    # Dodaj kolumny w tabeli 2
    for kanal in TabKanalyGrupa:
        headerlist.append({'title': 'Ilość zleceń'})
        headerlist.append({'title': 'Ilość badań'})
        headerlist.append({'title': 'Wartość'})

    headerFull.append(headerlist)

    res['progress'] = task_group.progress

    res['results'].append({
        'type': 'table',
        'title': 'wykaz ile zleceń dla danego płatnika zarejestrował punkt rejstrujące się samodzielnie przez iCentrum',
        'header': headerFull,
        'data': wiersze
    })

    res['results'].append({
        'type': 'table',
        'title': 'wykaz wartości sprzedaży gotówkowej w ramach zleceń zarejestrowanych przez iCentrum w punkcie pobrań z uwzględnieniem średniej ceny paragonu',
        'header': 'Laboratorium,Symbol \nPunktu Pobrań,Nazwa\nPunktu Pobrań,Ilość Zleceń,Ilość Badań,Wartość,Średnia Cena Paragonu'.split(
            ','),
        'data': wierszeg
    })

    return res
