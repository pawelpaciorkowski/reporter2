
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch
from tasks import TaskGroup, Task
from outlib.xlsx import ReportXlsx
from helpers import prepare_for_json
from datasources.snr import SNR
import base64
import datetime

MENU_ENTRY = 'Płatnicy'

ADD_TO_ROLE = ['R-PM']

LAUNCH_DIALOG = Dialog(title='Eksport płatników z SNR', panel=VBox(
))

SQL = """
    select pl.hs->'umowa' as "Nr K", pl.nip as "NIP", pl.nazwa as "Nazwa", 
	case when pl.aktywny then
		case when pl.hs->'bezrejestracji'='True' then 'Nieużywany' else 'Aktywny' end
		else case when pl.Gotowy then
			case when pl.hs->'douzupelnienia'='True' then 'Do uzupełnienia' else 'Gotowy' end
		else 'Wprowadzany' end
	end as "Status",
	pl.hs->'grupa' as "Grupa",
    c.nazwa as "Cegła", coalesce(pl.hs->'ulica', '') || ' ' || coalesce(pl.hs->'kodpocztowy', '') || ' ' || pl.miejscowosc as "Adres",
    pl.hs->'telefon' as "Telefon", pl.hs->'email' as "E-mail", pl.hs->'osobakontaktowa' as "Osoba do kontaktu",
    case when pl.hs->'fakturyelektroniczne'='True' then 'T' else '' end as "E-faktury",
    pl.hs->'mpk' as "MPK", pl.hs->'zestawienia' as "Zestawienia", pl.hs->'eksporty' as "Eksporty",
    pl.hs->'zestawieniaofl' as "Zestawienia offline", pl.hs->'eksportyofl' as "Eksporty offline",
    pl.hs->'inflacja' as "Podnoszenie cen wg GUS", pl.hs->'niestandardoweustalenia' as "Niestandardowe ustalenia",
    pl.hs->'notatka' as "Notatka wewnętrzna",
    trim(
        case when pl.hs->'osobnospozaumowy'='True' then 'osobno badania spoza umowy, ' else '' end
    ||	case when pl.hs->'rozliczaczbiorczo'='True' then 'rozliczać zbiorczo, ' else '' end
    ||	case when pl.hs->'dzielicnaumowy'='True' then 'dzielić na umowy, ' else '' end
    ||	case when pl.hs->'dzielicnaaneksy'='True' then 'dzielić na aneksy, ' else '' end
    ||	case when pl.hs->'dzielicnalaboratoria'='True' then 'dzielić na laboratoria, ' else '' end
    ||	case when pl.hs->'dzielicnagrupyzleceniodawcow'='True' then 'dzielić na grupy zleceniodawców, ' else '' end
    ||	case when pl.hs->'dzielicnazleceniodawcow'='True' then 'dzielić na zleceniodawców, ' else '' end
    ||	case when pl.hs->'dzielicnagrupybadan'='True' then ('dzielić na grupy badań: ' || coalesce(pl.hs->'osobnogrupybadan', '') || ', ') else '' end
    ||	case when pl.hs->'uwagidofaktur'!='' then 'uwagi do faktur: ' || coalesce(pl.hs->'uwagidofaktur', '') || ', ' else '' end
    , ', ') as "Ustalenia finansowe",
    array_to_string(array_agg(
        um1.identyfikatorwrejestrze || ' wyst. ' || um1.datawystawienia
        || case when coalesce(um1.hs->'cennikinflacja', '') != '' then ' cennik autoaktualizacji: ' || coalesce(um1.hs->'cennikinflacja', '') else '' end
    ), '; ') as "Umowy",
    array_to_string(array_agg(
        um2.identyfikatorwrejestrze || ' wyst. ' || um2.datawystawienia
        || case when coalesce(um2.hs->'cennikinflacja', '') != '' then ' cennik autoaktualizacji: ' || coalesce(um2.hs->'cennikinflacja', '') else '' end
    ), '; ') as "Aneksy",
    array_to_string(array_agg(
        um3.identyfikatorwrejestrze || ' wyst. ' || um3.datawystawienia
        || case when coalesce(um3.hs->'cennikinflacja', '') != '' then ' cennik autoaktualizacji: ' || coalesce(um3.hs->'cennikinflacja', '') else '' end
    ), '; ') as "Poza umową",
    trim(coalesce(prz.nazwisko, '') || ' ' || coalesce(prz.imiona, '')) as przedstawiciel
    from platnicy pl
    left join cegly c on c.id=pl.hs->'cegla'
    left join umowy um1 on um1.platnik=pl.id and not um1.del and (um1.dodnia is null or um1.dodnia >= 'NOW') and um1.rejestr='UMOWY'
    left join umowy um2 on um2.platnik=pl.id and not um2.del and (um2.dodnia is null or um2.dodnia >= 'NOW') and um2.rejestr='ANEKSY'
    left join umowy um3 on um3.platnik=pl.id and not um3.del and (um3.dodnia is null or um3.dodnia >= 'NOW') and um3.rejestr='POZAUMOW'
    left join pracownicy prz on prz.id=pl.hs->'przedstawiciel'
    where not pl.del
    group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,24
"""

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'eksport_snr'
    }
    report.create_task(task)
    report.save()
    return report


def eksport_snr(task_params):
    snr = SNR()
    cols, rows = snr.select(SQL)
    rep = ReportXlsx({'results': [{
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    }]})
    return {
        'type': 'download',
        'content': base64.b64encode(rep.render_as_bytes()).decode(),
        'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'filename': 'platnicy_snr_%s.xlsx' % datetime.datetime.now().strftime('%Y%m%d'),
    }
