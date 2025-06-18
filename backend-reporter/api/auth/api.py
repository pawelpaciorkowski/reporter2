import datetime

import jwt
import json
import requests

try:
    from jwt.contrib.algorithms.pycrypto import RSAAlgorithm
except ImportError:
    from jwt.algorithms import RSAAlgorithm

try:
    jwt.register_algorithm('RS256', RSAAlgorithm(RSAAlgorithm.SHA256))
except ValueError:
    pass
from api.restplus import api, pagination_arguments, pagination, status
from flask import request, abort, current_app
from flask_restx import Resource, fields, reqparse, inputs
from .utils import login_required, get_jwt, check_password, encrypt_password
from ..common import get_db

ns = api.namespace('auth', description="Logowanie i autoryzacja")


@ns.route('/')
class AuthEndpoint(Resource):
    @login_required
    def get(self):
        """Sprawdzenie ważności i odświeżenie tokena (przesłanego w nagłówkach)"""
        return {}

    def login_from_external_token(self, db, source, ext_token):
        login = None
        user_id = None
        rights = []
        display_name = None
        email = None
        if source == 'EXT$MOP':
            try:
                decoded = jwt.decode(ext_token, key=current_app.config['MOP_PUBLIC_KEY'])
                if decoded is not None:
                    login = 'MOP$' + decoded['username']
                    display_name = decoded['email']
                    email = decoded['email']
                    #                    for role in decoded['roles']:
                    #                        if role == 'ROLE_SUPER_ADMIN':
                    #                            rights.append('C-ADM:*')
                    #                    if len(rights) == 0:
                    #                        return self.result_error('Brak uprawnień w tym systemie')
                    for row in db.select(
                            """select o.id, o.nazwisko, o.login, o.passwd, o.email from osoby o where o.login=%s""",
                            [login]):
                        user_id = row['id']
                        if row['nazwisko'] != display_name or row['email'] != email:
                            db.execute("""update osoby set nazwisko=%s, email=%s where id=%s""",
                                       [display_name, email, user_id])
                    if user_id is None:
                        for row in db.select(
                                """insert into osoby(zrodlo, nazwisko, login, typ) values('MOP', %s, %s, 'USER') returning id as nid""",
                                [display_name, login]):
                            user_id = row['nid']
                    for row in db.select("""select uprawnienia, laboratoria from uprawnienia where osoba=%s""",
                                         [user_id]):
                        rights.append('%s:%s' % (row['uprawnienia'], row['laboratoria']))
                    db.execute("""update osoby set external_token=%s where id=%s""", [json.dumps(decoded), user_id])
                    return self.result_success(user_id, login, rights, display_name)
            except:
                return self.result_error('Błąd tokena')
        elif source == 'EXT$OAUTH':
            # TODO: zrefaktoryzować to do jakiejś oddzielnej metodki, dorobić mapowanie uprawnień
            cfg = current_app.config['KONTO_ALAB']
            base_url = cfg['oauth_base_url']
            client_id = cfg['client_id']
            client_secret = cfg['client_secret']
            [code, redirect_url] = ext_token.split('^')
            payload = {
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
                'redirect_uri': redirect_url,
                'grant_type': 'authorization_code'
            }

            headers = {
                'Cache-Control': 'no-cache',
                'Content-Type': 'application/x-www-form-urlencoded',
            }
            url = base_url + 'o/token/'
            response = requests.request("POST", url, headers=headers, data=payload)
            token_resp = response.json()
            if 'access_token' in token_resp:
                access_token = token_resp['access_token']
                url = base_url + 'app-users/app-users'
                headers = {
                    'Cache-Control': 'no-cache',
                    'Authorization': 'Bearer %s' % access_token
                }
                response = requests.get(url, headers=headers)
                user_resp = response.json()
                if isinstance(user_resp, list):
                    user_resp = user_resp[0]
                # zwrotka zawiera różnież listę global_roles
                if len(user_resp.get('application_roles', [])) > 0:
                    login = 'ALAB$' + user_resp['username']
                    display_name = ('%s %s' % (
                        user_resp.get('employee', {}).get('name') or '',
                        user_resp.get('employee', {}).get('surname') or '',
                    )).strip()
                    email = user_resp.get('employee', {}).get('mail')
                    for row in db.select(
                            """select o.id, o.nazwisko, o.login, o.passwd, o.email from osoby o where o.login=%s""",
                            [login]):
                        user_id = row['id']
                        if row['nazwisko'] != display_name or row['email'] != email:
                            db.execute("""update osoby set nazwisko=%s, email=%s where id=%s""",
                                       [display_name, email, user_id])
                    if user_id is None:
                        for row in db.select(
                                """insert into osoby(zrodlo, nazwisko, login, typ) values('ALAB', %s, %s, 'USER') returning id as nid""",
                                [display_name, login]):
                            user_id = row['nid']
                    for row in db.select("""select uprawnienia, laboratoria from uprawnienia where osoba=%s""",
                                         [user_id]):
                        rights.append('%s:%s' % (row['uprawnienia'], row['laboratoria']))
                    return self.result_success(user_id, login, rights, display_name)
                else:
                    return {'status': 'error', 'error': 'Użytkownik nie posiada żadnej roli w systemie'}
            else:
                return {'status': 'error', 'error': 'Brak dostępu'}
        else:
            return self.result_error('Nieznane źródło tokena')

    def post(self):
        """Logowanie i pobranie tokena / sprawdzenie ważności i odświeżenie tokena (przesłanego w żądaniu)"""
        # print('AUTH POST', request.json)
        data = request.json
        if 'login' in data:
            with get_db() as db:
                if data['login'].startswith('EXT$'):
                    return self.login_from_external_token(db, data['login'], data['passwd'])
                login = data['login'].lower()
                user_rows = db.select("""select o.id, o.nazwisko, o.login, o.passwd
                    from osoby o 
                    where o.login=%s and aktywny""", [login])
                if len(user_rows) == 0:
                    return self.result_error('Nie znaleziono użytkownika')
                user = user_rows[0]
                passwd_ok = check_password(data.get('passwd'), user['passwd'])
                if passwd_ok:
                    rights = []
                    for row in db.select(
                            """select uprawnienia, laboratoria from uprawnienia where osoba=%s and not del""",
                            [user['id']]):
                        rights.append('%s:%s' % (row['uprawnienia'], row['laboratoria']))
                    display_name = user['nazwisko']
                    return self.result_success(user['id'], login, rights, display_name)
                else:
                    return self.result_error('Nieprawidłowe hasło')
        elif 'loginInfo' in data:
            token = get_jwt(data['loginInfo'].get('token'))
            if token is not None:
                # TODO: być może odświeżenie tokena
                return {'status': 'ok', 'loginInfo': data['loginInfo']}
            else:
                return self.result_error('Brak / nieprawidłowy token')
        else:
            return self.result_error('error')

    def result_success(self, user_id, login, rights, display_name):
        if login in ('adamek', 'akac', 'jgiel', 'tstach', 'rszl', 'mskon', 'mseli', 'ALAB$bacies', 'bacies', 'kjak'):
            rights.append('searchbox')
        token = jwt.encode({
                'iss': 'reporter', 'sub': login, 'user': user_id,
                'rights': ';'.join(rights),
                'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=9)
            }, current_app.config['SECRET_KEY'], algorithm='HS512')
        if isinstance(token, bytes):
            token = token.decode('ascii')
        return {'status': 'ok', 'loginInfo': {'displayName': display_name, 'token': token, 'searchBox': ('searchbox' in rights) }}

    def result_error(self, error):
        return {'status': 'error', 'error': error}


@ns.route('/logout')
class AuthLogout(Resource):
    def post(self):
        """Wylogowanie - unieważnienie tokena"""
        # TODO: unieważnienie tokena
        return {'status': 'ok'}


@ns.route('/user')
class AuthUser(Resource):
    @login_required
    def get(self):
        """Pobranie pełnych informacji o bieżącym użytkowniku, uprawnieniach i preferencjach"""
        return {}

    @login_required
    def post(self):
        """Zmiana hasła, aktualizacja preferencji"""
        return {}


@ns.route('/oauth_login')
class OAuthLogin(Resource):
    def get(self):
        redirect_url = request.args.get('redirect')
        print(redirect_url)
        cfg = current_app.config['KONTO_ALAB']
        base_url = cfg['oauth_base_url']
        if '10.1.1.181' in redirect_url or 'reporter.alab.local' in redirect_url:
            base_url = base_url.replace('2.0.214.5', '10.1.254.252')
        client_id = cfg['client_id']
        login_url = f'{base_url}o/authorize/?response_type=code&client_id={client_id}&redirect_uri={redirect_url}'
        return {
            'url': login_url,
        }
    #
    # def post(self):
    #     return {}
