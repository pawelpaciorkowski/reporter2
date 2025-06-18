from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json, divide_chunks, Kalendarz
from helpers.validators import validate_date_range
from datasources.snrkonf import SNRKonf
from datasources.helper import HelperDb
from tasks import TaskGroup, Task
import datetime
from helpers.connections import get_centra, get_db_engine

MENU_ENTRY = 'Badania przeterminowane'

ADD_TO_ROLE = ['L-PRAC']

SQL_COMMON = """
    SELECT
        W.ID AS WYKONANIE,
		Z.Numer AS NUMERZL,
		coalesce(z.Kodkreskowy, '') || '|' || coalesce(w.kodkreskowy, '') as KODY,
		TZ.Symbol AS TYPZLECENIA,
		W.DataRejestracji AS REJESTRACJA,
		W.Dystrybucja AS DYSTRYBUCJA,
		P.Symbol AS PRACOWNIA,
		B.Symbol AS SYMBOLB,
		B.Nazwa AS NAZWAB,
        Z.ZewnetrznyIdentyfikator AS NUMERZEW,
		Z.Komentarz AS KOMENTARZ,
		Z.Opis AS OPIS,
		A.Symbol AS APARAT,
		(PA.Nazwisko || ' ' || PA.Imiona || ' ' || coalesce(cast(PA.PESEL as varchar(20)),'')) as PACJENT,
		O.Symbol as PP,
		o.Nazwa as PPN,
		PL.Symbol as PL,
		PL.Nazwa as PLN,
		(cast(b.czasmaksymalny as decimal(18,0))/cast(24 as decimal(18,0))*1) as MAXCZAS,
		W.DataRejestracji + (cast((b.czasmaksymalny - 48) as decimal(18,6))/cast(24 as decimal(18,6))) as TERMINOSTRZEGAWCZY,
		W.DataRejestracji + (cast(b.czasmaksymalny as decimal(18,6))/cast(24 as decimal(18,6))) as BADANIEPRZETERMINOWANE
	FROM Wykonania W
		LEFT JOIN Zlecenia Z ON Z.ID = W.Zlecenie
		LEFT JOIN Pacjenci PA on Z.Pacjent = PA.Id and PA.Del = 0
		LEFT JOIN Badania B ON B.ID = W.Badanie
		LEFT JOIN GrupyBadan GB ON GB.ID = B.Grupa
		LEFT JOIN Pracownie P on P.ID = W.Pracownia
		LEFT JOIN Oddzialy O on O.id=Z.Oddzial
		LEFT JOIN PLATNICY PL on PL.id=Z.platnik
		LEFT JOIN APARATY A ON A.ID=W.APARAT
		LEFT JOIN TYPYZLECEN TZ ON TZ.ID=Z.TypZlecenia
	WHERE
		W.pozamknieciu = 0 and W.Zatwierdzone IS Null and B.Czasmaksymalny is not null and
		W.anulowane is null and W.BladWykonania is null and 
"""

SQL_COMMON_PQSL = """
    SELECT
        W.ID AS WYKONANIE,
		Z.Numer AS NUMERZL,
		coalesce(z.Kodkreskowy, '') || '|' || coalesce(w.kodkreskowy, '') as KODY,
		TZ.Symbol AS TYPZLECENIA,
		W.DataRejestracji AS REJESTRACJA,
		W.Dystrybucja AS DYSTRYBUCJA,
		P.Symbol AS PRACOWNIA,
		B.Symbol AS SYMBOLB,
		B.Nazwa AS NAZWAB,
        Z.ZewnetrznyIdentyfikator AS NUMERZEW,
		Z.Komentarz AS KOMENTARZ,
		Z.Opis AS OPIS,
		A.Symbol AS APARAT,
		(PA.Nazwisko || ' ' || PA.Imiona || ' ' || coalesce(cast(PA.PESEL as varchar(20)),'')) as PACJENT,
		O.Symbol as PP,
		o.Nazwa as PPN,
		PL.Symbol as PL,
		PL.Nazwa as PLN,
			(cast(b.czasmaksymalny as decimal(18,0))/cast(24 as decimal(18,0))*1) as MAXCZAS,
		W.DataRejestracji + cast((cast((b.czasmaksymalny - 48) as decimal(18,6))/cast(24 as decimal(18,6))) as integer) as TERMINOSTRZEGAWCZY,
		W.DataRejestracji + cast((cast(b.czasmaksymalny as decimal(18,6))/cast(24 as decimal(18,6))) as integer) as BADANIEPRZETERMINOWANE
		
	FROM Wykonania W
		LEFT JOIN Zlecenia Z ON Z.ID = W.Zlecenie
		LEFT JOIN Pacjenci PA on Z.Pacjent = PA.Id and PA.Del = 0
		LEFT JOIN Badania B ON B.ID = W.Badanie
		LEFT JOIN GrupyBadan GB ON GB.ID = B.Grupa
		LEFT JOIN Pracownie P on P.ID = W.Pracownia
		LEFT JOIN Oddzialy O on O.id=Z.Oddzial
		LEFT JOIN PLATNICY PL on PL.id=Z.platnik
		LEFT JOIN APARATY A ON A.ID=W.APARAT
		LEFT JOIN TYPYZLECEN TZ ON TZ.ID=Z.TypZlecenia
	WHERE
		W.pozamknieciu = 0 and W.Zatwierdzone IS Null and B.Czasmaksymalny is not null and
		W.anulowane is null and W.BladWykonania is null and 
"""
LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="Raport z badań przeterminowanych i tych, którym data przeterminowania się zbliża"),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', pokaz_nieaktywne=True),
    HBox(
        VBox(
            Switch(field="tylkodystr", title="Tylko po dystrybucji"),
            Switch(field="histopa", title="Bez Histopatologii"),
            Switch(field="tylkohist", title="Tylko Histopatologia"),
        ),
        VBox(
            Switch(field="tylkoprzet", title="Tylko przetermionowane"),
            Switch(field="bakter", title="Bez Bakteriologii"),
            Switch(field="tylkobakter", title="Tylko Bakteriologia"),
        )
    ),
    TextInput(field='pracownia', title='Pojedyncza pracownia (symbol)'),
    Switch(field="oddystrybucji", title="Termin od dystrybucji a nie od rejestracji (tylko przyjęte)")
    # Switch(field="zmianaaparatu", title="Pokaż ostatnią zmianę aparatu (tylko Histopatologia Warszawa)"),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
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


def get_db(lab):

    centra = get_centra(lab)
    return get_db_engine(centra)


def get_sql(db_engine):
    if db_engine == 'postgres':
        return SQL_COMMON_PQSL
    if db_engine == 'firebird':
        return SQL_COMMON


def raport_pojedynczy(task_params):
    params = task_params['params']
    db_engine = get_db(task_params['target'])
    sql = get_sql(db_engine)
    kal = Kalendarz()
    sql_params = []
    if params['oddystrybucji']:
        sql = sql.replace('W.DataRejestracji +', 'cast(w.dystrybucja as date) +')
    if params['tylkohist']:
        sql += "GB.symbol in ('HISTOPA', 'HIS-ALA') and "
    elif params['tylkobakter']:
        sql += "GB.Symbol in ('BAKTER') and "
    else:
        if params['histopa']:
            sql += "(GB.symbol is null or (GB.symbol != 'HISTOPA' and GB.symbol != 'HIS-ALA')) and "
        if params['bakter']:
            sql += "(GB.symbol is null or GB.symbol != 'BAKTER') and "
    if params['tylkoprzet']:
        if db_engine == 'firebird':
            sql += """(
                    (W.Dystrybucja + (cast((b.czasmaksymalny) as decimal(18,6))/cast(24 as decimal(18,6))) < current_timestamp and w.dystrybucja is not null) or
                    (W.DataRejestracji + (cast((b.czasmaksymalny) as decimal(18,6))/cast(24 as decimal(18,6))) < current_timestamp and w.dystrybucja is null)
                )"""
        if db_engine == 'postgres':
            sql += """(
                    (extract(epoch from W.Dystrybucja) + (cast((b.czasmaksymalny) as decimal(18,6))*cast(3600 as decimal(18,6))) < extract(epoch from current_timestamp) and w.dystrybucja is not null) or
                    (extract(epoch from W.DataRejestracji) + cast((cast((b.czasmaksymalny) as decimal(18,6))*cast(3600 as decimal(18,6))) as integer) < extract(epoch from current_timestamp) and w.dystrybucja is null)
                )"""
    else:
        if db_engine == 'firebird':
            sql += """(
                (W.Dystrybucja + (cast((b.czasmaksymalny - 48) as decimal(18,6))/cast(24 as decimal(18,6))) < current_timestamp and b.czasmaksymalny > '48' and w.dystrybucja is not null) or
                (W.Dystrybucja + (cast((b.czasmaksymalny) as decimal(18,6))/cast(24 as decimal(18,6))) < current_timestamp and b.czasmaksymalny < '48' and w.dystrybucja is not null) or
                (W.DataRejestracji + (cast((b.czasmaksymalny - 48) as decimal(18,6))/cast(24 as decimal(18,6))) < current_timestamp and b.czasmaksymalny > '48' and w.dystrybucja is null) or
                (W.DataRejestracji + (cast((b.czasmaksymalny) as decimal(18,6))/cast(24 as decimal(18,6))) < current_timestamp and b.czasmaksymalny < '48' and w.dystrybucja is null)
            )"""

        if db_engine == 'postgres':
            sql += """(
                    (extract(epoch from W.Dystrybucja) + (cast((b.czasmaksymalny - 48) as decimal(18,6))*cast(3600 as decimal(18,6))) < extract(epoch from current_timestamp) and b.czasmaksymalny > '48' and w.dystrybucja is not null) or
                    (extract(epoch from W.Dystrybucja) + (cast((b.czasmaksymalny) as decimal(18,6))*cast(3600 as decimal(18,6))) < extract(epoch from current_timestamp) and b.czasmaksymalny < '48' and w.dystrybucja is not null) or
                    (extract(epoch from W.DataRejestracji) + (cast((b.czasmaksymalny - 48) as decimal(18,6))*cast(3600 as decimal(18,6))) < extract(epoch from current_timestamp) and b.czasmaksymalny > '48' and w.dystrybucja is null) or
                    (extract(epoch from W.DataRejestracji) + (cast((b.czasmaksymalny) as decimal(18,6))*cast(3600 as decimal(18,6))) < extract(epoch from current_timestamp) and b.czasmaksymalny < '48' and w.dystrybucja is null)
                )"""
    if params['oddystrybucji'] or params['tylkodystr']:
        sql += ' and w.dystrybucja is not null '
    if params['pracownia'] is not None and params['pracownia'].strip() != '':
        sql += " and p.symbol=? "
        sql_params.append(params['pracownia'].strip().upper())
    sql += " ORDER BY W.DataRejestracji, Z.Numer, B.Symbol"
    wiersze = []
    zleceniodawcy = []
    wykonania = []
    zmiany_aparatu = {}
    przeterminowane = 0
    wszystkie = 0
    teraz = datetime.date.today()
    with get_centrum_connection(task_params['target']) as conn:
        print(sql)
        for row in conn.raport_slownikowy(sql, sql_params):
            wszystkie += 1
            if row['badanieprzeterminowane'] <= teraz:
                przeterminowane += 1
                kolor = '#ff0000'
            else:
                kolor = '#ffff00'
            if params['oddystrybucji']:
                kal.ustaw_teraz(row['dystrybucja'].strftime('%Y-%m-%d'))
            else:
                kal.ustaw_teraz(row['rejestracja'].strftime('%Y-%m-%d'))
            termin_dr = kal.data(f"+{int(row['maxczas'])}DR")
            if termin_dr < teraz.strftime('%Y-%m-%d'):
                kolor2 = '#ff0000'
            elif termin_dr == teraz.strftime('%Y-%m-%d'):
                kolor2 = '#ffff00'
            else:
                kolor2 = '#ffffff'
            row['pp'] = (row['pp'] or '').strip()
            if row['pp'] not in zleceniodawcy:
                zleceniodawcy.append(row['pp'])
            row['wykonanie'] = '%s:%d' % (task_params['target'], row['wykonanie'])
            wykonania.append(row['wykonanie'])
            notatka = ''
            if row['opis'] is not None and '$&' in row['opis']:
                opis_tab = row['opis'].split('$&')
                notatka = opis_tab[1]
            wiersz = [
                row['wykonanie'],
                row['rejestracja'], row['numerzl'], row['kody'], row['typzlecenia'], row['dystrybucja'], row['pracownia'],
                row['pacjent'], row['pp'], row['ppn'], row['pl'], row['pln'], '',
                row['symbolb'], row['nazwab'], row['numerzew'], row['komentarz'], notatka, row['aparat'], row['maxczas'],
                {'value': row['terminostrzegawczy'], 'background': kolor},
                {'value': row['badanieprzeterminowane'], 'background': kolor},
                {'value': termin_dr, 'background': kolor2},
            ]
            wiersze.append(wiersz)
    platnicy_pierwotni = {}
    snr = SNRKonf()
    if len(zleceniodawcy) > 0:
        for row in snr.dict_select("""
            select zwl.symbol, pl.nazwa
            from zleceniodawcywlaboratoriach zwl 
            left join zleceniodawcy zl on zl.id=zwl.zleceniodawca
            left join platnicy pl on pl.id=zl.platnik
            where zwl.symbol in %s and not zwl.del and not zl.del and not pl.del
        """, [tuple(zleceniodawcy)]):
            platnicy_pierwotni[row['symbol']] = row['nazwa']
    result = []
    # if params['zmianaaparatu']:
    #     hdb = HelperDb('hist_czasy.db')
    #     sql = """select wykonanie, max(czas) from zdarzenia where wykonanie in ($IDENTS$) and zdarzenie='APARAT' group by wykonanie"""
    #     for chunk in divide_chunks(wykonania, 1000):
    #         local_sql = sql.replace('$IDENTS$', ','.join('?'*len(chunk)))
    #         _, rows = hdb.select(local_sql, chunk)
    #         print(chunk)
    #         for row in rows:
    #             print(row)
    #             zmiany_aparatu[row[0]] = row[1]
    for wiersz in wiersze:
        wykonanie = wiersz.pop(0)
        wiersz[10] = platnicy_pierwotni.get(wiersz[10], '')
        kody = (wiersz[2] or '|').replace('=', '').split('|')
        if len(kody[0]) > 9 and len(kody[1]) > 9:
            if kody[0][:9] == kody[1][:9]:
                wiersz[2] = kody[1]
            else:
                wiersz[2] = 'Zl: %s, Wyk: %s' % tuple(kody)
        else:
            for kod in kody:
                if len(kod) > 5:
                    wiersz[2] = kod
        # if params['zmianaaparatu']:
        #     wiersz.insert(15, zmiany_aparatu.get(wykonanie, ''))
        result.append(prepare_for_json(wiersz))
    header = 'Data Rejestracji,Numer,Kody kreskowe,Typ zl.,Dystrybucja,Pracownia,Pacjent,Zleceniodawca,Zleceniodawca Nazwa,Płatnik,Płatnik Nazwa,Płatnik pierwotny,Symbol,Nazwa Badania,Nr zewnętrzny,Komentarz,Notatka,Aparat,Czas Na Wykonanie,Termin Ostrzegawczy,Badanie Przeterminowane,Przeterminowane (dni robocze)'.split(
        ',')
    # if params['zmianaaparatu']:
    #     header.insert(15, 'Ost. zmiana aparatu')
    return {
        'results': [
            {
                'type': 'info',
                'text': 'W sumie %d badań w tym %d przeterminowanych' % (wszystkie, przeterminowane)
            },
            {
                'type': 'table',
                'header': header,
                'data': result
            }
        ],
        'actions': ['xlsx'],
        'errors': [],
    }
