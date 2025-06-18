from dataclasses import dataclass
from urllib import response
from decimal import Decimal

from requests import head
from dialog import Dialog, VBox, LabSelector, InfoText, DateInput, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup
from helpers import prepare_for_json
from datasources.nocka import NockaDatasource
from datasources.postgres import PostgresDatasource
from config import Config
from pprint import pprint
import datetime

datetime.date
MENU_ENTRY = "Dodatkowa sprzedaż gotówkowa - laboratoria 3"

REQUIRE_ROLE = ["C-FIN"]

LAUNCH_DIALOG = Dialog(
    title=MENU_ENTRY,
    panel=VBox(
        InfoText(
            text="Raport przedstawiający dzienną dodatkową sprzedaż gotówkową na poziomie laboratorium"
        ),
        LabSelector(multiselect=True, field="laboratoria", title="Laboratoria"),
        DateInput(field="dataod", title="Data początkowa", default="-7D"),
        DateInput(field="datado", title="Data końcowa", default="-1D"),
    ),
)

SQL_2 = """
with t as (select
pacjent, lab, lab_zlecenie_data, lab_gotowka, lab_znacznik_dystrybucja,platnik_zlecenia, zleceniodawca, ile_zlecen, ile_wykonan, wartosc_gotowki
from  dzienna_sprzedaz ds ),
 base as (
select *
from
		t ds
where	
lab_zlecenie_data between %s and %s
	{{LABS}}
	and platnik_zlecenia is not null
	--and ds.lab_znacznik_dystrybucja is false
	--and ds.kanal is not null
) select *
from base
"""

SQL_BIC = """
select symbol, name from config_labs
"""

SQL_BIC_2 = """
select
    skarbiec_data -> 'name' "name",
    skarbiec_data -> 'marcel' kanal,
    skarbiec_data -> 'symbol' symbol
from config_collection_points
where is_active
"""

HEADER_MAPPING = {
    "net": "Liczba klientów ze sklepu internetowego",
    "cash": "Liczba klientów gotówkowych",
    "nocash": "Liczba klientów bezgotówkowych",
    "extra_sale_net": "Sprzedaż łączona internetowa + gotówkowa",
    "extra_sale_nocash": "Sprzedaż łączona bezgotówkowa + gotówkowa",
    "extra_sale_net_nocash": "Sprzedaż łączona bezgotówkowa + internatowa",
    "extra_sale_net_cash": "Sprzedaż łączona bezgotówkowa + gotówkowa + internatowa",
    "only_net": "Liczba klientów tylko internetowych",
    "only_cash": "Libczna klientów gotówkoych",
    "only_nocash": "Liczba klientów bezgotówkowych",
    "cash_value": "Wartość gotówki",
    "cash_from_extra_sale": "Wartość gotówki ze sprzedaży łączonej",
    "cash_from_extra_sale_net": "Wartość gotówki ze sprzedaży łączonej internetowa + gotówkowa",
    "cash_from_extra_sale_nocash": "Wartość gotówki ze sprzedaży łączonej bezgotówkowa + gotówkowa",
    "cash_from_extra_sale_nocash_net": "Wartość gotówki ze sprzedaży łączonej bezgotówkowa + internetowa + gotówkowa",
    "cash_sale": "Wartość ze sprzedaży tylko gotówkowej",
    "extra_sale": "Liczba klientów ze sprzedażą łączoną",
}


class Groupper:
    def __init__(self, data):
        self.raw_data = data
        self.groupped = {}
        self.extra_fields = []
        self.display_fields = [
            "net",
            "only_net",
            "only_cash",
            "only_nocash",
            "extra_sale",
            "extra_sale_net",
            "extra_sale_nocash",
            "extra_sale_net_cash",
            "extra_sale_net_nocash",
            "cash_value",
            "cash_from_extra_sale",
            "cash_from_extra_sale_net",
            "cash_from_extra_sale_nocash",
            "cash_sale",
            "cash_from_extra_sale_nocash_net",
        ]

    def _group_with_empty_dict(self, val, current_level):
        if not val in current_level:
            current_level[val] = {}
        return current_level

    def _add_level(self, value_name, previous_level_value, previous_level, data):
        value = data[value_name]
        try:
            level = previous_level[previous_level_value]
        except:
            level = previous_level
        self._group_with_empty_dict(value, level)

    def add_details(self, pacjent, current_level, row):
        if not current_level.get("zlecenia"):
            current_level["zlecenia"] = []
        current_level["zlecenia"].append(row)

    def add_pacjent(self, kanal, current_level, row):
        pacjent = row["pacjent"]
        level = current_level
        self._add_level("pacjent", kanal, level, row)
        self.add_details(pacjent, level[pacjent], row)

    def add_kanal(self, lab, current_level, row):
        kanal = row["kanal"]
        level = current_level
        self._add_level("kanal", lab, level, row)
        self.add_pacjent(kanal, level[kanal], row)

    def add_lab(self, current_date, row):
        lab = row["lab"]
        level = self.groupped[current_date]
        self._add_level("lab", current_date, level, row)
        self.add_pacjent(lab, level[lab], row)

    def group_by_date(self):
        for row in self.raw_data:
            current_date = row["lab_zlecenie_data"]
            self._group_with_empty_dict(current_date, self.groupped)
            self.add_lab(current_date, row)

    def _set_defaults(self, fields, value, client):
        for f in fields:
            if not f in self.extra_fields:
                self.extra_fields.append(f)
            client["fields"][f] = value

    def _check_payments(self, client):
        fields = client["fields"]
        ki = fields["net"]
        kg = fields["cash"]
        kb = fields["nocash"]
        if ki and kg and not kb:
            fields["extra_sale_net"] = 1
        if kb and kg and not ki:
            fields["extra_sale_nocash"] = 1
        if kb and kg and ki:
            fields["extra_sale_net_cash"] = 1
        if kb and ki and not kg:
            fields["extra_sale_net_nocash"] = 1
        if (kb and kg) or (ki and kg) or (kb and ki):
            fields["extra_sale"] = 1

        if ki and not kg and not kb:
            fields["only_net"] = True
        if kg and not ki and not kb:
            fields["only_cash"] = 1
        if kb and not ki and not kg:
            fields["only_nocash"] = 1

    def _check_platnik(self, client, z):
        fields = client["fields"]
        if "SKIN" in z["platnik_zlecenia"]:
            fields["net"] = 1

        if "GOT" in z["platnik_zlecenia"]:
            fields["cash"] = 1

        if not "SKIN" in z["platnik_zlecenia"] and (not "GOT" in z["platnik_zlecenia"]):
            fields["nocash"] = 1

    def _add_cash_value(self, client, zlecenia):
        fields = client["fields"]
        if fields["extra_sale"]:
            for z in zlecenia:
                if z["wartosc_gotowki"]:
                    if fields["extra_sale_net"]:
                        fields["cash_from_extra_sale_net"] += z["wartosc_gotowki"]
                    if fields["extra_sale_nocash"]:
                        fields["cash_from_extra_sale_nocash"] += z["wartosc_gotowki"]
                    if fields["extra_sale_net_cash"]:
                        fields["cash_from_extra_sale_nocash"] += z["wartosc_gotowki"]
                    if fields["extra_sale_net_nocash"]:
                        fields["cash_from_extra_sale_nocash_net"] += z[
                            "wartosc_gotowki"
                        ]

                    fields["cash_from_extra_sale"] += z["wartosc_gotowki"]
                    fields["cash_value"] += z["wartosc_gotowki"]
        else:
            for z in zlecenia:
                if z["wartosc_gotowki"]:
                    fields["cash_sale"] += z["wartosc_gotowki"]
                    fields["cash_value"] += z["wartosc_gotowki"]

    def add_calculated_fields(self, client):
        client["fields"] = {}
        self._set_defaults(
            [
                "net",
                "cash",
                "nocash",
                "extra_sale_net",
                "extra_sale_nocash",
                "extra_sale_net_cash",
                "extra_sale_net_nocash",
                "only_net",
                "only_cash",
                "only_nocash",
                "extra_sale",
                "cash_value",
                "cash_from_extra_sale_nocash",
                "cash_from_extra_sale_net",
                "cash_from_extra_sale_nocash_net",
            ],
            0,
            client,
        )
        self._set_defaults(["cash_from_extra_sale", "cash_sale"], 0, client)
        zlecenia = client["zlecenia"]
        for z in zlecenia:
            self._check_platnik(client, z)
        self._check_payments(client)
        self._add_cash_value(client, zlecenia)

    def iterate_by_clients(self):
        for d in self.groupped:
            current_date = self.groupped[d]
            for l in current_date:
                current_lab = current_date[l]
                for p in current_lab:
                    current_client = current_lab[p]
                    self.add_calculated_fields(current_client)

    def sum_on_kanal_level(self):
        response = []
        for d in self.groupped:
            current_date = self.groupped[d]
            for l in current_date:
                current_lab = current_date[l]
                for k in current_lab:
                    current_kanal = current_lab[k]
                    row = []
                    row.append(str(d))
                    row.append(l)
                    row.append(k)
                    row.append(sum(1 for c in current_kanal))
                    for h in self.display_fields:
                        row.append(
                            sum([current_kanal[c]["fields"][h] for c in current_kanal])
                        )
                    response.append(row)

        return response

    def sum_on_lab_level(self):
        response = []
        for d in self.groupped:
            current_date = self.groupped[d]
            for l in current_date:
                current_lab = current_date[l]
                row = []
                row.append(str(d))
                row.append(l)
                row.append(sum(1 for c in current_lab))
                for h in self.display_fields:
                    row.append(sum([current_lab[c]["fields"][h] for c in current_lab]))
                response.append(row)

        return response

    def sum_on_date_range(self, data, params):
        date_range = str(params["dataod"]) + "-" + str(params["datado"])
        response = {}
        for r in data:
            start_numbers_indx = 3
            for f in r:
                if not isinstance(f, str):
                    start_numbers_indx = r.index(f)
                    break
            key = ",".join(r[1:start_numbers_indx])
            if key not in response:
                to_append = [date_range]
                to_append += r[1:]
                response[key] = to_append
            else:
                for i in range(start_numbers_indx, len(response[key])):
                    response[key][i] += r[i]
        result = []
        for r in response:
            result.append(response[r])
        return sorted(result, key=lambda x: (x[2], x[4]))

    def create_rows(self):
        response = []
        for d in self.groupped:
            current_date = self.groupped[d]
            for l in current_date:
                current_lab = current_date[l]
                for k in current_lab:
                    current_kanal = current_lab[k]
                    for p in current_kanal:
                        current_client = current_kanal[p]
                        row = []
                        row.append(str(d))
                        row.append(l)
                        row.append(k)
                        [
                            row.append(current_client["fields"][f])
                            for f in current_client["fields"]
                        ]
                        response.append(row)

        return response

    def result(self):
        return self.groupped


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params["laboratoria"]) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    validate_date_range(params["dataod"], params["datado"], max_days=31)
    task = {
        "type": "noc",
        "priority": 1,
        "params": params,
        "function": "dzienna_sprzedaz",
    }
    report.create_task(task)
    report.save()
    return report


def get_labs(sql, labs):
    if labs:
        return sql.replace("{{LABS}}", " and lab in  %s  ")
    return sql.replace("{{LABS}}", " ")


def set_sql_params(params, labs):
    if labs:
        return (params["dataod"], params["datado"], labs)
    else:
        return [params["dataod"], params["datado"]]


def append_lab_name(rows, labs_details):
    response = []
    for r in rows:
        lab_symbol = r[1]
        name = [l["name"] for l in labs_details if l["symbol"] == lab_symbol]
        r = list(r)
        r.insert(2, name[0])
        response.append(r)
    return response


def append_cp_name(rows, cp_details):
    response = []
    for r in rows:
        cp_symbol = r[3]
        name = [l["name"] for l in cp_details if l["kanal"] == cp_symbol]
        r = list(r)
        if not name:
            continue
        r.insert(4, name[0])
        response.append(r)
    return response


def append_by_indx(val, joined):
    if val not in joined:
        joined[val] = {}
    return joined


def append_by_fieldname(name, joined):
    if name not in joined:
        joined[name] = {}
    return joined


def append_date(row, joined):
    return append_by_fieldname("lab_zlecenie_data", joined)


def create_headers(mapping, fields):
    headers = [
        "Data",
        "Laboratorium",
        "Nazwa laboratorium",
        "Liczba klientów",
    ] + [h for h in fields]
    for h in mapping:
        try:
            if headers.index(h):
                headers[headers.index(h)] = mapping[h]
        except:
            continue
    return headers


def dzienna_sprzedaz(task_params):
    params = task_params["params"]

    db_bic = PostgresDatasource(Config.BIC_DATABASE, False)
    labs_details = db_bic.dict_select(SQL_BIC)
    db = NockaDatasource()
    labs = tuple(params["laboratoria"])
    sql_params = set_sql_params(params, labs)
    sql = get_labs(SQL_2, labs)
    cp_details = db_bic.dict_select(SQL_BIC_2)
    data = db.dict_select(sql, sql_params)
    result = Groupper(data)
    result.group_by_date()
    result.iterate_by_clients()
    response = result.sum_on_lab_level()
    headers = create_headers(HEADER_MAPPING, result.display_fields)
    response = append_lab_name(response, labs_details)
    # response = append_cp_name(response, cp_details)
    response = result.sum_on_date_range(response, params)

    return {
        "type": "table",
        "title": f"Raport z dziennej sprzedaży",
        "header": headers,
        "data": response,
    }
