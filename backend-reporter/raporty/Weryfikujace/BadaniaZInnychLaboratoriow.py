from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
import datetime

MENU_ENTRY = 'Badania z innych laboratoriów'

ADD_TO_ROLE = ['L-PRAC']

SQL = """
    SELECT
		Z.Numer AS NUMERZL,
		W.DataRejestracji AS DATAREJESTRACJI,
		W.Dystrybucja AS DYSTRYBUCJA,
		RE.Symbol AS REJESTRACJA,
		OD.Symbol AS PPOBRAN,
		B.Symbol AS SYMBOLB,
		B.Nazwa AS NAZWAB,
		P.Symbol AS PRACOWNIA,
		(PA.Nazwisko || ' ' || PA.Imiona || ' ' || coalesce(cast(PA.PESEL as varchar(20)),'')) as PACJENT, 
		W.Datarejestracji + (cast(b.czasmaksymalny as decimal(18,6))/cast(24 as decimal(18,6))) as DATAPRZETERMINOWANIA
	FROM Wykonania W
		LEFT OUTER JOIN Zlecenia Z ON Z.ID = W.Zlecenie
		LEFT OUTER JOIN Pacjenci PA on Z.Pacjent = PA.Id and PA.Del = 0 
		LEFT OUTER JOIN Badania B ON B.ID = W.Badanie
		LEFT OUTER JOIN Rejestracje RE on RE.ID = Z.Rejestracja
		LEFT OUTER JOIN Oddzialy OD on OD.ID = Z.Oddzial
		LEFT OUTER JOIN Pracownie P on P.ID = W.Pracownia
	WHERE 
		W.pozamknieciu = 0 and W.Zatwierdzone IS Null and W.anulowane is null and W.BladWykonania is null and
		W.Datarejestracji + (cast((b.czasmaksymalny - 96) as decimal(18,6))/cast(24 as decimal(18,6))) < current_timestamp and
		RE.SYMBOL <> ? 
	ORDER BY W.DataRejestracji, Z.Numer, B.Symbol
"""

SQL_PG = """
    SELECT
		Z.Numer AS NUMERZL,
		W.DataRejestracji AS DATAREJESTRACJI,
		W.Dystrybucja AS DYSTRYBUCJA,
		RE.Symbol AS REJESTRACJA,
		OD.Symbol AS PPOBRAN,
		B.Symbol AS SYMBOLB,
		B.Nazwa AS NAZWAB,
		P.Symbol AS PRACOWNIA,
		(PA.Nazwisko || ' ' || PA.Imiona || ' ' || coalesce(cast(PA.PESEL as varchar(20)),'')) as PACJENT, 
		case when b.czasmaksymalny is not null then
		    w.datarejestracji + interval '1 hour' * b.czasmaksymalny
        else null end as DATAPRZETERMINOWANIA
	FROM Wykonania W
		LEFT OUTER JOIN Zlecenia Z ON Z.ID = W.Zlecenie
		LEFT OUTER JOIN Pacjenci PA on Z.Pacjent = PA.Id and PA.Del = 0 
		LEFT OUTER JOIN Badania B ON B.ID = W.Badanie
		LEFT OUTER JOIN Rejestracje RE on RE.ID = Z.Rejestracja
		LEFT OUTER JOIN Oddzialy OD on OD.ID = Z.Oddzial
		LEFT OUTER JOIN Pracownie P on P.ID = W.Pracownia
	WHERE 
		W.pozamknieciu = 0 and W.Zatwierdzone IS Null and W.anulowane is null and W.BladWykonania is null and
		W.Datarejestracji + ((b.czasmaksymalny-96) * interval '1 hour') < current_timestamp and
		RE.SYMBOL <> %s 
	ORDER BY W.DataRejestracji, Z.Numer, B.Symbol
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="Raport z badań zleconych z innych laboratoriów ALAB do wykonania w wybranej placówce"),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_pojedynczy'
    }
    report.create_task(task)
    report.save()
    return report


def raport_pojedynczy(task_params):
    with get_centrum_connection(task_params['target']) as conn:
        rows = conn.raport_slownikowy(SQL, [task_params['target']], sql_pg=SQL_PG)
    wiersze = []
    przeterminowane = 0
    wszystkie = 0
    teraz = datetime.date.today()
    for row in rows:
        wszystkie += 1
        wiersz = [
            row['datarejestracji'], row['numerzl'], row['rejestracja'], row['ppobran'],
            row['pacjent'],row['symbolb'], row['pracownia'], row['nazwab'], row['dystrybucja'],
            row['dataprzeterminowania']
        ]
        if row['dystrybucja'] is None:
            wiersz.append({'value': 'Przed dystrybucją', 'fontstyle': 'b', 'background': 'yellow'})
            wiersz.append('')
        else:
            wiersz.append('')
            wiersz.append({'value': 'Niewykonane', 'fontstyle': 'b', 'background': 'green'})
        if row['dataprzeterminowania'].date() <= teraz:
            przeterminowane += 1
            wiersz.append({'value': 'Przeterminowane', 'fontstyle': 'b', 'background': 'red'})
        else:
            wiersz.append('')
        wiersze.append(wiersz)
    return {
        'results': [
            {
                'type': 'info',
                'text': 'W sumie %d badań w tym %d przeterminowanych' % (wszystkie, przeterminowane)
            },
            {
                'type': 'table',
                'header': 'Data Rejestracji,Numer,Rejestracja,Punkt Pobrań,Pacjent,Symbol,Pracownia,Nazwa Badania,Dystrybucja,Data Przeterminowania,Przed Dystrybucją,Po Dystrybucji,Przeterminowane'.split(
                    ','),
                'data': prepare_for_json(wiersze)
            }
        ],
        'errors': [],
    }


"""


Legenda
czerwony kolor - badania przeterminowane;
żółty kolor - badania przedystrybucją;
zielony kolor - badania podystrybucji, a niewykonane;

Data Rejestracji	Numer	Rejestracja	Punkt Pobrań	Pacjent	Symbol	Pracownia	Nazwa Badania	
    Dystrybucja	Data Przeterminowania	Przed Dystrybucją	Po Dystrybucji	Przeterminowane

"""
