from .simple_widgets import Button
from .dynamic_select import DynamicSelect
from .dynamic_search import DynamicSearch


class LabSelector(DynamicSelect):
    datasource = 'laboratoria'


class RoleSelector(DynamicSelect):
    datasource = 'role'


class PosiadaneDostepySelector(DynamicSelect):
    datasource = 'posiadane_dostepy'


class RaportSelector(DynamicSelect):
    datasource = 'raporty'


class PracowniaSelector(DynamicSelect):
    datasource = 'pracownie'


class KuponSelector(DynamicSelect):
    datasource = 'kupony'


class HistoUzytkownicySelector(DynamicSelect):
    datasource = 'histo_uzytkownicy'


class PlatnikSearch(DynamicSearch):
    datasource = 'platnicy'


class ZleceniodawcaSearch(DynamicSearch):
    datasource = 'zleceniodawcy'


class PunktPobranSearch(DynamicSearch):
    datasource = 'punkty'


class BadanieSearch(DynamicSearch):
    datasource = 'badania'


class GrupaBadanSearch(DynamicSearch):
    datasource = 'grupy_badan'


class LabSearch(DynamicSearch):
    datasource = 'laboratoria'


class Preset(Button):
    def __init__(self, *args, **kwargs):
        if 'intent' not in kwargs:
            kwargs['intent'] = 'primary'
        super().__init__(*args, **kwargs)
