import datetime
from copy import copy
from dialog import Dialog, VBox, InfoText, DateInput, Radio, Switch
from tasks import TaskGroup, Task
from pprint import pprint
from helpers import prepare_for_json
from datasources.nocka import NockaDatasource
from datasources.postgres import PostgresDatasource
from helpers.validators import validate_date_range
from config import Config

MENU_ENTRY = "Wymazy po punktach pobrań - TESTS"

ADD_TO_ROLE = ['R-DYR']

TESTS = {"all": "Wszsystkie", "pcr": "Tylko PCR", "antigen": "Tylko Antygen"}

LAUNCH_DIALOG = Dialog(
    title="",
    panel=VBox(
        InfoText(
            text="""Raport zawiera informacje o wykonanwych wymazach covidowych w poszególnych punktach pobrań.
    Źródła danych: Wymazy - nocka, Informacje o punktach pobrań - BIC"""
        ),
        DateInput(field="dataod", title="Data od", default="T"),
        DateInput(field="datado", title="Data do", default="T"),
        Radio(field="test_type", values=TESTS, default="all"),
        Switch(field="only_covid_pp", title="Tylko punkty oznaczone jako covid?"),
    ),
)

HEADERS = [
    {"title": "Miasto", "rowspan": 2, "fontstyle": "cb"},
    {"title": "Ulica", "rowspan": 2, "fontstyle": "cb"},
    {"title": "Dni i godziny pobrań", "rowspan": 2, "fontstyle": "cb"},
]
DATE_HEADER = {"title": "Data", "rowspan": 1, "colspan": 2, "fontstyle": "cb"}
D_HEADERS = []
DAILY_HEADERS = ["Gotówka", "NFZ"]

DAILY_ONLY_ANTIGEN = [
    "Gotówka",
]
SQL = """
select
    lab,
    kanal,
    zleceniodawca_nazwa,
    sum("GOT") as "GOT",
    sum("UM") as "UM",
    sum("NFZ") as "NFZ",
    date
from
    (select
    lab
    , kanal
    , zleceniodawca_nazwa
    , cast(lab_wykonanie_godz_rejestracji as date) as date
    , case when (
       platnik_zlecenia like '%%GOT%%' or ( platnik_zlecenia like '%%GRATIS%%'
        and kanal != '')) then count(*) else 0 end "GOT"
    , case when platnik_zlecenia like '%%-PK%%' then count(*) else 0 end "UM"
    , case when (platnik_zlecenia like '%%NFZ%%' and zleceniodawca_nazwa ilike 'punkt%%') or (zleceniodawca_nazwa ilike 'punkt%%' and zleceniodawca_nazwa ilike '%%NFZ%%') then count(*) else 0 end "NFZ"
    from wykonania_pelne wpa
    where lab_zlecenie_data between %s and %s
    {{TESTS}}
    group by lab, kanal, platnik_zlecenia, zleceniodawca_nazwa, lab_wykonanie_godz_rejestracji
    order by lab) as w
group by lab, kanal, zleceniodawca_nazwa, date
"""

SQL_BIC = """
select
    skarbiec_data -> 'name' "name",
    skarbiec_data -> 'city' -> 'name' city,
    skarbiec_data -> 'street' street,
    skarbiec_data -> 'mpk' mpk,
    skarbiec_data -> 'marcel' kanal,
    skarbiec_data -> 'symbol' symbol,
    skarbiec_data -> 'periodsSimple' period,
    skarbiec_data -> 'isCovidNfz' isCovidNfz
from config_collection_points
where is_active
    and (skarbiec_data->>'isCovidPrivate'='true'
        or skarbiec_data->>'isCovidNfz'='true')
"""

# SELECTS ALL ACTIVE COLLECTION POINTS
# NOT ONLY COVID ONES
SQL_BIC_ALL = """
select
    skarbiec_data -> 'name' "name",
    skarbiec_data -> 'city' -> 'name' city,
    skarbiec_data -> 'street' street,
    skarbiec_data -> 'mpk' mpk,
    skarbiec_data -> 'marcel' kanal,
    skarbiec_data -> 'symbol' symbol,
    skarbiec_data -> 'periodsSimple' period,
    skarbiec_data -> 'isCovidNfz' isCovidNfz
from config_collection_points
where is_active
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)

    validate_date_range(params["dataod"], params["datado"], 31)

    task = {"type": "noc", "priority": 1, "params": params, "function": "raport_wymazy"}
    report.create_task(task)
    report.save()
    return report


def raport_wymazy(task_params):

    db = NockaDatasource()
    sql = set_tests(task_params["params"], SQL)
    date_params = get_date_params(task_params["params"])
    report_type = task_params["params"]["test_type"]
    rows = db.dict_select(sql, date_params)
    days = get_all_days(rows, "raw")
    date_headers(days, report_type)

    db_bic = PostgresDatasource(Config.BIC_DATABASE, False)
    if task_params["params"]["only_covid_pp"]:
        cp = db_bic.dict_select(SQL_BIC)
    else:
        cp = db_bic.dict_select(SQL_BIC_ALL)

    rows_dict = join_results_with_collection_point_data(rows, cp)
    grupped_rows = group_by_city_and_street(rows_dict)
    display_rows = dict_to_display_list(grupped_rows, days, report_type)
    display_rows = add_summary_row(display_rows)

    return {
        "type": "table",
        "title": f"Raport z wymazów po punkach pobrań ",
        "header": [HEADERS, D_HEADERS],
        "data": prepare_for_json(display_rows),
    }


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


def date_headers(dates, report_type):
    for date in dates:
        date_header = copy(DATE_HEADER)
        date_header["title"] = date.strftime("%Y-%m-%d")
        HEADERS.append(date_header)
        d = copy(get_daily_display_headers(report_type))
        for a in d:
            D_HEADERS.append(a)


def add_summary_row(rows):
    summary_row = ["", "", {"value": "Suma:", "fontstyle": "rb"}]
    for i in range(len(D_HEADERS)):
        to_sum = []
        for row in rows:
            value = row[i + 3]
            if isinstance(value, dict):
                to_sum.append(value["value"])
            else:
                to_sum.append(value)
        summary_row.append({"value": sum(to_sum), "fontstyle": "cb"})
    rows.append(summary_row)
    return rows


def set_tests(params, sql):
    test_type = params["test_type"]
    if test_type == "all":
        sql = sql.replace(
            "{{TESTS}}",
            "and badanie in ('VIPCOVP', 'VIPCOVA', '2019COV', '19COVA', '19COVN', 'COV2ANT', 'COVANTA', 'COVANTN', 'CANPOCP', 'CANPOCA', 'CANPOCN')",
        )
    if test_type == "pcr":
        sql = sql.replace(
            "{{TESTS}}",
            "and badanie in ('VIPCOVP', 'VIPCOVA', '2019COV', '19COVA', '19COVN')",
        )
    if test_type == "antigen":
        sql = sql.replace(
            "{{TESTS}}",
            "and badanie in ('COV2ANT', 'COVANTA', 'COVANTN', 'CANPOCP', 'CANPOCA', 'CANPOCN')",
        )
    return sql


def append_collection_point_data(cp_data, row):
    if cp_data:
        row["city"] = cp_data["city"]
        row["street"] = cp_data["street"]
        row["period"] = cp_data["period"]
        row["iscovidnfz"] = cp_data["iscovidnfz"]
    return row


def get_collection_point_data_for_row(data, row):
    for d in data:
        if check_collection_point_for_kanal(d, row):
            return d
        if check_collection_point_for_name(d, row):
            return d
        if check_names(d, row):
            return d
        if check_name_streets(d, row):
            return d

def check_names(cp, row):
    cp_name = cp['name']
    row_name = row['zleceniodawca_nazwa']
    if cp_name and row_name:
        if cp_name.lower() == row_name.lower():
            return cp

def remove_extra_chars(val):
    char_list = ''',;-_:'"'''
    for ch in char_list:
        val = val.replace(ch, '')
    return val.strip()

def get_street(data, splitter):
    cp_street = data.lower().split(splitter)

    if len(cp_street) > 1:
        cp_street2 =  cp_street[1].strip().split(',')
        if not cp_street2:
            cp_street2 =  cp_street[1].strip().split(' ')
        if cp_street2:
            el1= cp_street2[0].lower()
            try:
                el2 = str(int(remove_extra_chars(cp_street2[1])))
                return ' '.join([el1, el2])
            except (ValueError, IndexError):
                return cp_street2[0].lower()
            except Exception as e:
                print(e, cp_street2)
                exit()

def street(data):
    cp_street = get_street(data, 'ul.')
    if cp_street:
        return cp_street.strip()

    cp_street = get_street(data, 'al.')
    if cp_street:
        return cp_street.strip()

def check_name_streets(cp, row):
    cp_name = cp['name']
    row_name = row['zleceniodawca_nazwa']
  
    if cp_name == row_name:
        return cp
    if cp_name and row_name:
        cp_street = street(cp_name)
        row_street = street(row_name)
        if cp_street and row_street and (cp_street == row_street) :
            return cp

def check_collection_point_for_kanal(cp, row):
    if row["kanal"]:
        if cp.get("kanal") and cp.get("kanal").lower() == row["kanal"].lower():
            return cp


def check_collection_point_for_name(cp, row):
    try:
        if should_search_in_name(row):
            zleceniodawca = [r.lower() for r in row["zleceniodawca_nazwa"].split()]
            city = cp.get("city").lower()
            street = [s.lower() for s in cp.get("street").replace('-', ' ').split() if not hasNumbers(s)]
            if is_city_and_street_match(city, street, zleceniodawca):
                return cp
    except AttributeError:
        pass


def search_for_street(street, zleceniodawca):
    for s in street:
        for z in zleceniodawca:
            if s in z and len(s) > 3 and len(z) > 3:
                return True


def is_city_and_street_match(city, street, zleceniodawca):
    city2 = city.split()
    for c in city2:
        if not c in zleceniodawca:
            return False

    if search_for_street(street, zleceniodawca):
        return True
    return False


def should_search_in_name(row):
    if "Punkt Pobrań Covid NFZ".lower() in row["zleceniodawca_nazwa"].lower():
        return True
    if "Punkt Pobrań\xa0Covid NFZ".lower() in row["zleceniodawca_nazwa"].lower():
        return True
    if row["kanal"] is None and row["GOT"] > 0:
        return True
    return False


def hasNumbers(inputString):
    return any(char.isdigit() for char in inputString)


def join_results_with_collection_point_data(rows, cp):
    rows_list = []
    for row in rows:
        cp_data = get_collection_point_data_for_row(cp, row)
        new_row = append_collection_point_data(cp_data, row)
        rows_list.append(new_row)
    rows_list = append_all_covid_pp(rows_list, cp)
    return rows_list


def append_all_covid_pp(rows, cp):
    report_date_range = list(get_all_days(rows, "raw"))
    for point in cp:
        for day in report_date_range:
            if point["city"]:
                row = {
                    "city": point["city"],
                    "street": point["street"],
                    "period": point["period"],
                    "iscovidnfz": point["iscovidnfz"],
                    "date": day,
                    "GOT": 0,
                    "NFZ": 0,
                }
                rows.append(row)
    return rows


def add_to_existing_key(grouped, key, date, row):
    grouped = add_to_existing_key_missing_date(grouped, key, date)
    grouped = add_to_existing_key_and_date(grouped, key, date, row)
    return grouped


def add_to_existing_key_missing_date(grouped, key, date):
    if date not in grouped[key]:
        grouped[key][date] = {"got": 0, "nfz": 0}
    return grouped


def add_to_existing_key_and_date(grouped, key, date, row):
    grouped[key][date]["got"] += row["GOT"]
    grouped[key][date]["nfz"] += row["NFZ"]
    return grouped


def add_new_key(grouped, key, row, date=None):
    if row.get("date"):
        return add_new_key_with_date(grouped, key, row)
    else:
        return add_new_key_with_date(grouped, key, row, date)


def add_new_key_with_date(grouped, key, row, date=None):
    if not date:
        date = row["date"]
    grouped[key] = {
        "city": row["city"],
        "street": row["street"],
        "period": row["period"],
        "iscovidnfz": row["iscovidnfz"],
        date: {
            "got": row["GOT"],
            "nfz": row["NFZ"],
        },
    }
    return grouped


def group_by_city_and_street(rows):
    grouped = {}
    for row in rows:
        try:
            key = row["city"] + row["street"]
            date = row["date"]
        except KeyError:
            continue

        if key in grouped:
            grouped = add_to_existing_key(grouped, key, date, row)
        else:
            grouped = add_new_key(grouped, key, row, date)

    return grouped


def display_period(row_data):
    res = ""
    try:
        for r in row_data["period"]:
            if r["type"] == "collect":
                for period in r["periods"]:
                    res = " ".join([res, period["dayOfWeek"], period["period"]])
    except TypeError:
        pass
    return res


def get_formating(value, row_data):
    res = {"value": value, "fontstyle": "c"}
    if row_data["iscovidnfz"]:
        res["background"] = "#d6d636de"
    return res


def dict_to_display_list(rows, days, report_type):
    display_rows = []
    fields = get_daily_display_fields(report_type)
    for row in sorted(rows):
        row_data = rows[row]
        single_row = []
        single_row.append(get_formating(row_data["city"], row_data))
        single_row.append(get_formating(row_data["street"], row_data))
        period = display_period(row_data)
        single_row.append(get_formating(period, row_data))
        single_row = append_display_list_with_daily_test_data(
            days, single_row, row_data, fields
        )
        display_rows.append([key for key in single_row])
    return display_rows


def is_antigen(report_type):
    if report_type == "antigen":
        return True
    return False


def get_daily_display_fields(report_type):
    if is_antigen(report_type):
        return ["got"]
    return ["got", "nfz"]


def get_daily_display_headers(report_type):
    if is_antigen(report_type):
        return DAILY_ONLY_ANTIGEN
    return DAILY_HEADERS


def append_display_list_with_daily_test_data(days, single_row, row_data, fields):
    for d in days:
        for f in fields:
            single_row.append(get_formating(row_data[d][f], row_data))

    return single_row


def get_date_params(params):
    return (params["dataod"], params["datado"])
