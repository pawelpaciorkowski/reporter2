from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from outlib.xlsx import ReportXlsx
from helpers import prepare_for_json
from datasources.snr import SNR
import base64
import datetime

MENU_ENTRY = 'Niezgodni płatnicy'

LAUNCH_DIALOG = Dialog(title='Niezgodni płatnicy w SNR', panel=VBox(
    InfoText(text='''Raport przedstawia wykonania z bazy SNR, z płatnikiem niezgodnym ze zleceniodawcą,
        z pominięciem grup płatników ALAB i SZAL. Przy wykonaniach wymienione są rozliczenia i faktury, w których występują.
        Raport wg dat rozliczeniowych. Zwraca max 1000 wykonań.'''),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa', default='PZT'),
    DateInput(field='datado', title='Data końcowa', default='KZT'),
))

SQL = """
    select a.laboratorium, a."Data rejestracji", a."Numer", a."Kod kreskowy", a."Zleceniodawca", a."Płatnik", a."Płatnik zleceniodawcy",
        a."Data rozliczeniowa", a.badanie, a.material, a.bladwykonania, a.powodanulowania, a."Płatne", a."Netto dla płatnika",
        a.statusprzeliczenia as "Status przeliczenia", a.statusrozliczenia as "Status rozliczenia",
        a."Godzina rozliczenia", sum(case when a.pozycjarozliczenia='--BRAK--' then 0 else 1 end) as "Ile rozliczeń",
        array_to_string(array_agg(case when a.pozycjarozliczenia != '--BRAK--' then
    'Rozl. ' || rozl.identyfikatorwrejestrze || ' z ' || rozl.datarozliczenia 
    || (
        case when rozl.faktura is not null then
        ' Faktura nr ' || fakt.numer
        else ' BRAK FAKTURY' end
    ) || ' na ' || plr.nazwa || ' ' || (plr.hs->'umowa') || ' ' || plr.nip 
    else null end), '; ') as "Rozliczenia i faktury"
    
    from (select w.laboratorium, w.datarejestracji as "Data rejestracji", w.hs->'numer' as "Numer", w.hs->'kodkreskowy' as "Kod kreskowy",
            coalesce(zwl.symbol, '---') || ' - ' || zl.nazwa as "Zleceniodawca",
            coalesce(pwl.symbol, '---') || ' - ' || pl.nazwa || ' ' || (pl.hs->'umowa') || ' ' || pl.nip as "Płatnik",
            plz.nazwa || ' ' || (plz.hs->'umowa') || ' ' || plz.nip as "Płatnik zleceniodawcy",
            w.datarozliczeniowa as "Data rozliczeniowa",
            w.badanie, w.material, w.bladwykonania, w.powodanulowania, case when w.bezplatne then 'N' else 'T' end as "Płatne",
            w.nettodlaplatnika as "Netto dla płatnika", w.statusprzeliczenia, w.statusrozliczenia, w.godzinarozliczenia as "Godzina rozliczenia",
            unnest(string_to_array(coalesce(w.pozycjerozliczen, '--BRAK--'), ' ')) as pozycjarozliczenia
        from wykonania w
        left join platnicy pl on pl.id=w.platnik
        left join zleceniodawcy zl on zl.id=w.zleceniodawca
        left join platnicy plz on plz.id=w.platnikzleceniodawcy
        left join zleceniodawcywlaboratoriach zwl on zwl.zleceniodawca=zl.id and zwl.laboratorium=w.laboratorium and not zwl.del
        left join platnicywlaboratoriach pwl on pwl.platnik=pl.id and pwl.laboratorium=w.laboratorium and not pwl.del
        
        where w.datarozliczeniowa between %s and %s and w.laboratorium in %s
        and w.platnik is not null and w.platnikzleceniodawcy is not null and w.platnikzleceniodawcy != w.platnik
        and pl.hs->'grupa' not in ('ALAB', 'SZAL') and not pl.gotowkowy and not plz.gotowkowy
        limit 1000
    ) a
    left join pozycjerozliczen pr on pr.id=a.pozycjarozliczenia
    left join rozliczenia rozl on rozl.id=pr.rozliczenie
    left join faktury fakt on fakt.id=rozl.faktura
    left join platnicy plr on plr.id=rozl.platnik
    
    group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Wybierz co najmniej 1 lab")
    validate_date_range(params['dataod'], params['datado'], 7)
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
    snr = SNR()
    cols, rows = snr.select(SQL, [params['dataod'], params['datado'], tuple(params['laboratoria'])])
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    }
