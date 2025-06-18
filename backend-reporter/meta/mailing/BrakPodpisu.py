from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError, EmailInput, Button
from datasources.reporter import ReporterDatasource
from helpers import TrustedAction, prepare_for_json

MENU_ENTRY = 'Brak podpisu'

GUI_MODE = 'mailing'

MAILING_NAME = 'BrakPodpisu'
MAILING_TARGETS = 'labs'

DESC = """Raporty wysyłane do laboratoriów, wg danych z baz laboratoryjnych z informacją o zatwierdzonych wykonaniach, 
    do których nie powstały wyniki podpisane elektronicznie."""

MAILING_TABLE = {
    'key': 'id',
    'header': [
        {'field': 'nazwa', 'title': 'Laboratorium'},
        {'field': 'emaile', 'title': 'Emaile'},
        {'meta': 'preview'},
        {'meta': 'edit'},
        {'meta': 'delete'},
    ]
}


def labs_available():
    rep = ReporterDatasource()
    res = []
    for row in rep.dict_select("""
        select l.symbol from laboratoria l 
        where (l.aktywne or l.pracownia_domyslna) and l.adres_fresh is not null
        and l.id not in (select lab from mailing_adresy where raport=%s and lab is not null)
    """, [MAILING_NAME]):
        res.append(row['symbol'])
    return res


MAILING_DIALOG = Dialog(ident='MAILING', panel=VBox(
    LabSelector(field='laboratorium', title='Laboratorium', disableInModes=['edit'], show_only=labs_available),
    EmailInput(field='emaile', title='E-maile'),
    HBox(
        Button(action='save', text='Zapisz', intent='success'),
        Button(action='cancel', text='Anuluj', intent='danger'),
    )
))


class PreviewHistory(TrustedAction):
    params_available = ['id']

    def execute(self):
        rep = ReporterDatasource()
        res = rep.get_log_for('mailing_adresy', self.params['id'])
        return prepare_for_json(res)


class PreviewMailingList(TrustedAction):
    # Pobieranie całego miesiąca, wyświetlanie kalendarza z zaznaczonymi dniami z wysyłką, po kliknięciu na dzień lista maili
    params_available = ['id']

    def execute(self, *args, **kwargs):
        return {'t': 'PreviewMailingList', 'args': args, 'kwargs': kwargs}


class PreviewMailingContent(TrustedAction):
    params_available = ['id']

    def execute(self, *args, **kwargs):
        return {'t': 'PreviewMailingContent', 'args': args, 'kwargs': kwargs}


def action_data():
    rows = []
    sql = """
        select ma.id, ma.nazwa, ma.emaile, ma.parametry, l.symbol as laboratorium, l.nazwa as lab_nazwa, ma.del
        from mailing_adresy ma
        left join laboratoria l on l.id=ma.lab
        where ma.raport=%s
        and ma.lab is not null
        order by ma.del, l.kolejnosc
    """
    rep = ReporterDatasource()
    for row in rep.dict_select(sql, [MAILING_NAME]):
        # TODO: podokładać tu akcje?
        row['history_token'] = PreviewHistory(id=row['id']).get_token()
        row['mailing_list_token'] = PreviewMailingList(id=row['id']).get_token()
        row['mailing_content_token'] = PreviewMailingContent(id=row['id']).get_token()
        rows.append(row)
    return {'rows': rows, 'title': MENU_ENTRY}


"""

-5dni do dzisiaj


"""

# TODO: po każdej akcji zakolejkować przegenerowanie konfiguracji airflowa

def action_save(user_login, data):
    rep = ReporterDatasource()
    if 'id' in data:
        existing = rep.select_and_unwrap("select * from mailing_adresy where id=%s and raport=%s",
                                         [data['id'], MAILING_NAME])
        if len(existing) == 0:
            raise ValidationError('Nie znaleziono raportu')
        # TODO: uprawnienia
        existing = existing[0]
        if existing['emaile'] == data['emaile']:
            # TODO: na razie validation error nie przechodzi na zewnątrz
            raise ValidationError('Nic się nie zmieniło')
        rep.update_with_log(user_login, 'mailing_adresy', existing['id'], {'emaile': data['emaile']})
    else:
        labs = rep.select_and_unwrap("select * from laboratoria where symbol=%s", [data['laboratorium']])
        # TODO: uprawnienia
        if len(labs) == 0:
            raise ValidationError('Nie znaleziono laboratorium')
        lab = labs[0]
        values = {
            'raport': MAILING_NAME,
            'nazwa': lab['nazwa'],
            'emaile': data['emaile'],
            'vpn': lab['adres_fresh'],
            'baza': lab['baza_fresh'],
            'baza_pg': lab['baza_pg'],
            'lab': lab['id'],
        }
        nid = rep.insert_with_log(user_login, 'mailing_adresy', values)
        return {'status': 'ok', 'id': nid}


# TODO sprawdzić czemu w okienku nowego mailingu enter odświeża okienko a nic nie dodaje


def action_delete(user_login, data):
    rep = ReporterDatasource()
    if 'id' in data:
        existing = rep.select_and_unwrap("select * from mailing_adresy where id=%s and raport=%s",
                                         [data['id'], MAILING_NAME])
        if len(existing) == 0:
            raise ValidationError('Nie znaleziono raportu')
        # TODO: uprawnienia
        existing = existing[0]
        if existing['del']:
            raise ValidationError('Już usunięto')
        rep.update_with_log(user_login, 'mailing_adresy', existing['id'], {'del': True})
    else:
        raise ValidationError('Nie znaleziono')


def action_undelete(user_login, data):
    rep = ReporterDatasource()
    if 'id' in data:
        existing = rep.select_and_unwrap("select * from mailing_adresy where id=%s and raport=%s",
                                         [data['id'], MAILING_NAME])
        if len(existing) == 0:
            raise ValidationError('Nie znaleziono raportu')
        # TODO: uprawnienia
        existing = existing[0]
        if not existing['del']:
            raise ValidationError('Rekord nie jest usunięty')
        rep.update_with_log(user_login, 'mailing_adresy', existing['id'], {'del': False})
    else:
        raise ValidationError('Nie znaleziono')


"""

create table mailing_adresy (
	id serial primary key,
	raport varchar(255),
	nazwa varchar(255),
	emaile text,
	parametry json
);

create table mailing_harmonogram (
	id serial primary key,
	raport varchar(255),
	nazwa varchar(255),
	harmonogram varchar(255),
	parametry json
)

"""
