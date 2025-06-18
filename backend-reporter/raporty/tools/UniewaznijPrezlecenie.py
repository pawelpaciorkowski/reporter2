from typing import List, Optional

from datasources.ick import IckDatasource
from datasources.vouchery import VouchersDatasource, VoucherDeactivationError
from datasources.prezlecenia import PreordersRepository, PreorderRepositoryError
from dialog import Dialog, VBox, TextInput, InfoText, ValidationError
from helpers.confirmation_code import validate_confirmation_code, ConfirmationError, MissingConfirmation
from tasks import TaskGroup


MENU_ENTRY = 'Prezlecenia - unieważnij prezlecenie'
REQUIRE_ROLE = ['C-ADM']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text='''Wprowadź kody voucherów, które mają zostać anulowane oddzielone przecinkiem'''),
    TextInput(field='codes', title='Kody voucherów'),
    TextInput(field='confirm', title='Kod potwierdzenia'),
))


def split_preorders(preorders: List[dict]) -> dict:
    preorders_in_split = {
        "preorders_to_delete": tuple(),
        "used_preorders": tuple()
    }

    for preorder in preorders:
        if preorder["ic_system"] is None:
            preorders_in_split["preorders_to_delete"] += (preorder,)
        else:
            preorders_in_split["used_preorders"] += (preorder,)
    return preorders_in_split


def unpack_codes(codes: str) -> tuple:
    """Rozpakowanie kodów zleceń ze stringa do tupla wraz z:
    — usunięciem białych znaków
    — pomięciem pustych kodów w przypadku wystąpienia nadmiarowych przecinków
    — usunięciem duplikatów"""
    return tuple({code.strip() for code in codes.split(",") if code.strip()})


def validate_params(params: dict):
    codes = params.get("codes")
    if not codes:
        raise ValidationError('Wprowadź przynajmniej jeden kod zlecenia')

    unpacked_codes = unpack_codes(codes)
    for code in unpacked_codes:
        if ' ' in code:
            raise ValidationError('Kody zleceń muszą być oddzielone przecinkiem')
    params["codes"] = unpacked_codes
    return params


def prepare_response(
        preorders_in_split: Optional[dict] = None,
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

    deleted_preorders = preorders_in_split["preorders_to_delete"]
    used_preorders = preorders_in_split["used_preorders"]

    if deleted_preorders:
        deleted_codes = [preorder['kod_zlecenia'] for preorder in deleted_preorders]
        res['results'].append({
            'type': 'success',
            'text': f"Lista usuniętych prezleceń: {', '.join(deleted_codes)}"})

    if used_preorders:
        used_codes = [preorder['kod_zlecenia'] for preorder in used_preorders]
        res['results'].append({
            'type': 'error',
            'text': f"Lista nieusuniętych prezleceń: {', '.join(used_codes)}"})

    return res


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    params = validate_params(params)

    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'noc',
        'priority': 1,
        'params': params,
        'function': 'raport_anuluj'
    }
    report.create_task(task)
    report.save()
    return report


def raport_anuluj(task_params):
    params = task_params['params']
    codes = params["codes"]
    confirm = params["confirm"]

    db = IckDatasource(read_write=True)
    vouchers_db = VouchersDatasource(read_write=True)
    preorders_repo = PreordersRepository(db)

    try:
        preorders = preorders_repo.get_preorders(codes)
        preorders_in_split = split_preorders(preorders)
        preorders_to_delete = preorders_in_split["preorders_to_delete"]
        codes_to_delete = [preorder['kod_zlecenia'] for preorder in preorders_to_delete]
        vouchers_to_delete = vouchers_db.get_vouchers(codes_to_delete)
        validate_confirmation_code(confirm, preorders_to_delete, str(codes_to_delete))

        preorders_repo.delete_preorders(preorders_to_delete)
        vouchers_db.deactivate_vouchers(vouchers_to_delete)

    except (PreorderRepositoryError, ConfirmationError) as e:
        return prepare_response(error=str(e))

    except MissingConfirmation as e:
        return prepare_response(info=str(e))

    except VoucherDeactivationError as e:
        return prepare_response(info=str(e))

    return prepare_response(preorders_in_split)
