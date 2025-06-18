import base64

import openpyxl

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from outlib.xlsx import ReportXlsx
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_snr_connection, odpiotrkuj

MENU_ENTRY = 'Siedlce'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Proszę wybrać laboratorium oraz datę wygenerowania rozliczenia, aby pobrać zestawienie dla płatnika. Jeśli danego dnia było więcej niż jedno rozliczenie, należy podać jego identyfikator w formacie NNNNN/RRRR'),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', show_only=['SIEDLCE', 'RUDKA', 'ZAWODZI']),
    DateInput(field='data', title='Data rozliczenia', default='T'),
    TextInput(field='ident', title='Identyfikator rozliczenia')
))

PLATNICY = {
    'SIEDLCE': 'EZSIEDL',
    'RUDKA': 'EU-SZPI',
}


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    print('startReport', __PLUGIN__, params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    if params['data'] is None:
        raise ValidationError("Nie podano daty")
    sql = """select r.id, pwl.symbol, l.symbol as lab, 
                r.oddnia::varchar as oddnia, r.dodnia::varchar as dodnia, r.identyfikatorwrejestrze, f.numer, l.vpn 
            from rozliczenia r
            left join faktury f on f.rozliczenie=r.id
            left join laboratoria l on l.symbol=r.laboratorium
            left join platnicywlaboratoriach pwl on pwl.laboratorium=l.symbol and pwl.platnik=r.platnik
            where r.platnik='WZORC.1565241' and r.datarozliczenia = %s and r.laboratorium = %s"""
    sql_params = [params['data'], params['laboratorium']]
    if params['ident'] is not None:
        sql += ' and r.identyfikatorwrejestrze = %s'
        sql_params.append(params['ident'])
    with get_snr_connection() as snr:
        rozliczenia = snr.dict_select(sql, sql_params)
        if len(rozliczenia) == 0:
            raise ValidationError("Nie znaleziono rozliczenia dla podanego laboratorium, daty (i identyfikatora)")
        for fld in 'id symbol lab oddnia dodnia identyfikatorwrejestrze numer vpn'.split(' '):
            params['_rozliczenie_%s' % fld] = rozliczenia[0][fld]
    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'timeout': 2400,
        'function': 'raport_siedlce_centrum'
    }
    report.create_task(task)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport_siedlce_snr'
    }
    report.create_task(task)
    report.save()
    return report


def raport_siedlce_centrum(task_params):
    params = task_params['params']
    system = task_params['target']
    res = []
    id_wykonan = []
    with get_centrum_connection(system) as conn:
        cols, rows = conn.raport_z_kolumnami("""
            select w.id as wykonanie, z.id as zlecenie, w.rozliczone, z.numer, 
                z.datarejestracji, w.godzina as godzinapobrania,
                w.zatwierdzone as godzinawydruku, 
                b.symbol, m.symbol, wz.parametry,
                pl.nazwa, o.nazwa, coalesce(lek.nazwisko, '') || ' ' || coalesce(lek.imiona, ''),
                w.kodkreskowy,
                pac.nazwisko, pac.imiona, pac.dataurodzenia, pac.pesel,
                tz.symbol, b.nazwa, m.nazwa, b.kod, m.kod,
                z.godzinarejestracji, w.dystrybucja,
                w.system, w.sysid, w.rozliczone
            from wykonania w 
            left join zlecenia z on z.id=w.zlecenie
            left outer join platnicy pl on pl.id=z.platnik
            left outer join oddzialy o on o.id=z.oddzial
            left outer join pacjenci pac on pac.id=z.pacjent
            left outer join lekarze lek on lek.id=z.lekarz
            left outer join typyzlecen tz on tz.id=z.typzlecenia
            left outer join badania b on b.id=w.badanie
            left outer join materialy m on m.id=w.material
            left outer join wykonaniazewnetrzne wz on wz.wykonanie=w.id
            where w.rozliczone between ? and ? and w.platnik in (select id from platnicy where symbol='%s' and del=0) --  
            order by w.rozliczone, z.datarejestracji, z.numer, b.symbol, m.symbol
        """ % PLATNICY[system], [params['_rozliczenie_oddnia'], params['_rozliczenie_dodnia']])
        # TODO: jak nie pójdzie to zmniejszyć zakres dat, zrzucić ręcznie albo i
        for row in rows:
            if row[0] in id_wykonan:
                continue
            id_wykonan.append(row[0])
            row[9] = odpiotrkuj(row[9])
            res.append(row)
    return res


def raport_siedlce_snr(task_params):
    params = task_params['params']
    with get_snr_connection() as snr:
        cols, rows = snr.select("""
            select w.id, w.wykonanie, pr.netto, w.hs->'kodkreskowy',
            coalesce(w.badanie, '') || ':' || coalesce(w.material, '') || ' ' || coalesce(w.hs->'numer', '') || '/' || coalesce(w.datarejestracji::text, '') as opis
            from wykonania w
            left join pozycjerozliczen pr on pr.wykonanie=w.id
            where pr.rozliczenie=%s""", [params['_rozliczenie_id']])
        # wcześniej zamiast pr.netto było w.nettodlaplatnika
        return rows


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    params = dane_centrum = dane_snr = None
    results = []
    errors = []
    for job_id, task_params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            if task_params['function'] == 'raport_siedlce_centrum':
                dane_centrum = result
                params = task_params['params']
                params['system'] = task_params['target']
            elif task_params['function'] == 'raport_siedlce_snr':
                dane_snr = result
    if dane_centrum is not None and dane_snr is not None:
        rap = RaportWykonaniaCentrumSnr(dane_centrum, dane_snr, params)
        rap.laduj_slownik('/var/www/reporter/config_files/siedlce_slownik_2.xlsx')
        results.append(rap.zrob_raport())
        results.append({
            'type': 'info',
            'text': 'Wygenerowano zestawienie. Proszę sprawdzić czy suma cen pozycji zgadza się z wartością faktury!'
        })
        for err in rap.braki():
            errors.append(err)
    return {
        'results': results,
        'progress': task_group.progress,
        'actions': [],
        'errors': errors,
    }


class RaportWykonaniaCentrumSnr:
    def __init__(self, dane_centrum, dane_snr, params):
        self.dane_centrum = dane_centrum
        self.dane_snr = dane_snr
        self.params = params
        self.system = params['laboratorium']
        self.snr_bylo = []

    def laduj_slownik(self, filename):
        self.slownik = {}
        self.slownik_hl7 = {}
        self.slownik_powtorki = {}
        wb = openpyxl.load_workbook(filename)
        ws = wb.active
        for row in ws:
            bad = row[0].value
            mat = row[1].value or ''
            bad_hl7 = row[2].value or ''
            mat_hl7 = row[3].value or ''
            if bad is None:
                continue
            nazwa = row[4].value
            bad_mat = bad + ':' + mat
            bad_mat_hl7 = bad_hl7 + ':' + mat_hl7
            if bad_mat_hl7 != ':':
                if bad_mat_hl7 in self.slownik_hl7:
                    if nazwa != self.slownik_hl7[bad_mat_hl7]:
                        raise Exception('Powtórzony ident. hl7 z różnymi nazwami', bad_mat_hl7, nazwa,
                                        self.slownik_hl7[bad_mat_hl7])
                self.slownik_hl7[bad_mat_hl7] = nazwa
            if bad_mat in self.slownik:
                if nazwa != self.slownik[bad_mat]:
                    n1p = self.slownik[bad_mat].split('|')[0]
                    n2p = nazwa.split('|')[0]
                    if n1p != n2p:
                        if bad_mat not in self.slownik_powtorki:
                            self.slownik_powtorki[bad_mat] = []
                        if nazwa not in self.slownik_powtorki[bad_mat]:
                            self.slownik_powtorki[bad_mat].append(nazwa)
                        if self.slownik[bad_mat] not in self.slownik_powtorki[bad_mat]:
                            self.slownik_powtorki[bad_mat].append(self.slownik[bad_mat])
            self.slownik[bad_mat] = nazwa
            if bad not in self.slownik:
                self.slownik[bad] = nazwa

    def braki(self):
        res = []
        for row in self.dane_snr:
            if row[1] not in self.snr_bylo:
                res.append("Brak danych z Centrum dla wiersza %s" % "; ".join([str(v) for v in row]))
        return res

    def zrob_raport(self):
        fn = "wykaz_badan_do_faktury-%s_%s_%s.xlsx" % (
            self.params['system'], (self.params['_rozliczenie_symbol'] or 'BRAK'),
            (self.params['_rozliczenie_numer'] or 'BRAK').replace('/', '_')
        )
        ceny_wykonan = {}
        kody_wykonan = {}
        opisy_wykonan = {}
        pelne_identy = {}
        result_rows = []
        systemy = []
        for row in self.dane_snr:
            ident = row[1]
            sys_id = int(row[1].split('^')[0])
            system = row[1].split('^')[1]
            if system not in systemy:
                systemy.append(system)
            cena = row[2]
            ceny_wykonan[ident] = cena
            kody_wykonan[ident] = row[3]
            opisy_wykonan[ident] = row[4]
            pelne_identy[ident] = row[1]
        for row in self.dane_centrum:
            ident = '%d^%s' % (row[26], row[25].strip())
            if ident not in ceny_wykonan:
                continue
            self.snr_bylo.append(ident)
            nazwa_hl7 = None
            parametry = row[9]
            ident_hl7 = ''
            if 'Badanie' in parametry:
                ident_hl7 = parametry['Badanie']
            ident_hl7 += ':'
            if 'Material' in parametry:
                ident_hl7 += parametry['Material']
            if ident_hl7 != ':':
                nazwa_hl7 = self.slownik_hl7.get(ident_hl7)
            bad = row[7].strip()
            mat = (row[8] or '').strip()
            bad_mat = bad + ':' + mat
            nazwa_bm = self.slownik.get(bad_mat, self.slownik.get(bad))
            nazwa = nazwa_hl7 or nazwa_bm or bad_mat
            row[9] = nazwa  # zastępujemy parametry
            rodzaj_bad = row[19]
            if row[20] is not None:
                rodzaj_bad += ' (' + row[20] + ')'
            if row[21] is not None:
                rodzaj_bad += ' (IDC9: ' + row[21]
                if row[22] is not None:
                    rodzaj_bad += '.' + row[22]
                rodzaj_bad += ')'
            uwagi = []
            if nazwa == bad_mat:
                uwagi.append('Badanie spoza umowy')
            elif ceny_wykonan.get(ident, 0) == 0:
                uwagi.append('Zerowa cena badania')
            result_row = [
                row[10], row[11], row[12], row[13],
                row[14], row[15], row[16], row[17],
                row[18], row[5], row[6],
                rodzaj_bad, ceny_wykonan.get(ident), row[23],
                'BRAK DANYCH',
                row[24], nazwa, '; '.join(uwagi), ident_hl7, bad_mat
            ]
            result_rows.append(result_row)
        cols = ['Płatnik', 'Jednostka organizacyjna', 'Lekarz zlecający', 'Kod kreskowy',
                'Nazwisko pac.', 'Imiona pac.', 'Data ur. pac.', 'PESEL pac.',
                'Tryb badania', 'Data i godz. pobrania', 'Data i godz. wydania wyniku',
                'Rodzaj badania', 'Cena badania', 'Data i godz. przyjęcia zlecenia',
                'Data i godz. wyjścia próbki z oddziału zlecającego',
                'Data i godz. przyjęcia materiału do badań', 'Pozycje z wykazu', 'Uwagi', 'Ident. HL7', 'Symbol Alab']

        # TODO: raport mógłby zwracać postać do ściągnięcia od razu
        # TODO 2; mogłoby to być jednak ściągane dopiero po kliknięciu

        rep = ReportXlsx({'results': [{
            'type': 'table',
            'header': cols,
            'data': prepare_for_json(result_rows)
        }]})

        return {
            'type': 'download',
            'content': base64.b64encode(rep.render_as_bytes()).decode(),
            'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'filename': fn,
        }
