import datetime

import sentry_sdk
import sys

import jwt
import hashlib
from passlib.hash import pbkdf2_sha256, bcrypt
from decorator import decorator
from flask import request
import click
from flask.cli import AppGroup
from api.restplus import api
from api.common import get_db
from datasources.bic import BiCDatasource
from datasources.efaktura import EFakturaDatasource
from datasources.snrkonf import SNRKonf
from datasources.wyniki_stats import WynikiStats
from helpers.strings import parse_hstore
import string
import random
import inspect
from config import Config
import sqlite3

from helpers import copy_from_remote


def encrypt_password(passwd):
    return pbkdf2_sha256.hash(passwd)


def check_password(passwd, encrypted):
    try:
        if encrypted.startswith('$pbkdf2-sha256$'):
            return pbkdf2_sha256.verify(passwd, encrypted)
        elif encrypted.startswith('$2a$'):
            return bcrypt.verify(passwd, encrypted)
    except:
        return False


def get_jwt(encoded_token=None):
    if encoded_token is None:
        try:
            auth_header = request.headers.get('Authorization')
            if auth_header:
                try:
                    encoded_token = auth_header.split(' ')[1]
                except:
                    pass
        except RuntimeError:
            if 'cron' in sys.modules.keys():
                return {'user': -1, 'sub': 'CRON', 'rights': 'C-ALL:*'}
            elif 'sync_api_server' in sys.modules.keys():
                # TODO zmienić to na uprawnienia z właściwego tokena (nie wiem czy będzie prosto)
                return {'user': -1, 'sub': 'SYNC_API', 'rights': 'C-ALL:*'}
            else:
                raise
    if encoded_token is not None:
        try:
            token = jwt.decode(encoded_token, Config.SECRET_KEY, algorithms=['HS512'])
            return token
        except jwt.ExpiredSignatureError as e:
            # przeterminowany podpis
            return None
        except (jwt.DecodeError, jwt.InvalidTokenError) as e:
            # błąd dekodowania JWT
            return None
        except:
            # nieprawidłowy token
            return None
    # Brak tokena
    return None


def login_required(method):
    def wrapper(*args, **kwargs):
        token = get_jwt()
        if token is None:
            api.abort(403, 'Token required')
        if 'user_token' in inspect.getargs(method.__code__).args:
            kwargs['user_token'] = token
        if 'user_id' in inspect.getargs(method.__code__).args:
            kwargs['user_id'] = token['user']
        if 'user_lab' in inspect.getargs(method.__code__).args:
            kwargs['user_lab'] = token['lab']
        if 'user_login' in inspect.getargs(method.__code__).args:
            kwargs['user_login'] = token['sub']
        if 'user_permissions' in inspect.getargs(method.__code__).args:
            res = []
            for right in token['rights'].split(';'):
                if ':' in right:
                    res.append(right.split(':'))
                else:
                    res.append([right, None])
            kwargs['user_permissions'] = res
        if 'user_labs_available' in inspect.getargs(method.__code__).args:
            labs_available = []
            for right in token['rights'].split(';'):
                if ':' in right:
                    right = right.split(':')
                    for lab in right[1].split(' '):
                        if lab not in labs_available:
                            labs_available.append(lab)
            kwargs['user_labs_available'] = labs_available
        return method(*args, **kwargs)

    wrapper.__doc__ = method.__doc__
    wrapper.__name__ = method.__name__
    wrapper.__wrapped__ = method
    return wrapper


@decorator
class permission_required:
    def __init__(self, permission):
        self.permission = permission

    def __call__(self, method):
        def wrapper(*args, **kwargs):
            current_user = None
            return method(args, kwargs, current_user=current_user)

        wrapper.__doc__ = method.__doc__
        wrapper.__name__ = method.__name__
        wrapper.__wrapped__ = method
        return wrapper


user_cli = AppGroup('user', help='Zarządzanie użytkownikami')


@user_cli.command('create')
@click.argument('nazwisko')
@click.argument('login')
@click.argument('haslo', default='^__^__^')
def create_user(nazwisko, login, haslo):
    with get_db() as db:
        login = login.strip().lower()
        if len(login) < 3:
            print('Login powinien mieć co najmniej 3 litery')
            return 1
        # TODO: co robić ze skasowanymi? Może wrzucać cały rekord w log_zmiany i kasować?
        user_rows = db.select("select * from osoby where login=%s", [login])
        if len(user_rows) > 0:
            print('Użytkownik o podanym loginie już istnieje')
            return 1
        if haslo == '^__^__^':
            haslo = ''.join(random.choice(string.ascii_letters) for i in range(12))
            print('Wygenerowano losowe hasło:', haslo)
            print(' - przekaż je użytkownikowi')
        haslo = encrypt_password(haslo)
        db.execute("insert into osoby(zrodlo, nazwisko, login, passwd) values(%s, %s, %s, %s)", [
            'CLI', nazwisko, login, haslo
        ])
        db.commit()
        # TODO: powiadomienia na maila? / link aktywacyjny
        print('Dodano użytkownika.')


@user_cli.command('reset')
@click.argument('login')
@click.argument('haslo', default='RANDOM')
def reset_password(login, haslo):
    with get_db() as db:
        user_rows = db.select("select * from osoby where login=%s", [login])
        if len(user_rows) == 0:
            print('Nie znaleziono użytkownika')
            return 1
        if haslo == 'RANDOM':
            haslo = ''.join(random.choice(string.ascii_letters) for i in range(12))
        print('Zmiana hasła na:', haslo)
        print(' - przekaż je użytkownikowi')
        haslo = encrypt_password(haslo)
        db.execute("update osoby set passwd=%s where id=%s", [haslo, user_rows[0]['id']])
        db.commit()


@user_cli.command('mrcopy')
@click.argument('login')
def copy_user_from_mr(login):
    with get_db() as db:
        user_rows = db.select("select * from osoby where login=%s", [login])
        if len(user_rows) > 0:
            print('Użytkownik o podanym loginie już istnieje w reporterze')
            return 1
        copy_from_remote('2.0.0.1', '/var/www/raporty_db/uzytkownicy.db', '/tmp/uzytkownicy.db')
        mr_db = sqlite3.connect('/tmp/uzytkownicy.db')
        cur = mr_db.cursor()
        cur.execute("select haslo, nazwisko from uzytkownicy where login=?", [login])
        (haslo, nazwisko) = cur.fetchone()
        db.execute("insert into osoby(zrodlo, nazwisko, login, passwd) values(%s, %s, %s, %s)", [
            'MR', nazwisko, login, haslo
        ])
        print("Użytkownik %s (%s) przeniesiony. Nie zapomnij nadać uprawnień!" % (login, nazwisko))
        db.commit()


@user_cli.command('show')
@click.argument('login')
def show_user(login):
    with get_db() as db:
        user_rows = db.select("select id, nazwisko from osoby where login=%s", [login])
        if len(user_rows) == 0:
            print('Nie znaleziono użytkownika')
            return 1
        user_data = user_rows[0]
        print("%s - %s" % (login, user_data['nazwisko']))
        for row in db.select("select * from uprawnienia where osoba=%s", [user_data['id']]):
            print("  %s ( %s )" % (row['uprawnienia'], row['laboratoria']))


@user_cli.command('search')
@click.argument('search_string')
def search_user(search_string):
    with get_db() as db:
        search_string = '%' + search_string + '%'
        user_rows = db.select("select id, login, nazwisko from osoby where login ilike %s or nazwisko ilike %s",
                              [search_string, search_string])
        if len(user_rows) == 0:
            print('Nie znaleziono użytkownika')
            return 1
        for user_data in user_rows:
            print("%s - %s" % (user_data['login'], user_data['nazwisko']))
            for row in db.select("select * from uprawnienia where osoba=%s", [user_data['id']]):
                print("  %s ( %s )" % (row['uprawnienia'], row['laboratoria']))


@user_cli.command('add_rights')
@click.argument('login')
@click.argument('rights')
@click.argument('labs')
def show_user(login, rights, labs):
    with get_db() as db:
        user_rows = db.select("select id, nazwisko from osoby where login=%s", [login])
        if len(user_rows) == 0:
            print('Nie znaleziono użytkownika')
            return 1
        user_data = user_rows[0]
        db.execute("insert into uprawnienia(osoba, uprawnienia, laboratoria) values(%s, %s, %s)", [
            user_data['id'], rights, labs
        ])
        db.commit()


@user_cli.command('create_external_token')
@click.argument('login')
@click.argument('valid_to')
def create_external_token(login, valid_to):
    valid_to = datetime.datetime.strptime(valid_to, '%Y-%m-%d')
    with get_db() as db:
        user_rows = db.select("""select o.id, o.nazwisko, o.login, o.passwd
            from osoby o 
            where o.login=%s and aktywny""", [login])
        if len(user_rows) == 0:
            raise ValueError("Nie znaleziono użytkownika")
        user = user_rows[0]
        rights = []
        for row in db.select(
                """select uprawnienia, laboratoria from uprawnienia where osoba=%s and not del""",
                [user['id']]):
            rights.append('%s:%s' % (row['uprawnienia'], row['laboratoria']))
        token = jwt.encode({
            'iss': 'reporter', 'sub': login, 'user': user['id'],
            'rights': ';'.join(rights),
            'exp': valid_to
        }, Config.SECRET_KEY, algorithm='HS512')
        if isinstance(token, bytes):
            token = token.decode('ascii')
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        db.insert('external_tokens', {
            'osoba_id': user['id'], 'valid_to': valid_to, 'token_hash': token_hash
        })
        db.commit()
        print(token)


cfg_cli = AppGroup('cfg', help='Zarządzanie konfiguracją')


@cfg_cli.command('refresh_labs')
def refresh_labs():
    """Aktualizuj listę labów wg SNR"""
    bazy_do_gellerta = {}
    with get_db() as db:
        snr = SNRKonf()
        efak = EFakturaDatasource()
        existing_labs = db.select("select * from laboratoria")
        aktywne = {}
        existing_symbols = []
        postgresy = []
        for lab in existing_labs:
            symbol = lab['symbol_snr']
            existing_symbols.append(symbol)
            aktywne[symbol] = lab['aktywne']
            if lab['baza_pg']:
                postgresy.append(symbol)
        to_add = []
        for row in snr.dict_select(
                """select *, hs->'centrumrozliczeniowe' as centrumrozliczeniowe, hs->'bazazdalna' as bazazdalna,
                    hs->'mpk' as mpk 
                    from laboratoria where not del and coalesce(vpn, '') != ''"""):
            hs = parse_hstore(row['hs']) or {}
            if row['aktywne'] and row['symbol'] not in existing_symbols:
                to_add.append({
                    'symbol': row['symbol'],
                    'symbol_snr': row['symbol'],
                    'adres': row['vpn'],
                    'baza': row['bazazdalna'],
                    'adres_fresh': row['vpn'],
                    'baza_fresh': row['bazazdalna'],
                    'baza_pg': hs.get('bazapg') == 'True',
                    'marcel': True,
                    'centrum_kosztow': row['centrumrozliczeniowe'],
                    'replikacja': True,
                    'aktywne': True,
                    'laboratorium': True,
                    'wewnetrzne': True,
                    'zewnetrzne': False,
                    'zewnetrzne_got': False,
                    'pracownia_domyslna': True,
                    'nazwa': row['nazwa']
                })
            if not row['aktywne'] and row['symbol'] in existing_symbols and aktywne[row['symbol']]:
                print('do dezaktywacji', row['symbol'])
                db.execute("update laboratoria set aktywne=false where symbol_snr=%s", [row['symbol']])
            if hs.get('bazapg') == 'True' and row['symbol'] in existing_symbols and row['symbol'] not in postgresy:
                print('zmigrowany do postgresa', row['symbol'])
                db.execute("update laboratoria set baza=%s, baza_fresh=%s, baza_pg=true where symbol_snr=%s", [
                    row['bazazdalna'], row['bazazdalna'], row['symbol']
                ])
                try:
                    bic = BiCDatasource(read_write=True)
                    bic.mark_migration_to_postgres(row['symbol'], row['bazazdalna'])
                except:
                    sentry_sdk.capture_exception()
            if row['aktywne'] and row['mpk'] is not None and len(row['mpk']) == 3:
                if row['symbol'] not in ('KOPERNI', 'KOPERNIKA', 'CPLEK'):
                    if efak.lab_not_in_db(row['symbol']):
                        print('Dodaję lab', row['symbol'], 'do efucktury z mpk', row['mpk'])
                        efak.add_lab_to_db(row['symbol'], row['nazwa'], row['mpk'])
            if row['aktywne'] and row['bazazdalna'] not in (None, '') and row['vpn'] not in (None, ''):
                bazy_do_gellerta[row['symbol'][:7]] = {
                    'symbol': row['symbol'][:7],
                    'adres': row['vpn'],
                    'alias': row['bazazdalna'],
                    'pg': hs.get('bazapg') == 'True',
                    'internal_symbol': row['symbol'][:7],
                }
        if len(to_add):
            for row in to_add:
                for krow in db.select(
                        "select max(kolejnosc)+1 as kolejnosc, max(kolejnosc_marcel)+1 as kolejnosc_marcel from laboratoria"):
                    row['kolejnosc'] = krow['kolejnosc']
                    row['kolejnosc_marcel'] = krow['kolejnosc_marcel']
                print('Dodaję', row['symbol'], row['nazwa'])
                db.insert('laboratoria', row)
        db.commit()
        ws = WynikiStats(read_write=True)
        gellert_istniejace = {}
        for row in ws.dict_select("select * from bazy where orders_to  is null order by symbol"):
            gellert_istniejace[row['symbol']] = row
        for symbol in bazy_do_gellerta:
            if symbol not in gellert_istniejace:
                print(symbol, "do dodania do św Gellerta")
                to_add = bazy_do_gellerta[symbol]
                to_add['orders_from'] = (datetime.date.today() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
                to_add['old_schema'] = False
                ws.insert('bazy', to_add)
        for symbol in gellert_istniejace:
            if symbol not in bazy_do_gellerta:
                print(symbol, "do dezaktywowania w św Gellercie")
                ws.update('bazy', {'id': gellert_istniejace[symbol]['id']}, {
                    'orders_to': datetime.date.today().strftime('%Y-%m-%d')
                })
            else:
                if gellert_istniejace[symbol]['pg'] != bazy_do_gellerta[symbol]['pg']:
                    print(symbol, "zmiana typu bazy")
                    ws.update('bazy', {'id': gellert_istniejace[symbol]['id']}, {
                        'pg': bazy_do_gellerta[symbol]['pg'],
                        'alias': bazy_do_gellerta[symbol]['alias']
                    })
        ws.commit()
