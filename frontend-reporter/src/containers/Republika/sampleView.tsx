import React from "react";
import {RepublikaEventStreamView} from "./republika";


const ZLECENIE = {
    "events": [{
        "id": 237414,
        "src": "BELCHAT",
        "trans_id": 3848937,
        "src_ts": "2023-03-15 08:23",
        "repl_ts": "2023-03-15 08:23",
        "event_ts": "2023-03-15 08:23",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": null,
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntZlecUtworzone",
        "event_data": {"sys_id": 495772, "system": "BELCHAT"}
    }, {
        "id": 237415,
        "src": "BELCHAT",
        "trans_id": 3848937,
        "src_ts": "2023-03-15 08:23",
        "repl_ts": "2023-03-15 08:23",
        "event_ts": "2023-03-15 07:59",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": null,
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntZlecRejestracjaZNumerem",
        "event_data": {
            "numer": 104,
            "pracownik": "BELCHAT:364953",
            "kodkreskowy": "5905146250",
            "data_rejestracji": "2023-03-15",
            "kanal_internetowy": null,
            "zewnetrzny_identyfikator": null
        }
    }, {
        "id": 237416,
        "src": "BELCHAT",
        "trans_id": 3848937,
        "src_ts": "2023-03-15 08:23",
        "repl_ts": "2023-03-15 08:23",
        "event_ts": "2023-03-15 08:23",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": null,
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntZlecKomentarz",
        "event_data": {"komentarz": "", "pracownik": "BELCHAT:364953"}
    }, {
        "id": 237417,
        "src": "BELCHAT",
        "trans_id": 3848937,
        "src_ts": "2023-03-15 08:23",
        "repl_ts": "2023-03-15 08:23",
        "event_ts": "2023-03-15 08:23",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": null,
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntZlecOpis",
        "event_data": {"opis": "", "pracownik": "BELCHAT:364953"}
    }, {
        "id": 237418,
        "src": "BELCHAT",
        "trans_id": 3848937,
        "src_ts": "2023-03-15 08:23",
        "repl_ts": "2023-03-15 08:23",
        "event_ts": "2023-03-15 08:23",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": null,
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntZlecDaneRejestracyjne",
        "event_data": {
            "dzm": null,
            "waga": null,
            "dyzur": false,
            "pilne": false,
            "lekarz": {
                "id": "BELCHAT:316",
                "adres": null,
                "numer": null,
                "tytul": null,
                "imiona": null,
                "hl7sysid": null,
                "nazwisko": "P\u0142atne",
                "telefony": null,
                "miejscepracy": null,
                "specjalizacja": null
            },
            "pacjent": {
                "id": "BELCHAT:159028",
                "plec": "K",
                "adres": null,
                "email": "",
                "pesel": "88121509280",
                "imiona": "Justyna",
                "telefon": "663191643",
                "hl7sysid": null,
                "nazwisko": "Ochman",
                "dodatkowe": "",
                "data_urodzenia": "1988-12-15"
            },
            "platnik": "EBGOTOW",
            "kontrolne": false,
            "kodkreskowy": "5905146250",
            "niekompletne": false,
            "profilaktyka": false,
            "typ_zlecenia": "R",
            "zleceniodawca": "EB-ALAB",
            "obcykodkreskowy": null,
            "status_pacjenta": null,
            "miejsceodeslania": 0,
            "nieprawidlowedane": false,
            "opismiejscaodeslania": null,
            "projektowana_godzina": null,
            "zewnetrzny_identyfikator": null
        }
    }, {
        "id": 237419,
        "src": "BELCHAT",
        "trans_id": 3848939,
        "src_ts": "2023-03-15 08:23",
        "repl_ts": "2023-03-15 08:23",
        "event_ts": "2023-03-15 08:23",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykUtworzone",
        "event_data": {
            "pakiet": null,
            "sys_id": 4624740,
            "system": "BELCHAT",
            "badanie": "P-MOCZ",
            "material": "MOCZ-P",
            "powtorka": false,
            "jest_pakietem": false,
            "jest_skladowa": false
        }
    }, {
        "id": 237420,
        "src": "BELCHAT",
        "trans_id": 3848939,
        "src_ts": "2023-03-15 08:23",
        "repl_ts": "2023-03-15 08:23",
        "event_ts": "2023-03-15 08:23",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZmianaMetody",
        "event_data": {"aparat": "X-WYSYL", "metoda": "X-ZBAKT", "pracownia": "X-ZBAKT", "pracownik": null}
    }, {
        "id": 237421,
        "src": "BELCHAT",
        "trans_id": 3848939,
        "src_ts": "2023-03-15 08:23",
        "repl_ts": "2023-03-15 08:23",
        "event_ts": "2023-03-15 08:23",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZmianaMaterialu",
        "event_data": {"material": "MOCZ-P "}
    }, {
        "id": 237422,
        "src": "BELCHAT",
        "trans_id": 3848939,
        "src_ts": "2023-03-15 08:23",
        "repl_ts": "2023-03-15 08:23",
        "event_ts": "2023-03-15 08:23",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZmianaPlatnika",
        "event_data": {"zgodny": true, "pracownik": null, "platnik_zlecenia": "EBGOTOW", "platnik_wykonania": "EBGOTOW"}
    }, {
        "id": 237423,
        "src": "BELCHAT",
        "trans_id": 3848939,
        "src_ts": "2023-03-15 08:23",
        "repl_ts": "2023-03-15 08:23",
        "event_ts": "2023-03-15 08:23",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZmianaOdplatnosci",
        "event_data": {"koszt": null, "platne": true, "punkty": null, "pracownik": null, "na_koszt_labu": true}
    }, {
        "id": 237424,
        "src": "BELCHAT",
        "trans_id": 3848939,
        "src_ts": "2023-03-15 08:23",
        "repl_ts": "2023-03-15 08:23",
        "event_ts": "2023-03-15 04:36",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykPobrane",
        "event_data": {"poborca": null}
    }, {
        "id": 237425,
        "src": "BELCHAT",
        "trans_id": 3848940,
        "src_ts": "2023-03-15 08:23",
        "repl_ts": "2023-03-15 08:23",
        "event_ts": "2023-03-15 07:59",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZmianaPlatnika",
        "event_data": {
            "zgodny": true,
            "pracownik": "BELCHAT:364953",
            "platnik_zlecenia": "EBGOTOW",
            "platnik_wykonania": null
        }
    }, {
        "id": 237426,
        "src": "BELCHAT",
        "trans_id": 3848940,
        "src_ts": "2023-03-15 08:23",
        "repl_ts": "2023-03-15 08:23",
        "event_ts": "2023-03-15 08:23",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWycenaWLab",
        "event_data": {"cena": 37.0, "cennik": "CENG   ", "stawka_vat": "AL     "}
    }, {
        "id": 237436,
        "src": "BELCHAT",
        "trans_id": 3848945,
        "src_ts": "2023-03-15 08:23",
        "repl_ts": "2023-03-15 08:23",
        "event_ts": "2023-03-15 08:23",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": null,
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntZlecOpis",
        "event_data": {"opis": "Kobieta w ci\u0105\u017cy", "pracownik": "BELCHAT:364953"}
    }, {
        "id": 237437,
        "src": "BELCHAT",
        "trans_id": 3848946,
        "src_ts": "2023-03-15 08:23",
        "repl_ts": "2023-03-15 08:23",
        "event_ts": "2023-03-15 07:59",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZmianaPlatnika",
        "event_data": {
            "zgodny": true,
            "pracownik": "BELCHAT:364953",
            "platnik_zlecenia": "EBGOTOW",
            "platnik_wykonania": null
        }
    }, {
        "id": 237438,
        "src": "BELCHAT",
        "trans_id": 3848946,
        "src_ts": "2023-03-15 08:23",
        "repl_ts": "2023-03-15 08:23",
        "event_ts": "2023-03-15 08:23",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWycenaWLab",
        "event_data": {"cena": 37.0, "cennik": "CENG   ", "stawka_vat": "AL     "}
    }, {
        "id": 237445,
        "src": "BELCHAT",
        "trans_id": 3848950,
        "src_ts": "2023-03-15 08:24",
        "repl_ts": "2023-03-15 08:24",
        "event_ts": "2023-03-15 07:59",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZmianaPlatnika",
        "event_data": {
            "zgodny": true,
            "pracownik": "BELCHAT:364953",
            "platnik_zlecenia": "EBGOTOW",
            "platnik_wykonania": null
        }
    }, {
        "id": 237446,
        "src": "BELCHAT",
        "trans_id": 3848950,
        "src_ts": "2023-03-15 08:24",
        "repl_ts": "2023-03-15 08:24",
        "event_ts": "2023-03-15 08:24",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWycenaWLab",
        "event_data": {"cena": 37.0, "cennik": "CENG   ", "stawka_vat": "AL     "}
    }, {
        "id": 244657,
        "src": "BELCHAT",
        "trans_id": 3851217,
        "src_ts": "2023-03-15 08:54",
        "repl_ts": "2023-03-15 08:54",
        "event_ts": "2023-03-15 08:30",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZmianaPlatnika",
        "event_data": {
            "zgodny": true,
            "pracownik": "BELCHAT:632617",
            "platnik_zlecenia": "EBGOTOW",
            "platnik_wykonania": null
        }
    }, {
        "id": 244658,
        "src": "BELCHAT",
        "trans_id": 3851217,
        "src_ts": "2023-03-15 08:54",
        "repl_ts": "2023-03-15 08:54",
        "event_ts": "2023-03-15 08:54",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWycenaWLab",
        "event_data": {"cena": 37.0, "cennik": "CENG   ", "stawka_vat": "AL     "}
    }, {
        "id": 244659,
        "src": "BELCHAT",
        "trans_id": 3851217,
        "src_ts": "2023-03-15 08:54",
        "repl_ts": "2023-03-15 08:54",
        "event_ts": "2023-03-15 08:30",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykKodKreskowyNadanie",
        "event_data": {"pracownik": "BELCHAT:632617", "kodkreskowy": "5905146251"}
    }, {
        "id": 244660,
        "src": "BELCHAT",
        "trans_id": 3851222,
        "src_ts": "2023-03-15 08:55",
        "repl_ts": "2023-03-15 08:55",
        "event_ts": "2023-03-15 08:55",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": null,
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntZlecOpis",
        "event_data": {"opis": "Kobieta w ci\u0105\u017cy", "pracownik": "BELCHAT:364953"}
    }, {
        "id": 244661,
        "src": "BELCHAT",
        "trans_id": 3851222,
        "src_ts": "2023-03-15 08:55",
        "repl_ts": "2023-03-15 08:55",
        "event_ts": "2023-03-15 08:30",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZmianaPlatnika",
        "event_data": {
            "zgodny": true,
            "pracownik": "BELCHAT:632617",
            "platnik_zlecenia": "EBGOTOW",
            "platnik_wykonania": null
        }
    }, {
        "id": 244662,
        "src": "BELCHAT",
        "trans_id": 3851222,
        "src_ts": "2023-03-15 08:55",
        "repl_ts": "2023-03-15 08:55",
        "event_ts": "2023-03-15 08:55",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWycenaWLab",
        "event_data": {"cena": 37.0, "cennik": "CENG   ", "stawka_vat": "AL     "}
    }, {
        "id": 244663,
        "src": "BELCHAT",
        "trans_id": 3851222,
        "src_ts": "2023-03-15 08:55",
        "repl_ts": "2023-03-15 08:55",
        "event_ts": "2023-03-15 08:31",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykDystrybucja",
        "event_data": {"material": "MOCZ-P ", "pracownik": "BELCHAT:632617", "kodkreskowy": "5905146251"}
    }, {
        "id": 346870,
        "src": "BELCHAT",
        "trans_id": 3873416,
        "src_ts": "2023-03-15 14:22",
        "repl_ts": "2023-03-15 14:22",
        "event_ts": "2023-03-15 08:30",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykListaRobocza",
        "event_data": {
            "statyw": null,
            "pracownik": "BELCHAT:632617",
            "polozenie_x": null,
            "polozenie_y": null,
            "lista_robocza": "BELCHAT:1132041"
        }
    }, {
        "id": 347619,
        "src": "BELCHAT",
        "trans_id": 3873837,
        "src_ts": "2023-03-15 14:25",
        "repl_ts": "2023-03-15 14:25",
        "event_ts": "2023-03-15 08:30",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykListaRobocza",
        "event_data": {
            "statyw": null,
            "pracownik": "BELCHAT:632617",
            "polozenie_x": null,
            "polozenie_y": null,
            "lista_robocza": "BELCHAT:1132041"
        }
    }, {
        "id": 347620,
        "src": "BELCHAT",
        "trans_id": 3873837,
        "src_ts": "2023-03-15 14:25",
        "repl_ts": "2023-03-15 14:25",
        "event_ts": "2023-03-15 08:30",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykIdentyfikatorNadanie",
        "event_data": {"pracownik": "BELCHAT:632617", "identyfikator": "5905146251"}
    }, {
        "id": 349902,
        "src": "BELCHAT",
        "trans_id": 3873932,
        "src_ts": "2023-03-15 14:30",
        "repl_ts": "2023-03-15 14:30",
        "event_ts": "2023-03-15 08:30",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykListaRobocza",
        "event_data": {
            "statyw": null,
            "pracownik": "BELCHAT:632617",
            "polozenie_x": null,
            "polozenie_y": null,
            "lista_robocza": "BELCHAT:1132041"
        }
    }, {
        "id": 349903,
        "src": "BELCHAT",
        "trans_id": 3873932,
        "src_ts": "2023-03-15 14:30",
        "repl_ts": "2023-03-15 14:30",
        "event_ts": "2023-03-15 14:06",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykCzynnoscTechniczna",
        "event_data": {"czynnosc": "wyslanezlecenie"}
    }, {
        "id": 349904,
        "src": "BELCHAT",
        "trans_id": 3873932,
        "src_ts": "2023-03-15 14:30",
        "repl_ts": "2023-03-15 14:30",
        "event_ts": "2023-03-15 08:30",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykIdentyfikatorNadanie",
        "event_data": {"pracownik": "BELCHAT:632617", "identyfikator": "5905146251"}
    }, {
        "id": 820112,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:30",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZmianaMetody",
        "event_data": {"aparat": "F-MAN  ", "metoda": "F-MAN  ", "pracownia": "X-ZBAKT", "pracownik": "BELCHAT:0"}
    }, {
        "id": 820113,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:54",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZmianaMaterialu",
        "event_data": {"material": "MOCZ-T "}
    }, {
        "id": 820114,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:30",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykListaRobocza",
        "event_data": {
            "statyw": null,
            "pracownik": "BELCHAT:0",
            "polozenie_x": null,
            "polozenie_y": null,
            "lista_robocza": null
        }
    }, {
        "id": 820115,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:54",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykPowtorka",
        "event_data": {"liczba_powtorzen": 1}
    }, {
        "id": 820116,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:30",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWydruk",
        "event_data": {
            "wyniki": [{
                "id": "BELCHAT:484478875",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": false,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Wynik badania:",
                    "format": null,
                    "symbol": "WYNIK",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": "Results:"
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": "",
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": "Drobnoustroj\u00f3w uropatogennych w mianie >=10^2 CFU/ml nie wyhodowano",
                "flaga_deltacheck": 0
            }, {
                "id": "BELCHAT:484478874",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": false,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Uwagi:",
                    "format": null,
                    "symbol": "UWAGI",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": null
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": null,
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": null,
                "flaga_deltacheck": null
            }],
            "ponowny": false,
            "pracownik": null,
            "dane_wykonania": {
                "aparat": {"nazwa": "Manualnie (Zawodzie Warszawa)", "symbol": "F-MAN"},
                "metoda": {
                    "kod": null,
                    "opis": null,
                    "nazwa": "Manualnie (Bakteriologia Zawodzie)",
                    "symbol": "F-MAN",
                    "zakres_akredytacji": null
                },
                "badanie": {
                    "kod": "91.33",
                    "grupa": "BAKTER",
                    "nazwa": "Posiew moczu (91.33)",
                    "rodzaj": "POS",
                    "symbol": "P-MOCZ",
                    "nazwa_alternatywna": null
                },
                "pracownia": {
                    "grupa": "ALAB",
                    "nazwa": "Wysy\u0142ka do Warszawy Bakteriologia, Zawodzie - ALAB",
                    "symbol": "X-ZBAKT",
                    "zewnetrzna": true
                },
                "akredytacja": false
            }
        }
    }, {
        "id": 820117,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:22",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWykonanie",
        "event_data": {
            "prawie": false,
            "wyniki": [{
                "id": "BELCHAT:484478875",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": false,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Wynik badania:",
                    "format": null,
                    "symbol": "WYNIK",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": "Results:"
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": "",
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": "Drobnoustroj\u00f3w uropatogennych w mianie >=10^2 CFU/ml nie wyhodowano",
                "flaga_deltacheck": 0
            }, {
                "id": "BELCHAT:484478874",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": false,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Uwagi:",
                    "format": null,
                    "symbol": "UWAGI",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": null
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": null,
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": null,
                "flaga_deltacheck": null
            }],
            "pracownik": null,
            "dane_wykonania": {
                "aparat": {"nazwa": "Manualnie (Zawodzie Warszawa)", "symbol": "F-MAN"},
                "metoda": {
                    "kod": null,
                    "opis": null,
                    "nazwa": "Manualnie (Bakteriologia Zawodzie)",
                    "symbol": "F-MAN",
                    "zakres_akredytacji": null
                },
                "badanie": {
                    "kod": "91.33",
                    "grupa": "BAKTER",
                    "nazwa": "Posiew moczu (91.33)",
                    "rodzaj": "POS",
                    "symbol": "P-MOCZ",
                    "nazwa_alternatywna": null
                },
                "pracownia": {
                    "grupa": "ALAB",
                    "nazwa": "Wysy\u0142ka do Warszawy Bakteriologia, Zawodzie - ALAB",
                    "symbol": "X-ZBAKT",
                    "zewnetrzna": true
                },
                "akredytacja": false
            }
        }
    }, {
        "id": 820118,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:22",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZatwierdzenie",
        "event_data": {
            "wyniki": [{
                "id": "BELCHAT:484478875",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": false,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Wynik badania:",
                    "format": null,
                    "symbol": "WYNIK",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": "Results:"
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": "",
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": "Drobnoustroj\u00f3w uropatogennych w mianie >=10^2 CFU/ml nie wyhodowano",
                "flaga_deltacheck": 0
            }, {
                "id": "BELCHAT:484478874",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": false,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Uwagi:",
                    "format": null,
                    "symbol": "UWAGI",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": null
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": null,
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": null,
                "flaga_deltacheck": null
            }],
            "pracownik": null,
            "dane_wykonania": {
                "aparat": {"nazwa": "Manualnie (Zawodzie Warszawa)", "symbol": "F-MAN"},
                "metoda": {
                    "kod": null,
                    "opis": null,
                    "nazwa": "Manualnie (Bakteriologia Zawodzie)",
                    "symbol": "F-MAN",
                    "zakres_akredytacji": null
                },
                "badanie": {
                    "kod": "91.33",
                    "grupa": "BAKTER",
                    "nazwa": "Posiew moczu (91.33)",
                    "rodzaj": "POS",
                    "symbol": "P-MOCZ",
                    "nazwa_alternatywna": null
                },
                "pracownia": {
                    "grupa": "ALAB",
                    "nazwa": "Wysy\u0142ka do Warszawy Bakteriologia, Zawodzie - ALAB",
                    "symbol": "X-ZBAKT",
                    "zewnetrzna": true
                },
                "akredytacja": false
            },
            "bardzo_zatwierdzone": false
        }
    }, {
        "id": 820119,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:30",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykIdentyfikatorModyfikacja",
        "event_data": {"pracownik": "BELCHAT:0", "identyfikator": null}
    }, {
        "id": 820120,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:30",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWykonanie",
        "event_data": {
            "prawie": true,
            "wyniki": [{
                "id": "BELCHAT:484478875",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": false,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Wynik badania:",
                    "format": null,
                    "symbol": "WYNIK",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": "Results:"
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": "",
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": "Drobnoustroj\u00f3w uropatogennych w mianie >=10^2 CFU/ml nie wyhodowano",
                "flaga_deltacheck": 0
            }, {
                "id": "BELCHAT:484478874",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": false,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Uwagi:",
                    "format": null,
                    "symbol": "UWAGI",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": null
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": null,
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": null,
                "flaga_deltacheck": null
            }],
            "pracownik": "BELCHAT:0",
            "dane_wykonania": {
                "aparat": {"nazwa": "Manualnie (Zawodzie Warszawa)", "symbol": "F-MAN"},
                "metoda": {
                    "kod": null,
                    "opis": null,
                    "nazwa": "Manualnie (Bakteriologia Zawodzie)",
                    "symbol": "F-MAN",
                    "zakres_akredytacji": null
                },
                "badanie": {
                    "kod": "91.33",
                    "grupa": "BAKTER",
                    "nazwa": "Posiew moczu (91.33)",
                    "rodzaj": "POS",
                    "symbol": "P-MOCZ",
                    "nazwa_alternatywna": null
                },
                "pracownia": {
                    "grupa": "ALAB",
                    "nazwa": "Wysy\u0142ka do Warszawy Bakteriologia, Zawodzie - ALAB",
                    "symbol": "X-ZBAKT",
                    "zewnetrzna": true
                },
                "akredytacja": false
            }
        }
    }, {
        "id": 820121,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:54",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykRozliczenie",
        "event_data": {
            "blad": null,
            "koszty": true,
            "platne": true,
            "badanie": "P-MOCZ ",
            "platnik": {
                "id": "BELCHAT:698",
                "nip": null,
                "nazwa": "Got\u00f3wka ALAB EB",
                "symbol": "EBGOTOW",
                "gotowkowy": true
            },
            "material": "MOCZ-T ",
            "zleceniodawca": {
                "id": "BELCHAT:834",
                "nazwa": "Punkt pobra\u0144 ALAB (Be\u0142chat\u00f3w)",
                "symbol": "EB-ALAB",
                "platnik": "EBGOTOW",
                "gotowkowy": true
            },
            "data_rozliczeniowa": "2023-03-17",
            "inny_platnik_wykonania": null
        }
    }, {
        "id": 820122,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:54",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631353",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykUtworzone",
        "event_data": {
            "pakiet": null,
            "sys_id": 8984478,
            "system": "ZAWODZI",
            "badanie": "DZOD24H",
            "material": null,
            "powtorka": false,
            "jest_pakietem": false,
            "jest_skladowa": false
        }
    }, {
        "id": 820123,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:54",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631353",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZmianaMetody",
        "event_data": {"aparat": "F-MAN  ", "metoda": "F-MAN  ", "pracownia": "X-ZBAKT", "pracownik": null}
    }, {
        "id": 820124,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:54",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631353",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykPowtorka",
        "event_data": {"liczba_powtorzen": 1}
    }, {
        "id": 820125,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:54",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631353",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZmianaOdplatnosci",
        "event_data": {"koszt": null, "platne": true, "punkty": null, "pracownik": null, "na_koszt_labu": true}
    }, {
        "id": 820126,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:30",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631353",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWydruk",
        "event_data": {
            "wyniki": [{
                "id": "BELCHAT:484478877",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": true,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Opis",
                    "format": null,
                    "symbol": "OPIS",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": null
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": "",
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": "UJEMNY",
                "flaga_deltacheck": 0
            }],
            "ponowny": false,
            "pracownik": null,
            "dane_wykonania": {
                "aparat": {"nazwa": "Manualnie (Zawodzie Warszawa)", "symbol": "F-MAN"},
                "metoda": {
                    "kod": null,
                    "opis": null,
                    "nazwa": "Manualnie (Zawodzie Warszawa)",
                    "symbol": "F-MAN",
                    "zakres_akredytacji": null
                },
                "badanie": {
                    "kod": null,
                    "grupa": "TECHNIC",
                    "nazwa": "01. Odczyt dzie\u0144 1",
                    "rodzaj": "DZIALAN",
                    "symbol": "DZOD24H",
                    "nazwa_alternatywna": null
                },
                "pracownia": {
                    "grupa": "ALAB",
                    "nazwa": "Wysy\u0142ka do Warszawy Bakteriologia, Zawodzie - ALAB",
                    "symbol": "X-ZBAKT",
                    "zewnetrzna": true
                },
                "akredytacja": false
            }
        }
    }, {
        "id": 820127,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:22",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631353",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWykonanie",
        "event_data": {
            "prawie": false,
            "wyniki": [{
                "id": "BELCHAT:484478877",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": true,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Opis",
                    "format": null,
                    "symbol": "OPIS",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": null
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": "",
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": "UJEMNY",
                "flaga_deltacheck": 0
            }],
            "pracownik": null,
            "dane_wykonania": {
                "aparat": {"nazwa": "Manualnie (Zawodzie Warszawa)", "symbol": "F-MAN"},
                "metoda": {
                    "kod": null,
                    "opis": null,
                    "nazwa": "Manualnie (Zawodzie Warszawa)",
                    "symbol": "F-MAN",
                    "zakres_akredytacji": null
                },
                "badanie": {
                    "kod": null,
                    "grupa": "TECHNIC",
                    "nazwa": "01. Odczyt dzie\u0144 1",
                    "rodzaj": "DZIALAN",
                    "symbol": "DZOD24H",
                    "nazwa_alternatywna": null
                },
                "pracownia": {
                    "grupa": "ALAB",
                    "nazwa": "Wysy\u0142ka do Warszawy Bakteriologia, Zawodzie - ALAB",
                    "symbol": "X-ZBAKT",
                    "zewnetrzna": true
                },
                "akredytacja": false
            }
        }
    }, {
        "id": 820128,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:22",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631353",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZatwierdzenie",
        "event_data": {
            "wyniki": [{
                "id": "BELCHAT:484478877",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": true,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Opis",
                    "format": null,
                    "symbol": "OPIS",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": null
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": "",
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": "UJEMNY",
                "flaga_deltacheck": 0
            }],
            "pracownik": null,
            "dane_wykonania": {
                "aparat": {"nazwa": "Manualnie (Zawodzie Warszawa)", "symbol": "F-MAN"},
                "metoda": {
                    "kod": null,
                    "opis": null,
                    "nazwa": "Manualnie (Zawodzie Warszawa)",
                    "symbol": "F-MAN",
                    "zakres_akredytacji": null
                },
                "badanie": {
                    "kod": null,
                    "grupa": "TECHNIC",
                    "nazwa": "01. Odczyt dzie\u0144 1",
                    "rodzaj": "DZIALAN",
                    "symbol": "DZOD24H",
                    "nazwa_alternatywna": null
                },
                "pracownia": {
                    "grupa": "ALAB",
                    "nazwa": "Wysy\u0142ka do Warszawy Bakteriologia, Zawodzie - ALAB",
                    "symbol": "X-ZBAKT",
                    "zewnetrzna": true
                },
                "akredytacja": false
            },
            "bardzo_zatwierdzone": false
        }
    }, {
        "id": 820129,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:30",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631353",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykDystrybucja",
        "event_data": {"material": null, "pracownik": "BELCHAT:0", "kodkreskowy": null}
    }, {
        "id": 820130,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:30",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631353",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWykonanie",
        "event_data": {
            "prawie": true,
            "wyniki": [{
                "id": "BELCHAT:484478877",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": true,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Opis",
                    "format": null,
                    "symbol": "OPIS",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": null
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": "",
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": "UJEMNY",
                "flaga_deltacheck": 0
            }],
            "pracownik": "BELCHAT:0",
            "dane_wykonania": {
                "aparat": {"nazwa": "Manualnie (Zawodzie Warszawa)", "symbol": "F-MAN"},
                "metoda": {
                    "kod": null,
                    "opis": null,
                    "nazwa": "Manualnie (Zawodzie Warszawa)",
                    "symbol": "F-MAN",
                    "zakres_akredytacji": null
                },
                "badanie": {
                    "kod": null,
                    "grupa": "TECHNIC",
                    "nazwa": "01. Odczyt dzie\u0144 1",
                    "rodzaj": "DZIALAN",
                    "symbol": "DZOD24H",
                    "nazwa_alternatywna": null
                },
                "pracownia": {
                    "grupa": "ALAB",
                    "nazwa": "Wysy\u0142ka do Warszawy Bakteriologia, Zawodzie - ALAB",
                    "symbol": "X-ZBAKT",
                    "zewnetrzna": true
                },
                "akredytacja": false
            }
        }
    }, {
        "id": 820131,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:54",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631353",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykRozliczenie",
        "event_data": {
            "blad": null,
            "koszty": true,
            "platne": true,
            "badanie": "DZOD24H",
            "platnik": {
                "id": "BELCHAT:698",
                "nip": null,
                "nazwa": "Got\u00f3wka ALAB EB",
                "symbol": "EBGOTOW",
                "gotowkowy": true
            },
            "material": null,
            "zleceniodawca": {
                "id": "BELCHAT:834",
                "nazwa": "Punkt pobra\u0144 ALAB (Be\u0142chat\u00f3w)",
                "symbol": "EB-ALAB",
                "platnik": "EBGOTOW",
                "gotowkowy": true
            },
            "data_rozliczeniowa": "2023-03-17",
            "inny_platnik_wykonania": null
        }
    }, {
        "id": 820132,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:54",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631353",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWycenaWLab",
        "event_data": {"cena": 323153.0, "cennik": "CENG   ", "stawka_vat": null}
    }, {
        "id": 820133,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:54",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631354",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykUtworzone",
        "event_data": {
            "pakiet": null,
            "sys_id": 8984477,
            "system": "ZAWODZI",
            "badanie": "URICULT",
            "material": "PODL2",
            "powtorka": false,
            "jest_pakietem": false,
            "jest_skladowa": false
        }
    }, {
        "id": 820134,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:54",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631354",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZmianaMetody",
        "event_data": {"aparat": "F-MAN  ", "metoda": "F-MAN  ", "pracownia": "X-ZBAKT", "pracownik": null}
    }, {
        "id": 820135,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:54",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631354",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZmianaOdplatnosci",
        "event_data": {"koszt": null, "platne": true, "punkty": null, "pracownik": null, "na_koszt_labu": true}
    }, {
        "id": 820136,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:30",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631354",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWydruk",
        "event_data": {
            "wyniki": [{
                "id": "BELCHAT:484478879",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": true,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "URICULT",
                    "format": null,
                    "symbol": "URICULT",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": null
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": "",
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": null,
                "flaga_deltacheck": null
            }],
            "ponowny": false,
            "pracownik": null,
            "dane_wykonania": {
                "aparat": {"nazwa": "Manualnie (Zawodzie Warszawa)", "symbol": "F-MAN"},
                "metoda": {
                    "kod": null,
                    "opis": null,
                    "nazwa": "Manualnie (Zawodzie Warszawa)",
                    "symbol": "F-MAN",
                    "zakres_akredytacji": null
                },
                "badanie": {
                    "kod": null,
                    "grupa": "TECHNIC",
                    "nazwa": "URICULT",
                    "rodzaj": "PODLOZE",
                    "symbol": "URICULT",
                    "nazwa_alternatywna": null
                },
                "pracownia": {
                    "grupa": "ALAB",
                    "nazwa": "Wysy\u0142ka do Warszawy Bakteriologia, Zawodzie - ALAB",
                    "symbol": "X-ZBAKT",
                    "zewnetrzna": true
                },
                "akredytacja": false
            }
        }
    }, {
        "id": 820137,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-15 19:00",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631354",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWykonanie",
        "event_data": {
            "prawie": false,
            "wyniki": [{
                "id": "BELCHAT:484478879",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": true,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "URICULT",
                    "format": null,
                    "symbol": "URICULT",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": null
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": "",
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": null,
                "flaga_deltacheck": null
            }],
            "pracownik": null,
            "dane_wykonania": {
                "aparat": {"nazwa": "Manualnie (Zawodzie Warszawa)", "symbol": "F-MAN"},
                "metoda": {
                    "kod": null,
                    "opis": null,
                    "nazwa": "Manualnie (Zawodzie Warszawa)",
                    "symbol": "F-MAN",
                    "zakres_akredytacji": null
                },
                "badanie": {
                    "kod": null,
                    "grupa": "TECHNIC",
                    "nazwa": "URICULT",
                    "rodzaj": "PODLOZE",
                    "symbol": "URICULT",
                    "nazwa_alternatywna": null
                },
                "pracownia": {
                    "grupa": "ALAB",
                    "nazwa": "Wysy\u0142ka do Warszawy Bakteriologia, Zawodzie - ALAB",
                    "symbol": "X-ZBAKT",
                    "zewnetrzna": true
                },
                "akredytacja": false
            }
        }
    }, {
        "id": 820138,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:22",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631354",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZatwierdzenie",
        "event_data": {
            "wyniki": [{
                "id": "BELCHAT:484478879",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": true,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "URICULT",
                    "format": null,
                    "symbol": "URICULT",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": null
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": "",
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": null,
                "flaga_deltacheck": null
            }],
            "pracownik": null,
            "dane_wykonania": {
                "aparat": {"nazwa": "Manualnie (Zawodzie Warszawa)", "symbol": "F-MAN"},
                "metoda": {
                    "kod": null,
                    "opis": null,
                    "nazwa": "Manualnie (Zawodzie Warszawa)",
                    "symbol": "F-MAN",
                    "zakres_akredytacji": null
                },
                "badanie": {
                    "kod": null,
                    "grupa": "TECHNIC",
                    "nazwa": "URICULT",
                    "rodzaj": "PODLOZE",
                    "symbol": "URICULT",
                    "nazwa_alternatywna": null
                },
                "pracownia": {
                    "grupa": "ALAB",
                    "nazwa": "Wysy\u0142ka do Warszawy Bakteriologia, Zawodzie - ALAB",
                    "symbol": "X-ZBAKT",
                    "zewnetrzna": true
                },
                "akredytacja": false
            },
            "bardzo_zatwierdzone": false
        }
    }, {
        "id": 820139,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:30",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631354",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykDystrybucja",
        "event_data": {"material": "PODL2  ", "pracownik": "BELCHAT:0", "kodkreskowy": "084806"}
    }, {
        "id": 820140,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:54",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631354",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykRozliczenie",
        "event_data": {
            "blad": null,
            "koszty": true,
            "platne": true,
            "badanie": "URICULT",
            "platnik": {
                "id": "BELCHAT:698",
                "nip": null,
                "nazwa": "Got\u00f3wka ALAB EB",
                "symbol": "EBGOTOW",
                "gotowkowy": true
            },
            "material": "PODL2  ",
            "zleceniodawca": {
                "id": "BELCHAT:834",
                "nazwa": "Punkt pobra\u0144 ALAB (Be\u0142chat\u00f3w)",
                "symbol": "EB-ALAB",
                "platnik": "EBGOTOW",
                "gotowkowy": true
            },
            "data_rozliczeniowa": "2023-03-17",
            "inny_platnik_wykonania": null
        }
    }, {
        "id": 820141,
        "src": "BELCHAT",
        "trans_id": 3935631,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:54",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631354",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWycenaWLab",
        "event_data": {"cena": 323153.0, "cennik": "CENG   ", "stawka_vat": null}
    }, {
        "id": 820142,
        "src": "BELCHAT",
        "trans_id": 3935632,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:30",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZmianaMetody",
        "event_data": {"aparat": "F-MAN  ", "metoda": "F-MAN  ", "pracownia": "X-ZBAKT", "pracownik": "BELCHAT:0"}
    }, {
        "id": 820143,
        "src": "BELCHAT",
        "trans_id": 3935632,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:54",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZmianaMaterialu",
        "event_data": {"material": "MOCZ-T "}
    }, {
        "id": 820144,
        "src": "BELCHAT",
        "trans_id": 3935632,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:30",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykListaRobocza",
        "event_data": {
            "statyw": null,
            "pracownik": "BELCHAT:0",
            "polozenie_x": null,
            "polozenie_y": null,
            "lista_robocza": null
        }
    }, {
        "id": 820145,
        "src": "BELCHAT",
        "trans_id": 3935632,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:54",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykPowtorka",
        "event_data": {"liczba_powtorzen": 1}
    }, {
        "id": 820146,
        "src": "BELCHAT",
        "trans_id": 3935632,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:30",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWydruk",
        "event_data": {
            "wyniki": [{
                "id": "BELCHAT:484478875",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": false,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Wynik badania:",
                    "format": null,
                    "symbol": "WYNIK",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": "Results:"
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": "",
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": "Drobnoustroj\u00f3w uropatogennych w mianie >=10^2 CFU/ml nie wyhodowano",
                "flaga_deltacheck": 0
            }, {
                "id": "BELCHAT:484478874",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": false,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Uwagi:",
                    "format": null,
                    "symbol": "UWAGI",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": null
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": null,
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": null,
                "flaga_deltacheck": null
            }],
            "ponowny": false,
            "pracownik": null,
            "dane_wykonania": {
                "aparat": {"nazwa": "Manualnie (Zawodzie Warszawa)", "symbol": "F-MAN"},
                "metoda": {
                    "kod": null,
                    "opis": null,
                    "nazwa": "Manualnie (Bakteriologia Zawodzie)",
                    "symbol": "F-MAN",
                    "zakres_akredytacji": null
                },
                "badanie": {
                    "kod": "91.33",
                    "grupa": "BAKTER",
                    "nazwa": "Posiew moczu (91.33)",
                    "rodzaj": "POS",
                    "symbol": "P-MOCZ",
                    "nazwa_alternatywna": null
                },
                "pracownia": {
                    "grupa": "ALAB",
                    "nazwa": "Wysy\u0142ka do Warszawy Bakteriologia, Zawodzie - ALAB",
                    "symbol": "X-ZBAKT",
                    "zewnetrzna": true
                },
                "akredytacja": false
            }
        }
    }, {
        "id": 820147,
        "src": "BELCHAT",
        "trans_id": 3935632,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:22",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWykonanie",
        "event_data": {
            "prawie": false,
            "wyniki": [{
                "id": "BELCHAT:484478875",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": false,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Wynik badania:",
                    "format": null,
                    "symbol": "WYNIK",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": "Results:"
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": "",
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": "Drobnoustroj\u00f3w uropatogennych w mianie >=10^2 CFU/ml nie wyhodowano",
                "flaga_deltacheck": 0
            }, {
                "id": "BELCHAT:484478874",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": false,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Uwagi:",
                    "format": null,
                    "symbol": "UWAGI",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": null
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": null,
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": null,
                "flaga_deltacheck": null
            }],
            "pracownik": null,
            "dane_wykonania": {
                "aparat": {"nazwa": "Manualnie (Zawodzie Warszawa)", "symbol": "F-MAN"},
                "metoda": {
                    "kod": null,
                    "opis": null,
                    "nazwa": "Manualnie (Bakteriologia Zawodzie)",
                    "symbol": "F-MAN",
                    "zakres_akredytacji": null
                },
                "badanie": {
                    "kod": "91.33",
                    "grupa": "BAKTER",
                    "nazwa": "Posiew moczu (91.33)",
                    "rodzaj": "POS",
                    "symbol": "P-MOCZ",
                    "nazwa_alternatywna": null
                },
                "pracownia": {
                    "grupa": "ALAB",
                    "nazwa": "Wysy\u0142ka do Warszawy Bakteriologia, Zawodzie - ALAB",
                    "symbol": "X-ZBAKT",
                    "zewnetrzna": true
                },
                "akredytacja": false
            }
        }
    }, {
        "id": 820148,
        "src": "BELCHAT",
        "trans_id": 3935632,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:22",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykZatwierdzenie",
        "event_data": {
            "wyniki": [{
                "id": "BELCHAT:484478875",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": false,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Wynik badania:",
                    "format": null,
                    "symbol": "WYNIK",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": "Results:"
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": "",
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": "Drobnoustroj\u00f3w uropatogennych w mianie >=10^2 CFU/ml nie wyhodowano",
                "flaga_deltacheck": 0
            }, {
                "id": "BELCHAT:484478874",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": false,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Uwagi:",
                    "format": null,
                    "symbol": "UWAGI",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": null
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": null,
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": null,
                "flaga_deltacheck": null
            }],
            "pracownik": null,
            "dane_wykonania": {
                "aparat": {"nazwa": "Manualnie (Zawodzie Warszawa)", "symbol": "F-MAN"},
                "metoda": {
                    "kod": null,
                    "opis": null,
                    "nazwa": "Manualnie (Bakteriologia Zawodzie)",
                    "symbol": "F-MAN",
                    "zakres_akredytacji": null
                },
                "badanie": {
                    "kod": "91.33",
                    "grupa": "BAKTER",
                    "nazwa": "Posiew moczu (91.33)",
                    "rodzaj": "POS",
                    "symbol": "P-MOCZ",
                    "nazwa_alternatywna": null
                },
                "pracownia": {
                    "grupa": "ALAB",
                    "nazwa": "Wysy\u0142ka do Warszawy Bakteriologia, Zawodzie - ALAB",
                    "symbol": "X-ZBAKT",
                    "zewnetrzna": true
                },
                "akredytacja": false
            },
            "bardzo_zatwierdzone": false
        }
    }, {
        "id": 820149,
        "src": "BELCHAT",
        "trans_id": 3935632,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:30",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykIdentyfikatorModyfikacja",
        "event_data": {"pracownik": "BELCHAT:0", "identyfikator": null}
    }, {
        "id": 820150,
        "src": "BELCHAT",
        "trans_id": 3935632,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:30",
        "domain_name": "lab",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykWykonanie",
        "event_data": {
            "prawie": true,
            "wyniki": [{
                "id": "BELCHAT:484478875",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": false,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Wynik badania:",
                    "format": null,
                    "symbol": "WYNIK",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": "Results:"
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": "",
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": "Drobnoustroj\u00f3w uropatogennych w mianie >=10^2 CFU/ml nie wyhodowano",
                "flaga_deltacheck": 0
            }, {
                "id": "BELCHAT:484478874",
                "flaga": "N",
                "kryt_h": null,
                "kryt_l": null,
                "ukryty": false,
                "norma_h": null,
                "norma_l": null,
                "parametr": {
                    "nazwa": "Uwagi:",
                    "format": null,
                    "symbol": "UWAGI",
                    "granica_h": null,
                    "granica_l": null,
                    "nazwa_alternatywna": null
                },
                "org_alert": false,
                "wynik_mic": null,
                "norma_tekst": null,
                "org_patogen": false,
                "wynik_liczbowy": null,
                "wynik_tekstowy": null,
                "flaga_deltacheck": null
            }],
            "pracownik": "BELCHAT:0",
            "dane_wykonania": {
                "aparat": {"nazwa": "Manualnie (Zawodzie Warszawa)", "symbol": "F-MAN"},
                "metoda": {
                    "kod": null,
                    "opis": null,
                    "nazwa": "Manualnie (Bakteriologia Zawodzie)",
                    "symbol": "F-MAN",
                    "zakres_akredytacji": null
                },
                "badanie": {
                    "kod": "91.33",
                    "grupa": "BAKTER",
                    "nazwa": "Posiew moczu (91.33)",
                    "rodzaj": "POS",
                    "symbol": "P-MOCZ",
                    "nazwa_alternatywna": null
                },
                "pracownia": {
                    "grupa": "ALAB",
                    "nazwa": "Wysy\u0142ka do Warszawy Bakteriologia, Zawodzie - ALAB",
                    "symbol": "X-ZBAKT",
                    "zewnetrzna": true
                },
                "akredytacja": false
            }
        }
    }, {
        "id": 820151,
        "src": "BELCHAT",
        "trans_id": 3935632,
        "src_ts": "2023-03-17 13:54",
        "repl_ts": "2023-03-17 13:54",
        "event_ts": "2023-03-17 13:54",
        "domain_name": "billing",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykRozliczenie",
        "event_data": {
            "blad": null,
            "koszty": true,
            "platne": true,
            "badanie": "P-MOCZ ",
            "platnik": {
                "id": "BELCHAT:698",
                "nip": null,
                "nazwa": "Got\u00f3wka ALAB EB",
                "symbol": "EBGOTOW",
                "gotowkowy": true
            },
            "material": "MOCZ-T ",
            "zleceniodawca": {
                "id": "BELCHAT:834",
                "nazwa": "Punkt pobra\u0144 ALAB (Be\u0142chat\u00f3w)",
                "symbol": "EB-ALAB",
                "platnik": "EBGOTOW",
                "gotowkowy": true
            },
            "data_rozliczeniowa": "2023-03-17",
            "inny_platnik_wykonania": null
        }
    }, {
        "id": 833432,
        "src": "BELCHAT",
        "trans_id": 3938640,
        "src_ts": "2023-03-17 15:16",
        "repl_ts": "2023-03-17 15:16",
        "event_ts": "2023-03-17 15:16",
        "domain_name": "results",
        "order_id": "BELCHAT:495772",
        "order_item_id": null,
        "entity_name": "wydrukiwzleceniach",
        "entity_id": "BELCHAT:830676",
        "event_type": "CntWydrUtworzony",
        "event_data": {"wydruk_id": "BELCHAT:830676"}
    }, {
        "id": 833433,
        "src": "BELCHAT",
        "trans_id": 3938640,
        "src_ts": "2023-03-17 15:16",
        "repl_ts": "2023-03-17 15:16",
        "event_ts": "2023-03-17 14:52",
        "domain_name": "results",
        "order_id": "BELCHAT:495772",
        "order_item_id": null,
        "entity_name": "wydrukiwzleceniach",
        "entity_id": "BELCHAT:830676",
        "event_type": "CntWydrOdebrany",
        "event_data": {
            "plik": "ZAWODZI-LABMIK73-20230317145512-134.pdf",
            "odebral": "Automatycznie odebrany od ZAWODZI",
            "sciezka": "202303/15/0104/ZAWODZI-LABMIK73-20230317145512-134.pdf",
            "wydruk_id": "BELCHAT:830676",
            "zlecenie_data": "2023-03-15",
            "zlecenie_numer": 104
        }
    }, {
        "id": 833434,
        "src": "BELCHAT",
        "trans_id": 3938640,
        "src_ts": "2023-03-17 15:16",
        "repl_ts": "2023-03-17 15:16",
        "event_ts": "2023-03-17 14:52",
        "domain_name": "results",
        "order_id": "BELCHAT:495772",
        "order_item_id": null,
        "entity_name": "wydrukiwzleceniach",
        "entity_id": "BELCHAT:830676",
        "event_type": "CntWydrCzynnoscTechniczna",
        "event_data": {"rodzaj": "podpisany", "wydruk_id": "BELCHAT:830676"}
    }, {
        "id": 833452,
        "src": "BELCHAT",
        "trans_id": 3938685,
        "src_ts": "2023-03-17 15:20",
        "repl_ts": "2023-03-17 15:20",
        "event_ts": "2023-03-17 14:56",
        "domain_name": "results",
        "order_id": "BELCHAT:495772",
        "order_item_id": null,
        "entity_name": "wydrukiwzleceniach",
        "entity_id": "BELCHAT:830676",
        "event_type": "CntWydrCzynnoscTechniczna",
        "event_data": {"rodzaj": "wyslany", "wydruk_id": "BELCHAT:830676"}
    }, {
        "id": 857880,
        "src": "BELCHAT",
        "trans_id": 3943634,
        "src_ts": "2023-03-17 21:08",
        "repl_ts": "2023-03-17 21:08",
        "event_ts": "2023-03-17 20:44",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4624740",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykCzynnoscTechniczna",
        "event_data": {"czynnosc": "wyslanerozliczenie"}
    }, {
        "id": 857881,
        "src": "BELCHAT",
        "trans_id": 3943634,
        "src_ts": "2023-03-17 21:08",
        "repl_ts": "2023-03-17 21:08",
        "event_ts": "2023-03-17 20:44",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631353",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykCzynnoscTechniczna",
        "event_data": {"czynnosc": "wyslanerozliczenie"}
    }, {
        "id": 857882,
        "src": "BELCHAT",
        "trans_id": 3943634,
        "src_ts": "2023-03-17 21:08",
        "repl_ts": "2023-03-17 21:08",
        "event_ts": "2023-03-17 20:44",
        "domain_name": "orders",
        "order_id": "BELCHAT:495772",
        "order_item_id": "BELCHAT:4631354",
        "entity_name": null,
        "entity_id": null,
        "event_type": "CntWykCzynnoscTechniczna",
        "event_data": {"czynnosc": "wyslanerozliczenie"}
    }, {
        "id": 867233,
        "src": "BELCHAT",
        "trans_id": 3954526,
        "src_ts": "2023-03-20 06:33",
        "repl_ts": "2023-03-20 06:33",
        "event_ts": "2023-03-20 06:09",
        "domain_name": "results",
        "order_id": "BELCHAT:495772",
        "order_item_id": null,
        "entity_name": "wydrukiwzleceniach",
        "entity_id": "BELCHAT:830676",
        "event_type": "CntWydrWydrukowany",
        "event_data": {
            "podpisany": true,
            "pracownik": "BELCHAT:209160",
            "wydruk_id": "BELCHAT:830676",
            "co_podpisano": null,
            "powtorny_wydruk": false
        }
    }],
    "lookup": {
        "pracownicy": {
            "BELCHAT:364953": "Walczak Teresa",
            "BELCHAT:209160": "Walczak Teresa",
            "BELCHAT:0": "(system)",
            "BELCHAT:632617": "Dorf Gra\u017cyna"
        }
    }
};


export const RepublikaSampleView = () => {

    return (<div>
        <h6>Republika przykład</h6>
        <RepublikaEventStreamView eventStream={ZLECENIE}/>
    </div>);

}
