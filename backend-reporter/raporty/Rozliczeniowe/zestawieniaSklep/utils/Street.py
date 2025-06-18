class Street:

    def __init__(self, street_type: str, street_name: str):
        self._street_type = street_type
        self._street_name = street_name

    @property
    def full_street(self) -> str:
        return f'{self._street_type} {self._street_name}'

    @property
    def street_type(self) -> str:
        return self._street_type

    @property
    def street_name(self) -> str:
        return self._street_name


class StreetMiesieczny(Street):
    def __init__(self, row_data):
        street_name = row_data['street']
        street_type = row_data['street_type']
        super().__init__(street_type, street_name)
