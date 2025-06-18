from pprint import pprint

from dialog import Dialog, VBox, InfoText, DateInput, Radio, Switch
from tasks import TaskGroup
from helpers import prepare_for_json
from datasources.snr import SNR
from datasources.nocka import NockaDatasource
from helpers.validators import validate_date_range


MENU_ENTRY = "Profilaktyka 40+ - NFZ"
HEADERS = [
    {"title": "Zleceniodawca", "rowspan": 2, "fontstyle": "b"},
    {"title": "Zleceniodawca nazwa", "rowspan": 2, "fontstyle": "b"},
]

HEADERS_WITH_TESTS = [
    "Zleceniodawca",
    "Zleceniodawca nazwa",
    "Badanie",
    "Badanie nazwa",
]

LAUNCH_DIALOG = Dialog(
    title="Profilaktyka 40+ - Widok miesięczny zlicza badania jedynie z wybranego zakresu dat.",
    panel=VBox(
        InfoText(text="""  """),
        DateInput(field="dataod", title="Data od", default="T"),
        DateInput(field="datado", title="Data do", default="T"),
        Switch(field="show_tests", title="Wyświetl badania"),
        Switch(field="monthly_view", title="Widok miesięczny"),
    ),
)
# select date(lab_wykonanie_godz_dystrybucji) as date,
# select concat(extract(YEAR from lab_wykonanie_godz_dystrybucji),'-', extract(MONTH from lab_wykonanie_godz_dystrybucji)) as date,

SQL_ZLECENIODAWCY = """
select zwl.symbol from zleceniodawcy zl left join zleceniodawcywlaboratoriach zwl on zwl.zleceniodawca=zl.id and not zwl.del where zl.platnik='ALAB.1.407243684' and zl.nazwa like '%40+%'
"""

SQL = """

select
    "date",
    zleceniodawca,
    zleceniodawca_nazwa,
    {{tests2}}
    sum(badania) as badania
from (
        select {{monthly_view}} as date,
                zleceniodawca,
                zleceniodawca_nazwa,
                lab_zlecenie,
                {{tests}}
                count(*) as badania
         from wykonania_pelne wpa
         where zleceniodawca in %s
and badanie in (
    'PLYTKI',
    'CHOL',
    'GLU',
    'KREA',
    'MOCZ',
    'URIC',
    'TPSA',
    'KREW-UT',
    'ALT',
    'AST',
    'GGTP',
    'brak',
    'GLU-M',
    'HDL',
    'LDL',
    'LDL-WYL',
    'MORF',
    'OSAD',
    'ROZMAZ',
    'TG',
    'TP-M',
    'KON-ROZ',
    'PKLIPID'
)
        and (extract(years from age(lab_wykonanie_godz_dystrybucji::timestamp, lab_pacjent_data_urodzenia::timestamp)) > 39
        or lab_pacjent_data_urodzenia is null)
        and blad_wykonania is null
        and date(lab_wykonanie_godz_dystrybucji) between %s and %s
         group by 1, 2, 3, 4 {{group_by2}}
         order by 1, 2, 3
     ) as a
group by 1,2,3 {{group_by}}


"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)

    validate_date_range(params["dataod"], params["datado"], 93)

    task = {"type": "noc", "priority": 1, "params": params, "function": "raport_wymazy"}
    report.create_task(task)
    report.save()
    return report


def get_all_days(rows, format=None):
    dates = set()
    for row in rows:
        try:
            if format == "raw":
                dates.add(row["date"])
            else:
                dates.add(row["date"].strftime("%Y-%m-%d"))
        except KeyError:
            pass
    return sorted(list(dates))


def add_new_zleceniodawca(grouped, zleceniodawca):
    if zleceniodawca not in grouped:
        grouped[zleceniodawca] = {}
    return grouped


def add_new_zleceniodawca_with_badanie(grouped, zleceniodawca):
    grouped = add_new_zleceniodawca(grouped, zleceniodawca)
    if grouped[zleceniodawca].get("badania") is None:
        grouped[zleceniodawca]["badania"] = {}
    return grouped


def add_zleceniodawca_details(grouped, row, zleceniodawca):
    g_zleceniodawca = grouped[zleceniodawca]
    g_zleceniodawca["zleceniodawca_nazwa"] = row["zleceniodawca_nazwa"]
    g_zleceniodawca["zleceniodawca"] = row["zleceniodawca"]
    return g_zleceniodawca


def group_zleceniodawca(grouped, row, zleceniodawca):
    grouped = add_new_zleceniodawca(grouped, zleceniodawca)
    grouped[zleceniodawca] = add_zleceniodawca_details(grouped, row, zleceniodawca)
    return grouped


def group_zleceniodawca_with_badanie(grouped, row, zleceniodawca):
    grouped = add_new_zleceniodawca_with_badanie(grouped, zleceniodawca)
    grouped[zleceniodawca] = add_zleceniodawca_details(grouped, row, zleceniodawca)
    return grouped


def group_badania(grouped, row, zleceniodawca):
    badanie = row["badanie"]
    badanie_nazwa = row["badanie_nazwa"]
    g_zleceniodawca = grouped[zleceniodawca]
    if badanie not in g_zleceniodawca["badania"]:
        grouped[zleceniodawca]["badania"][badanie] = {}
        g_badanie = g_zleceniodawca["badania"][badanie]
        g_badanie["badanie"] = badanie
        g_badanie["badanie_nazwa"] = badanie_nazwa
    return grouped


def add_dates(zleceniodawca, date):
    if date not in zleceniodawca:
        zleceniodawca[date] = {}
    return zleceniodawca


def group_with_tests(data):
    grouped = {}
    for row in data:
        zleceniodawca = row["zleceniodawca"]
        date = row["date"]
        badanie = row["badanie"]

        grouped = group_zleceniodawca_with_badanie(grouped, row, zleceniodawca)
        grouped = group_badania(grouped, row, zleceniodawca)
        g_zleceniodawca = grouped[zleceniodawca]
        g_badanie = g_zleceniodawca["badania"][badanie]

        if date not in g_badanie:
            g_badanie[date] = {}

        g_badanie_dnia = grouped[zleceniodawca]["badania"][badanie][date]
        g_badanie_dnia["liczba"] = row["badania"]
    return grouped


def group_without_tests(data):
    grouped = {}
    for row in data:
        zleceniodawca = row["zleceniodawca"]
        date = row["date"]

        grouped = group_zleceniodawca(grouped, row, zleceniodawca)
        g_zleceniodawca = grouped[zleceniodawca]
        g_zleceniodawca = add_dates(g_zleceniodawca, date)
        g_dnia = g_zleceniodawca[date]
        g_dnia["klienci"] = row["klienci"]
        g_dnia["badania"] = row["badania"]
    return grouped


def group_data_badania(data, show_tests=None):
    if show_tests:
        return group_with_tests(data)
    return group_without_tests(data)


def get_sql(params, sql):
    if params["monthly_view"]:
        sql = sql.replace(
            "{{monthly_view}}",
            " concat(extract(YEAR from lab_wykonanie_godz_dystrybucji),'-', extract(MONTH from lab_wykonanie_godz_dystrybucji)) ",
        )
    else:
        sql = sql.replace("{{monthly_view}}", " date(lab_wykonanie_godz_dystrybucji) ")
    if params["show_tests"] is True:
        sql = sql.replace("{{tests}}", "badanie, badanie_nazwa,")
        sql = sql.replace("{{tests2}}", "badanie, badanie_nazwa,")
        sql = sql.replace("{{group_by}}", ", 4,5 ")
        sql = sql.replace("{{group_by2}}", ", 5,6 ")
        return sql
    sql = sql.replace("{{tests}}", "")
    sql = sql.replace("{{group_by}}", "")
    sql = sql.replace("{{tests2}}", "count(*) as klienci, ")
    sql = sql.replace("{{group_by2}}", "")
    return sql


def get_data_without_badania(row, zleceniodawca, days):
    response = []
    badanie_row = []
    badanie_row.append(row["zleceniodawca"])
    badanie_row.append(row["zleceniodawca_nazwa"])
    for day in days:
        if row.get(day):
            badanie_row.append(row[day]["klienci"])
            badanie_row.append(row[day]["badania"])
        else:
            badanie_row.append(0)
            badanie_row.append(0)
    response.append(badanie_row)
    return response


def get_data_with_badania(row, zleceniodawca, days):
    response = []
    badania = row["badania"]
    for b in badania:
        badanie = badania[b]
        badanie_row = []
        badanie_row.append(row["zleceniodawca"])
        badanie_row.append(row["zleceniodawca_nazwa"])
        badanie_row.append(badanie["badanie"])
        badanie_row.append(badanie["badanie_nazwa"])
        for day in days:
            if badanie.get(day):
                badanie_row.append(badanie[day]["liczba"])
            else:
                badanie_row.append(0)
        response.append(badanie_row)
    return response


def display2(data, days):
    response = []
    for data_row in data:
        badania = get_data_without_badania(data[data_row], data_row, days)
        for badanie in badania:
            response.append(badanie)
    return response


def display(data, days):
    response = []
    for data_row in data:
        badania = get_data_with_badania(data[data_row], data_row, days)
        for badanie in badania:
            response.append(badanie)
    return response


def raport_wymazy(task_params):
    snr = SNR()
    zleceniodawcy = [row['symbol'] for row in snr.dict_select(SQL_ZLECENIODAWCY)]
    db = NockaDatasource()
    params = task_params["params"]
    sql = get_sql(params, SQL)
    dt = db.dict_select(sql, (tuple(zleceniodawcy), params["dataod"], params["datado"]))
    days = get_all_days(dt, "raw")
    if params["show_tests"]:
        headers = HEADERS_WITH_TESTS
        for day in days:
            headers.append(str(day))
    else:
        headers3 = HEADERS
        headers2 = []
        for day in days:
            headers3.append(
                {"title": str(day), "rowspan": 1, "colspan": 2, "fontstyle": "b"}
            )
            headers2.append("klienci")
            headers2.append("badania")
        headers = [headers3, headers2]

    days = get_all_days(dt, "raw")
    gruped = group_data_badania(dt, params["show_tests"])
    if params["show_tests"]:
        dis = display(gruped, days)
    else:
        dis = display2(gruped, days)
    return {
        "type": "table",
        "title": f"Profilaktyka 40+",
        "header": headers,
        "data": prepare_for_json(dis),
    }
