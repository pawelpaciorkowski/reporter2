import json
import os
import traceback
import time
import progressbar
import datetime

import datasources.centrum
from datasources.nocka import NockaDatasource
from datasources.reporter import ReporterDatasource
from tasks import TaskGroup, Task
from helpers import Kalendarz, get_snr_connection, get_centrum_connection, divide_chunks, divide_by_key, globalny_hash_pacjenta
from helpers.cli import pb_iterate

MARCEL_FRESH = True

MENU_ENTRY = None

POMIN_ZAWSZE = 'SWIECIE ZAMOSC PRZ-PLN PRZ-KUT PRZ-SIE PINCZOW MIECHOW JEDRZEJ'.split(' ')
POMIN_TIMEOUT = ''.split(' ')
STARA_BAZA = 'HISTZDU JEDRZEJ HISTMSW HISTGDY HISTPOZ LUBINSE ELK PRABUTY GDYNPOW '.split(' ')

SQL_WYKONANIA_COMMON = """
    select w.id as lab_id, w.dc as lab_dc, w.system as lab_system, w.sysid as lab_sysid, z.id as lab_zlecenie,
        z.numer as lab_zlecenie_nr, z.datarejestracji as lab_zlecenie_data,
        z.system as lab_zlecenie_system, z.sysid as lab_zlecenie_sysid,
        pac.plec as lab_pacjent_plec, pac.dataurodzenia as lab_pacjent_data_urodzenia,
        w.pakiet as lab_pakiet, coalesce(b.pakiet, 0) as lab_jest_pakietem,
        w.godzinarejestracji as lab_wykonanie_godz_rejestracji, w.godzina as lab_wykonanie_godz_pobrania,
        w.dystrybucja as lab_wykonanie_godz_dystrybucji,
        w.wykonane as lab_wykonanie_godz_wykonania, w.zatwierdzone as lab_wykonanie_godz_zatw,
        w.anulowane as lab_wykonanie_godz_anulowania, w.rozliczone as lab_wykonanie_data_rozliczenia,
        w.kodkreskowy as lab_kodkreskowy, z.kodkreskowy as lab_zlecenie_kodkreskowy,
        w.badanie as lab_badanie, w.material as lab_material, b.grupa as lab_grupa_badan,
        w.pracownia as lab_pracownia, w.metoda as lab_metoda, w.aparat as lab_aparat,
        w.bladwykonania as lab_bladwykonania, w.powodanulowania as lab_powodanulowania,
        w.wydrukowane as lab_wykonanie_godz_wydruku,
        z.typzlecenia as lab_typzlecenia, pr.kanalinternetowy as lab_kanal, 
        z.oddzial as lab_oddzial, z.platnik as lab_zlecenie_platnik, w.platnik as lab_wykonanie_platnik,
        plz.grupa as lab_zl_gr_platnika, plw.grupa as lab_wyk_gr_platnika,
        pr.id as lab_zlecenie_prac_rej, w.pracownikodrejestracji as lab_pracownik_rejestracji,
        w.pracownikodwykonania as lab_pracownik_wykonania, w.pracownikodzatwierdzenia as lab_pracownik_zatwierdzenia,
        w.cena as lab_cena, w.platne as lab_platne,
        case when UPPER (pob.NAZWISKO) = UPPER(pob.NUMER) and pob.HL7SYSID is not NULL then 1 else 0 end as lab_znacznik_dystrybucja,
        case when gb.symbol in ('TECHNIC', 'DOPLATY', 'INNE') or TZ.Symbol in ('K', 'KZ', 'KW') then 1 else 0 end as lab_techniczne_lub_kontrola,
        case when gp.symbol = 'ALAB' then 1 else 0 end as lab_pracownia_alab,
        pac.nazwisko as pacjent_nazwisko, pac.imiona as pacjent_imiona, pac.pesel as pacjent_pesel
    $KOLEJNOSC$         
        left join badania b on b.id=w.badanie
        left join pracownie p on p.id=w.pracownia
        left join pracownicy pr on pr.id=z.pracownikodrejestracji
        left join poborcy pob on pob.id=w.poborca
        left join typyzlecen tz on tz.id=z.typzlecenia
        left join grupypracowni gp on gp.id=p.grupa
        left join grupybadan gb on gb.id=b.grupa
        left join platnicy plz on plz.id=z.platnik
        left join platnicy plw on plw.id=w.platnik
        left join pacjenci pac on pac.id=z.pacjent
    where $WARUNEK$
"""

SQL_KOLEJNOSC_WYKONANIA = """
    from wykonania w
        left join zlecenia z on z.id=w.zlecenie
"""

SQL_KOLEJNOSC_ZLECENIA = """
    from zlecenia z
        left join wykonania w on w.zlecenie = z.id
"""

SQL_WYNIKI = """
    select y.id as lab_id, y.dc as lab_dc, y.del as lab_del, y.wykonanie as lab_wykonanie,
        w.zatwierdzone as lab_zatwierdzone, coalesce(y.badanie, w.badanie) as lab_badanie,
        w.metoda as lab_metoda, y.parametr as lab_parametr, y.norma as lab_norma,
        y.wynikliczbowy, y.wyniktekstowy, y.opis, y.ukryty, y.poprawiony, y.obowiazkowy,
        y.flaganormy, y.normatekstowa, y.zakresnormyod, y.zakresnormydo, y.flagadeltacheck,
        y.flagakrytycznych, y.rodzajparametru, y.wynikmic
    from wyniki y
    left join wykonania w on w.id=y.wykonanie
    where y.wykonanie in ($LISTA_WYKONAN$)
"""

SQL_NORMY = """
    select 
        trim(b.symbol) as badanie,
        trim(m.SYMBOL) as metoda,
        trim(p.symbol) as parametr,
        p.nazwa as parametr_nazwa,
        n.id as lab_id, n.del as lab_del, n.dc as lab_dc,
        n.opis, n.DLUGIOPIS, n.ZAKRESOD, n.ZAKRESDO,
        n.DOWOLNYWIEK, n.WIEKOD, n.WIEKDO, n.JEDNOSTKAWIEKU,
        n.DOWOLNAPLEC, trim(pl.symbol) as plec,
        n.DOWOLNYTYPNORMY, trim(tn.symbol) as typnormy, tn.nazwa as typnormy_nazwa,
        n.WYDRUKNORM,
        n.KRYTYCZNYPONIZEJ, n.KRYTYCZNYPOWYZEJ, n.KIEDYZATWIERDZANIE, n.ZATWIERDZANIEOD, n.ZATWIERDZANIEDO
    from normy n
        left join parametry p on p.id=n.PARAMETR
        left join metody m on m.id=p.metoda
        left join badania b on b.id=m.BADANIE
        left join plci pl on pl.id=n.PLEC
        left join TYPYNORM tn on tn.id=n.TYPNORMY
        left join MATERIALY mat on mat.id=n.MATERIAL
    where not m.SYMBOL like 'X-%'
"""

SQL_METODY = """
    select
        pm.id as lab_id,
        (pm.del+m.del+b.del+p.del) as lab_del,
        maxvalue(pm.dc, m.dc, b.dc) as lab_dc,
        trim(b.Symbol) as BADANIE, 
        b.CzasMaksymalny as czas_max, 
        trim(m.Symbol) as METODA,
        m.NAZWA as METODA_NAZWA,
        trim(p.symbol) as pracownia
                
    FROM PowiazaniaMetod pm 
    left outer join Badania b on b.id = pm.badanie and b.del = 0 
    left outer join Metody m on m.id = pm.metoda and m.del = 0 
    left outer join Systemy s on s.id = pm.system and s.del = 0 
    left outer join Pracownie p on p.id = m.pracownia and p.del = 0 
    WHERE 
        s.SYMBOL=? and pm.del=0 and m.del=0 and b.del=0 and p.del=0
        and pm.dowolnytypzlecenia=1 and pm.dowolnarejestracja=1 and pm.dowolnyoddzial=1 and pm.dowolnyplatnik=1 and pm.dowolnymaterial=1
"""


# TODO: wykonywanie w taskach, powiązanie tasków zależnościami (zakończenie uzupełniania lab powinno kolejkować task snr)

class LabSynchroniser:
    def __init__(self, lab):
        self.lab = lab
        self.ds = NockaDatasource(read_write=True)
        self.existing_idents = []
        self.touched_this_session = []

    def _update_existing(self, idents):
        idents = [id for id in idents if id not in self.existing_idents]
        if len(idents) == 0:
            return
        self.existing_idents += self.ds.get_lab_existing_idents(self.lab, idents)

    def _synchronizuj_slownik(self, slownik, translacja):
        def translacja_wew(row):
            res = translacja(row)
            res['id'] = row['id']
            res['dc'] = row['dc']
            res['del'] = row['del'] == 0
            if 'parametry' in res and isinstance(res['parametry'], dict):
                res['parametry'] = json.dumps(res['parametry'])
            if 'symbol' in row and row['symbol'] is not None:
                res['symbol'] = row['symbol'].strip()
            return res

        last_dc = self.ds.get_slownik_last_dc(self.lab, slownik)
        sql = "select * from " + slownik
        sql_params = []
        if last_dc is not None:
            sql += " where dc >= ?"
            sql_params.append(last_dc)
        with get_centrum_connection(self.lab, fresh=MARCEL_FRESH) as conn:
            rows = conn.raport_slownikowy(sql, sql_params)
        rows = [translacja_wew(row) for row in rows]
        self.ds.load_lab_slownik(self.lab, slownik, rows)
        self.ds.commit()

    def synchronizuj_slowniki(self):
        self._synchronizuj_slownik('badania', lambda row: {
            'symbol': row['symbol'],
            'nazwa': row['nazwa'],
            'parametry': {
                'grupa': row['grupa'],
                'grupadorejestracji': row['grupadorejestracji'],
                'pakiet': row['pakiet']
            }
        })
        self._synchronizuj_slownik('grupybadan', lambda row: {
            'symbol': row['symbol'],
            'nazwa': row['nazwa'],
        })
        self._synchronizuj_slownik('grupydorejestracji', lambda row: {
            'symbol': row['symbol'],
            'nazwa': row['nazwa'],
        })
        self._synchronizuj_slownik('materialy', lambda row: {
            'symbol': row['symbol'],
            'nazwa': row['nazwa'],
        })
        self._synchronizuj_slownik('pracownie', lambda row: {
            'symbol': row['symbol'],
            'nazwa': row['nazwa'],
        })
        self._synchronizuj_slownik('aparaty', lambda row: {
            'symbol': row['symbol'],
            'nazwa': row['nazwa'],
        })
        self._synchronizuj_slownik('oddzialy', lambda row: {
            'symbol': row['symbol'],
            'nazwa': row['nazwa'],
        })
        self._synchronizuj_slownik('platnicy', lambda row: {
            'symbol': row['symbol'],
            'nazwa': row['nazwa'],
            'parametry': {
                'nip': row['nip'],
            }
        })
        self._synchronizuj_slownik('grupyplatnikow', lambda row: {
            'symbol': row['symbol'],
            'nazwa': row['nazwa'],
        })
        self._synchronizuj_slownik('kanaly', lambda row: {
            'symbol': row['symbol'],
            'nazwa': row['nazwa'],
        })
        self._synchronizuj_slownik('pracownicy', lambda row: {
            'nazwa': row['logowanie'],
            'parametry': {
                'nazwisko': row['nazwisko'],
                'kanal': row['kanalinternetowy'],
            }
        })
        self._synchronizuj_slownik('metody', lambda row: {
            'symbol': row['symbol'],
            'nazwa': row['nazwa'],
            'parametry': {
                'badanie': row['badanie'],
                'kod': row['kod'],
                'pracownia': row['pracownia'],
                'aparat': row['aparat'],
            }
        })
        self._synchronizuj_slownik('parametry', lambda row: {
            'symbol': row['symbol'],
            'nazwa': row['nazwa'],
            'parametry': {
                'metoda': row['metoda'],
                'nazwaalternatywna': row['nazwaalternatywna'],
                'typ': row['typ'],
                'pochodzenie': row['pochodzenie'],
                'format': row['format'],
                'wyrazenie': row['wyrazenie'],
                'kolejnosc': row['kolejnosc'],
            }
        })
        self._synchronizuj_slownik('typyzlecen', lambda row: {
            'symbol': row['symbol'],
            'nazwa': row['nazwa'],
        })
        self._synchronizuj_slownik('bledywykonania', lambda row: {
            'symbol': row['symbol'],
            'nazwa': row['nazwa'],
        })
        self._synchronizuj_slownik('powodyanulowania', lambda row: {
            'symbol': row['symbol'],
            'nazwa': row['nazwa'],
        })
        self._synchronizuj_slownik('plci', lambda row: {
            'symbol': row['symbol'],
            'nazwa': row['nazwa'],
        })

    def synchronizuj_metody_i_normy(self):
        last_dc = None
        idents = []
        # TODO odkomentować / zrobić oddzielną synchronizację norm
        for row in self.ds.dict_select("select lab_id, lab_dc from normy where lab=%s", [self.lab]):
            if last_dc is None or last_dc < row['lab_dc']:
                last_dc = row['lab_dc']
            idents.append(row['lab_id'])
        sql = SQL_NORMY
        sql_params = []
        if last_dc is not None:
            sql += ' and (n.dc >= ? or (n.dd is not null and n.dd >= ?)) '
            sql_params += [last_dc, last_dc]
        with get_centrum_connection(self.lab, fresh=MARCEL_FRESH) as conn:
            rows = conn.raport_slownikowy(sql, sql_params)
        for row in pb_iterate(rows):
            row['lab'] = self.lab
            row['lab_del'] = row['lab_del'] != 0
            row['dowolnywiek'] = row['dowolnywiek'] == 1
            row['dowolnaplec'] = row['dowolnaplec'] == 1
            row['dowolnytypnormy'] = row['dowolnytypnormy'] == 1
            if row['lab_id'] in idents:
                self.ds.update('normy', {'lab': self.lab, 'lab_id': row['lab_id']}, row)
            else:
                self.ds.insert('normy', row)
        self.ds.commit()
        last_dc = None
        idents = []
        idents_not_del = []
        for row in self.ds.dict_select("select lab_id, lab_dc, lab_del from metody where lab=%s", [self.lab]):
            if last_dc is None or last_dc < row['lab_dc']:
                last_dc = row['lab_dc']
            idents.append(row['lab_id'])
            if not row['lab_del']:
                idents_not_del.append(row['lab_id'])
        sql = SQL_METODY
        sql_params = [self.lab]
        last_dc = None # TODO poprawka
        if last_dc is not None:
            sql += ' and maxvalue(pm.dc, m.dc, b.dc) >= ? '
            sql_params.append(last_dc)
        with get_centrum_connection(self.lab, fresh=MARCEL_FRESH) as conn:
            rows = conn.raport_slownikowy(sql, sql_params)
        byly_id = set()
        for row in pb_iterate(rows):
            row['lab'] = self.lab
            row['lab_del'] = row['lab_del'] != 0
            byly_id.add(row['lab_id'])
            if row['lab_id'] in idents:
                self.ds.update('metody', {'lab': self.lab, 'lab_id': row['lab_id']}, row)
            else:
                self.ds.insert('metody', row)
        for lab_id in idents:
            if lab_id not in byly_id:
                self.ds.update('metody', {'lab': self.lab, 'lab_id': lab_id}, {'lab_del': True})
        self.ds.commit()

    def _synchronizuj_wykonania_z_danych(self, rows):
        rows = [row for row in rows if row['lab_id'] not in self.touched_this_session]
        if len(rows) == 0:
            return
        idents = [row['lab_id'] for row in rows]
        self._update_existing(idents)
        new_rows = []
        existing_rows = []
        pacjenci = {}
        for row in rows:
            if row['lab_zlecenie'] not in pacjenci:
                pacjenci[row['lab_zlecenie']] = globalny_hash_pacjenta(
                    row['pacjent_nazwisko'], row['pacjent_imiona'], row['pacjent_pesel'], row['lab_pacjent_data_urodzenia']
                )
            for fld in ('pacjent_nazwisko', 'pacjent_imiona', 'pacjent_pesel'):
                del row[fld]
            if row['lab_id'] in self.existing_idents:
                existing_rows.append(row)
            else:
                new_rows.append(row)
        print('chunk', len(idents), len(new_rows), len(existing_rows))
        self.ds.load_lab_new(self.lab, new_rows)
        self.ds.load_lab_existing(self.lab, existing_rows)
        self.ds.load_patients(self.lab, pacjenci)
        self.existing_idents += [row['lab_id'] for row in new_rows]
        self.touched_this_session += idents

    def _synchronizuj_wykonania_nowe(self, data):
        sql = SQL_WYKONANIA_COMMON.replace('$WARUNEK$', """
            z.datarejestracji = ? and w.id is not null
        """).replace('$KOLEJNOSC$', SQL_KOLEJNOSC_ZLECENIA)
        if self.lab in STARA_BAZA:
            sql = sql.replace(
                "case when UPPER (pob.NAZWISKO) = UPPER(pob.NUMER) and pob.HL7SYSID is not NULL then 1 else 0 end", "0")
        with get_centrum_connection(self.lab, fresh=MARCEL_FRESH) as conn:
            for chunk in conn.raport_slownikowy_chunked(sql, [data], chunk_size=1000):
                self._synchronizuj_wykonania_z_danych(chunk)
        self.ds.commit()

    def _synchronizuj_wykonania_rozliczone_zatwierdzone(self, data):
        sql = SQL_WYKONANIA_COMMON.replace('$WARUNEK$', """
            (w.rozliczone = ? or w.zatwierdzone between ? and ? or w.wydrukowane between ? and ? or w.godzinarejestracji between ? and ?) and z.datarejestracji <> ?
        """).replace('$KOLEJNOSC$', SQL_KOLEJNOSC_WYKONANIA)
        if self.lab in STARA_BAZA:
            sql = sql.replace(
                "case when UPPER (pob.NAZWISKO) = UPPER(pob.NUMER) and pob.HL7SYSID is not NULL then 1 else 0 end", "0")
        kal = Kalendarz()
        kal.ustaw_teraz(data)
        nast_dzien = kal.data('+1D')
        czas_od = data + ' 0:00:00'
        czas_do = nast_dzien + ' 0:00:00'
        last_zatw = None
        with get_centrum_connection(self.lab, fresh=MARCEL_FRESH) as conn:
            sql_params = [data, czas_od, czas_do, czas_od, czas_do, czas_od, czas_do, data]
            for chunk in conn.raport_slownikowy_chunked(sql, sql_params,
                                                        chunk_size=1000):
                self._synchronizuj_wykonania_z_danych(chunk)
                for row in chunk:
                    if row['lab_wykonanie_godz_zatw'] is not None and \
                            (last_zatw is None or row['lab_wykonanie_godz_zatw'] > last_zatw):
                        last_zatw = row['lab_wykonanie_godz_zatw']
        self.ds.commit()
        return last_zatw

    def _uzupelnij_wyniki(self, data):
        sql_do_uzupelnienia = """
            select w.id, w.lab, w.lab_id, b.symbol, w.lab_results_updated_at
            from slowniki b
            left join wykonania w on b.slownik='badania' and b.lab=w.lab and b.lab_id=w.lab_badanie
            where
                b.symbol in ('2019COV', '19COVA', '19COVN', 'COV-GEN', 'VIPCOVP', 'VIPCOVA', 'VIPCOVN',
                    'SLCOVP', 'SLCOVA', 'SLCOVN',
                    'COVANTA', 'COVANTN', 'COVM+GA', 'COV2IGG', 'COV2IGM', 'SARCOVW', 'CANPOCP', 'CANPOCA', 'CANPOCN', 
                    'COVIGAM', 'COV2-IL', 'COV-ILA', 'COVIGGA', 'COVIGMA', 'COV2M+G', 'COVAIGG', 'COVAIGM', 'COVAM+G', 'ECOVIGG',
                    'COVAGGA', 'COVAGMA', 'COV2ANT', 'COVPAK', 'SARSCV2', 'COVGPOL', 'COVWARP', 'COVWARA', 'COVWARN')
                and w.lab = %s
                and w.id is not null 
                and (lab_results_updated_at is null or lab_results_updated_at < lab_wykonanie_godz_zatw)
        """
        rows = self.ds.dict_select(sql_do_uzupelnienia, [self.lab])
        if len(rows) == 0:
            return False
        wykonania = {}
        for row in rows:
            wykonania[row['lab_id']] = row['id']
        with get_centrum_connection(self.lab) as conn:
            for chunk in divide_chunks(rows, 1000):
                id_wykonan = ','.join(['%d' % row['lab_id'] for row in chunk])
                sql_wyniki = SQL_WYNIKI.replace('$LISTA_WYKONAN$', id_wykonan)
                for row in conn.raport_slownikowy(sql_wyniki, [self.lab]):
                    row['lab'] = self.lab
                    row['wykonanie'] = wykonania[row['lab_wykonanie']]
                    for fld in ('lab_del', 'ukryty', 'obowiazkowy', 'poprawiony'):
                        row[fld] = row[fld] not in (0, None)
                    self.ds.insert('wyniki', row)
        for row in rows:
            self.ds.update('wykonania', {'id': row['id']}, {'lab_results_updated_at': 'NOW'})
        self.ds.commit()
        return True

    def synchronizuj_dzien(self, data):
        print(self.lab, data)
        self._synchronizuj_wykonania_nowe(data)
        last_zatw = self._synchronizuj_wykonania_rozliczone_zatwierdzone(data)
        self._uzupelnij_wyniki(data)
        return last_zatw


def synchronizuj_snr():
    ds = NockaDatasource(read_write=True)
    snr = get_snr_connection()
    braki = ds.get_snr_braki()
    print("%d do uzupełnienia z SNR" % len(braki))
    for chunk in pb_iterate(divide_chunks(braki, chunk_size=1000)):
        idents_map = {}
        snr_rows = []
        for rows in divide_by_key(chunk, lambda row: row['lab']):
            lab = rows[0]['lab']
            if lab == 'KOPERNI':
                lab = 'KOPERNIKA'
            data_od = data_do = None
            idents = []
            for row in rows:
                data = row['lab_wykonanie_data_rozliczenia']
                if data_od is None or data_od > data:
                    data_od = data
                if data_do is None or data_do < data:
                    data_do = data
                ident = "%d^%s" % (row['lab_sysid'], row['lab_system'].replace("'", ""))
                idents.append("'%s'" % ident)
                idents_map[ident] = row['id']
            if len(idents) == 0:
                continue
            sql = """
                select w.id, w.wykonanie, w.platnik, w.zleceniodawca, w.platnikzleceniodawcy, w.nettodlaplatnika,
                    pl.nip
                from wykonania w
                left join platnicy pl on pl.id=w.platnik
                where w.laboratorium=%s and w.datarozliczeniowa between %s and %s and w.wykonanie in ($IDENTS$)
            """.replace('$IDENTS$', ','.join(idents))
            snr_rows += snr.dict_select(sql, [lab, data_od, data_do])
        snr_updates = []
        for row in snr_rows:
            warunek = {'id': idents_map[row['wykonanie']]}
            wartosci = {
                'snr_id': row['id'],
                'snr_platnik': row['platnik'],
                'snr_zleceniodawca': row['zleceniodawca'],
                'snr_platnik_zleceniodawcy': row['platnikzleceniodawcy'],
                'snr_nettodlaplatnika': row['nettodlaplatnika'],
                'snr_nip_platnika': row['nip'],
                'snr_updated_at': 'NOW',
            }
            snr_updates.append((warunek, wartosci))
        ds.multi_update('wykonania', snr_updates)
    ds.commit()


def lab_sync_task(task_params):
    lab = task_params['target']
    params = task_params['params']
    ls = LabSynchroniser(lab)
    ls.ds.update('log_synchronizacje', {'id': params['log_id']}, {'start_at': datetime.datetime.now()})
    ls.ds.commit()
    try:
        ls.synchronizuj_slowniki()
        last_zatw = ls.synchronizuj_dzien(params['data'])
        ls.ds.update('log_synchronizacje', {'id': params['log_id']}, {
            'end_at': datetime.datetime.now(), 'success': True, 'last_zatwierdzone': last_zatw,
        })
        ls.ds.commit()
        return 42, params['data'], lab
    except Exception as e:
        ls.ds.update('log_synchronizacje', {'id': params['log_id']}, {
            'end_at': datetime.datetime.now(), 'success': False, 'log': traceback.format_exc()
        })
        ls.ds.commit()
        raise


def synchronizuj_dzien(data, tylko_laby=None):
    print('Synchronizacja dnia', data)
    rep = ReporterDatasource()
    nds = NockaDatasource(read_write=True)
    nds.execute("""update log_synchronizacje set end_at=now(), success=false, log='Sesja niezakończona przez 24h' 
                    where extract(epoch from now() - start_at)>86400 and end_at is null""")
    omit_labs = POMIN_ZAWSZE + POMIN_TIMEOUT + [row['system'] for row in nds.dict_select("""
        select system from log_synchronizacje where sync_date=%s and (success or end_at is null)
    """, [data])]
    tasks = []
    for lab in rep.dict_select("select * from laboratoria where aktywne and adres_fresh is not null and wewnetrzne"):
        if lab['symbol'] in omit_labs:
            continue
        if tylko_laby is not None and lab['symbol'] not in tylko_laby:
            continue
        log_id = nds.insert('log_synchronizacje', {'system': lab['symbol'], 'sync_date': data})
        tasks.append({
            'type': 'centrum',
            'priority': 1,
            'target': lab['symbol'],
            'params': {'data': data, 'log_id': log_id},
            'function': 'lab_sync_task',
            'timeout': 2400
        })
    nds.commit()
    if len(tasks) == 0:
        print('  nic do zrobienia')
        return
    print('  %d labów' % len(tasks))
    task_group = TaskGroup(__PLUGIN__, {})
    for task in tasks:
        task_group.create_task(task)
        # tu zapisać początki sesji i końce / faile
    task_group.save()
    finished = False
    finished_labs = []
    success_labs = []
    failed_labs = []
    pb = progressbar.ProgressBar(maxval=len(tasks))
    pb.start()
    while not finished:
        for job_id, params, status, result in task_group.get_tasks_results():
            lab = params['target']
            if lab not in finished_labs:
                if status == 'finished' and result is not None:
                    finished_labs.append(lab)
                    success_labs.append(lab)
                elif status == 'failed':  # timeout to też failed
                    finished_labs.append(lab)
                    failed_labs.append(lab)
                    log_id = params['params']['log_id']
                    for row in nds.dict_select("select * from log_synchronizacje where id=%s", [log_id]):
                        if row['end_at'] is None:
                            nds.update('log_synchronizacje', {'id': log_id},
                                       {'end_at': 'NOW', 'success': False, 'log': 'TIMEOUT'})
                            nds.commit()
        pb.update(len(finished_labs))
        if len(finished_labs) == len(tasks):
            finished = True
        else:
            time.sleep(5)
    pb.finish()
    print('  pobrano dane z %d labów, nie udało się pobrać z %d: %s' % (
        len(success_labs), len(failed_labs), ', '.join(failed_labs)
    ))


def str_id(lab, ident):
    return '%d^%s' % (ident, lab)


def akcja_uzupelniania():
    nds = NockaDatasource(read_write=True)
    sql = """
        select
            w.id, w.lab, w.lab_id, b.symbol as badanie,
            w.lab_wykonanie_godz_zatw
        from wykonania w
        left join slowniki b on b.slownik='badania' and b.lab=w.lab and b.lab_id=w.lab_badanie 
        left join slowniki pr on pr.slownik='pracownie' and pr.lab=w.lab and pr.lab_id=w.lab_pracownia
        where w.lab_wykonanie_godz_wydruku is null and b.symbol in ('2019COV', '19COVA', 'COV-GEN')
        limit 40000
    """
    do_uzupelnienia = nds.dict_select(sql)
    if len(do_uzupelnienia) == 0:
        return False
    labs = []
    for row in do_uzupelnienia:
        if row['lab'] not in labs:
            labs.append(row['lab'])
    print('Laby: %s' % ', '.join(labs))
    dane = {}
    for lab in labs:
        idents = [row['lab_id'] for row in do_uzupelnienia if row['lab'] == lab]
        for chunk in divide_chunks(idents, 1000):
            idents_s = ','.join(['%d' % ident for ident in chunk])
            lab_sql = "select id, wydrukowane from wykonania where id in (%s)" % idents_s
            with get_centrum_connection(lab) as conn:
                for row in conn.raport_slownikowy(lab_sql):
                    dane[str_id(lab, row['id'])] = row['wydrukowane']
    print('uzupełnianie')
    for row in do_uzupelnienia:
        nds.update('wykonania', {'id': row['id']}, {
            'lab_wykonanie_godz_wydruku': dane[str_id(row['lab'], row['lab_id'])],
            'lab_updated_at': 'NOW'
        })
    nds.commit()
    return True


def uzupelniaj_wyniki():
    # WYN_ID_FN = '/tmp/wyniki_id'
    # if os.path.exists(WYN_ID_FN):
    #     with open(WYN_ID_FN, 'r') as f:
    #         wyniki_id = json.loads(f.read())
    # else:
    #     wyniki_id = []

    sql_do_uzupelnienia = """
        select w.id, w.lab, w.lab_id, b.symbol, w.lab_results_updated_at
        from slowniki b
        left join wykonania w on b.slownik='badania' and b.lab=w.lab and b.lab_id=w.lab_badanie
        where
            b.symbol in ('2019COV', '19COVA', '19COVN', 'COV-GEN', 'VIPCOVP', 'VIPCOVA', 'VIPCOVN',
                    'SLCOVP', 'SLCOVA', 'SLCOVN',
                    'COVANTA', 'COVANTN', 'COVM+GA', 'COV2IGG', 'COV2IGM', 'SARCOVW', 'CANPOCP', 'CANPOCA', 'CANPOCN', 
                    'COVIGAM', 'COV2-IL', 'COV-ILA', 'COVIGGA', 'COVIGMA', 'COV2M+G', 'COVAIGG', 'COVAIGM', 'COVAM+G', 'ECOVIGG',
                    'COVAGGA', 'COVAGMA', 'COV2ANT', 'COVPAK', 'SARSCV2', 'COVGPOL', 'COVWARP', 'COVWARA', 'COVWARN')
            and w.id is not null and w.lab_wykonanie_godz_zatw is not null and w.lab_wykonanie_godz_zatw >= '2021-09-01'
            and (lab_results_updated_at is null or lab_results_updated_at<lab_wykonanie_godz_zatw)
        limit 10000
    """
    nds = NockaDatasource(read_write=True)
    rows = nds.dict_select(sql_do_uzupelnienia)
    if len(rows) == 0:
        return False
    laby = {}

    for row in rows:
        # if row['id'] in wyniki_id:
        #     raise Exception('Powtórzone id', row['id'])
        # wyniki_id.append(row['id'])

        if row['lab'] not in laby:
            laby[row['lab']] = {'wykonania': {}, 'wiersze': [], 'czasy': {}}
        laby[row['lab']]['wykonania'][row['lab_id']] = row['id']
        laby[row['lab']]['czasy'][row['lab_id']] = row['lab_results_updated_at']
        laby[row['lab']]['wiersze'].append(row)
    for lab, dane in laby.items():
        print(lab, len(dane['wiersze']))
        try:
            with get_centrum_connection(lab) as conn:
                for chunk in divide_chunks(dane['wiersze'], 1000):
                    id_wykonan = ','.join(['%d' % row['lab_id'] for row in chunk])
                    sql_wyniki = SQL_WYNIKI.replace('$LISTA_WYKONAN$', id_wykonan)
                    for row in conn.raport_slownikowy(sql_wyniki, [lab]):
                        row['lab'] = lab
                        row['wykonanie'] = dane['wykonania'][row['lab_wykonanie']]
                        for fld in ('lab_del', 'ukryty', 'obowiazkowy', 'poprawiony'):
                            row[fld] = row[fld] not in (0, None)
                        if dane['wykonania'][row['lab_wykonanie']] is None:
                            nds.insert('wyniki', row)
                        else:
                            existing = nds.dict_select("select id from wyniki where wykonanie=%s and lab_parametr=%s",
                                                       [row['wykonanie'], row['lab_parametr']])
                            if len(existing) > 0:
                                nds.update('wyniki', {'id': existing[0]['id']}, row)
                            else:
                                nds.insert('wyniki', row)
            for row in dane['wiersze']:
                nds.update('wykonania', {'id': row['id']}, {'lab_results_updated_at': datetime.datetime.now()})
        except datasources.centrum.CentrumConnectionError as e:
            print('NIE UDAŁO SIĘ POŁĄCZYĆ', lab)
        nds.commit()
        # with open(WYN_ID_FN, 'w') as f:
        #     json.dump(wyniki_id, f)

    return True


def synchronizuj_slowniki(lab):
    ls = LabSynchroniser(lab)
    ls.synchronizuj_slowniki()

# 508906371


# create unique index on pacjenci(lab, lab_zlecenie);
# create index on pacjenci(pacjent);
# create index on pacjenci(sprawdzony);