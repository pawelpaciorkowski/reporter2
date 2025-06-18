from typing import List, Optional

from datasources.ick import IckDatasource
from datasources.vouchery import VouchersDatasource, VoucherDeactivationError
from datasources.prezlecenia import PreordersRepository, PreorderRepositoryError
from dialog import Dialog, VBox, TextInput, InfoText, ValidationError
from helpers.confirmation_code import ConfirmationError, MissingConfirmation, validate_confirmation_code
from tasks import TaskGroup

MENU_ENTRY = 'Vouchery - unieważnij generacje voucherów oreaz prezlecenia'
REQUIRE_ROLE = ['ADMIN']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text='''Wprowadź kody generacji voucherów'''),
    TextInput(field='generation_id', title='Id generacji'),
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
    codes = params.get("generation_id")
    if not codes:
        raise ValidationError('Wprowadź przynajmniej jeden id generacji')
    #
    # unpacked_codes = unpack_codes(codes)
    # for code in unpacked_codes:
    #     if ' ' in code:
    #         raise ValidationError('Kody zleceń muszą być oddzielone przecinkiem')
    # params["codes"] = unpacked_codes
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
            'text': f"Liczba usuniętych prezleceń: {len(deleted_codes)}"})

    if used_preorders:
        used_codes = [preorder['kod_zlecenia'] for preorder in used_preorders]
        res['results'].append({
            'type': 'error',
            'text': f"Lista nieusuniętych prezleceń(już wykorzystanych): {len(used_codes)}"})

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

    db = IckDatasource(read_write=True)
    vouchers_db = VouchersDatasource(read_write=True)
    preorders_repo = PreordersRepository(db)
    generation_id = params['generation_id']
    confirm = params['confirm']

    try:
        vouchers = vouchers_db.get_vouchers_by_generation(generation_id)
        codes = tuple([v['barcode'] for v in vouchers])
        preorders = preorders_repo.get_preorders(codes)
        preorders_in_split = split_preorders(preorders)
        preorders_to_delete = preorders_in_split["preorders_to_delete"]
        validate_confirmation_code(confirm, preorders_to_delete, generation_id)
        codes_to_delete = [preorder['kod_zlecenia'] for preorder in preorders_to_delete]
        vouchers_to_delete = [voucher for voucher in vouchers if voucher['barcode'] in codes_to_delete]

        preorders_repo.delete_preorders(preorders_to_delete)
        vouchers_db.deactivate_vouchers(vouchers_to_delete)
        vouchers_db.deactivate_generation(generation_id, vouchers_to_delete)

    except (PreorderRepositoryError, ConfirmationError) as e:
        return prepare_response(error=str(e))

    except MissingConfirmation as e:
        return prepare_response(info=str(e))

    except VoucherDeactivationError as e:
        return prepare_response(info=str(e))

    return prepare_response(preorders_in_split)
