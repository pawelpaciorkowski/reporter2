from dialog import (
    Dialog,
    Panel,
    HBox,
    VBox,
    TextInput,
    LabSelector,
    PracowniaSelector,
    TabbedView,
    Tab,
    InfoText,
    DateInput,
    Select,
    Radio,
    ValidationError,
    Switch,
)
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers.connections import get_centra, get_db_engine

MENU_ENTRY = "Ile zarejestrowanych / wykonanych"

REQUIRE_ROLE = ["C-FIN", "C-CS", "PP-S"]


SQL = """
    select $POLA$, 
        sum(zarejestrowane) as zarejestrowane, sum(przyjete) as przyjete,
        sum(anulowane) as anulowane, sum(zabledowane) as zabledowane,
        sum(wykonane) as wykonane,
        sum(oczekujace_zarejestrowane) as oczekujace_zarejestrowane,
        sum(oczekujace_przyjete) as oczekujace_przyjete
    from (
    select 
        '$LAB$' as lab,
        cast(w.godzinarejestracji as date) as DataRejestracji,
        cast(w.godzina as date) as DataPobrania,
        pl.symbol as platnik, pl.nazwa as platnik_nazwa,
        o.symbol as zleceniodawca, o.nazwa as zleceniodawca_nazwa,
        pr.symbol as pracownia, pr.nazwa as pracownia_nazwa,
        mat.symbol as material, mat.nazwa as material_nazwa,
        bad.symbol as badanie, bad.nazwa as badanie_nazwa,
        count(W.id) as zarejestrowane,
        sum(case when W.Dystrybucja is not null then 1 else 0 end) as przyjete,
        sum(case when W.Anulowane is not null then 1 else 0 end) as anulowane,
        sum(case when W.BladWykonania is not null then 1 else 0 end) as zabledowane,
        sum(case when W.Anulowane is null and W.BladWykonania is null and W.Zatwierdzone is not null then 1 else 0 end) as wykonane,
        sum(case when W.Anulowane is null and W.BladWykonania is null and W.Zatwierdzone is null then 1 else 0 end) as oczekujace_zarejestrowane,
        sum(case when W.Dystrybucja is not null and W.Anulowane is null and W.BladWykonania is null and W.Zatwierdzone is null then 1 else 0 end) as oczekujace_przyjete,
        sum(case when W.Anulowane is null and W.BladWykonania is null and W.Zatwierdzone is not null 
            and (coalesce(w.podpisane, w.wydrukowane)-w.dystrybucja > 1) then 1 else 0 end) as podpisane_przeterminowane
    from wykonania W
        left outer join Pracownie Pr on Pr.Id = W.Pracownia 
        left outer join Materialy Mat on Mat.Id = W.Material
        left outer join GrupyPracowni GP on GP.Id = Pr.Grupa 
        left outer join zlecenia z on z.id=w.zlecenie 
        left join oddzialy o on o.id=z.oddzial
        left join platnicy pl on pl.id=z.platnik
        left join grupyplatnikow gpl on gpl.id=pl.grupa
        left outer join typyzlecen tz on tz.id = z.typzlecenia 
        left join badania bad on bad.id=w.badanie
    where W.godzinarejestracji between ? and ? and W.Badanie in ($BADANIA$)
        and $WARUNKI$
    group by cast(w.godzinarejestracji as date), cast(w.godzina as date), o.symbol, pl.symbol, o.nazwa, pl.nazwa, pr.symbol, pr.nazwa, bad.symbol, bad.nazwa, mat.symbol, mat.nazwa
    ) as a
    group by $POLA$ order by $POLA$
"""

SQL_PSQL = """
    select $POLA$, 
        sum(zarejestrowane) as zarejestrowane, sum(przyjete) as przyjete,
        sum(anulowane) as anulowane, sum(zabledowane) as zabledowane,
        sum(wykonane) as wykonane,
        sum(oczekujace_zarejestrowane) as oczekujace_zarejestrowane,
        sum(oczekujace_przyjete) as oczekujace_przyjete
    from (
    select 
        '$LAB$' as lab,
        cast(w.godzinarejestracji as date) as DataRejestracji,
        cast(w.godzina as date) as DataPobrania,
        pl.symbol as platnik, pl.nazwa as platnik_nazwa,
        o.symbol as zleceniodawca, o.nazwa as zleceniodawca_nazwa,
        pr.symbol as pracownia, pr.nazwa as pracownia_nazwa,
        mat.symbol as material, mat.nazwa as material_nazwa,
        bad.symbol as badanie, bad.nazwa as badanie_nazwa,
        count(W.id) as zarejestrowane,
        sum(case when W.Dystrybucja is not null then 1 else 0 end) as przyjete,
        sum(case when W.Anulowane is not null then 1 else 0 end) as anulowane,
        sum(case when W.BladWykonania is not null then 1 else 0 end) as zabledowane,
        sum(case when W.Anulowane is null and W.BladWykonania is null and W.Zatwierdzone is not null then 1 else 0 end) as wykonane,
        sum(case when W.Anulowane is null and W.BladWykonania is null and W.Zatwierdzone is null then 1 else 0 end) as oczekujace_zarejestrowane,
        sum(case when W.Dystrybucja is not null and W.Anulowane is null and W.BladWykonania is null and W.Zatwierdzone is null then 1 else 0 end) as oczekujace_przyjete,
        sum(case when W.Anulowane is null and W.BladWykonania is null and W.Zatwierdzone is not null 
            and (extract(day from (coalesce(w.podpisane, w.wydrukowane)-w.dystrybucja)) > 1) then 1 else 0 end) as podpisane_przeterminowane
    from wykonania W
        left outer join Pracownie Pr on Pr.Id = W.Pracownia 
        left outer join Materialy Mat on Mat.Id = W.Material
        left outer join GrupyPracowni GP on GP.Id = Pr.Grupa 
        left outer join zlecenia z on z.id=w.zlecenie 
        left join oddzialy o on o.id=z.oddzial
        left join platnicy pl on pl.id=z.platnik
        left join grupyplatnikow gpl on gpl.id=pl.grupa
        left outer join typyzlecen tz on tz.id = z.typzlecenia 
        left join badania bad on bad.id=w.badanie
    where W.godzinarejestracji between ? and ? and W.Badanie in ($BADANIA$)
        and $WARUNKI$
    group by cast(w.godzinarejestracji as date), cast(w.godzina as date), o.symbol, pl.symbol, o.nazwa, pl.nazwa, pr.symbol, pr.nazwa, bad.symbol, bad.nazwa, mat.symbol, mat.nazwa
    ) as a
    group by $POLA$ order by $POLA$
"""

LAUNCH_DIALOG = Dialog(
    title=MENU_ENTRY,
    panel=VBox(
        InfoText(
            text="""Raport z liczby zarejestrowanych w danym przedziale wykonań wybranego badania, oraz liczby badań już wykonanych (spośród liczby zarejestrowanych)
                Od dn. 2022-07-20 raport jest wykonywany wg pola GodzinaRejestracji w wykonaniach, a nie DataRejestracji, tzn rzeczywistego momentu rejestracji a nie daty ze zlecenia. Wartości te nie muszą się pokrywać."""
        ),
        LabSelector(multiselect=True, field="laboratoria", title="Laboratoria"),
        DateInput(field="dataod", title="Data początkowa", default="-1D"),
        DateInput(field="datado", title="Data końcowa", default="-1D"),
        TextInput(field="badania", title="Badania (symbole oddzielone spacjami)"),
        Switch(field="wyklucz_alab", title="Wyklucz grupę pracowni ALAB"),
        Switch(field="wyklucz_pl_alab", title="Wyklucz grupę płatników ALAB"),
        Switch(field="wyklucz_x", title="Wyklucz pracownie wysyłkowe (symbole X-)"),
        Switch(field="podzial_daty", title="Podział na daty rejestracji"),
        Switch(field="podzial_pobrania", title="Podział na daty pobrania"),
        Switch(field="podzial_podmioty", title="Podział na płatników i zleceniodawców"),
        Switch(field="podzial_pracownie", title="Podział na pracownie"),
        Switch(field="podzial_materialy", title="Podział na materialy"),
        Switch(field="podzial_badania", title="Podział na badania"),
        Switch(field="tylko_przyjete", title="Tylko przyjęte"),
        Switch(
            field="policz_przeterminowane",
            title="Policz przeterminowane (wykonane bez błędów, ale wynik podpisany później niż 24h od dystrybucji)",
        ),
        Switch(
            field="wg_zatwierdzenia", title="Wg daty zatwierdzenia (a nie rejestracji)"
        ),
    ),
)


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params["laboratoria"]) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    validate_date_range(params["dataod"], params["datado"], 180)
    if params["badania"] is None or params["badania"].strip() == "":
        raise ValidationError("Nie podano symbolu żadnego badania")
    for lab in params["laboratoria"]:
        lab_task = {
            "type": "centrum",
            "priority": 1,
            "timeout": 90,
            "target": lab,
            "params": params,
            "function": "zbierz_lab",
        }
        report.create_task(lab_task)
    report.save()
    return report


def get_sql(lab):

    centra = get_centra(lab)
    db_engine = get_db_engine(centra)

    if db_engine == "postgres":
        return SQL_PSQL
    if db_engine == "firebird":
        return SQL


def zbierz_lab(task_params):
    params = task_params["params"]
    oddnia = params["dataod"] + " 0:00:00"
    dodnia = params["datado"] + " 23:59:59"
    lab = task_params["target"]
    res = []
    sql = get_sql(lab)
    pola = ["lab"]
    naglowek = ["Laboratorium"]
    if params["wg_zatwierdzenia"]:
        sql = sql.replace(
            "W.godzinarejestracji between ? and ?", "w.zatwierdzone between ? and ?"
        )
    warunki = [
        "(GP.Symbol not like '%KONT%' or GP.Symbol is null)",
        "TZ.symbol <> 'K' and Tz.symbol <> 'KZ' and Tz.symbol <> 'KW'",
    ]
    sql_params = [oddnia, dodnia]
    # TODO: zależności od zahaczek
    if params["podzial_daty"]:
        pola.append("datarejestracji"),
        naglowek.append("Data rejestracji")
    if params["podzial_pobrania"]:
        pola.append("datapobrania"),
        naglowek.append("Data pobrania")
    if params["podzial_podmioty"]:
        pola += ["platnik", "platnik_nazwa", "zleceniodawca", "zleceniodawca_nazwa"]
        naglowek += ["Płatnik", "Płatnik nazwa", "Zleceniodawca", "Zleceniodawca nazwa"]
    if params["podzial_pracownie"]:
        pola += ["pracownia", "pracownia_nazwa"]
        naglowek += ["Pracownia", "Pracownia nazwa"]
    if params["podzial_materialy"]:
        pola += ["material", "material_nazwa"]
        naglowek += ["Material", "Material nazwa"]
    if params["podzial_badania"]:
        pola += ["badanie", "badanie_nazwa"]
        naglowek += ["Badanie", "Badanie nazwa"]
    if params["tylko_przyjete"]:
        warunki.append("W.Dystrybucja is not null")
    if params["wyklucz_alab"]:
        warunki.append("(GP.Symbol <> 'ALAB' or GP.Symbol is null)")
    if params["wyklucz_x"]:
        warunki.append("pr.symbol not like 'X-%'")
    if params["wyklucz_pl_alab"]:
        warunki.append("(GPL.Symbol <> 'ALAB' or GPL.Symbol is null)")
    naglowek += [
        "Zarejestrowane",
        "Przyjęte",
        "Anulowane",
        "Zabłędowane",
        "Wykonane ok",
        "Oczekujące wszystkie",
        "Oczekujące przyjęte",
    ]
    if params["policz_przeterminowane"]:
        naglowek.append("Wyk., podp. pow. 24h")
        sql = sql.replace(
            "sum(oczekujace_przyjete) as oczekujace_przyjete",
            "sum(oczekujace_przyjete) as oczekujace_przyjete, sum(podpisane_przeterminowane) as podpisane_przeterminowane",
        )
    badania_symbole = (params["badania"] or "").strip().upper().split(" ")
    badania_id = []
    with get_centrum_connection(lab, fresh=True) as conn:
        for bad in badania_symbole:
            bad = bad.strip()
            if len(bad) > 0:
                cols, rows = conn.raport_z_kolumnami(
                    "select id from badania where symbol=? and del=0", [bad]
                )
                if len(rows) > 0:
                    badania_id.append(rows[0][0])
    if len(badania_id) == 0:
        return "Nie znaleziono żadnego badania"
    sql = (
        sql.replace("$LAB$", lab)
        .replace("$POLA$", ", ".join(pola))
        .replace("$WARUNKI$", " and ".join(warunki))
    )
    sql = sql.replace("$BADANIA$", ",".join([str(id) for id in badania_id]))
    print(sql)
    with get_centrum_connection(lab, fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
    return naglowek, rows


def get_result(ident):
    task_group = TaskGroup.load(ident)
    header = None
    if task_group is None:
        return None
    res = {"errors": [], "results": [], "actions": ["xlsx"]}
    wiersze = []
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == "finished" and result is not None:
            if isinstance(result, str):
                res["errors"].append("%s - %s" % (params["target"], result))
            else:
                partial_header, partial_rows = result
                if header is None:
                    header = partial_header
                for row in partial_rows:
                    wiersze.append(row)
        if status == "failed":
            res["errors"].append("%s - błąd połączenia" % params["target"])
    res["progress"] = task_group.progress
    if header is not None:
        res["results"].append(
            {"type": "table", "header": header, "data": prepare_for_json(wiersze)}
        )
    return res
