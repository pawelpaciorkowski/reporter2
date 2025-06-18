from datasources.kakl import KaKlDatasource
from dialog import Dialog, VBox
from helpers import prepare_for_json
from tasks import TaskGroup

MENU_ENTRY = 'Eksport kart klienta'

REQUIRE_ROLE = ['C-CS']
ADD_TO_ROLE = ['R-DYR', 'R-PM']

SQL = """
    select 
    nazwa_klienta as "Klient",
    (ksnrp.imie || ' ' || ksnrp.nazwisko || ' - ' || ko.nazwisko || ' ' || ko.imiona) as "Przedstawiciel medyczny (SNR)",
    platnik_kontakt_tel as "Osoba kontaktowa płatnika - numer telefonu",
    kp.nip as "NIP Płatnika",
    platnik_kontakt_mail as "Dane kontaktowe płatnika - adres e-mail", 
    (kk.czas_umowy_start || ' - ' || kk.czas_umowy_koniec) as "Czas trwania umowy SNR",
        case
            when kk.sieciowy = true then 'TAK'
            when kk.sieciowy = false then 'NIE'
            else 'UNDEFINED'
        end as "Klient sieciowy", 
        case
            when kk.gotowkowe = true then 'TAK'
            when kk.gotowkowe = false then 'NIE'
            else 'UNDEFINED'
        end as "Obsługa gotówkowa (SNR)", 
        case
            when pp_alab = true then 'TAK'
            when pp_alab = false then 'NIE'
            else 'UNDEFINED'
        end as "Korzysta z punktów pobrań ALAB:",
        case
            when pp_alab_wszystkie = 1 then 'TAK'
            when pp_alab_wszystkie = 0 then 'NIE'
            else 'UNDEFINED'
        end as "Korzysta z wszystkich punktów pobrań ALAB w Polsce:", pp_alab_wybrane as "Wybrane punkty pobrań ALAB w Polsce",
        case
            when pp_alab_spolki_new = 1 then 'TAK'
            when pp_alab_spolki_new = 0 then 'NIE'
            else 'UNDEFINED'
        end as "Korzysta z punktów pobrań spółek grupy ALAB",
        case
            when widocznosc_pp_new  = 1 then 'TAK'
            when widocznosc_pp_new = 0 then 'NIE'
            else 'UNDEFINED'
        end as "Widoczność karty w punktach pobrań",
        case when owpp_inne = '' then '' else owpp_inne end || ' ' ||
            case when owpp_hl7 = true then 'hl7' else '' end || ' ' ||
                case when owpp_mail = true then 'e-mail' else '' end || ' ' ||
                    case when owpp_sms = true then 'sms' else '' end || ' ' ||
                        case when owpp_pieczatka = true then 'pieczątka' else '' end || ' ' as "Na jakiej podstawie Klient jest obsługiwany w PP",
        uwagi as "Niestandardowe ustalenia / wymagania",
        case when sow_alablaboratoria_pl = true then 'alablaboratoria.pl' else '' end || ' ' ||
            case when sow_his_lis = true then 'his_lis' else '' end || ' ' ||
                case when sow_kurier = true then 'kurier' else '' end || ' ' ||
                    case when sow_twoje_wyniki = true then 'twoje_wyniki' else '' end || ' ' as "Sposób odbioru wyników",
        (aom_ulica || ' ' || aom_ulica_nr || ' ' || aom_miasto  || ' ' || aom_kod_pocztowy)
        as "Adres odbioru materiału",
        case
            when material_swieta_new = 1 then 'TAK'
            when material_swieta_new = 0 then 'NIE'
            else 'UNDEFINED'
        end as "Odbiór materiału w święta",
        case
            when material_16_new = 1 then 'TAK'
            when material_16_new = 0 then 'NIE'
            else 'UNDEFINED'
        end as "Odbiór materialu po godzinie 16",
        case
            when material_noc_new = 1 then 'TAK'
            when material_noc_new = 0 then 'NIE'
            else 'UNDEFINED'
        end as "Odbiór materiału w nocy",
        krytyczne_tel, krytyczne_fax, krytyczne_email,
        case
            when klient_zintegrowany = 1 then 'TAK'
            when klient_zintegrowany = 0 then 'NIE'
            else 'UNDEFINED'
        end as klient_zintegrowany,
    array_to_string(array_agg(kz.symbol),' ') as "symbole zleceniodawcow przypisanych do karty"
    from kakl_kartaklienta kk
    LEFT JOIN kartoteki_platnik kp
    ON kk.platnik_id = kp.id
    left join kartoteki_snrprzedstawiciel ksnrp
    on kp.snr_przedstawiciel_id = ksnrp.id
    left join kartoteki_osoba ko
    on ko.id = ksnrp.user_id
    left join kakl_kartaklienta_zleceniodawcy kkz 
    on kkz.kartaklienta_id = kk.id
    left join kartoteki_zleceniodawca kz 
    on kkz.zleceniodawca_id = kz.id
    group by nazwa_klienta, platnik_kontakt_tel, platnik_kontakt_mail, kk.czas_umowy_start, sow_alablaboratoria_pl, sow_his_lis, sow_kurier, sow_twoje_wyniki, 
    kk.czas_umowy_koniec, kk.sieciowy, kk.gotowkowe, pp_alab, pp_alab_spolki_new, pp_alab_wybrane, widocznosc_pp_new, owpp_inne, owpp_hl7, owpp_mail, owpp_sms, owpp_pieczatka,
    pp_alab_wszystkie, uwagi, aom_ulica, aom_ulica_nr, aom_miasto, aom_kod_pocztowy, material_swieta_new, material_16_new, kp.nip,
    material_noc_new, krytyczne_tel, krytyczne_fax, krytyczne_email, klient_zintegrowany, ksnrp.imie, ksnrp.nazwisko, ko.nazwisko, ko.imiona
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    # LabSelector(multiselect=True, field='laboratoria', title='Laboratorium'),
))


def start_report(params):
    report = TaskGroup(__PLUGIN__, params)
    task = {"type": "noc", "priority": 1, "params": params, "function": "raport_djalab"}
    report.create_task(task)
    report.save()
    return report


def raport_djalab(task_params):
    params = task_params['params']
    kakl = KaKlDatasource()
    cols, rows = kakl.select(SQL)
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    }
