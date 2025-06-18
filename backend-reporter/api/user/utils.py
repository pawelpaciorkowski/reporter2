import string
import random
from passlib.hash import pbkdf2_sha256
from datasources.reporter import ReporterDatasource
from dialog import ValidationError
from dialog.custom_fields import LabSelector
from helpers.widget_data import WidgetDataProvider, BRAK_ROLI

GET_USERS = '''
select
    o.id,
    o.nazwisko,
    o.email,
    o.login,
    u.id uprawnienia_id,
    u.uprawnienia,
    u.laboratoria,
    o.aktywny
from osoby o
left join (select * from uprawnienia where not del) u on u.osoba = o.id
{{CONDITIONS}}
order by o.login
'''

USER_BY_LOGIN = """
select
    o.id,
    o.nazwisko,
    o.email,
    o.login,
    u.uprawnienia,
    u.laboratoria,
    o.aktywny
from osoby o
left join uprawnienia u on u.osoba = o.id
where o.login = %s
order by o.id
"""

USER_BY_EMAIL = """
select
    o.id,
    o.nazwisko,
    o.email,
    o.login,
    u.uprawnienia,
    u.laboratoria,
    o.aktywny
from osoby o
left join uprawnienia u on u.osoba = o.id
where 
 o.email = %s
order by o.id
"""


def _all_users_from_db():
    db = ReporterDatasource()
    condition = ' '
    sql = GET_USERS.replace('{{CONDITIONS}}', condition)
    return db.dict_select(sql)


def _single_user_from_db(uid):
    db = ReporterDatasource()
    condition = ' where o.id = %s  '
    sql = GET_USERS.replace('{{CONDITIONS}}', condition)
    return db.dict_select(sql, [uid])


def _user_id_from_login(db, login):
    _is_login_exist(db, login)
    return db.dict_select(USER_BY_LOGIN, [login])


def _group_by_login(data):
    response = {}
    for row in data:
        uid = row['id']
        uprawnienia = row['uprawnienia']
        uprawnienia_id = row['uprawnienia_id']
        labs = row['laboratoria']

        if not response.get(uid):
            response[uid] = {
                'id': row['id'],
                'login': row['login'],
                'nazwisko': row['nazwisko'],
                'email': row['email'],
                'aktywny': row['aktywny'],
                'uprawnienia': []
            }
        if not response[uid]['uprawnienia']:
            response[uid]['uprawnienia'] = []
        response[uid]['uprawnienia'].append(
            {'id': uprawnienia_id,
             'role': uprawnienia,
             'labs': labs})
    return [response[r] for r in response]


def _login_length_validation(login):
    if len(login) < 3:
        raise ValidationError('Login powiennien mieć co najmniej 3 znaki')


def _is_login_exist(db, login):
    user_rows = db.dict_select(USER_BY_LOGIN, [login])
    if len(user_rows) > 0:
        return True
    return False


def _is_email_exist(db, email):
    user_rows = db.dict_select(USER_BY_EMAIL, [email])
    if len(user_rows) > 0:
        return True
    return False


def _login_existence_validation(db, login):
    if not _is_login_exist(db, login):
        raise ValidationError('Nie znaleziono użytkownika')


def _login_uniqueness_validation(db, login):
    if _is_login_exist(db, login):
        raise ValidationError('Użytkownik o podanym loginie już istnieje')


def _email_validation(db, email):
    if '@' not in email:
        raise ValidationError('Email jest niepoprawny')
    # if _is_email_exist(db, email):
    #     raise ValidationError('Email już istnieje')


def _password_generator():
    def encrypt_password(passwd):
        return pbkdf2_sha256.hash(passwd)
    plain_password = ''.join(
        random.choice(string.ascii_letters) for i in range(12))
    password = encrypt_password(plain_password)
    return password, plain_password


def _reset_password(uid, user_login):
    db = ReporterDatasource()
    password = _password_generator()
    plain_pass = password[1]
    db.update_with_log(user_login, 'osoby', uid, {'passwd': password[0]})
    return plain_pass


def _get_asterisk_if_all_labs(user_data: str, lab_selector: LabSelector):
    user_labs = set(user_data.split(' '))
    w = WidgetDataProvider(lab_selector)
    labs = [lab['value'] for lab in w.get_data_laboratoria(lab_selector, None)]
    set_all_labs = set(labs)
    diff = set_all_labs - user_labs
    if len(diff) == 0:
        return '*'
    else:
        return user_data


def _get_uid(user_data: dict):
    db = ReporterDatasource()
    checked_uid = None
    login = user_data.get('login')
    uid = user_data.get('id')
    if not uid:
        try:
            user_from_db = _user_id_from_login(db, login)[0]
        except IndexError:
            raise ValidationError(
                'Nie znaleziono użytkownika dla podanego loginu')
        checked_uid = user_from_db['id']

    if uid:
        try:
            user_from_db = _single_user_from_db(uid)[0]
        except IndexError:
            raise ValidationError(
                'Nie znaleziono użytkownika dla podanego uid')
        checked_uid = user_from_db['id']

    if not checked_uid:
        raise ValidationError('Nie znaleziono użytkownika dla podanego loginu')

    return checked_uid


def _activate_user(uid: int, user_login):
    db = ReporterDatasource()
    db.update_with_log(user_login, 'osoby', uid, {'aktywny': True})


def _deactivate_user(uid: int, user_login):
    db = ReporterDatasource()
    db.update_with_log(user_login, 'osoby', uid, {'aktywny': False})


def _validate_required_fields(data, required_fields):
    for required_field in required_fields:
        if isinstance(required_field, dict):
            field = required_field['field']
            value = data.get(field)
        else:
            field = required_field
            value = data.get(field)
        if not value:
            raise ValidationError(
                f'Pole {field} jest wymagane')
    return None


def _validate_user_login_id(user_data: dict):
    login = user_data.get('login')
    uid = user_data.get('id')

    if not uid and not login:
        raise ValidationError('Login lub id użytkownika jest wymagane')


# PUBLIC
def all_users():
    data = _all_users_from_db()
    return _group_by_login(data)


def reset_password(user_data: dict, user_login):
    uid = _get_uid(user_data)
    new_password = _reset_password(uid, user_login)
    return {'message': f'Hasło zostało zmianione na {new_password}',
            'password': new_password}


def toggle_user_access(user_data: dict, user_login):
    _validate_user_login_id(user_data)
    uid = _get_uid(user_data)
    user_db_data = _single_user_from_db(uid)[0]
    if user_db_data['aktywny']:
        _deactivate_user(user_db_data['id'], user_login)
        return {'message': 'Użytkownik został deaktywowany'}
    else:
        _activate_user(user_db_data['id'], user_login)
        return {'message': 'Użytkownik został aktywowany'}


def restrict_rights(user_data: dict, user_login):
    _validate_required_fields(user_data, ['rights_id'])

    db = ReporterDatasource()
    try:
        passed_ids = user_data['rights_id'].split(' ')
    except:
        raise ValidationError('Przesłano błędne dane upraawnień. Spróbuj raz jeszcze')
    for id in passed_ids:
        db.delete_with_log(user_login, 'uprawnienia', id)

    return {'message': 'Uprawnienia zostały usunięte'}

def change_rights(data: dict, user_login):

    db = ReporterDatasource()
    access_id = data.get('access_id')
    access_data = data['data']
    role = access_data.get('rola')
    labs = access_data.get('laboratoria')
    reports = access_data.get('raporty')

    if role and reports:
        raise ValidationError('Nie można jednocześnie zmienić roli oraz raportów')

    if role:
       db.update_with_log(user_login, 'uprawnienia', access_id, {'uprawnienia': role}) 

    if labs:
       db.update_with_log(user_login, 'uprawnienia', access_id, {'laboratoria': labs})

    if reports:
       db.update_with_log(user_login, 'uprawnienia', access_id, {'uprawnienia': reports}) 

    return {'message': 'Uprawnienia zostały zmienione'}


def add_rights(user_data: dict, lab_selector: LabSelector, user_login):
    _validate_required_fields(user_data, ['rights', 'labs'])
    uid = _get_uid(user_data)
    rights = user_data.get('rights')
    reports = user_data.get('reports')
    labs = user_data.get('labs')
    labs = _get_asterisk_if_all_labs(labs, lab_selector)

    if rights == BRAK_ROLI:
        rights = reports

    if not rights:
        raise ValidationError(
            f'Pole rola bądź raporty jest wymagane')

    db = ReporterDatasource()
    split_rights = rights.split(' ')
    alredy_exists = db.dict_select('select * from uprawnienia where uprawnienia = %s and osoba = %s', [rights, uid])
    if alredy_exists:
        if len(alredy_exists) > 1:
            raise ValidationError('Uzytkownik posiada zduplikowaną rolę, usuń duplikaty z bazy')
        if alredy_exists[0]['del']:
            db.update_with_log(user_login, 'uprawnienia', alredy_exists[0]['id'], {'uprawnienia': rights, 'laboratoria': labs, 'del': False})
            return {'message': 'Uprawnienia zostały dodane'}
        else:
            raise ValidationError('Uzytkownik posiada już tę rolę, użyj opcji edytuj')

    if len(split_rights) > 1:
        for right in split_rights:
            values = {
                'osoba': uid,
                'uprawnienia': right,
                'laboratoria': labs
            }
            db.insert_with_log(user_login, 'uprawnienia', values)
    else:
        values = {
                'osoba': uid,
                'uprawnienia': rights,
                'laboratoria': labs
            }
        db.insert_with_log(user_login, 'uprawnienia', values)

    return {'message': 'Uprawnienia zostały dodane'}


def add_user(user_data: dict, lab_selector: LabSelector, user_login):
    nazwisko = user_data.get('nazwisko').strip()
    login = user_data.get('login').strip().lower()
    email = user_data.get('email').strip()
    db = ReporterDatasource()

    _validate_required_fields(user_data, ['login', 'nazwisko', 'email'])
    _login_length_validation(login)
    _login_uniqueness_validation(db, login)
    _email_validation(db, email)

    password, plain_password = _password_generator()

    values = {
        'zrodlo': 'WEB_REPORTER',
        'nazwisko': nazwisko,
        'login': login,
        'passwd': password,
        'email': email
    }
    db.insert_with_log(user_login, 'osoby', values)
    uid = _user_id_from_login(db, login)

    if uid and user_data.get('rights') and user_data.get('labs'):
        add_rights(user_data, lab_selector, user_login)

    return {
        'message': f'Użytkowik został dodany, wegenerowane hasło to {plain_password}',
        'password': plain_password}
