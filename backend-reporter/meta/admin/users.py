from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Switch
from dialog import Dialog, HBox, VBox, TextInput, LabSelector, \
    RaportSelector, RoleSelector, Button, PosiadaneDostepySelector

from api.user.utils import all_users, add_user, change_rights, toggle_user_access, \
    reset_password, restrict_rights, add_rights


def get_display_data_list(data):
    response = []
    for row in data:
        rights = row['uprawnienia']
        rights = None if rights == {None: [None]} else rights
        response.append(
            {
                'id': row['id'],
                'login': row['login'],
                'nazwisko': row['nazwisko'],
                'email': row['email'],
                'uprawnienia': rights,
                'aktywny': row.get('aktywny')
            })
    return response


def get_response_data():
    data = all_users()
    return get_display_data_list(data)


def get_rights_list(row):
    return [u for u in row['uprawnienia']]


def get_lab_list(row):
    labs = []
    for lab in row['uprawnienia']:
        labs.append(
            ' '.join(a for a in row['uprawnienia'][lab] if a is not None))
    return labs


# DIALOG
MENU_ENTRY = 'Użytkownicy'
REQUIRE_ROLE = ['C-ADM', 'R-ADM', 'L-ADM']
GUI_MODE = 'settings_table'

DIALOGS = {
    'nowy': Dialog(title='Nowy użytkownik', panel=VBox(
        TextInput(field='login', title='Login'),
        TextInput(field='nazwisko', title='Imię i nazwisko'),
        Select(field='rola', title='Rola', values={'C-CS': 'CS - Centrala', 'R-CS': 'CS - Region'}),
        # TODO - wartości ze słowniczka, ograniczone uprawnieniem administratora
        Switch(field='wszystkielaby', title='Wszystkie laboratoria', default=False),
        LabSelector(field='laboratoria', title='Laboratoria', pokaz_nieaktywne=True, alfabetycznie=True),
        # TODO: przycisk do zapisywania
    )),
    'edycja': Dialog(title='Edycja użytkownika', panel=VBox(
        TextInput(field='nazwisko', title='Imię i nazwisko'),
    )),
}
REQUIRE_ROLE = ['C-ADM']
GUI_MODE = 'settings'
DESC = "Panel do zarządzania dostępami użytkowników"
LAB_SELECTOR = LabSelector(
    field='laboratoria',
    title='Laboratoria',
    multiselect=True,
    pokaz_nieaktywne=True,
    disableInModes=['restrict'],
    hideInModes=['restrict'],
    alfabetycznie=True,
)
USERS_DIALOG = Dialog(
    ident='USERS',
    title='Panel użytkowników',
    panel=VBox(
        TextInput(field='login', title='Login',
                  disableInModes=['append', 'restrict', 'change']),
        TextInput(
            field='nazwisko',
            title='Imię i nazwisko',
            disableInModes=['append', 'restrict', 'change']),
        TextInput(
            field='email',
            title='Email',
            disableInModes=['append', 'restrict', 'change']),
        RoleSelector(
            field='rola',
            title='Rola',
            disableInModes=['restrict',],
            hideInModes=['restrict']),
        LAB_SELECTOR,
        RaportSelector(
            field='raporty',
            title='''Pojedyńcze raporty
             (poza rolą)''',
            multiselect=True,
            disableInModes=['restrict',],
            hideInModes=['restrict']),
        PosiadaneDostepySelector(
            field='uprawnienia',
            title='Posiadane dostępy',
            multiselect=True,
            disableInModes=['append', 'new'],
            hideInModes=['append', 'new'],
            loadData=False),
        HBox(
            Button(action='save', text='Zapisz', intent='success'),
            Button(action='cancel', text='Anuluj', intent='danger'),
        ),
    )
)

TABLES = {
    'uzytkownicy': {
        'header': ['Login', 'Imię i nazwisko', 'Źródło', 'Uprawnienia'],
        'data_provider': 'lista_uzytkownikow',
        'global_operations': {
            'new': {
                'title': 'Nowy użytkownik',
                'dialog': 'nowy',
                'function': 'dodaj_uzytkownika'
            }
        },
        'row_operations': {
            'reset_password': {
                'title': 'Reset hasła',
                'confirm': 'Hasło zostanie zresetowane. Nowe hasło będzie trzeba przekazać użytkownikowi. Czy chcesz kontynuować?',
                'funcion': 'resetuj_haslo',
            }
        }
    }
}

ENTRY_POINT = 'uzytkownicy'
# GUI ACTIONS
def action_data(pata=None):
    print(pata)
    return {
        'rows': get_response_data(),
        'title': 'Użytkownicy'}


def action_add(data, user_login):
    return add_user(data, LAB_SELECTOR, user_login)


def action_toggle_access(data, user_login):
    return toggle_user_access(data, user_login)


def action_append(data, user_login):
    return add_rights(data, LAB_SELECTOR, user_login)


def action_restrict(data, user_login):
    return restrict_rights(data, user_login)


def action_reset_password(data, user_login):
    return reset_password(data, user_login)

def action_change(data, user_login):
    return change_rights(data, user_login)


USERS_TABLE = {
    'title': 'Użytkownicy',
    'header': [
        {'field': 'id', 'title': 'id'},
        {'field': 'login', 'title': 'Login'},
        {'field': 'nazwisko', 'title': 'Nazwisko'},
        {'field': 'email', 'title': 'Email'},
        {'field': 'uprawnienia', 'title': 'Uprawnienia'},
        {'field': 'aktywny', 'title': 'Aktywny'},
        {'meta': 'reset_password', 'title': 'Zresetuj hasło'},
        {'meta': 'edit', 'title': 'Dodaj uprawnienia'},
        {'meta': 'restrict', 'title': 'Usuń uprawnienia'},
        {'meta': 'change', 'title': 'Zmień uprawnienia'},
    ],
    'data': action_data(None)
}
