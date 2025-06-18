from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task

MENU_ENTRY = 'Wykaz udzielonych rabatów'

REQUIRE_ROLE = ['L-KIER', 'C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="Wykaz rabatów udzielonych w sprzedaży gotówkowej"),
    DateInput(field='dataod', title='Data początkowa', default='-7D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
))

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)
    for lab in params['laboratoria']:
        task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'raport_pojedynczy'
        }
        report.create_task(task)
    report.save()
    return report



def raport_pojedynczy(task_params):
    params = task_params['params']
    with get_centrum_connection(task_params['target']) as conn:
        cols, rows = conn.raport_z_kolumnami("""
        select
            sp.symbol as SS,
            sp.nazwa as SN,
            z.DATAREJESTRACJI as DATA, 
            z.numer as NR,
			p.NAZWISKO as RE,
			k.symbol as KS,
			k.nazwa as KN,
			coalesce(pa.nazwisko, '') || ' ' || coalesce(pa.imiona, '') as PACJENT,
			b.symbol as BS, b.nazwa as BN, 
			b.pakiet as PAK,
			w.cena as WART
		from zlecenia z
			left outer join pracownicy p on p.id = z.pracownikodrejestracji
			left outer join PACJENCI pa on pa.id = z.PACJENT
			left outer join kanaly k on k.id = p.kanalinternetowy
			left outer join platnicy pl on pl.id =z.platnik
			left outer join wykonania w on w.zlecenie=z.id
			left outer join Badania B on w.badanie = b.id
			left outer join GrupyBadan GB on GB.Id = B.Grupa
			left outer join GrupyPlatnikow GP on GP.Id = pl.Grupa
			left outer join STATUSYPACJENTOW sp on sp.id=z.STATUSPACJENTA
		where z.datarejestracji between ? and ? and z.STATUSPACJENTA is not null and w.TARYFA is not null
		and z.pracownikodrejestracji is not null and w.anulowane is null and w.platne = '1' and (GB.Symbol != 'TECHNIC' or GB.Symbol is null)
		order by sp.SYMBOL, p.NAZWISKO, z.DATAREJESTRACJI
        """, [params['dataod'], params['datado']])
        return {
            'title': task_params['target'],
            'type': 'table',
            'header': 'Symbol rabatu,Nazwa rabatu,Data Rejestracji,Numer,Osoba rejestrująca,Symbol miejsca rej.,Nazwa miejsca rej.,Pacjent,Symbol badania,Nazwa badania,Pakiet,Cena po rabacie'.split(
                ','),
            'data': prepare_for_json(rows)
        }
