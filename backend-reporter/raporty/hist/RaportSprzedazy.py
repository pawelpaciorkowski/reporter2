from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_bank_krwi_connection, get_snr_connection

MENU_ENTRY = 'Raport ze sprzedaży'

SQL_WYKONANIA = """
	select 
		w.laboratorium, 
		Pwl.symbol as "Płatnik", P.nazwa as "Płatnik nazwa", p.hs->'grupa' as "Grupa płatnika", p.hs->'umowa' as "Nr K",
		u.centrumrozliczeniowe as "Centr.Rozl.", 
		plz.nazwa as "Płatnik zleceniodawcy",
		plz.hs->'grupa' as "Grupa pł.zlec.", plz.hs->'umowa' as "Nr K pł.zlec.",
		coalesce(zl.hs->'kodpocztowydzialalnosci', plz.hs->'kodpocztowydzialalnosci') as "Kod poczt. dział.",
		(select pow.wojewodztwo
        from kodypocztowe kp
        left join powiaty pow on pow.symbol=substring(kp.wojewodztwoipowiat from 1 for 4)
        where kod=coalesce(zl.hs->'kodpocztowydzialalnosci', plz.hs->'kodpocztowydzialalnosci')
        limit 1) as "Województwo dział.",
		pr.nazwisko as "Przedstawiciel",
		w.badanie as "BADANIE", pk.hs->'grupa' as "Grupa badań", pk.hs->'grupadorejestracji' as "Grupa do rej.", 
		count(W.id) as "ILOSC", sum(w.nettodlaplatnika) as "WARTOSC"
    from Wykonania W
		left outer join Platnicy P on W.platnik = P.ID
		left join zleceniodawcy zl on zl.id=w.zleceniodawca
		left join platnicy plz on plz.id=zl.platnik
		left join Umowy u on U.ID = W.Umowa
		left outer join Platnicywlaboratoriach Pwl on PWL.laboratorium = w.laboratorium and PWL.platnik = P.ID and not pwl.del
		left outer join pozycjekatalogow pk on pk.symbol=w.badanie and pk.katalog = 'BADANIA'
		left join pracownicy pr on pr.id=p.hs->'przedstawiciel'
	where
		w.datarozliczeniowa between %s and %s
		and pk.hs->'grupa' in ('HISTOPA', 'HIS-ALA')
		and not W.bezPlatne and not w.jestpakietem and (p.hs->'grupa') is distinct from 'ALAB'
	group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
	order by W.laboratorium, P.nazwa, w.badanie; 
"""

LAUNCH_DIALOG = Dialog(title='Sprzedaż badań histopatologicznych', panel=VBox(
    DateInput(field='dataod', title='Data od', default='PZM'),
    DateInput(field='datado', title='Data do', default='KZM'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 31)

    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'raport_snr'
    }
    report.create_task(task)
    report.save()
    return report


def raport_snr(task_params):
    params = task_params['params']
    snr = get_snr_connection()
    cols, rows = snr.select(SQL_WYKONANIA, [params['dataod'], params['datado']])
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    }
