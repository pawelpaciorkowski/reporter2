import datetime
from typing import Optional

from datasources.ick import IckDatasource
from datasources.prezlecenia import PreordersRepository, PreorderRepositoryError
from datasources.vouchery import VouchersDatasource, VoucherProlongError
from dialog import Dialog, VBox, TextInput, InfoText, ValidationError, DateInput
from helpers.confirmation_code import validate_confirmation_code, ConfirmationError, MissingConfirmation
from tasks import TaskGroup

MENU_ENTRY = 'Prezlecenia - przedłuż generacje prezleceń'
REQUIRE_ROLE = ['C-ADM']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text='''Wprowadź id generacji, który ma zostać przedłużony'''),
    TextInput(field='generation_id', title='Id generacji'),
    DateInput(field='date', title='Data ważności'),
    TextInput(field='confirm', title='Kod potwierdzenia'),
))


def validate_params(params: dict):
    generation_id = params.get("generation_id")
    if not generation_id:
        raise ValidationError('Wprowadź id generacji')

    date = params.get("date")
    if not date:
        raise ValidationError('Wprowadź datę')

    if datetime.datetime.strptime(date, '%Y-%m-%d' ) < datetime.datetime.now():
        raise ValidationError('Data musi być w przyszłości')

    return params


def prepare_response(
        generation_id: Optional[int] = None,
        error: Optional[str] = None, 
        info: Optional[str]= None) -> dict:

    res = {
        'errors': [],
        'results': [],
        'actions': []
    }

    if info:
        res['results'].append({
            'type': 'info',
            'text': info})
        return res

    if error:
        res['errors'].append(error)
        return res

    if generation_id:
        res['results'].append({
            'type': 'success',
            'text': f"Przedłużono  gneracje: {generation_id}" })

    return res


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    params = validate_params(params)

    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'noc',
        'priority': 1,
        'params': params,
        'function': 'raport_przedluz'
    }
    report.create_task(task)
    report.save()
    return report


def raport_przedluz(task_params):
    params = task_params['params']
    generation_id = params["generation_id"]
    date = params["date"]
    confirm = params.get('confirm')

    db = IckDatasource(read_write=True)
    vouchers_db = VouchersDatasource(read_write=True)
    preorders_repo = PreordersRepository(db)

    try:
        vouchers = vouchers_db.get_vouchers_by_generation(generation_id)
        validate_confirmation_code(confirm, vouchers, generation_id)

        codes = [voucher['barcode'] for voucher in vouchers]

        preorders = preorders_repo.get_preorders(codes)
        codes_to_update = [p['kod_zlecenia'] for p in preorders]
        vouchers_to_update = [voucher for voucher in vouchers if voucher['barcode'] in codes_to_update]

        preorders_repo.prolong_preorders(preorders, date)
        vouchers_db.prolong_vouchers(vouchers_to_update, date)

    except (PreorderRepositoryError, ConfirmationError) as e:
        return prepare_response(error=str(e))

    except MissingConfirmation as e:
        return prepare_response(info=str(e))

    except VoucherProlongError as e:
        return prepare_response(info=str(e))

    return prepare_response(generation_id)
