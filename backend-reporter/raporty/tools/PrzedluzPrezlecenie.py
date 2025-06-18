import datetime
from typing import Optional

from datasources.ick import IckDatasource
from datasources.vouchery import VouchersDatasource, VoucherProlongError
from datasources.prezlecenia import PreordersRepository, PreorderRepositoryError
from dialog import Dialog, VBox, TextInput, InfoText, ValidationError, DateInput
from helpers.confirmation_code import validate_confirmation_code, ConfirmationError, MissingConfirmation
from tasks import TaskGroup

MENU_ENTRY = 'Prezlecenia - przedłuż prezlecenie'
REQUIRE_ROLE = ['C-ADM']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text='''Wprowadź kod vouchera, który ma zostać przedłużony'''),
    TextInput(field='code', title='Kod vouchera'),
    DateInput(field='date', title='Data ważności'),
    TextInput(field='confirm', title='Kod potwierdzenia'),
))


def validate_params(params: dict):
    code = params.get("code")
    if not code:
        raise ValidationError('Wprowadź kod zlecenia')

    date = params.get("date")
    if not date:
        raise ValidationError('Wprowadź datę')

    if datetime.datetime.strptime(date, '%Y-%m-%d' ) < datetime.datetime.now():
        raise ValidationError('Data musi być w przyszłości')

    return params


def prepare_response(
        preorder: Optional[dict] = None,
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

    if preorder:
        res['results'].append({
            'type': 'success',
            'text': f"Przedłużono  prezlecenie: {preorder['kod_zlecenia']}" })

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
    code = params["code"]
    date = params["date"]
    confirm = params["confirm"]

    db = IckDatasource(read_write=True)
    vouchers_db = VouchersDatasource(read_write=True)
    preorders_repo = PreordersRepository(db)

    try:
        preorder = preorders_repo.get_preorder(code)
        voucher = vouchers_db.get_voucher(code)[0]
        validate_confirmation_code(confirm, preorder, code)

        preorders_repo.prolong_preorder(preorder, date)
        vouchers_db.prolong_voucher(voucher, date)

    except (PreorderRepositoryError, ConfirmationError) as e:
        return prepare_response(error=str(e))

    except MissingConfirmation as e:
        return prepare_response(info=str(e))

    except VoucherProlongError as e:
        return prepare_response(info=str(e))

    return prepare_response(preorder)
