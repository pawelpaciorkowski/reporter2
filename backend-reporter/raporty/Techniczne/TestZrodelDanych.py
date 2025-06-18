from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError, Switch, Preset
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty

MENU_ENTRY = 'Test źródeł danych'
REQUIRE_ROLE = 'ADMIN'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="""
            Ten raport służy do sprawdzenia poprawności połączenia ze wszystkimi źródłami danych oraz drożność
            kolejek i workerów zbierających dane"""),
))


def start_report(params):
    pass