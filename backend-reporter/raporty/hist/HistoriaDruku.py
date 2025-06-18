from pprint import pprint

from dialog import Dialog, VBox, LabSelector, InfoText, DateInput, ValidationError, HistoUzytkownicySelector, Switch
from helpers.validators import validate_date_range
from tasks import TaskGroup
from helpers import prepare_for_json
from datasources.alabinfo import AlabInfoDatasource

MENU_ENTRY = "Historia druku"

LAUNCH_DIALOG = Dialog(
    title=MENU_ENTRY,
    panel=VBox(
        InfoText(
            text='Raport statystyczy wydrukowanych szkiełek/kasetek\n'
            'Brak wyboru użytkowników generuje raport - Badania ilości\n'
            'Wybór użytkowników bez zaznaczonych opcji generuje raport - Badania ilości z podziałem na użytkowników\n'
            'Wybór użytkowników z zaznaczoną opcją "Zbiorowe" generuje raport - Pracownik zbiorcze\n'
            'Wybór użytkowników z zaznaczoną opcją "Podział na badania" generuje raport - Badania pracownik'
        ),
        HistoUzytkownicySelector(multiselect=True, field='uzytkownicy', title='Użytkownicy'),
        DateInput(field="dataod", title="Data początkowa", default="-7D"),
        DateInput(field="datado", title="Data końcowa", default="-1D"),
        Switch(field='zbiorowe', title='Zbiorowe'),
        Switch(field='podzial_badania', title='Podział na badania'),
    ),
)

SQL = """
-- Raport na badania (Histopatologia)

select hp.code as "Symbol badania", hp.locality as "Rodzaj", COUNT(*) as "Suma wydrukowanych" from histopathology_printed hp
where update >= %s and update <= %s and hp.code is not null and hp.code <> ''
group by hp.code, hp.locality
"""

SQL_Uzytkownik = """
-- Raport na badania uzytkownik (Histopatologia)

select u."name" as "Nazwa użytkownika", hp.code as "Symbol badania", hp.locality as "Rodzaj", COUNT(*) as "Suma wydrukowanych" from histopathology_printed hp
left join users u on hp.user_id = u.id
where user_id in %s and update >= %s and update <= %s and hp.code is not null and hp.code <> ''
group by u."name", hp.code, hp.locality
order by u."name"
"""

SQL_Zbiorowe = """
-- Raport zbiorowy per użytkownik (Histopatologia)

select u."name" as "Nazwa użytkownika", hp.locality as "Rodzaj", COUNT(*) as "Suma wydrukowanych" from histopathology_printed hp
left join users u on hp.user_id = u.id
where user_id in %s and update >= %s and update <= %s
group by hp.locality, u."name"
order by u."name"
"""

SQL_Podzial_badania = """
-- Raport na badania per użytkownik (Histopatologia)

select u."name" as "Nazwa użytkownika", hp.code as "Symbol badania", hp.locality as "Rodzaj", hp.number_of_books as "Numer badania", hp.text_2 as "Numer bloku", hp.update as "Czas druku" from histopathology_printed hp
left join users u on hp.user_id = u.id
where user_id in %s and update >= %s and update <= %s
ORDER by u."name", hp.update DESC
"""


def start_report(params):
    report = TaskGroup(__PLUGIN__, params)
    params = LAUNCH_DIALOG.load_params(params)
    if params['zbiorowe'] and not params['uzytkownicy']:
        raise ValidationError('Wybierz użytkowników aby wygenerować zbiorczy raport')
    if params['podzial_badania'] and not params['uzytkownicy']:
        raise ValidationError('Wybierz użytkowników aby wygenerować raport z podziałem na badania')
    if params['podzial_badania'] and params['zbiorowe']:
        raise ValidationError('Nie możesz wygenerować raportu zbiorczego z podziałem na badania')
    validate_date_range(params["dataod"], params["datado"], 93)
    task = {
        "type": "ick",
        "priority": 1,
        "params": params,
        "function": "raport_badania_ilosci",
    }
    report.create_task(task)
    report.save()
    return report


def raport_badania_ilosci(task_params):
    params = task_params["params"]
    dataczas_od = "{} 00:00:00".format(params["dataod"])
    dataczas_do = "{} 23:59:59".format(params["datado"])
    ds = AlabInfoDatasource()
    if params['uzytkownicy'] is None or len(params['uzytkownicy']) == 0:
        cols, rows = ds.select(SQL, [dataczas_od, dataczas_do])
    else:
        if params['zbiorowe']:
            cols, rows = ds.select(SQL_Zbiorowe, [tuple(params['uzytkownicy']), dataczas_od, dataczas_do])
        elif params['podzial_badania']:
            cols, rows = ds.select(SQL_Podzial_badania, [tuple(params['uzytkownicy']), dataczas_od, dataczas_do])
        else:
            cols, rows = ds.select(SQL_Uzytkownik, [tuple(params['uzytkownicy']), dataczas_od, dataczas_do])
    return {"type": "table", "header": cols, "data": prepare_for_json(rows)}
