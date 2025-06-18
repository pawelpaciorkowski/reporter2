import os
import shutil

from datasources.reporter import ReporterDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, NumberInput, \
    Select, Radio, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json, Kalendarz, random_path, copy_from_remote, get_and_cache
from helpers.crystal_ball.marcel_servers import katalog_wydrukow, sciezka_wydruku
from helpers.marcel_pdf_xml import MarcelPdf, MarcelSig
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
import datetime

MENU_ENTRY = "Ważność certyfikatów podpisu"

ADD_TO_ROLE = ['L-PRAC']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="""
            Raport sprawdza ważność certyfikatów podpisu elektronicznego dla diagnostów podpisujących w ostatnim tygodniu.
            Informacje odczytywane z jednego sprawozdania dla każdego z pracowników.  
        """),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', pokaz_nieaktywne=True),
))

# Cyrta: status żółto miesiąc przed, czerwono 10 dni przed datą ważności

SQL_PRACOWNICY_FB = """
    select first 200 count(wwz.id) as ilosc, min(wwz.id) as last_id, prac.nazwisko, prac.logowanie 
    from wydrukiwzleceniach wwz
    left join pracownicy prac on prac.id=wwz.pc
    left join zlecenia zl on zl.id=wwz.zlecenie
    where wwz.odebrany > ? and wwz.podpisany=1 and wwz.del=0 and wwz.odwolanywydrukowany is null
    and wwz.wydrukowany2 is null and zl.numer is not null
    group by 3, 4 order by 1 desc
"""

SQL_PRACOWNICY_PG = """
    select count(wwz.id) as ilosc, min(wwz.id) as last_id, prac.nazwisko, prac.logowanie 
    from wydrukiwzleceniach wwz
    left join pracownicy prac on prac.id=wwz.pc
    left join zlecenia zl on zl.id=wwz.zlecenie
    where wwz.odebrany > %s and wwz.podpisany=1 and wwz.copodpisano='pdf' and wwz.del=0 and wwz.odwolanywydrukowany is null
    and wwz.wydrukowany2 is null and zl.numer is not null
    group by 3, 4 order by 1 desc
    limit 200
"""

SQL_DOKUMENTY = """
    select zl.numer, zl.datarejestracji, wwz.id, wwz.plik 
    from wydrukiwzleceniach wwz
    left join zlecenia zl on zl.id=wwz.zlecenie 
    where wwz.id in ($IDENTS$)
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_pojedynczy'
    }
    report.create_task(task)
    report.save()
    return report


def get_result_for_lab(lab):
    kal = Kalendarz()
    tmp_dir = random_path('waznosc_certyfikatow_')
    os.makedirs(tmp_dir, 0o755)
    res_rows = []
    nazwy_plikow = {}
    try:
        rep = ReporterDatasource()
        for row in rep.dict_select("select * from laboratoria where symbol=%s", [lab]):
            adres = row['adres_fresh']
        with get_centrum_connection(lab) as conn:
            pracownicy_rows = conn.raport_slownikowy(SQL_PRACOWNICY_FB, [kal.data('-7D')], sql_pg=SQL_PRACOWNICY_PG)
            if len(pracownicy_rows) > 0:
                sql_dokumenty = SQL_DOKUMENTY.replace('$IDENTS$', ','.join(
                    [str(row['last_id']) for row in pracownicy_rows]))
            for row in conn.raport_slownikowy(sql_dokumenty):
                sciezka = sciezka_wydruku(lab, row['datarejestracji'], row['numer'], row['plik'])
                if sciezka.endswith('.xml'):
                    sciezka += '.sig'
                nazwy_plikow[row['id']] = sciezka
                copy_from_remote(adres, sciezka, os.path.join(tmp_dir, str(row['id'])))
        for row in pracownicy_rows:
            res_row = [
                row['nazwisko'], row['logowanie'], row['ilosc']
            ]
            fn = os.path.join(tmp_dir, str(row['last_id']))
            if os.path.exists(fn):
                is_signed = False
                with open(fn, 'rb') as f:
                    content = f.read()
                    for doc_cls in (MarcelPdf, MarcelSig):
                        doc = doc_cls(content=content)
                        if doc.is_signed():
                            is_signed = True
                            try:
                                cert_info = doc.get_cert_info()
                                valid_to = doc.get_cert_valid_to()
                                wystawca = doc.get_cert_issuer()
                                if valid_to is None:
                                    valid_to = 'NIE UDAŁO SIĘ ODCZYTAĆ DATY WAŻNOŚCI'
                                else:
                                    if datetime.datetime.now() + datetime.timedelta(days=10) > valid_to:
                                        valid_to = {'value': valid_to, 'background': '#ff0000'}
                                    elif datetime.datetime.now() + datetime.timedelta(days=31) > valid_to:
                                        valid_to = {'value': valid_to, 'background': '#ffff00'}
                                res_row += [cert_info, valid_to, wystawca]
                                break
                            except Exception as e:
                                res_row += ['', {'value': 'Nie udało się odczytać ' + str(sciezka) + '  - ' + str(e), 'background': '#ff0000'}]
                if not is_signed:
                    res_row += ['', {
                        'value': f"Plik niepodpisany: {nazwy_plikow[row['last_id']]}",
                        'background': '#ff0000'
                    }]
            else:
                res_row += ['', {
                    'value': f"Nie udało się pobrać {nazwy_plikow[row['last_id']]}",
                    'background': '#ff0000'
                }]
            res_rows.append(res_row)
    finally:
        shutil.rmtree(tmp_dir)

    return {
        'type': 'table',
        'header': 'Pracownik,Login,Przybl. ilość,CN z certyfikatu,Ważność certyfikatu,Wystawca'.split(','),
        'data': prepare_for_json(res_rows)
    }


def raport_pojedynczy(task_params):
    lab = task_params['target']
    return get_and_cache(f'waznosc_certyfikatow_{lab}', get_result_for_lab, timeout=12 * 3600, args=[lab])
