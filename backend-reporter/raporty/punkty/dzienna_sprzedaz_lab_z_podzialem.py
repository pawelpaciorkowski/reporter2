from dataclasses import dataclass
from dialog import Dialog, VBox, LabSelector, InfoText, DateInput, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup
from datasources.nocka import NockaDatasource
from datasources.postgres import PostgresDatasource
from config import Config
from pprint import pprint
import datetime

datetime.date
MENU_ENTRY = "Dodatkowa sprzedaż gotówkowa - laboratoria z podziałem TEST"

REQUIRE_ROLE = ["C-FIN"]


SEXES = ( 'K', 'M' )
DATE_RANGES = (
    (0,5),(6,20),(21,25), (26,35),(36,45),(46,60),(60,200)
)
ILIST = ["extra_sale_net_examines",
    "extra_sale_nocash_examines",
    "extra_sale_net_cash_examines",
    "extra_sale_net_nocash_examines"]

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
pacjent, lab, lab_zlecenie_data, lab_gotowka, lab_znacznik_dystrybucja,platnik_zlecenia, zleceniodawca, ile_zlecen, ile_wykonan, wartosc_gotowki, badanie,
plec, DATE_PART('year', lab_zlecenie_data) - DATE_PART('year', data_urodzenia) wiek 
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
    "only_net": "Liczba klientów internetowych",
    "only_cash": "Libczna klientów gotówkoych",
    "only_nocash": "Liczba klientów bezgotówkowych",
    "cash_value": "Wartość gotówki",
    "cash_from_extra_sale": "Wartość gotówki ze sprzedaży łączonej",
    "cash_from_extra_sale_net": "Wartość gotówki ze sprzedaży łączonej internetowa + gotówkowa",
    "cash_from_extra_sale_nocash": "Wartość gotówki ze sprzedaży łączonej bezgotówkowa + gotówkowa",
    "cash_from_extra_sale_net_nocash": "Wartość ze sprzedaży łączonej bezgotówkowa + internetowa",
    "cash_from_extra_sale_net_cash":  "Wartość gotówki ze sprzedaży łączonej bezgotówkowa + internetowa + gotówkowa",
    "cash_sale": "Wartość ze sprzedaży tylko gotówkowej",
    "extra_sale": "Liczba klientów ze sprzedażą łączoną",
    "extra_exams_all": "Dosprzedane badania łącznie",
    "extra_sale_net_examines": "Dokupione badania internet + gotówka",
    "extra_sale_nocash_examines": "Dokupione badania bezgotówka + gotówka" ,
    "extra_sale_net_cash_examines":  "Dokupione badania bezgotówka + internet + gotówka",
    "extra_sale_net_nocash_examines": "Dokupione badania bezgotówka + internet",
}

@dataclass
class RowRepresentation:
   pass 

class Groupper:
    def __init__(self, data):
        self.raw_data = data
        self.groupped = {}
        self.extra_fields = []
        self.display_fields = [
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
            "cash_from_extra_sale_net_cash",
            "cash_from_extra_sale_nocash",
            "cash_sale",
            "cash_from_extra_sale_net_nocash",
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


    def _add_extra_examines(self, client, examines_field_name, examines):

        fields = client["fields"]
        examines_field = fields[examines_field_name]
        examines_field_all_extra = fields['extra_sale_examines']
        examines_list = examines.strip('{}').split(',')
        for examine in examines_list:
            if examine in examines_field:
                examines_field[examine] += 1
            else:
                examines_field[examine] = 1

            if examine in examines_field_all_extra:
                examines_field_all_extra[examine] += 1
            else:
                examines_field_all_extra[examine] = 1

    def _add_extra_cash(self, client, cash_field_name, cash_value):
        fields = client["fields"]
        fields[cash_field_name] += cash_value

    def _add_extra_cash_and_examines(self, client, zlecenia):
        fields = client["fields"]
        if fields["extra_sale"]:
            for z in zlecenia:
                cash_value = z["wartosc_gotowki"]
                examines = z['badanie']
                if not examines:
                    continue
                if cash_value:
                    if fields["extra_sale_net"]:
                        self._add_extra_cash(client,"cash_from_extra_sale_net", cash_value)
                        self._add_extra_examines(
                            client,"extra_sale_net_examines", examines)

                    if fields["extra_sale_nocash"]:
                        self._add_extra_cash(client, "cash_from_extra_sale_nocash", cash_value)
                        self._add_extra_examines(
                            client, "extra_sale_nocash_examines", examines)

                    if fields["extra_sale_net_cash"]:
                        self._add_extra_cash(client,"cash_from_extra_sale_net_cash", cash_value)
                        self._add_extra_examines(
                            client,'extra_sale_net_cash_examines', examines)

                    if fields["extra_sale_net_nocash"]:
                        self._add_extra_cash(client,"cash_from_extra_sale_net_nocash", cash_value)
                        self._add_extra_examines(
                            client, "extra_sale_net_nocash_examines", examines)

                    fields["cash_from_extra_sale"] += cash_value
                    fields["cash_value"] += cash_value
        else:
            for z in zlecenia:
                cash_value  = z["wartosc_gotowki"]
                if cash_value:
                    fields["cash_sale"] += cash_value
                    fields["cash_value"] += cash_value

    def _add_sex_and_age(self, client, zlecenia):
        client['fields']['sex'] = zlecenia[0]['plec']
        client['fields']['age'] = zlecenia[0]['wiek']

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
                "cash_from_extra_sale_net_nocash",
                "cash_from_extra_sale_net_cash",
            ],
            0,
            client,
        )
        self._set_defaults(["cash_from_extra_sale", "cash_sale"], 0, client)
        self._set_defaults(["extra_sale_net_examines"], {}, client)
        self._set_defaults(["extra_sale_nocash_examines"], {}, client)
        self._set_defaults(["extra_sale_net_cash_examines"], {}, client)
        self._set_defaults(["extra_sale_net_nocash_examines"], {}, client)
        self._set_defaults(["extra_sale_net_nocash_examines"], {}, client)
        self._set_defaults(["extra_sale_examines"], {}, client)

        zlecenia = client["zlecenia"]
        for z in zlecenia:
            self._check_platnik(client, z)
        self._check_payments(client)
        self._add_extra_cash_and_examines(client, zlecenia)
        self._add_sex_and_age(client, zlecenia)

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

    @staticmethod
    def get_dict_name(i, sex, from_age, to_age):
           return f'{i}_{sex}_{from_age}_{to_age}' 

    @staticmethod
    def generate_examines_range_names():
        result = []
        for i in ILIST:
            for s in SEXES:
                for d in DATE_RANGES:
                    result.append(Groupper.get_dict_name(i, s, d[0], d[1]))
        return result

    @staticmethod
    def sort_desc(values):
            dict_response = {}
            srted =  sorted(values.items(), key=lambda item: item[1], reverse=True)
            for s in srted:
                dict_response[s[0]] = s[1]
            return dict_response

    def add_examines_result(self, row, current_lab):
        def append_examines(examine, examines, fields):
            if examine in examines:
                examines[examine] += fields[examine]
            else:
                examines[examine] = fields[examine]
            return examines

        def examine_section_name(name):
            dash_count = name.count('_')
            splited_name = name.split('_', dash_count-2)
            return '_'.join(splited_name[:-1])

        def section_name(name):
            dash_count = name.count('_')
            splited_name = name.split('_', dash_count-3)
            return '_'.join(splited_name[:-1])

        def section_sex(name):
            dash_count = name.count('_')
            splited_name = name.split('_', dash_count-2)
            sex = splited_name[-1].split('_')
            return sex[0]

        def section_age(name):
            dash_count = name.count('_')
            splited_name = name.split('_', dash_count-2)
            sex = splited_name[-1].split('_')
            return (int(sex[1]), int(sex[2]))

        def append_ex(variant, fields):
            for examine in fields:
                    append_examines(examine, variant, fields)

        def sort_variances(variances):
            temp_var = {}
            for i in ILIST:
                s_name = examine_section_name(i)
                if not s_name in temp_var:
                    for r in DATE_RANGES:
                        k_name = Groupper.get_dict_name(i, 'K', r[0], r[1])
                        m_name = Groupper.get_dict_name(i, 'M', r[0], r[1])
                        temp_var[k_name] = variances[k_name]
                        temp_var[m_name] = variances[m_name]
            return temp_var
        examine_variances = {}
        examines_all = {}
        examines_k = {}
        examines_m = {}


        for a in self.generate_examines_range_names():
            examine_variances[a] = {}

        for c in current_lab:
            client_sex = current_lab[c]['fields']['sex']
            client_age = current_lab[c]['fields']['age']
            for i in ILIST:
                fields = current_lab[c]['fields'][i]
                for examine in fields:
                    examines_all = append_examines(examine, examines_all, fields)
                    if client_sex == 'K':
                        examines_k = append_examines(examine, examines_k, fields)
                    else:
                        examines_m = append_examines(examine, examines_m, fields)


            for k, i in enumerate(examine_variances):
                section_field_name = examine_section_name(i)
                section_fields = current_lab[c]['fields'][section_field_name]
                s_sex = section_sex(i)
                s_age = section_age(i)
                variant = examine_variances[i]

                # SKIP CLIENTS WITH NO AGE
                if not client_age:
                    continue

                if client_age >= s_age[0] and client_age <= s_age[1] and client_sex == s_sex:
                    append_ex(variant, section_fields)

        examine_variances = sort_variances(examine_variances)
        sorted_examines = self.sort_desc(examines_all)
        sorted_examines_k = self. sort_desc(examines_k)
        sorted_examines_m = self. sort_desc(examines_m)
        row.append(sorted_examines)
        row.append(sorted_examines_k)
        row.append(sorted_examines_m)
        for s in examine_variances:
            row.append(self.sort_desc(examine_variances[s]))

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
                self.add_examines_result(row, current_lab)
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
                    # DICT SUM
                    if isinstance(r[i], dict):
                        for k, value in r[i].items():
                            if not k in response[key][i]:
                                response[key][i][k] = value
                            else:
                                response[key][i][k] += value
                    else:
                        response[key][i] += r[i]
        result = []
        for r in response:

            # DICTS TO STR
            for idx, c in enumerate(response[r]):
                if isinstance(c, dict):
                    response[r][idx] = str(self.sort_desc(c)).replace('{', '').replace('}','')

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

    def header(title, rowspan=1, colspan=1, fontyle='b'):
        return {'title':title, 'rowspan': rowspan, 'colspan': colspan,
                'fontstyle': fontyle}

    headers = [[
       header("Data", 3),
       header("Laboratorium", 3),
       header("Nazwa laboratorium",3),
       header("Liczba klientów", 3),
     ],[],[]]
    [headers[0].append(header(h ,3)) for h in fields]
    headers[0].append(header('Dokupione badania wszyscy',3))
    headers[0].append(header('Dokupione badnia kobiety',3))
    headers[0].append(header('Dokupione badania męzczyźni',3))

    for i in ILIST:
        headers[0].append(header(i,1,14))
        for h in DATE_RANGES:
            headers[1].append(header(h,1,2))
            for s in SEXES:
                headers[2].append(header(s))

    for hdr_sec in headers:
        for hdr in hdr_sec:
            title = hdr['title']
            if title in mapping:
                hdr['title'] = mapping[title]
            if isinstance(title, tuple):
                # print('TUPLE', title)
                hdr['title'] = f'Wiek {title[0]}-{title[1]}'
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
    # pprint(response)
    response = result.sum_on_date_range(response, params)

    return {
        "type": "table",
        "title": f"Raport z dziennej sprzedaży",
        "header": headers,
        "data": response,
    }
