from dataclasses import dataclass

class Purchaser:
    def __init__(
            self, firstname: str, surname: str, telephone: str, email: str,
            pesel: str):
        self._name = firstname
        self._surname = surname
        self._telephone = telephone
        self._email = email
        self._pesel = pesel

    def get_name(self):
        return self._name

    def report_representation(self):
        return f'{self._name} {self._surname} \n tel:{self._telephone} \n' \
               f'email: {self._email} \n pesel: {self._pesel}'


class VatPurchaser:
    def __init__(self, **kwargs) -> None:
        self.firstname = kwargs.get('vat_name')
        self.surname = kwargs.get('vat_surname')
        self.company_name = kwargs.get('vat_name_company')
        self.nip = kwargs.get('vat_nip')
        self.street = kwargs.get('vat_street')
        self.city = kwargs.get('vat_city')
        self.post_code = kwargs.get('vat_postcode')
        self.type = kwargs.get('vat_type')

    def report_representation(self):
        if self.type and self.type.lower() != 'customer':
            return self._report_representation_company()
        return self._report_representation_customer()

    def _report_representation_company(self) -> dict:
        return f'''
                {self.company_name}\n
                nip: {self.nip} \n
                {self.street} \n
                {self.post_code} \n
                {self.city}
                '''

    def _report_representation_customer(self) -> dict:

        return f'''
                {self.firstname}\n
                {self.surname}\n
                {self.street} \n
                {self.post_code} \n
                nip: {self.nip} \n
                {self.city}
                '''