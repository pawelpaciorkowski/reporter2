import hashlib
from typing import List, Any


class ConfirmationError(Exception):
    pass


class MissingConfirmation(Exception):
    pass


def validate_confirmation_code(confirm: str, data: Any, related_ref: str):
    confirmation_code = generate_confirmation_code(data)
    if not confirm:
        raise MissingConfirmation(f'Operacja dla  {related_ref} nie została wykonana. Aby ją wykonać, wprowadź kod potwierdzenia: {confirmation_code}')
    if confirm != confirmation_code:
        raise ConfirmationError(f'Niepoprawny kod potwierdzenia')


def generate_confirmation_code(preorder: dict) -> str:
    return hashlib.sha256(repr(preorder).encode()).hexdigest()
