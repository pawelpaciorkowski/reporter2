from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection
from api.common import get_db

MENU_ENTRY = 'Sprzedaż gotówkowa pakietów'
REQUIRE_ROLE = ['C-FIN', 'C-PP']
REQUIRE_ROLE = 'ADMIN' # TODO: usunąć po implementacji

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport ze sprzedaży gotówkowej pakietów w podziale na pracowników Punktów Pobrań. Raport generowany jest wg dat rejestracji.'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))