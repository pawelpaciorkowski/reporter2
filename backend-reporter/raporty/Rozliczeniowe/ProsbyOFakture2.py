from dialog import Dialog, VBox, TextInput, InfoText, ValidationError, NumberInput
from helpers import prepare_for_json
from tasks import TaskGroup
import requests as r

MENU_ENTRY = 'Prosby o fakture 2'
ADD_TO_ROLE = ['C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text='''Szukaj prośby'''),
    TextInput(field='ident', title='Identyfikator'),
    TextInput(field='barcode', title='Kod kreskowy'),
))


def validate_params(params: dict):
    ident = params.get('ident')
    barcode = params.get('kodkreskowy')

    if ident and barcode:
        raise ValidationError('Podaj identyfikator ALBO kod kreskowy')

    if ident and len(ident) != 10:
        raise ValidationError('Podaj 10-znakowy identyfikator')

    if barcode and len(barcode) < 9:
        raise ValidationError('Podaj co najmniej 9 znaków kodu kreskowego')

    return params

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    params = validate_params(params)

    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'noc',
        'priority': 1,
        'params': params,
        'function': 'search_requests'
    }
    report.create_task(task)
    report.save()
    return report


def search_requests(task_params):
    params = task_params['params']
    validated_params = validate_params(params)
    res = {
        'errors': [],
        'results': [],
        'actions': []
    }

    request_params = {}
    if validated_params.get('ident'):
        request_params['ident'] = validated_params.get('ident')
    else:
        request_params['barcode'] = validated_params.get('barcode')
    try:
        response = r.get('http://10.192.6.1:80/reports', request_params, timeout=10)
    except:
        error = {
            'type': 'error',
            'text': f"Problem z połączeniem do API Próśb o fakturę"}
        res['results'].append(error)
        return res

    if response.status_code > 399 < 499:
        res['errors'].append(response.json()['detail'])
    if response.status_code == 200:
        data = response.json()
        for obj_type in data:
            try:
                if isinstance(data[obj_type], dict):
                    row = [{'title': d, 'value': str(data[obj_type][d])} for d in data[obj_type]]
                elif isinstance(data[obj_type], list):
                    a = data[obj_type][0]
                    row = [{'title': d, 'value': str(a[d])} for d in a]
                else:
                    row = [{'title': obj_type, 'value': data[obj_type]}]
            except Exception as e:
                print(str(e), obj_type, data[obj_type])
            table = {
                'type': 'vertTable',
                'title': obj_type,
                'data': row
            }
            res['results'].append(table)
    else:
        error = {
            'type': 'error',
            'text': f"Niespodziewany błąd API Próśb o fakturę"}
        res['results'].append(error)

    return res
