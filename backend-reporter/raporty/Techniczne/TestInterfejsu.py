from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError, Switch, Preset
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty

MENU_ENTRY = 'Test interfejsu'
REQUIRE_ROLE = 'ADMIN'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="""
            Ten raport ma kilka zadań. Po pierwsze definiuje wszystkie elementy i możliwe atrybuty (oraz ich typy),
            które mogą wystąpić w dialogach odpalających inne raporty. Dialog zawierający element lub atrybut
            niewystępujący tutaj nie przejdzie testów. Po drugie dialog ten służy do organoleptycznego sprawdzenia
            poprawności działania wszystkich kontrolek po stronie frontendu. Po trzecie sam raport sprawdza
            wszystkie możliwe obiekty, które mogą się pojawić na wyjściu raportu. Raport ten poza funkcjami
            sprawdzającymi może służyć jako dokumentacja poszczególnych kontrolek i elementów wyjściowych
            oraz miejsce, od którego powinno się zaczynać rozbudowę funkcjonalności dialogów/raportów."""),
))


def start_report(params):
    pass # TODO: wyciągnąć z outlib.test.conftest all_samples i tutaj zwrócić