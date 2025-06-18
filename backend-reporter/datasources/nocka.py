from .postgres import PostgresDatasource
from helpers import Kalendarz
from helpers.helpers import get_local_open_vpn_address
from config import Config

DDL = """

create table slowniki (
    id serial primary key,
    slownik varchar(32),
    lab varchar(10),
    lab_id bigint,
    snr_id varchar(32),
    symbol varchar(10),
    nazwa varchar(512),
    parametry jsonb,
    dc timestamp,
    del boolean
);

create index on slowniki(slownik, lab, lab_id);
create index on slowniki(slownik, lab, symbol);
create index on slowniki(slownik, symbol, del);
create index on slowniki(slownik, symbol);
create index on slowniki(slownik, snr_id);
create index on slowniki(slownik, lab, dc);

CREATE INDEX idx_platnicy_nip ON slowniki USING BTREE ((parametry->>'nip')) where slownik='platnicy';
-- https://bitnine.net/blog-postgresql/postgresql-internals-jsonb-type-and-its-indexes/

create table wykonania (
    id serial primary key,
    lab varchar(10),
    lab_id bigint,
    lab_dc timestamp,
    lab_system varchar(10),
    lab_sysid bigint,
    lab_zlecenie bigint,
    lab_zlecenie_nr int,
    lab_zlecenie_data date,
    lab_zlecenie_system varchar(10),
    lab_zlecenie_sysid varchar(10),
    lab_pacjent_plec bigint,
    lab_pacjent_data_urodzenia date,
    lab_pakiet bigint,
    lab_jest_pakietem boolean,
    lab_wykonanie_godz_rejestracji timestamp,
    lab_wykonanie_godz_pobrania timestamp,
    lab_wykonanie_godz_dystrybucji timestamp,
    lab_wykonanie_godz_wykonania timestamp,
    lab_wykonanie_godz_zatw timestamp,
    lab_wykonanie_godz_anulowania timestamp,
    lab_wykonanie_data_rozliczenia date,
    lab_kodkreskowy varchar(32),
    lab_zlecenie_kodkreskowy varchar(32),
    lab_badanie bigint,
    lab_material bigint,
    lab_grupa_badan bigint,
    lab_pracownia bigint,
    lab_metoda bigint,
    lab_aparat bigint,
    lab_bladwykonania bigint,
    lab_powodanulowania bigint,
    lab_typzlecenia bigint,
    lab_kanal bigint,
    lab_oddzial bigint,
    lab_zlecenie_platnik bigint,
    lab_wykonanie_platnik bigint,
    lab_zl_gr_platnika bigint,
    lab_wyk_gr_platnika bigint,
    lab_pracownik_rejestracji bigint,
    lab_zlecenie_prac_rej bigint,
    lab_pracownik_wykonania bigint,
    lab_pracownik_zatwierdzenia bigint,
    lab_cena decimal(12, 2),
    lab_platne boolean,
    lab_znacznik_dystrybucja boolean, -- UPPER (p.NAZWISKO) = UPPER(p.NUMER) and p.HL7SYSID is not NULL ; p - poborca
    lab_techniczne_lub_kontrola boolean, -- GrupaBadan.Symbol in ('TECHNIC', 'DOPLATY', 'INNE') or TypZlecenia.Symbol in ('K', 'KZ', 'KW')
    lab_pracownia_alab boolean, -- GrupaPracowni.symbol = 'ALAB'
    
    snr_id varchar(32),
    snr_platnik varchar(32),
    snr_zleceniodawca varchar(32),
    snr_platnik_zleceniodawcy varchar(32),
    snr_nettodlaplatnika decimal(12, 2),
    snr_nip_platnika varchar(32),
    
    created_at timestamp,
    lab_updated_at timestamp,
    snr_updated_at timestamp
    
);

create unique index on wykonania(lab, lab_id);
create index on wykonania(lab, lab_zlecenie);
create index on wykonania(lab, snr_id);
create index on wykonania(created_at);
create index on wykonania(lab_updated_at);
create index on wykonania(snr_updated_at);
create index on wykonania(snr_nip_platnika);
create index on wykonania(lab_zlecenie_data);
create index on wykonania(lab_wykonanie_godz_rejestracji);
create index on wykonania(lab_wykonanie_godz_pobrania);
create index on wykonania(lab_wykonanie_godz_dystrybucji);
create index on wykonania(lab_wykonanie_godz_zatw);
create index on wykonania(lab_wykonanie_data_rozliczenia);
create index on wykonania(lab_badanie);
create index on wykonania(lab_oddzial);
create index on wykonania(lab_zlecenie_platnik);
create index on wykonania(lab_wykonanie_platnik);

-- indeksy

create table cennik_wzorcowy (
    id serial primary key,
    badanie varchar(16),
    cena decimal(12, 2)
);

create index on cennik_wzorcowy(badanie);

create table log_synchronizacje (
    id serial primary key,
    system varchar(32),
    start_at timestamp,
    end_at timestamp,
    sync_date date,
    success boolean,
    log text
);

create index on log_synchronizacje(system, sync_date);

"""


class NockaDatasource(PostgresDatasource):
    def __init__(self, read_write=False):
        dsn = self._set_dsn(read_write)
        PostgresDatasource.__init__(self, dsn=dsn, read_write=read_write)

    @staticmethod
    def _set_dsn(read_write):
        dsn = get_local_open_vpn_address()
        if not dsn:
            if read_write:
                return Config.DATABASE_NOCKA_ADM
            return Config.DATABASE_NOCKA_RO
        return Config.DATABASE_NOCKA_OPENVPN

    def get_slownik_last_dc(self, lab, slownik):
        for row in self.dict_select("select max(dc) as dc from slowniki where slownik=%s and lab=%s", [slownik, lab]):
            return row['dc']
        return None

    def load_lab_slownik(self, lab, slownik, rows):
        existing_ids = set([row['lab_id'] for row in
                            self.dict_select("select lab_id from slowniki where slownik=%s and lab=%s",
                                             [slownik, lab])])
        insert_rows = []
        update_rows = []
        for row in rows:
            if row['id'] in existing_ids:
                warunek = {'slownik': slownik, 'lab': lab, 'lab_id': row['id']}
                del row['id']
                update_rows.append((warunek, row))
            else:
                row['lab_id'] = row['id']
                del row['id']
                row['slownik'] = slownik
                row['lab'] = lab
                insert_rows.append(row)
        self.multi_insert('slowniki', insert_rows)
        self.multi_update('slowniki', update_rows)

    def get_lab_existing_idents(self, lab, idents):
        sql_idents = ','.join(str(int(id)) for id in idents)
        sql = "select lab_id from wykonania where lab=%s and lab_id in (" + sql_idents + ")"
        return [row['lab_id'] for row in self.dict_select(sql, [lab])]

    def _process_lab_row(self, row):
        for fld in 'lab_jest_pakietem lab_platne lab_znacznik_dystrybucja lab_techniczne_lub_kontrola lab_pracownia_alab'.split(
                ' '):
            row[fld] = row[fld] == 1
        for fld in 'lab_system lab_zlecenie_system'.split(' '):
            if row[fld] is not None:
                row[fld] = row[fld].strip()
        row['lab_updated_at'] = 'NOW'
        return row

    def load_lab_new(self, lab, rows):
        insert_rows = []
        for row in rows:
            row['lab'] = lab
            insert_rows.append(self._process_lab_row(row))
        self.multi_insert('wykonania', insert_rows)

    def load_lab_existing(self, lab, rows):
        update_rows = []
        for row in rows:
            cond = {'lab': lab, 'lab_id': row['lab_id']}
            del row['lab_id']
            update_rows.append((cond, self._process_lab_row(row)))
        self.multi_update('wykonania', update_rows)

    def load_patients(self, lab, pacjenci):
        zlecenia = pacjenci.keys()
        sql = "select lab_zlecenie from pacjenci where lab=%s and lab_zlecenie in (" \
              + ','.join([str(id) for id in zlecenia]) + ")"
        istniejace = [row['lab_zlecenie'] for row in self.dict_select(sql, [lab])]
        insert_rows = []
        update_rows = []
        for id, pacjent in pacjenci.items():
            if id in istniejace:
                update_rows.append(({'lab': lab, 'lab_zlecenie': id}, {'pacjent': pacjent, 'sprawdzony': True}))
            else:
                insert_rows.append({'lab': lab, 'lab_zlecenie': id, 'pacjent': pacjent, 'sprawdzony': True})
        self.multi_insert('pacjenci', insert_rows)
        self.multi_update('pacjenci', update_rows)

    def get_snr_braki(self):
        return self.dict_select("""select id, lab, lab_sysid, lab_system, lab_wykonanie_data_rozliczenia, snr_id
            from wykonania 
            where (snr_updated_at is null or snr_updated_at < lab_updated_at) and lab_wykonanie_data_rozliczenia is not null
            order by lab, lab_wykonanie_data_rozliczenia""")

    def load_snr(self, rows):
        pass


def nocka_sprawdz_kompletnosc(task_params):
    ds = NockaDatasource()
    kal = Kalendarz()
    params = task_params['params']
    braki = []
    zebrane = {}
    for row in ds.dict_select("""select system, sync_date 
        from log_synchronizacje 
        where sync_date between %s and %s and success""", [params['dataod'], params['datado']]):
        data = kal.data(row['sync_date'])
        if data not in zebrane:
            zebrane[data] = []
        zebrane[data].append(row['system'])
    for data in kal.zakres_dat(params['dataod'], params['datado']):
        if data not in zebrane:
            braki.append(data)
        else:
            braki_lab = []
            for lab in params['laboratoria']:
                if lab not in zebrane[data]:
                    braki_lab.append(lab)
            if len(braki_lab) > 0:
                braki.append('%s (%s)' % (data, ', '.join(braki_lab)))
    if len(braki) > 0:
        return {'type': 'warning',
                'text': 'Dla podanych dat i baz nie ma ściągniętego kompletu danych: %s' % ', '.join(braki)}
