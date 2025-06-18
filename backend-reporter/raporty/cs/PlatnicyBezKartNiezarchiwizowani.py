from datasources.kakl import KaKlDatasource
from dialog import (
    Dialog,
    VBox,
    LabSelector,
    ValidationError,
)
from tasks import TaskGroup
from helpers import (
    prepare_for_json,
)

MENU_ENTRY = "Płatnicy bez kart, niezarchiwizowani"

REQUIRE_ROLE = ["C-CS"]
ADD_TO_ROLE = ["R-DYR", "R-PM"]

SQL = """
    select kp.nazwa, kp.symbole, kp.nip, concat(ks.imie, ' ', ks.nazwisko) AS przedstawiciel_snr from kartoteki_platnik kp
    left join kartoteki_laboratorium_platnicy klp on klp.platnik_id = kp.id
    left join kartoteki_snrprzedstawiciel ks on kp.snr_przedstawiciel_id = ks.id
    left join kartoteki_laboratorium kl on kl.id = klp.laboratorium_id
    left join kakl_kartaklienta kk on kp.id = kk.platnik_id
    where kp.archived = false and kp.archived_manually = false AND kk.platnik_id IS null and kl.symbol in %s and kp.gotowkowe = false
"""

LAUNCH_DIALOG = Dialog(
    title="Zestawienie płatników, którzy nie mają podpiętej karty klienta oraz nie są zarchiwizowani",
    panel=VBox(
        LabSelector(multiselect=True, field="laboratoria", title="Laboratorium"),
    ),
)


def start_report(params):
    report = TaskGroup(__PLUGIN__, params)
    params = LAUNCH_DIALOG.load_params(params)
    if len(params["laboratoria"]) == 0:
        raise ValidationError("")
    task = {"type": "noc", "priority": 1, "params": params, "function": "raport_djalab"}
    report.create_task(task)
    report.save()
    return report


def raport_djalab(task_params):
    params = task_params["params"]
    kakl = KaKlDatasource()
    cols, rows = kakl.select(SQL, [tuple(params["laboratoria"])])
    return {"type": "table", "header": cols, "data": prepare_for_json(rows)}
