import base64
from dialog import (
    Dialog,
    VBox,
    TextInput,
    InfoText,
    DateInput,
    ValidationError,
)
from tasks import TaskGroup
from helpers.validators import validate_date_range, validate_symbol
from helpers import (
    prepare_for_json,
    get_centrum_connection,
    get_snr_connection, empty, slugify,
    list_from_space_separated
)
from outlib.xlsx import ReportXlsx

MENU_ENTRY = "CMP"

LAUNCH_DIALOG = Dialog(
    title=MENU_ENTRY,
    panel=VBox(
        InfoText(
            text="Proszę datę wygenerowania rozliczenia, aby pobrać zestawienie dla płatnika."
        ),
        DateInput(field="data", title="Data rozliczenia", default="T"),
        TextInput(field="ident", title="Identyfikator rozliczenia"),
        TextInput(field="platnik", title="Symbol płatnika"),
        TextInput(field="nipy", title="NIPy płatników (oddzielone spacjami)"),  # 1230955789
    ),
)

SQL_SNR = f"""
select
    w.datarejestracji as "Data rejestracji",
    w.hs->'numer' as "Numer zlecenia",
    w.hs->'zewnetrznyidentyfikator' as "Numer zewnętrzny",
    w.hs->'zleceniodawcazlecenia' as "Punkt pobrań - symbol",
    Z.nazwa as "Punkt pobrań - nazwa",
    '' as "Grupa punktów pobrań - symbol",
    '' as "Grupa punktów pobrań - nazwa",
    PWL.symbol as "Płatnik - symbol",
    P.nazwa as "Płatnik - nazwa",
    pwl.hs->'grupa' as "Grupa płatników - symbol",
    pkg.nazwa as "Grupa płatników - nazwa",
    substring(w.pacjent,1,position('^' in w.pacjent)-1) as "Pacjent - ID",
    w.hs->'pacjencinazwisko' as "Pacjent - nazwisko",
    w.hs->'pacjenciimiona' as "Pacjent - imiona",
    '' as "Pacjent - adres",
    w.hs->'pacjencipesel' as "Pacjent - PESEL",
    w.hs->'pacjencidataurodzenia' as "Pacjent - data urodzenia",
    w.hs->'pacjenciplec' as "Pacjent - Płeć",
    '' as "Pacjent - historia choroby",
    '' as "Status pacjenta - Symbol",
    '' as "Status pacjenta - Nazwa",
    substring(w.lekarz,1,position('^' in w.lekarz)-1) as "Lekarz - ID",
    w.hs->'lekarzenazwisko' as "Lekarz - nazwisko",
    w.hs->'lekarzeimiona' as "Lekarz - imiona",
    w.hs->'lekarzenumer' as "Lekarz - numer stat",
    w.badanie as "Badanie - symbol",
    pkb.nazwa as "Badanie - nazwa",
    pkb.hs->'kod' as "Badanie - kod ICD",
    pkb.hs->'grupa' as "Grupa badań - symbol",
    pkgb.nazwa as "Grupa badań - nazwa",
    w.material as "Materiał - symbol",
    pkm.nazwa as "Materiał - nazwa",
    W.nettodlaplatnika as "Cena",
    '1' as "Płatne",
   case when w.jestpakietem then '1' else '0' end as "Pakiet",
    case when concat(
        substring(w.hs->'godzinapobrania'::varchar(20),0,5), '-',
        substring(w.hs->'godzinapobrania'::varchar(20),5,2), '-',
        substring(w.hs->'godzinapobrania'::varchar(20),7,2), ' ',
        substring(w.hs->'godzinapobrania'::varchar(20),9,2), ':',
        substring(w.hs->'godzinapobrania'::varchar(20),11,2), ':',
        substring(w.hs->'godzinapobrania'::varchar(20),13,2)
    )  = '-- ::' then '' else concat(
        substring(w.hs->'godzinapobrania'::varchar(20),0,5), '-',
        substring(w.hs->'godzinapobrania'::varchar(20),5,2), '-',
        substring(w.hs->'godzinapobrania'::varchar(20),7,2), ' ',
        substring(w.hs->'godzinapobrania'::varchar(20),9,2), ':',
        substring(w.hs->'godzinapobrania'::varchar(20),11,2), ':',
        substring(w.hs->'godzinapobrania'::varchar(20),13,2)
    ) end as "Godzina Pobrania",
    PR.Nazwisko as "Zarejestrowane przez",
    w.hs->'kodkreskowy' as "Kod Kreskowy",
    w.wykonanie
    from pozycjerozliczen pz 
    left outer join wykonania w on pz.wykonanie = w.id
    left outer join Platnicy P on W.platnik = P.ID
    left outer join Platnicywlaboratoriach Pwl on PWL.laboratorium = w.laboratorium and PWL.platnik = P.ID  and not pwl.del
    left outer join pozycjekatalogow pkg on pkg.symbol =  pwl.hs->'grupa' and pkg.katalog = 'GRUPYPLATNIKOW'
    left outer join zleceniodawcy z on W.Zleceniodawca = Z.ID
    left outer join pozycjekatalogow pkb on pkb.symbol=w.badanie and pkb.katalog = 'BADANIA'
    left outer join pozycjekatalogow pkgb on pkgb.symbol=pkb.hs->'grupa' and pkgb.katalog = 'GRUPYBADAN'
    left outer join pozycjekatalogow pkm on pkm.symbol=w.material and pkm.katalog = 'MATERIALY'
    left outer join pracownicy pr on pr.id=w.pc
    where pz.rozliczenie = %s
      and not W.bezplatne
    and (pkb.hs->'grupa') is distinct from 'TECHNIC'
    and not w.jestpakietem
"""

SQL_CENTRUM = f"""
    select
        w.system, w.sysid, w.zatwierdzone, p.symbol, trim(gb.symbol) as grupa, trim(prac.nazwisko) as pracownik
    from wykonania w
    left join platnicy p on p.id = w.platnik
    left join badania b on b.id=w.badanie
    left join grupybadan gb on gb.id=b.grupa
    left join pracownicy prac on prac.id=w.pracownikodrejestracji
    where w.rozliczone between ? and ?
    and p.symbol in ($PLATNICY$)
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    nipy = list_from_space_separated(params['nipy'], also_comma=True, also_semicolon=True, unique=True)
    if params["data"] is None:
        raise ValidationError("Nie podano daty")
    if empty(params['ident']) and empty(params['platnik']) and len(nipy) == 0:
        raise ValidationError("Nie podano danych rozliczenia ani płatnika")
    sql = """select r.id, pwl.symbol, l.symbol as lab, 
                r.oddnia::varchar as oddnia, r.dodnia::varchar as dodnia, r.identyfikatorwrejestrze, f.numer, l.vpn 
            from rozliczenia r
            left join faktury f on f.rozliczenie=r.id
            left join laboratoria l on l.symbol=r.laboratorium
            left join platnicy pl on pl.id=r.platnik
            left join platnicywlaboratoriach pwl on pwl.laboratorium=l.symbol and pwl.platnik=r.platnik
            where r.datarozliczenia = %s and not r.del"""

    sql_params = [params["data"]]
    if not empty(params["ident"]):
        sql += " and r.identyfikatorwrejestrze = %s"
        sql_params.append(params["ident"])

    if not empty(params["platnik"]):
        sql += " and pwl.symbol = %s"
        sql_params.append(params["platnik"])

    if len(nipy) > 0:
        sql += " and pl.nip in %s"
        sql_params.append(tuple(nipy))

    with get_snr_connection() as snr:
        rozliczenia = snr.dict_select(sql, sql_params)
        if len(rozliczenia) == 0:
            raise ValidationError(
                "Nie znaleziono rozliczenia dla podanego laboratorium, daty (i identyfikatora)"
            )
    params_centrum = {}
    dane_rozliczen = {}
    for rozl in rozliczenia:
        lab = rozl['lab']
        if lab not in params_centrum:
            params_centrum[lab] = {
                'oddnia': None, 'dodnia': None, 'platnicy': []
            }
        if params_centrum[lab]['oddnia'] is None or params_centrum[lab]['oddnia'] > rozl['oddnia']:
            params_centrum[lab]['oddnia'] = rozl['oddnia']
        if params_centrum[lab]['dodnia'] is None or params_centrum[lab]['dodnia'] < rozl['dodnia']:
            params_centrum[lab]['dodnia'] = rozl['dodnia']
        validate_symbol(rozl['symbol'])
        if rozl['symbol'] not in params_centrum[lab]['platnicy']:
            params_centrum[lab]['platnicy'].append(rozl['symbol'])
        dane_rozliczen[rozl['id']] = {
            'id': rozl['id'],
            'lab': rozl['lab'],
            'numer': rozl['numer'],
            'identyfikatorwrejestrze': rozl['identyfikatorwrejestrze'],
        }
    for lab, lab_params in params_centrum.items():
        lab = lab[:7]
        try:
            validate_date_range(lab_params['oddnia'], lab_params['dodnia'], 90)
        except ValidationError:
            raise ValidationError("Dla labu %s zakres danych większy niż 90 dni - nie można wykonać raportu" % lab)
        task = {
            "type": "centrum",
            "priority": 1,
            "target": lab,
            "timeout": 2400,
            "params": lab_params,
            "function": "raport_centrum",
        }
        report.create_task(task)
    for _, snr_params in dane_rozliczen.items():
        task = {"type": "snr", "priority": 1, "params": snr_params, "function": "raport_snr"}
        report.create_task(task)
    report.save()
    return report


def raport_snr(task_params):
    params = task_params["params"]
    with get_snr_connection() as snr:
        cols, rows = snr.select(SQL_SNR, [params["id"]])
    params['rows'] = rows
    return params


def raport_centrum(task_params):
    params = task_params["params"]
    system = task_params["target"]
    sql = SQL_CENTRUM
    sql_params = (
        params["oddnia"],
        params["dodnia"],
    )
    sql = sql.replace('$PLATNICY$', ', '.join("'%s'" % symbol for symbol in params['platnicy']))
    with get_centrum_connection(system) as centrum:
        coll, rows = centrum.raport_z_kolumnami(sql, sql_params)
    return rows


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    wszystkie_dane_centrum = {}
    wszystkie_dane_snr = []
    results = []
    errors = []
    for job_id, task_params, status, result in task_group.get_tasks_results():
        if status == "finished" and result is not None:
            if task_params["function"] == "raport_centrum":
                wszystkie_dane_centrum[task_params['target']] = result
            elif task_params["function"] == "raport_snr":
                wszystkie_dane_snr.append(result)
    if task_group.progress == 1.0:
        print(wszystkie_dane_centrum.keys())
        for dane_snr in wszystkie_dane_snr:
            dane_centrum = wszystkie_dane_centrum[dane_snr['lab']]
            rap = RaportCMP(dane_centrum, dane_snr['rows'])
            raport_xlsx = ReportXlsx({"results": [{
                "type": "table",
                "header": rap.get_header(),
                "data": prepare_for_json(rap.dane_z_zatwierdzeniem()),
            }]})
            fn = 'Raport_CMP_%s.xlsx' % slugify(dane_snr['numer'] if dane_snr['numer'] is not None else dane_snr['id'])
            results.append({
                "type": "download",
                "content": base64.b64encode(raport_xlsx.render_as_bytes()).decode(),
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "filename": fn,
            })
    return {
        "results": results,
        "progress": task_group.progress,
        "actions": [],
        "errors": errors,
    }


class RaportCMP:
    def __init__(self, centrum_data, snr_data) -> None:
        self.data_zatwierdzenia = None
        self.dorejestrowane_recznie = None
        self.zarejestrowane_przez = None
        self.centrum_data = centrum_data
        self.snr_data = snr_data
        self.zbierz_daty_zatwierdzenia()

    def zbierz_daty_zatwierdzenia(self):
        self.daty_zatwierdzenia = {}
        self.dorejestrowane_recznie = {}
        self.zarejestrowane_przez = {}
        for row in self.centrum_data:
            ident = "%d^%s" % (row[1], row[0].strip())
            grupa = row[4]
            prac = row[5]
            dorejestrowane = True
            if prac is not None and prac.startswith('hl7'):
                dorejestrowane = False
            if prac == '(system)' and grupa == 'TECHNIC':
                dorejestrowane = False
            self.daty_zatwierdzenia[ident] = row[2]
            self.dorejestrowane_recznie[ident] = 'T' if dorejestrowane else ''
            self.zarejestrowane_przez[ident] = prac

    def get_header(self):
        return [
            "Data rejestracji",
            "Numer zlecenia",
            "Numer zewnętrzny",
            "Punkt pobrań - symbol",
            "Punkt pobrań - nazwa",
            "Grupa punktów pobrań - symbol",
            "Grupa punktów pobrań - nazwa",
            "Płatnik - symbol",
            "Płatnik - nazwa",
            "Grupa płatników - symbol",
            "Grupa płatników - nazwa",
            "Pacjent - ID",
            "Pacjent - nazwisko",
            "Pacjent - imiona",
            "Pacjent - adres",
            "Pacjent - PESEL",
            "Pacjent - data urodzenia",
            "Pacjent - Płeć",
            "Pacjent - historia choroby",
            "Status pacjenta - Symbol",
            "Status pacjenta - Nazwa",
            "Lekarz - ID",
            "Lekarz - nazwisko",
            "Lekarz - imiona",
            "Lekarz - numer stat",
            "Badanie - symbol",
            "Badanie - nazwa",
            "Badanie - kod ICD",
            "Grupa badań - symbol",
            "Grupa badań - nazwa",
            "Materiał - symbol",
            "Materiał - nazwa",
            "Cena",
            "Płatne",
            "Pakiet",
            "Godzina Pobrania",
            "Zarejestrowane przez",
            "Kod Kreskowy",
            "Data zatwierdzenia",
            "Dorejestrowane ręcznie"
        ]

    def dane_z_zatwierdzeniem(self):
        res = []
        for row in self.snr_data:
            row = list(row)
            ident = row[-1]
            date = self.daty_zatwierdzenia.get(ident, 'BRAK DANYCH W CENTRUM')
            row[-3] = self.zarejestrowane_przez.get(ident, 'BRAK DANYCH W CENTRUM')
            row[-1] = date
            row.append(self.dorejestrowane_recznie.get(ident, ''))
            res.append(row)
        return res
