from datasources.snrkonf import SNRKonf
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from outlib.xlsx import ReportXlsx
from helpers import prepare_for_json
from datasources.snr import SNR
import base64
import datetime

MENU_ENTRY = 'Rozliczenia i faktury do badań'

SQL_ORG = """
    select rozl.datarozliczenia as "Data rozliczenia",
        rozl.identyfikatorwrejestrze as "Nr rozliczenia",
        pwl.symbol as "Płatnik",
        pl.nazwa as "Płatnik nazwa",
        pl.nip as "NIP",
        pl.hs->'umowa' as "Ident płatnika",
        f.numer as "Faktura",
        sum(case when wyk.badanie='2019COV' then 1 else 0 end) as "Ilość 2019COV",
        sum(case when wyk.badanie='19COVA' then 1 else 0 end) as "Ilość 19COVA",
        sum(case when wyk.badanie='19COVN' then 1 else 0 end) as "Ilość 19COVN",
        min(case when wyk.badanie='2019COV' then pr.netto else null end) as "2019COV min netto", 
        max(case when wyk.badanie='2019COV' then pr.netto else null end) as "2019COV max netto", 
        min(case when wyk.badanie='19COVA' then pr.netto else null end) as "19COVA min netto", 
        max(case when wyk.badanie='19COVA' then pr.netto else null end) as "19COVA max netto", 
        min(case when wyk.badanie='19COVN' then pr.netto else null end) as "19COVN min netto", 
        max(case when wyk.badanie='19COVN' then pr.netto else null end) as "19COVN max netto", 
        sum(pr.netto) as "Suma netto rozliczenia",
        (select sum(pf.kwotanetto) from pozycjefaktur pf where pf.faktura=f.id and not pf.del) as "Suma netto faktury"

    from rozliczenia rozl
    left join pozycjerozliczen pr on pr.rozliczenie=rozl.id
    left join wykonania wyk on wyk.id=pr.wykonanie
    left join platnicy pl on pl.id=rozl.platnik
    left join platnicywlaboratoriach pwl on pwl.platnik=pl.id and pwl.laboratorium=rozl.laboratorium and not pwl.del
    left join faktury f on f.rozliczenie=rozl.id

    where rozl.datarozliczenia between '2020-05-01' and '2021-01-31' and not rozl.del and not pr.del and not f.del
    and wyk.badanie in ('2019COV', '19COVA', '19COVN')
    group by 1, 2, 3, 4, 5, 6, 7, f.id
    order by 1, 2
"""

SQL = """
    select rozl.datarozliczenia as "Data rozliczenia",
        rozl.identyfikatorwrejestrze as "Nr rozliczenia",
        rozl.laboratorium as "Laboratorium",
        pwl.symbol as "Płatnik",
        pl.nazwa as "Płatnik nazwa",
        pl.nip as "NIP",
        pl.hs->'umowa' as "Ident płatnika",
        f.numer as "Faktura",
        $ILOSCI_CENY_BADAN$,
        sum(pr.netto) as "Suma netto rozliczenia",
        (select sum(pf.kwotanetto) from pozycjefaktur pf where pf.faktura=f.id and not pf.del) as "Suma netto faktury"

    from rozliczenia rozl
    left join pozycjerozliczen pr on pr.rozliczenie=rozl.id
    left join wykonania wyk on wyk.id=pr.wykonanie
    left join platnicy pl on pl.id=rozl.platnik
    left join platnicywlaboratoriach pwl on pwl.platnik=pl.id and pwl.laboratorium=rozl.laboratorium and not pwl.del
    left join faktury f on f.rozliczenie=rozl.id

    where rozl.datarozliczenia between %s and %s and not rozl.del and not pr.del and not f.del
    and wyk.badanie in ($BADANIA$) and rozl.laboratorium in ($LABORATORIA$)
    group by 1, 2, 3, 4, 5, 6, 7, 8, f.id
    order by 1, 2
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text='''Raport przedstawia rozliczenia zawierające wskazane badania, ilości i zakres cen badań
        na rozliczeniu i wartość całej faktury, jeśli została wystawiona do rozliczenia.
        Raport wg dat wygenerowania rozliczeń'''),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria', replikacje=True, symbole_snr=True),
    TextInput(field='badania', title='Symbole badań oddzielone spacją'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if len(params['laboratoria']) == 0:
        raise ValidationError('Nie wybrano żadnego laboratorium')
    validate_date_range(params['dataod'], params['datado'], 31)
    badania = []
    snrkonf = SNRKonf()
    for bad in (params['badania'] or '').replace(',', ' ').upper().split(' '):
        bad = bad.strip()
        if bad == '':
            continue
        if len(snrkonf.dict_select("select id from badania where symbol=%s and not del", [bad])) == 0:
            raise ValidationError("Nie znaleziono badania %s" % bad)
        badania.append(bad)
    if len(badania) == 0:
        raise ValidationError('Nie wybrano żadnego badania')
    params['badania'] = badania
    report = TaskGroup(__PLUGIN__, params)
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
    sql = SQL
    ilosci_ceny_badan = []
    for bad in params['badania']:
        ilosci_ceny_badan.append("sum(case when wyk.badanie='%s' then 1 else 0 end) as \"Ilość %s\"" % (bad, bad))
    for bad in params['badania']:
        ilosci_ceny_badan.append("min(case when wyk.badanie='%s' then pr.netto else null end) as \"%s min netto\"" % (bad, bad))
        ilosci_ceny_badan.append("max(case when wyk.badanie='%s' then pr.netto else null end) as \"%s max netto\"" % (bad, bad))
    sql = sql.replace('$ILOSCI_CENY_BADAN$', ','.join(ilosci_ceny_badan))
    sql = sql.replace('$BADANIA$', ', '.join(["'%s'" % l for l in params['badania']]))
    sql = sql.replace('$LABORATORIA$', ', '.join(["'%s'" % l for l in params['laboratoria']]))
    snr = SNR()
    cols, rows = snr.select(sql, [params['dataod'], params['datado']])
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    }
