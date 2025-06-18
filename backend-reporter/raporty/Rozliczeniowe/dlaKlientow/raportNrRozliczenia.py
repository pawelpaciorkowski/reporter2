from datetime import datetime
from math import ceil
from typing import List
from dialog import Dialog, VBox, InfoText, TextInput

from tasks import TaskGroup
from helpers import prepare_for_json, get_centrum_connection, get_snr_connection


MENU_ENTRY = 'Raport po numerze rozliczenia'
REQUIRE_ROLE = ['C-FIN', 'C-CS', 'C-ROZL']


LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text=MENU_ENTRY),
    TextInput(
        field='rozliczenie', title='Nr rozliczenia'),
))

SQL_SNR = """
    select
      substring(w.wykonanie,1,position('^' in w.wykonanie)-1) as "SYSID",
      trim(substring(w.wykonanie,position('^' in w.wykonanie)+1,7)) as "SYS",
      w.hs->'kodkreskowy' as "KOD",
      z.nazwa as "ODDZIAL",
      (w.hs->'lekarzenazwisko' || ' ' || (w.hs->'lekarzeimiona')) as "LEKARZ",
      w.hs->'pacjencipesel' as "PESEL",
      w.hs->'pacjencinazwisko' as "NAZWISKO",
      w.hs->'pacjenciimiona' as "IMIONA",
      w.hs->'pacjencidataurodzenia' as "DATAU",
      w.nazwa as "BADANIEN",
      w.badanie as "BADANIES",
      coalesce(nullif(trim(PK.hs->'kod'), ''), '-BRAK-') as "ICD9",
      w.typzlecenia as "TRYB",
      pr.netto as "CENA",
      w.material as "MATERIALS",
      r.identyfikatorwrejestrze,
      w.wykonanie as "WYKONANIE",
      w.laboratorium as "LAB"
    from rozliczenia r
      left outer join pozycjerozliczen pr on pr.rozliczenie = r.id
      left outer join wykonania w on w.id = pr.wykonanie
      left outer join pozycjekatalogow pk on pk.symbol=w.badanie and pk.katalog = 'BADANIA'
      left outer join zleceniodawcy z on w.zleceniodawca = z.id
    where r.identyfikatorwrejestrze = '%s'
      """


SQL_CENTRUM = '''
    select
        w.id as ID,
        w.sysid as SYSID,
        w.system as SYS,
        z.datarejestracji as DATAR,
        substring(cast(w.zatwierdzone as varchar(32)) from 1 for 16)  as GODZINA,
        substring(cast(w.dystrybucja as varchar(32)) from 1 for 16)  as DYST,
        z.OBCYKODKRESKOWY as NUMERZEW,
        (select min(wwz.odebrany) from wydrukiwzleceniach wwz where wwz.zlecenie=w.zlecenie) as DATAWYD
    from wykonania w
        left outer join zlecenia z on z.id=w.zlecenie
        left outer join badania b on b.id=w.badanie
        left outer join grupybadan gb on gb.id=b.grupa
        left outer join platnicy p on p.id=w.platnik
    where b.pakiet = '0' and w.platne ='1' and w.anulowane is null
    and (gb.Symbol <> 'TECHNIC' or gb.symbol is null) and ( %s ) '''


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)

    task = {
        'type': 'centrum',
        'priority': 1,
        'target': 'GWROCLA',
        'params': params,
        'timeout': 3000,
        'function': 'raport_lab',
    }
    report.create_task(task)
    report.save()
    return report


def group_ranges(values: List[int]) -> List[List]:

    id_ranges = []
    current_range = [values[0]]

    for current_id in values:
        diff = current_id - current_range[-1]

        if diff == 1:
            # Add current_range end value
            if len(current_range) == 1:
                current_range.append(current_id)
            else:
                current_range[1] = current_id
            continue
        # Add current range to id_ranges and create new
        # current range with start value of current_id
        if diff > 1:
            id_ranges.append(current_range)
            current_range = [current_id]
            continue

    id_ranges.append(current_range)
    return id_ranges


def keyed_groupped_ranges(data):
    # Order ids for each key
    for k in data:
        data[k] = sorted(data[k])

    # Group ids
    for k in data:
        data[k] = group_ranges(data[k])

    return data


def snr_sql(rozliczenie):
    return SQL_SNR % (rozliczenie)


def result_sql(data):
    grupped = keyed_groupped_ranges(data)
    systems = []
    chunk_size = 500

    def apd(data):
        ids = []
        for i in data:
            if len(i) == 1:
                ids.append(f'w.sysid = {i[0]}')
            else:
                ids.append(f'w.sysid between {i[0]} and {i[1]}')
        systems.append(system % ' or '.join(ids))

    for r in grupped:
        system = f"( w.system = '{r}' and (%s) )"
        len_grupped = len(grupped[r])
        if len_grupped > chunk_size:
            chunks = ceil(len_grupped/chunk_size)
            for i in range(chunks):
                if i == 0:
                    d = grupped[r][:chunk_size]
                    print('gstart', len(d), d[0])
                    apd(d)
                elif i == chunks:
                    d = grupped[r][chunk_size*i:]
                    print('gend', len(d), d[0])
                    apd(d)
                else:
                    d = grupped[r][chunk_size*i:(i+1)*chunk_size]
                    print('gmid', len(d), d[0])
                    apd(d)
        else:
            apd(grupped[r])
    return systems


def centrum_sql(wykonania):
    result = []
    where = result_sql(wykonania)
    for w in where:
        result.append(SQL_CENTRUM % w)
    return result


def prepera_centrum_data(centrum):
    new_tab = {}

    for row in centrum:
        sys = row['sys']
        sysid = row['sysid']
        if sys not in new_tab:
            new_tab[sys] = {}
        if sysid not in new_tab[sys]:
            new_tab[sys][sysid] = row

    return new_tab


def report_resut(tabb, new_tab):
    wynik = []
    for lb in tabb:
        sys = lb['sys']
        sysid = lb['sysid']
        lz = new_tab[sys].get(int(sysid))
        if lz:
            wynik.append([
                        lz['datar'],
                        lz['dataz'],
                        lz['godzinaz'],
                        lz['dyst'],
                        lb['kod'],
                        lb['oddzial'],
                        lb['lekarz'],
                        lb['pesel'],
                        lb['nazwisko'],
                        lb['imiona'],
                        lb['datau'],
                        lb['badanien'],
                        # lb['icd9'],
                        lb['tryb'],
                        1,
                        lb['cena'],
                        lz['numerzew'],
                        lb['badanie'],
                        lz['dataw']])
        else:
            wynik.append([
                        None,
                        None,
                        None,
                        None,
                        lb['kod'],
                        lb['oddzial'],
                        lb['lekarz'],
                        lb['pesel'],
                        lb['nazwisko'],
                        lb['imiona'],
                        lb['datau'],
                        lb['badanien'],
                        lb['tryb'],
                        1,
                        lb['cena'],
                        None,
                        lb['badanie'],
                        None])

    return {
        'type': 'table',
        'header': 'Data rejestracji;Data wykonania badania;Godzina;Data przyjęcia materiału;Kod zlecenia;Oddział zlecający;Lekarz zlecający;Pesel pacjenta;Nazwisko pacjenta;Imię pacjenta;Data urodzenia pacjenta;Nazwa badania;Tryb badania;Ilość;Cena badania;Numer zewnętrzny;Kod Usługi;Data Wydania wyniku'.split(';'),
        'data': wynik
    }


def fill_tabz_with_centrum_data(rows):
    tabz = []
    for row in rows:
        sysz = row[2]
        if row[2] is None:
            sysz = 'WOLSKI'

        syszid = row[1]
        if row[1] is None:
            syszid = row[0]
        godzina = prepare_for_json(row[4])
        if row[4] is None:
            godzina = '0000-00-00 00:00'
        tabz.append({
            'sys': sysz.strip(),
            'sysid': syszid,
            'dataz': prepare_for_json(godzina).split(' ')[0],
            'godzinaz': prepare_for_json(godzina).split(' ')[1][0:5],
            'godzina': prepare_for_json(godzina),
            'dyst': row[5],
            'numerzew': row[6],
            'datar': prepare_for_json(row[3]),
            'dataw': prepare_for_json(row[7])
        })
    return tabz


def fill_snr_tables(rows, rozliczenie):
    tabb = []
    wykonania = {}

    for row in rows:
        syss = row['SYS']
        if row['SYS'] is None:
            syss = 'BRAK'
        sbadanie = '' if row['BADANIES'] is None else row['BADANIES']
        smaterial = '' if row['MATERIALS'] is None else row['MATERIALS']
        if rozliczenie:
            row_lab = row['LAB']
            sysid, system = row['WYKONANIE'].split("^")
            if row_lab not in wykonania:
                wykonania[row_lab] = {}
            if system not in wykonania[row_lab]:
                wykonania[row_lab][system] = []
            wykonania[row_lab][system].append(int(sysid))

        tabb.append({
            'sysid': row['SYSID'],
            'sys': syss.strip(),
            'kod': row['KOD'],
            'oddzial': row['ODDZIAL'],
            'lekarz': row['LEKARZ'],
            'pesel': row['PESEL'],
            'nazwisko': row['NAZWISKO'],
            'imiona': row['IMIONA'],
            'datau': prepare_for_json(row['DATAU']),
            'badanien': row['BADANIEN'],
            'badanies': row['BADANIES'],
            'icd9': row['ICD9'],
            'tryb': row['TRYB'],
            'cena': prepare_for_json(row['CENA']),
            'badanie': sbadanie+':'+smaterial
        })

    return tabb, wykonania


def raport_lab(task_params):
    rozliczenie = task_params['params']['rozliczenie']
    centrum_data = []

    with get_snr_connection() as snr:
        sql = snr_sql(rozliczenie)
        snr_start = datetime.now()
        print(f'Rozpoczęto zapytanie do SNR {snr_start}')
        wyniki = snr.dict_select(sql)
        print(f'Zakończono zapytanie do SNR {datetime.now() - snr_start}')
        tabb, wykonania = fill_snr_tables(wyniki, rozliczenie)

    for lab_db in wykonania:
        print(f'connection to {lab_db}')
        with get_centrum_connection(lab_db, fresh=True) as conn:

            for system in wykonania[lab_db]:
                codes = wykonania[lab_db][system]
                temp = {system: codes}
                sqlz = centrum_sql(temp)
                for s in sqlz:
                    start = datetime.now()
                    print(f'started centrum {start}')
                    _, rows = conn.raport_z_kolumnami(s)
                    print(f'finished centrum {datetime.now() - start}')
                    centrum_data += fill_tabz_with_centrum_data(rows)

    c_data = prepera_centrum_data(centrum_data)

    # Raport finalny
    return report_resut(tabb, c_data)


