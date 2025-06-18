from dialog import Dialog, VBox, TextInput, InfoText, ValidationError, NumberInput
from tasks import TaskGroup
import requests as r

MENU_ENTRY = 'Zarezerwuj numer faktury'
ADD_TO_ROLE = ['C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text='''Zarezerwój numer faktury dla danego typu, mpk oraz roku'''),
    TextInput(field='code_type', title='Rodzaj faktury (G, GN, S, SN'),
    NumberInput(field='mpk', title='MPK punktu pobrań'),
    NumberInput(field='year', title='Rok'),
))


CODE_TYPES = ['S', 'SN', 'G', 'GN']


def validate_params(params: dict):
    code = params.get("code_type")
    if not code:
        raise ValidationError('Wprowadź kod zlecenia')
    if code not in CODE_TYPES:
        raise ValidationError('Niepoprawny typ')

    mpk = params.get("mpk")
    if not mpk:
        raise ValidationError('Wprowadź MPK')
    try:
        mpk = int(mpk)
    except ValueError:
        raise ValidationError('MPK musi być cyfrą')
    if mpk < 0 or mpk > 999:
        raise ValidationError('Niepoprawny numer MPK')

    year = params.get("year")
    if not year:
        raise ValidationError('Wprowadź rok')
    try:
        year = int(year)
    except ValueError:
        raise ValidationError('Rok musi być cyfrą')
    if year < 2020 or year > 2050:
        raise ValidationError('Niepoprawny rok')

    return {
        'code_type': code,
        'mpk': mpk,
        'year': year
    }


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    params = validate_params(params)

    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'noc',
        'priority': 1,
        'params': params,
        'function': 'book_code'
    }
    report.create_task(task)
    report.save()
    return report


def book_code(task_params):
    params = task_params['params']
    validated_params = validate_params(params)
    res = {
        'errors': [],
        'results': [],
        'actions': []
    }
    request_params = validated_params
    request_params['user'] = 'Reporer'
    try:
        response = r.get('http://10.192.6.1:80/book', request_params, timeout=10)
    except:
        error = {
            'type': 'error',
            'text': f"Problem z połączeniem do API Próśb o fakturę"}
        res['results'].append(error)
        return res

    if response.status_code > 399 < 499:
        res['errors'].append(response.json()['detail'])
    if response.status_code == 200:
        ok = {
            'type': 'success',
            'text': f"Zarezerwowano numer faktury: {response.json()['booked_code']}"}
        res['results'].append(ok)
    else:
        error = {
            'type': 'error',
            'text': f"Niespodziewany błąd API Próśb o fakturę"}
        res['results'].append(error)

    return res
