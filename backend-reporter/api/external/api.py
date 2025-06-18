import datetime

from flask import request, Response
from flask_restx import Resource

from api.auth import login_required
from api.restplus import api
from datasources.bic import BiCDatasource
from datasources.reporter import ReporterDatasource
from datasources.snrkonf import SNRKonf
from datasources.mop import MopDatasource
from datasources.alabinfo import AlabInfoDatasource
from helpers import empty
from helpers.crystal_ball.marcel_servers import katalog_wydrukow
from tasks.db import redis_conn

ns = api.namespace('external', description="API dla narzędzi zewnętrznych")


@ns.route('/tasks/new/<string:taskType>')
class UserReports(Resource):
    def get(self, taskType):
        res = []
        rep = ReporterDatasource()
        for row in rep.dict_select("select * from external_tasks where started_at is null and task_type=%s",
                                   [taskType]):
            res_row = dict(row['params'])
            res_row['guid'] = row['guid']
            res.append(res_row)
        return res


@ns.route('/tasks/start/<string:taskType>')
class UserReports(Resource):
    def post(self, taskType):
        params = request.json
        if 'guid' not in params:
            api.abort(400, 'Nie podano guid')
        rep = ReporterDatasource(read_write=True)
        rows = rep.dict_select("select * from external_tasks where task_type=%s and guid=%s and started_at is null",
                               [taskType, params['guid']])
        if len(rows) == 0:
            api.abort(404, 'Nie znaleziono zadania')
        if len(rows) > 1:
            api.abort(500, 'Znaleziono więcej niż jedno zadanie')
        task = rows[0]
        all_logs = []
        if task['log'] is not None:
            log = task['log'].strip()
            if log != '':
                all_logs.append(task['log'])
        if 'log' in params:
            log = params['log'].strip()
            if log != '':
                all_logs.append(params['log'])
        rep.update('external_tasks', {'id': task['id']}, {
            'started_at': datetime.datetime.now(),
            'log': '\n\n'.join(all_logs)
        })
        rep.commit()
        return {'status': 'ok'}


@ns.route('/tasks/finish/<string:taskType>')
class UserReports(Resource):
    def post(self, taskType):
        params = request.json
        if 'guid' not in params:
            api.abort(400, 'Nie podano guid')
        if 'status' not in params:
            api.abort(400, 'Nie podano statusu')
        rep = ReporterDatasource(read_write=True)
        rows = rep.dict_select(
            "select * from external_tasks where task_type=%s and guid=%s and started_at is not null and finished_at is null",
            [taskType, params['guid']])
        if params['status'] == 'ok':
            success = True
        elif params['status'] == 'error':
            success = False
        else:
            api.abort(400, 'Pole status powinno mieć wartość ok/error')
            success = False
        if len(rows) == 0:
            api.abort(404, 'Nie znaleziono zadania')
        if len(rows) > 1:
            api.abort(500, 'Znaleziono więcej niż jedno zadanie')
        task = rows[0]
        all_logs = []
        if task['log'] is not None:
            log = task['log'].strip()
            if log != '':
                all_logs.append(task['log'])
        if 'log' in params:
            log = params['log'].strip()
            if log != '':
                all_logs.append(params['log'])
        rep.update('external_tasks', {'id': task['id']}, {
            'finished_at': datetime.datetime.now(),
            'success': success,
            'log': '\n\n'.join(all_logs)
        })
        rep.commit()
        return {'status': 'ok'}


POLA_SNR = 'host_centrum_2 host_centrum_10 host_icentrum_2 host_lxd_2 host_ekrew prefiks po_prefiksie mpk centrum_rozliczeniowe nowe_sk nowa_synchronizacja cdc nazwa_twojewyniki instancja_ppalab adres_pocztowy wykonuje_badania'.split(
    ' ')


@ns.route('/status')
class StatusStatus(Resource):
    def get(self):
        return {'ok': True}


@ns.route('/labs')
class LabList(Resource):
    def get(self):
        res = []
        rep = ReporterDatasource()
        snr = SNRKonf()
        dane_snr = {}
        for row in snr.dict_select("""
            select symbol, vpn as host_centrum_2,
            hs->'vpnic' as host_icentrum_2,
            hs->'adres10' as host_centrum_10,
            hs->'vpnhost' as host_lxd_2,
            hs->'vpnek' as host_ekrew,
            hs->'twojewyniki' as nazwa_twojewyniki,
            hs->'instancjappalab' as instancja_ppalab,
            case when hs->'nowesk'='True' then true else false end as nowe_sk,
            case when hs->'nowasync'='True' then true else false end as nowa_synchronizacja,
            case when hs->'cdc'='True' then true else false end as cdc,
            hs->'mpk' as mpk,
            hs->'centrumrozliczeniowe' as centrum_rozliczeniowe,
            case when hs->'wykonujebadania'='True' then true else false end as wykonuje_badania,
            hs->'przedrosteksymbolu' as prefiks,
            hs->'symbolplatnika' as po_prefiksie,
            hs->'adres' as adres_pocztowy
            from laboratoria where not del
        """):
            if row['symbol'] is None:
                continue
            symbol = row['symbol'][:7]
            for fld in POLA_SNR:
                if empty(row[fld]):
                    row[fld] = None
            if empty(row['instancja_ppalab']):
                row['instancja_ppalab'] = 'ppalab'
            dane_snr[symbol] = row
        for row in rep.dict_select("""
            select
                symbol, nazwa, symbol_snr, adres, baza, adres_fresh, baza_fresh, baza_pg, 
                centrum_kosztow, replikacja, aktywne, laboratorium, wewnetrzne, zewnetrzne, zewnetrzne_got,
                pracownia_domyslna, adres_bank, baza_bank
            from laboratoria order by kolejnosc
        """):
            lab_snr = dane_snr.get(row['symbol'], {})
            row['katalog_wydrukow'] = katalog_wydrukow(row['symbol'])
            for fld in POLA_SNR:
                row[fld] = lab_snr.get(fld)
            baza_ok = True
            redis_key_ok = 'baza:ok:%s' % row['symbol']
            redis_key_ng = 'baza:ng:%s' % row['symbol']
            b_ok = redis_conn.get(redis_key_ok) or b''
            b_ng = redis_conn.get(redis_key_ng) or b''
            if b_ng != b'' and (b_ok == b'' or b_ok < b_ng):
                baza_ok = False
            row['baza_ok'] = baza_ok
            row['baza_last_ok'] = b_ok.decode()
            row['baza_last_ng'] = b_ng.decode()
            res.append(row)
        return res


@ns.route('/services/all')
class ServicesAll(Resource):
    def get(self):
        bic = BiCDatasource()
        return bic.dict_select("""
            select s.symbol, s.is_bundle, s.is_marketing_bundle, s.is_lab_editable, s.is_visible_ppalab, sn.name
            from services s left join service_names sn on sn.symbol=s.symbol and sn.lang='PL'
            where not s.is_admin_only 
        """)


# TODO wszyscy płatnicy - nip, nr K, nazwa, symbole w laboratoriach

@ns.route('/platnicyBezRejestracji')
class PlatnicyBezRejestracji(Resource):
    def get(self):
        res = []
        snr = SNRKonf()
        for row in snr.dict_select("""
            select distinct symbol from platnicywlaboratoriach z 
            where platnik in (select id from platnicy p where hs->'bezrejestracji'='True' and not del)
        """):
            res.append(row['symbol'])
        return res


@ns.route('/zleceniodawcyBezRejestracji')
class ZleceniodawcyBezRejestracji(Resource):
    def get(self):
        res = []
        snr = SNRKonf()
        for row in snr.dict_select("""
            select distinct symbol from zleceniodawcywlaboratoriach z 
            where zleceniodawca in (select id from zleceniodawcy p where hs->'bezrejestracji'='True' and not del)
        """):
            res.append(row['symbol'])
        return res


@ns.route('/zleceniodawcyWLaboratorium/<string:lab>')
class ZleceniodawcyWLaboratorium(Resource):
    def get(self, lab):
        res = []
        snr = SNRKonf()
        for row in snr.dict_select("""
            select 
            zwl.symbol as zleceniodawca, pwl.symbol as platnik, pl.gotowkowy 
            from zleceniodawcywlaboratoriach zwl
            left join zleceniodawcy zl on zl.id=zwl.zleceniodawca 
            left join platnicy pl on pl.id=zl.platnik 
            left join platnicywlaboratoriach pwl on pwl.platnik=pl.id and pwl.laboratorium=zwl.laboratorium and not pwl.del
            where zwl.laboratorium=%s and not zwl.del and not pl.del and pl.aktywny 
        """, [lab]):
            res.append(row)
        return res


@ns.route('/zleceniodawcyPlatnika/<string:platnik>')
class ZleceniodawcyPlatnika(Resource):
    def get(self, platnik):
        res = []
        snr = SNRKonf()
        for row in snr.dict_select("""
            select zwl.symbol, zl.nazwa
            from platnicywlaboratoriach pwl
            left join platnicy pl on pl.id=pwl.platnik
            left join zleceniodawcy zl on zl.platnik=pl.id and not zl.del
            left join zleceniodawcywlaboratoriach zwl on zwl.zleceniodawca=zl.id and zwl.laboratorium=pwl.laboratorium and not zwl.del
            where pwl.symbol=%s and not pwl.del
        """, [platnik]):
            res.append(row)
        return res


"""
koorydynator - imie nazwisko

tel do koordynatora

telefon do PP

godziny otwarcia

emial do PP

adres icentrum/ppalab
"""


def godziny_otwarcia(periods):
    res = []
    if periods is not None:
        for period in periods:
            pres = []
            for subperiod in period['periods']:
                pres.append(f"{subperiod['dayOfWeek']} {subperiod['period']}")
            res.append(f"{period['name']}: {', '.join(pres)}")
    return '; '.join(res)


@ns.route('/collectionPoints')
class CollectionPointsList(Resource):
    def get(self):
        res = []
        snr = SNRKonf()
        icentra = {}
        for row in snr.dict_select("""
            select symbol,
            hs->'twojewyniki' as nazwa_twojewyniki,
            hs->'instancjappalab' as instancja_ppalab
            from laboratoria where not del
        """):
            if row['symbol'] is None:
                continue
            symbol = row['symbol'][:7]
            nazwa_tw = row['nazwa_twojewyniki']
            inst_ppalab = row['instancja_ppalab']
            if empty(inst_ppalab):
                inst_ppalab = 'ppalab'
            if empty(nazwa_tw):
                continue
            icentra[symbol] = f'https://{nazwa_tw.strip()}.twojewyniki.com.pl/{inst_ppalab.strip()}'
        mop = MopDatasource()
        for pp in mop.get_cached_data('api/v2/collection-point'):
            adres_miasto = adres_ulica = None # Nie ma adresu w danych ze skarbca

            koord = pp.get('user') or {}
            lab_symbol = (pp.get('laboratory') or {}).get('symbol')
            res.append({
                'symbol': pp['marcel'],
                'nazwa': pp['name'],
                'mpk': pp['mpk'],
                'aktywny': pp['isActive'],
                'lab': lab_symbol,
                'labPrefix': (pp.get('laboratory') or {}).get('prefix'),
                'tel': ' '.join([str(p.get('number')) for p in (pp.get('phones') or [])]),
                'email': pp.get('email'),
                'icentrum': icentra.get(lab_symbol[:7]) if lab_symbol is not None else None,
                'koordynator': f"{koord.get('name')} {koord.get('surname')}" if koord else None,
                'koordynatorTel': ' '.join([str(p.get('number')) for p in (koord.get('phones') or [])]),
                'godzinyOtwarcia': godziny_otwarcia(pp.get('periodsSimple')),
                # 'adres_miasto': adres_miasto,
                # 'adres_ulica': adres_ulica
            })
        return res


@ns.route('/labs.csv')
class LabList(Resource):
    def get(self):
        res = []
        rep = ReporterDatasource()
        cols, rows = rep.select("""
            select
                symbol, nazwa, symbol_snr, adres, baza, adres_fresh, baza_fresh, baza_pg, 
                centrum_kosztow, replikacja, aktywne, laboratorium, wewnetrzne, zewnetrzne, zewnetrzne_got,
                pracownia_domyslna, adres_bank, baza_bank
            from laboratoria order by kolejnosc
        """)
        res.append(','.join(cols))
        for row in rows:
            res.append(','.join(
                [str(v) if (type(v) != str or ',' not in v) else ('"%s"' % str(v).replace('"', '\\"')) for v in row]))
        return Response('\n'.join(res), 200, {'Content-type': 'text/csv'})


@ns.route('/snrLabZleceniodawcy/<string:symbol>')
class LabZleceniodawcy(Resource):
    def get(self, symbol):
        snr = SNRKonf()
        res = 'BRAK'
        for row in snr.dict_select("""select zwl.laboratorium 
            from zleceniodawcywlaboratoriach zwl
            left join zleceniodawcy zl on zl.id=zwl.zleceniodawca
            where zwl.symbol=%s and not zwl.del and not zl.del""", [symbol]):
            res = row['laboratorium']
        return Response(res, 200, {'Content-type': 'text/plain'})


@ns.route('/ppalab_instances')
class PpalabInstancesList(Resource):
    def get(self):
        res = []
        snr = SNRKonf()
        for row in snr.dict_select("""
            select symbol, hs->'przedrosteksymbolu' as prefix, vpn, hs->'vpnic' as vpn_ic, hs->'instancjappalab' as ppalab
            from laboratoria 
            where aktywne and symbol not in ('_WZORCOWA') and vpn is not null and vpn != ''
        """):
            row = dict(row)
            if row['vpn_ic'] in (None, ''):
                row['vpn_ic'] = row['vpn']
            if row['ppalab'] in (None, ''):
                row['ppalab'] = 'ppalab'
            res.append(row)
        return res


@ns.route('/telefony')
class IntranetTelefony(Resource):
    @login_required
    def get(self):
        res = []
        alabinfo = AlabInfoDatasource()
        sql = """
            select u.name, u.job_function, u.phone_number, u.phone_landline, d.name as department
        	from users u 
        	left join user_departament ud on ud.user_id=u.id
        	left join department d on d.id=ud.departament_id where
            u.active_on_intranet
        """
        for row in alabinfo.dict_select(sql):
            res.append(row)
        return res
