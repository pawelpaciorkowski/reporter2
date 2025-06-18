from dialog import (
    Dialog,
    Panel,
    HBox,
    VBox,
    TextInput,
    LabSelector,
    TabbedView,
    Tab,
    InfoText,
    DateInput,
    Switch,
    ValidationError,
)
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection
from datasources.snr import SNR
from datasources.hbz import HBZ
from api.common import get_db
from decimal import Decimal

MENU_ENTRY = "Ile zleceń - Punkty Pobrań"

REQUIRE_ROLE = ["C-FIN", "C-CS", "PP-S", "C-PP"]

LAUNCH_DIALOG = Dialog(
    title=MENU_ENTRY,
    panel=VBox(
        InfoText(
            text="Raport ilu pacjentów obsłużyły Punkty Pobrań w danym zakresie dni"
        ),
        LabSelector(multiselect=True, field="laboratoria", title="Laboratoria"),
        DateInput(field="dataod", title="Data początkowa", default="-7D"),
        DateInput(field="datado", title="Data końcowa", default="-1D"),
        # Switch(field="rentownosc", title='Tylko wykaz zleceń na potrzeby obliczania rentowności'),
    ),
)

SQL_ILE = """
    select
        z.datarejestracji as DATA,
        k.symbol as SYMBOL,
        k.nazwa as NAZWA,
        count (z.id) as ILOSC
    from zlecenia z
        left outer join pracownicy p on p.id = z.pracownikodrejestracji
        left outer join kanaly k on k.id = p.kanalinternetowy
    where z.datarejestracji between ? and ? and  z.pracownikodrejestracji is not null and p.kanalinternetowy is not null
    group by z.datarejestracji, k.symbol, k.nazwa
    order by z.datarejestracji, k.symbol
"""

SQL_SP = """
    select
        k.symbol as SYMBOL,
        k.nazwa as NAZWA,
        pl.symbol as PLATNIKS,
        pl.nazwa as PLATNIK,
        gp.symbol as GPL,
        count (distinct z.id) as ILOSC,
        count (w.id) as BAD,
        sum (w.cena) as WART,
        cast (list(distinct z.id, ';') as varchar(32765)) as LISTA
    from zlecenia z
        left outer join pracownicy p on p.id = z.pracownikodrejestracji
        left outer join kanaly k on k.id = p.kanalinternetowy
        left outer join platnicy pl on pl.id =z.platnik
        left outer join wykonania w on w.zlecenie=z.id
        left outer join Badania B on w.badanie = b.id
        left outer join GrupyBadan GB on GB.Id = B.Grupa
        left outer join GrupyPlatnikow GP on GP.Id = pl.Grupa
    where z.datarejestracji between ? and ? and  z.pracownikodrejestracji is not null and p.kanalinternetowy is not null and w.anulowane is null and w.platne = '1' and (GB.Symbol != 'TECHNIC' or GB.Symbol is null)
    group by pl.symbol, pl.nazwa, gp.symbol, k.symbol, k.nazwa
    order by k.symbol, pl.nazwa;
"""

SQL_SP_PG = """
    select
        k.symbol as SYMBOL,
        k.nazwa as NAZWA,
        pl.symbol as PLATNIKS,
        pl.nazwa as PLATNIK,
        gp.symbol as GPL,
        count (distinct z.id) as ILOSC,
        count (w.id) as BAD,
        sum (w.cena) as WART,
        string_agg(distinct z.id::text) as LISTA
    from zlecenia z
        left outer join pracownicy p on p.id = z.pracownikodrejestracji
        left outer join kanaly k on k.id = p.kanalinternetowy
        left outer join platnicy pl on pl.id =z.platnik
        left outer join wykonania w on w.zlecenie=z.id
        left outer join Badania B on w.badanie = b.id
        left outer join GrupyBadan GB on GB.Id = B.Grupa
        left outer join GrupyPlatnikow GP on GP.Id = pl.Grupa
    where z.datarejestracji between ? and ? and  z.pracownikodrejestracji is not null and p.kanalinternetowy is not null and w.anulowane is null and w.platne = '1' and (GB.Symbol != 'TECHNIC' or GB.Symbol is null)
    group by pl.symbol, pl.nazwa, gp.symbol, k.symbol, k.nazwa
    order by k.symbol, pl.nazwa;
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params["laboratoria"]) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    # validate_date_range(params['dataod'], params['datado'], max_days=31)
    for lab in params["laboratoria"]:
        task = {
            "type": "centrum",
            "priority": 1,
            "params": params,
            "target": lab,
            "function": "ile_zlecen_pp",
        }
        report.create_task(task)
    for lab in params["laboratoria"]:
        task = {
            "type": "centrum",
            "priority": 1,
            "params": params,
            "target": lab,
            "function": "ile_zlecen_pp_platnik",
        }
        report.create_task(task)
    for lab in params["laboratoria"]:
        task = {
            "type": "centrum",
            "priority": 1,
            "params": params,
            "target": lab,
            "function": "ile_zlecen_pp_platnik_hl7",
        }
        report.create_task(task)
    for lab in params["laboratoria"]:
        task = {
            "type": "centrum",
            "priority": 1,
            "params": params,
            "target": lab,
            "function": "ile_pakietow_pp",
        }
        report.create_task(task)
    report.save()
    return report


def ile_zlecen_pp(task_params):
    params = task_params["params"]
    lab = task_params["target"]

    wiersze = []
    TabZlecenia = []
    TabDatyPAK = []
    TabKanalyPAK = []
    zestaw = []
    with get_centrum_connection(lab) as conn:
        cols, rows = conn.raport_z_kolumnami(
            SQL_ILE, [params["dataod"], params["datado"]]
        )
        for row in rows:
            TabZlecenia.append(
                {
                    "data": prepare_for_json(row[0]),
                    "symbol": prepare_for_json(row[1]),
                    "ilosc": prepare_for_json(row[3]),
                }
            )
            if prepare_for_json(row[0]) not in TabDatyPAK:
                TabDatyPAK.append(prepare_for_json(row[0]))
            if prepare_for_json(row[1]) not in TabKanalyPAK:
                TabKanalyPAK.append(prepare_for_json(row[1]))
            wiersze.append(prepare_for_json(row))

    for symbol in TabKanalyPAK:
        linia = []
        linia.append(symbol)
        for data in TabDatyPAK:
            ilosc = ""
            for zlecenie in TabZlecenia:
                if zlecenie["data"] == data:
                    if zlecenie["symbol"] == symbol:
                        ilosc = zlecenie["ilosc"]
            linia.append(ilosc)
        zestaw.append(linia)
    if len(wiersze) == 0:
        return {"title": lab, "type": "info", "text": "%s  - Brak danych" % lab}
    else:
        return {
            "type": "table",
            "title": lab,
            "header": ("Symbol, " + ",".join(TabDatyPAK)).split(","),
            "data": zestaw,
        }


def ile_zlecen_pp_platnik(task_params):
    params = task_params["params"]
    lab = task_params["target"]
    snr = SNR()
    wiersze = []
    wierszeg = []
    TabSkadPacjent = []
    TabSkadPacjentGrupa = []
    TabKanalySP = []
    TabPlatnicySP = []
    TabGrupa = []
    TabKanalyGrupa = []

    with get_centrum_connection(lab) as conn:
        if conn.db_engine == "postgres":
            sql = SQL_SP_PG
        else:
            sql = SQL_SP
        cols, rows = conn.raport_z_kolumnami(sql, [params["dataod"], params["datado"]])
        for row in rows:
            if (
                next(
                    (
                        i
                        for i in TabPlatnicySP
                        if i["symbol"] == prepare_for_json(row[2])
                    ),
                    None,
                )
                == None
            ):
                TabPlatnicySP.append(
                    {
                        "symbol": prepare_for_json(row[2]),
                        "nazwa": prepare_for_json(row[3]),
                    }
                )
            if (
                next(
                    (
                        i
                        for i in TabKanalyGrupa
                        if i["symbol"] == prepare_for_json(row[0])
                    ),
                    None,
                )
                == None
            ):
                TabKanalyGrupa.append(
                    {
                        "symbol": prepare_for_json(row[0]),
                        "nazwa": prepare_for_json(row[1]),
                    }
                )
            if (
                next(
                    (i for i in TabGrupa if i["Gpl"] == prepare_for_json(row[4])), None
                )
                == None
            ):
                TabGrupa.append({"Gpl": prepare_for_json(row[4])})

            sqlSNR = (
                "select sum(w.nettodlaplatnika) as wart from Wykonania W where W.datarejestracji between '%s' and '%s' and w.laboratorium = '%s' and w.zlecenie in ('%s') and not W.bezplatne; "
                % (
                    params["dataod"],
                    params["datado"],
                    lab,
                    row[8].replace(";", "^%s' ,'" % lab) + "^%s" % lab,
                )
            )
            _, rows = snr.select(sqlSNR)
            wartosc = 0
            if row[7] is None:
                wartosc = rows[0][0]
            else:
                wartosc = row[7]

            TabSkadPacjent.append(
                {
                    "Symbol": prepare_for_json(row[0]),
                    "Platnik": prepare_for_json(row[2]),
                    "Ilosc": prepare_for_json(row[5]),
                    "Badania": prepare_for_json(row[6]),
                    "Wartosc": prepare_for_json(wartosc),
                }
            )

        for platnik in TabPlatnicySP:
            linia = []
            for kanal in TabKanalyGrupa:
                dane = next(
                    (
                        i
                        for i in TabSkadPacjent
                        if i["Platnik"] == platnik["symbol"]
                        and i["Symbol"] == kanal["symbol"]
                    ),
                    {
                        "Symbol": kanal["symbol"],
                        "Platnik": platnik["symbol"],
                        "Ilosc": "",
                        "Badania": "",
                        "Wartosc": "",
                    },
                )
                if dane != None:
                    linia.append(list(dane.values())[2])
                    linia.append(list(dane.values())[3])
                    linia.append(list(dane.values())[4])
            wiersze.append(list(platnik.values()) + linia)

        suma = ["W SUMIE", "W sumie"]
        for kanal in TabKanalyGrupa:
            iloscZlecen = 0
            iloscBadan = 0
            wartosc = 0
            for i in TabSkadPacjent:
                if i["Symbol"] == kanal["symbol"]:
                    iloscZlecen = iloscZlecen + int(i["Ilosc"])
                    iloscBadan = iloscBadan + int(i["Badania"])
                    if i["Wartosc"] != "" and i["Wartosc"] != None:
                        wartosc = wartosc + float(i["Wartosc"] or 0.0)
            suma.append(iloscZlecen)
            suma.append(iloscBadan)
            suma.append((format(float(wartosc), "7.2f")))
        wiersze.append(suma)

        header = ["Symbol", "Nazwa płatnika"]
        for platnik in TabPlatnicySP:
            header.append({"title": platnik["symbol"], "colspan": 3})

        for platnik in TabPlatnicySP:
            if "GOTO" in platnik["symbol"]:
                for kanal in TabKanalyGrupa:
                    daneg = next(
                        (
                            i
                            for i in TabSkadPacjent
                            if i["Platnik"] == platnik["symbol"]
                            and i["Symbol"] == kanal["symbol"]
                        ),
                        None,
                    )
                    if daneg != None:
                        linia = [kanal["symbol"], kanal["nazwa"]]
                        linia.append(list(daneg.values())[2])
                        linia.append(list(daneg.values())[3])
                        linia.append(list(daneg.values())[4])
                        srednia = format(
                            float(list(daneg.values())[4])
                            / float(list(daneg.values())[2]),
                            "7.2f",
                        )
                        linia.append(srednia)
                        wierszeg.append(linia)
    headerFull = []
    headerlist = []
    header = []
    header.append({"title": "Symbol płatnika", "rowspan": 2, "fontstyle": "b"})
    header.append({"title": "Nazwa płatnika", "rowspan": 2, "fontstyle": "b"})
    for kanal in TabKanalyGrupa:
        header.append(
            {"title": kanal["symbol"], "rowspan": 1, "colspan": 3, "fontstyle": "b"}
        )
    headerFull.append(header)
    for kanal in TabKanalyGrupa:
        headerlist.append({"title": "Ilość zleceń"})
        headerlist.append({"title": "Ilość badań"})
        headerlist.append({"title": "Wartość"})
    headerFull.append(headerlist)

    if len(wiersze) == 0:
        return {"title": lab, "type": "info", "text": "%s  - Brak danych" % lab}
    else:
        return [
            {
                "type": "table",
                "title": "wykaz ile zleceń dla danego płatnika zarejestrował punkt rejstrujące się samodzielnie przez iCentrum w okresie od %s do %s"
                % (params["dataod"], params["datado"]),
                "header": headerFull,
                "data": wiersze,
            },
            {
                "type": "table",
                "title": "wykaz wartości sprzedaży gotówkowej w ramach zleceń zarejestrowanych przez iCentrum w punkcie pobrań od %s do %s z uwzględnieniem średniej ceny paragonu"
                % (params["dataod"], params["datado"]),
                "header": "Symbol \nPunktu Pobrań,Nazwa\nPunktu Pobrań,Ilość Zleceń,Ilość Badań,Wartość,Średnia Cena Paragonu".split(
                    ","
                ),
                "data": wierszeg,
            },
        ]


def ile_zlecen_pp_platnik_hl7(task_params):
    params = task_params["params"]
    lab = task_params["target"]
    sqlDH = """select
			p.NAZWISKO as SYMBOL,
			p.NAZWISKO as NAZWA,
			pl.symbol as PLATNIKS,
			pl.nazwa as PLATNIKN,
			gp.symbol as GPL,
			count (distinct z.id) as ILOSC,
			count (w.id) as BAD,
			sum (w.cena) as WART,
			cast (list(distinct z.id, ';') as varchar(32765)) as LISTA,
			cast (list(distinct z.OBCYKODKRESKOWY, ';') as varchar(32000)) as KODY
		from zlecenia z
			left outer join wykonania w on w.zlecenie=z.id
			left outer join POBORCY p on p.id = w.POBORCA
			left outer join platnicy pl on pl.id =z.platnik
			left outer join Badania B on w.badanie = b.id
			left outer join GrupyBadan GB on GB.Id = B.Grupa	
			left outer join GrupyPlatnikow GP on GP.Id = pl.Grupa
		where z.datarejestracji between ? and ? and w.anulowane is null and w.platne = '1' and (GB.Symbol != 'TECHNIC' or GB.Symbol is null) and UPPER (p.NAZWISKO) = UPPER(p.NUMER) and p.HL7SYSID is not NULL
		group by pl.symbol, pl.nazwa, gp.symbol, p.NAZWISKO
		order by p.NAZWISKO, pl.nazwa; """

    sqlDH_PG = """select
			p.NAZWISKO as SYMBOL,
			p.NAZWISKO as NAZWA,
			pl.symbol as PLATNIKS,
			pl.nazwa as PLATNIKN,
			gp.symbol as GPL,
			count (distinct z.id) as ILOSC,
			count (w.id) as BAD,
			sum (w.cena) as WART,
			string_agg(distinct z.id::text) as LISTA,
			string_agg(distinct z.OBCYKODKRESKOWY::text) as KODY
		from zlecenia z
			left outer join wykonania w on w.zlecenie=z.id
			left outer join POBORCY p on p.id = w.POBORCA
			left outer join platnicy pl on pl.id =z.platnik
			left outer join Badania B on w.badanie = b.id
			left outer join GrupyBadan GB on GB.Id = B.Grupa	
			left outer join GrupyPlatnikow GP on GP.Id = pl.Grupa
		where z.datarejestracji between ? and ? and w.anulowane is null and w.platne = '1' and (GB.Symbol != 'TECHNIC' or GB.Symbol is null) and UPPER (p.NAZWISKO) = UPPER(p.NUMER) and p.HL7SYSID is not NULL
		group by pl.symbol, pl.nazwa, gp.symbol, p.NAZWISKO
		order by p.NAZWISKO, pl.nazwa; """

    snr = SNR()
    hbz = HBZ()

    wiersze = []
    oddzialy = []
    platnicy = []
    zestaw = []
    with get_centrum_connection(lab) as conn:
        if conn.db_engine == "postgres":
            sql = sqlDH_PG
        else:
            sql = sqlDH

        cols, rows = conn.raport_z_kolumnami(sql, [params["dataod"], params["datado"]])
        for row in rows:
            pozycje = []
            if (
                next(
                    (
                        i
                        for i in oddzialy
                        if i["symbol"] == prepare_for_json(row[0])
                        and i["nazwa"] == prepare_for_json(row[1])
                    ),
                    None,
                )
                == None
            ):
                oddzialy.append(
                    {
                        "symbol": prepare_for_json(row[0]),
                        "nazwa": prepare_for_json(row[1]),
                    }
                )
            if (
                next(
                    (
                        i
                        for i in platnicy
                        if i["symbol"] == prepare_for_json(row[2])
                        and i["nazwa"] == prepare_for_json(row[3])
                    ),
                    None,
                )
                == None
            ):
                platnicy.append(
                    {
                        "symbol": prepare_for_json(row[2]),
                        "nazwa": prepare_for_json(row[3]),
                    }
                )

            sqlSNR = (
                "select sum(w.nettodlaplatnika) as wart from Wykonania W where W.datarejestracji between '%s' and '%s' and w.laboratorium = '%s' and w.zlecenie in ('%s') and not W.bezplatne; "
                % (
                    params["dataod"],
                    params["datado"],
                    lab,
                    row[8].replace(";", "^%s' ,'" % lab) + "^%s" % lab,
                )
            )
            _, rowsSNR = snr.select(sqlSNR)
            wartosc = row[7]
            if row[7] is None:
                wartosc = rowsSNR[0][0]
            pozycje.append(row[0])
            pozycje.append(row[1])
            pozycje.append(row[2])
            pozycje.append(row[3])
            pozycje.append(row[4])
            pozycje.append(row[5])
            pozycje.append(row[6])
            pozycje.append(prepare_for_json(wartosc))
            wiersze.append(pozycje)

    for platnik in platnicy:
        wiersz = []
        wiersz.append(platnik["symbol"])
        wiersz.append(platnik["nazwa"])
        for oddzial in oddzialy:
            iloscZlecen = ""
            iloscBadan = ""
            wartosc = ""
            for i in wiersze:
                if i[0] == oddzial["symbol"] and i[2] == platnik["symbol"]:
                    iloscZlecen = i[5]
                    iloscBadan = i[6]
                    wartosc = i[7]
            wiersz.append(iloscZlecen)
            wiersz.append(iloscBadan)
            wiersz.append(wartosc)
        zestaw.append(wiersz)

    # print(wiersze)
    # print(oddzialy)
    suma = ["W SUMIE", "W Sumie"]
    for oddzial in oddzialy:
        iloscZlecenSuma = 0
        iloscBadanSuma = 0
        wartoscSuma = 0
        for wiersz in wiersze:
            if wiersz[0] == oddzial["symbol"]:
                iloscZlecenSuma = iloscZlecenSuma + wiersz[5]
                iloscBadanSuma = iloscBadanSuma + wiersz[6]
                if wiersz[7] != None:
                    wartoscSuma = wartoscSuma + float(wiersz[7] or 0.0)
        suma.append(iloscZlecenSuma)
        suma.append(iloscBadanSuma)
        suma.append((format(float(wartoscSuma), "7.2f")))

    zestaw.append(suma)

    headerFull = []
    headerlist = []
    header = []
    header.append({"title": "Symbol Płatnika", "rowspan": 2, "fontstyle": "b"})
    header.append({"title": "Nazwa Płatnika", "rowspan": 2, "fontstyle": "b"})
    for oddzial in oddzialy:
        header.append(
            {"title": oddzial["nazwa"], "rowspan": 1, "colspan": 3, "fontstyle": "b"}
        )
    headerFull.append(header)
    for oddzial in oddzialy:
        headerlist.append({"title": "Ilość Zleceń"})
        headerlist.append({"title": "Ilość Badań"})
        headerlist.append({"title": "Wartość"})
    headerFull.append(headerlist)

    if len(zestaw) == 0:
        return {"title": lab, "type": "info", "text": "%s  - Brak danych" % lab}
    else:
        return {
            "type": "table",
            "title": "wykaz ile zleceń dla danego płatnika zarejestrował punkt poprzez moduł dystrybucji HL7 w okresie od %s do %s"
            % (params["dataod"], params["datado"]),
            "header": headerFull,
            "data": zestaw,
        }


def ile_pakietow_pp(task_params):
    params = task_params["params"]
    lab = task_params["target"]
    SQL_PAK = """
        select
            z.datarejestracji as DATA,
            k.symbol as SYMBOL,
            k.nazwa as NAZWA,
            count (w.id) as ILOSC,
            sum (w.cena) as WART
        from wykonania w
            left outer join zlecenia z on z.id=w.zlecenie
            left outer join pracownicy p on p.id = z.pracownikodrejestracji
            left outer join kanaly k on k.id = p.kanalinternetowy
            left outer join Badania B on w.badanie = b.id
            left outer join GrupyBadan GB on GB.Id = B.Grupa
        where z.datarejestracji between ? and ? and  z.pracownikodrejestracji is not null and p.kanalinternetowy is not null and 
            w.anulowane is null and w.platne = '1' and (GB.Symbol != 'TECHNIC' or GB.Symbol is null) and b.pakiet ='1' and b.rejestrowac ='1' and b.zerowacceny='1'
        group by z.datarejestracji, k.symbol, k.nazwa
        order by z.datarejestracji, k.symbol;
    """

    wiersze = []
    zestaw = []

    kanaly = []
    dni = []
    with get_centrum_connection(lab) as conn:
        cols, rows = conn.raport_z_kolumnami(
            SQL_PAK, [params["dataod"], params["datado"]]
        )
        for row in rows:
            wiersze.append(prepare_for_json(row))
            if prepare_for_json(row[0]) not in dni:
                dni.append(prepare_for_json(row[0]))
            if (
                next(
                    (
                        i
                        for i in kanaly
                        if i["symbol"] == prepare_for_json(row[1])
                        and i["nazwa"] == prepare_for_json(row[2])
                    ),
                    None,
                )
                == None
            ):
                kanaly.append(
                    {
                        "symbol": prepare_for_json(row[1]),
                        "nazwa": prepare_for_json(row[2]),
                    }
                )

    for kanal in kanaly:
        wiersz = []
        wiersz.append(kanal["symbol"])
        wiersz.append(kanal["nazwa"])
        for dzien in dni:
            ilosc = ""
            wartosc = ""
            for i in wiersze:
                if i[0] == dzien and i[1] == kanal["symbol"]:
                    ilosc = i[3]
                    wartosc = i[4]
            wiersz.append(ilosc)
            wiersz.append(wartosc)
        zestaw.append(wiersz)

    iloscPakietow = 0
    wartoscPakietow = 0
    for wiersz in wiersze:
        # print(wiersz[3])
        # print(wiersz[4])
        iloscPakietow = iloscPakietow + wiersz[3]
        wartoscPakietow = wartoscPakietow + float(wiersz[4] or 0.0)

    headerFull = []
    headerlist = []
    header = []
    header.append({"title": "Symbol", "rowspan": 2, "fontstyle": "b"})
    header.append({"title": "Nazwa punktu pobrań", "rowspan": 2, "fontstyle": "b"})
    for dzien in dni:
        header.append({"title": dzien, "rowspan": 1, "colspan": 2, "fontstyle": "b"})
    headerFull.append(header)
    for dzien in dni:
        headerlist.append({"title": "Ilość"})
        headerlist.append({"title": "Wartość"})
    headerFull.append(headerlist)

    if len(zestaw) == 0:
        return {"title": lab, "type": "info", "text": "%s  - Brak danych" % lab}
    else:
        return {
            "type": "table",
            "title": "Wykaz ile pakietów gotówkowych zarejestrowano przez iCentrum w punkcie pobrań od %s do %s z podziałem na poszczególne dni. Łącznie sprzedano %s pakietów na kwotę %s"
            % (
                params["dataod"],
                params["datado"],
                str(iloscPakietow),
                str(format(wartoscPakietow, "7.2f")),
            ),
            "header": headerFull,
            "data": zestaw,
        }
