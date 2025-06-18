"""

Alab Reporter Playground

Ten moduł służy uruchamianiu i testowaniu nowych / zmienianych funkcjonalności, w oddzieleniu od
interfejsu Reportera, ale w jego kompletnym środowisku, czyli czymś więcej, niż środowisko testów jednostkowych.
Testowane funkcjonalności należy umieszczać w funkcjach o znaczących nazwach i wywołwywać z maina,
a po testach / uruchomieniu nie usuwać tylko po prostu wykomentowywać (jeśli wywołanie mówi coś sensownego o argumentach
funkcji) lub wykasowywać ich użycie, a funkcje zostawić jako dokumentacje.
Nazwy testowych funkcji powinny się zaczynać prefikesem odpowiadającym ścieżce do testowanych modułów.
W funkcjach można używać assertów i innych konstrukcji charakterystycznych dla testów, żeby w razie potrzeby
używać ich jak testów w trakcie modyfikowania funkcjonalności. W przyszłości może to zostać przeniesione do
testów integracyjnych, jeśli takie powstaną.
Funkcje te powinny operować (ale nie zaśmiecać) na bieżącej bazie Reportera.

"""
import os.path

from datasources.reporter import ReporterDatasource
from datasources.nocka import NockaDatasource
from dialog import InfoText
from extras.raport_niezgodnosci import RaportNiezgodnosci
from extras.sprawozdanie_word import SprawozdanieWord, SprawozdanieZCentrum
from helpers import empty


def datasources_reporter_auxilary_db_functions():
    ds = ReporterDatasource(read_write=True)
    # czytanie danych, łącznie z polem typu json
    res = ds.select_and_unwrap("select * from mailing_adresy where id=%s", [129])
    assert len(res) == 1
    row = res[0]
    assert row['id'] == 129
    assert row['nazwa'] == 'Warszawa ATTIS'
    assert row['vpn'] == '2.0.4.105'
    # wstawianie i zmienianie danych, z zapisem do logu
    id = ds.insert_with_log('test', 'mailing_adresy', {
        'raport': 'TestReport123',
        'emaile': 'test@test.pl',
        'vpn': '2.0.0.0',
        'baza': 'Centrum'
    })
    assert id > 129
    res = ds.select_and_unwrap("select * from mailing_adresy where id=%s", [id])
    assert res[0]['vpn'] == '2.0.0.0'
    ds.update_with_log('test', 'mailing_adresy', id, {'email': 'test2@test.pl', 'vpn': '2.0.0.1', 'npole': 'zzz'})
    res = ds.select_and_unwrap("select * from mailing_adresy where id=%s", [id])
    assert res[0]['vpn'] == '2.0.0.1'
    assert res[0]['email'] == 'test2@test.pl'
    assert res[0]['npole'] == 'zzz'
    ds.delete_with_log('test', 'mailing_adresy', id)
    log = ds.get_log_for('mailing_adresy', id)
    assert len(log) == 3
    for line in log:
        print(line)
    # sprzątanie
    ds.execute("""delete from log_zmiany where obj_type='mailing_adresy' and obj_id in (
                    select id from mailing_adresy where raport='TestReport123')""")
    ds.execute("""delete from mailing_adresy where raport='TestReport123'""")
    ds.commit()


def datasources_nocka_test():
    ds = NockaDatasource(read_write=True)


def eksport_kart_klienta():
    import pickle
    import os
    import weasyprint
    from datasources.snrkonf import SNRKonf
    from datasources.kakl import karta_klienta
    from helpers.cli import pb_iterate
    snr = SNRKonf()
    if not os.path.exists('karty.dat'):
        karty = []
        for row in pb_iterate(snr.dict_select("""
            select pl.id, pwl.symbol 
            from platnicywlaboratoriach pwl
            left join platnicy pl on pl.id=pwl.platnik
            where pwl.laboratorium=%s and not pwl.del and not pl.del
            order by pwl.symbol
        """, ['SIEDLCE'])):
            karta = karta_klienta(platnik=row['id'])
            if karta is not None:
                karty.append(karta)
        with open('karty.dat', 'wb') as f:
            pickle.dump(karty, f)
    with open('karty.dat', 'rb') as f:
        karty = pickle.load(f)
    html = """<html><head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <style type="text/css">
            @page {
                size: %s;
                padding: 0;
                margin: 12pt 0;
            }
            @media print {
                html, body {
                    width: 210mm;
                    height: 297mm;
                    margin: 0;
                    padding: 0;
                    font-family: 'Arial', 'Helvetica', sans-serif;
                    font-size: 12pt;
                }
                div.karta {
                    page-break-after: always;
                    padding: 10pt;
                }
            }
            table.karta_klienta, table.karta_klienta td {
                border: 1px solid #000;
                border-collapse: collapse;
            }
        </style>
    </head><body>"""
    for k in karty:
        k = k.replace('id="karta_klienta"', 'class="karta_klienta"')
        html += '<div class="karta">%s</div>' % k
    html += "</body></html>"
    weasyprint.HTML(string=html).write_pdf('karty_klienta_siedlce.pdf')


SQL_SIMPLE_JAKIS = """
        select c.konto_idm, c.konto_nazwa, month(a.data_dekretu) as[miesiac operacji], a.data_dekretu, a.dekret_idm, 
            d.kwota_wn,0 ,'PLN', case when b.kurs_waluty > 1 then(d.kwota_wn/b.kurs_waluty)  else 0 end as kwota_WNEUR, 
            0, b.opis_pozycji, b.ident_operacji, a.ident_operacji, b.data_zaplaty 
        from fk_dekret a 
        inner join fk_dekret_pozycje b on a.dekret_id = b.dekret_id 
        inner join fk_konto c on b.konto_wn_id = c.konto_id 
        inner join fk_dekret_kwoty d on b.dekret_pozycje_id = d.dekret_pozycje_id 
        left join waluta e on a.waluta_id = e.waluta_id 
        WHERE c.konto_idm like %s 
        and a.data_dekretu between  %s and %s and a.status_dekretu in ('2','3') 
        and d.rodzaj_kwoty = '1' 
        order by a.data_dekretu ASC    
    """

SQL_DO_NAKLEJEK = """
    select a.datdok Data_dokumentu,i.stwystfakt_ids Stanowisko_sprzedaży,i.nazwa Nazwa_stanowiska_sprzedaży,
        d.typdok_idn,a.dok_idm,a.wartdok,e.odbiorca_idn,f.nip,f.nazwa,
        isnull(ltrim(rtrim(x.ulica)),'')+ISNULL(' '+ltrim(rtrim(x.nrdomu)),'')+ISNULL('m.'+ltrim(rtrim(x.nrmieszk)),'') ulica,
        isnull(ltrim(rtrim(x.kodpoczt)),'')+isnull(' '+ltrim(rtrim(x.miasto)),'') kod,kk.nazwa kraj 
    from doksprzed a 
    join typ_dokumentu_sprzedazy d on a.typdoksp_id=d.typdoksp_id 
    join odbiorca e on a.odbiorca_id=e.odbiorca_id
    inner join adrkontr x on e.adrwys_id=x.adrkontr_id 
    left join kraj kk on x.kraj_id=kk.kraj_id 
    inner join cechodb c on a.odbiorca_id=c.odbiorca_id 
    inner join katparam k on c.katparam_id=k.katparam_id 
    join kontrahent f on e.kontrahent_id=f.kontrahent_id 
    join stwystfakt i on a.stwystfakt_id=i.stwystfakt_id 
    where d.typdok_idn like 'FV_B%' and a.datdok between  %s and %s and left(i.stwystfakt_ids,3) like %s 
    and k.katparam_idn ='EFAKTURA' and c.wartoscparametru not like'TAK'"""


def simple_test():
    from datasources.simple import SimpleDatasource
    sds = SimpleDatasource()
    for row in sds.dict_select(SQL_DO_NAKLEJEK, ['2022-06-01', '2022-07-15', '002']):
        print(row)


def test_bgtasks():
    rn = RaportNiezgodnosci()
    rn.load_config('/home/adamek/Pobrane/raport_niezgodnosci.xlsx')
    rn.set_time('09:30')
    rn.assign_labs(z_platnikow_zleceniodawcow=True)
    rn.run_reports()

def test_sprawozdanie_word():
    from datasources.centrum import CentrumPostgres

    cnt = CentrumPostgres(adres='2.0.0.59', alias='centrum')
    cnt.system = 'ZAWODZI'
    for wwz_id in (17436678,):# (4395036, 16796883, 16796889, 16796893):
        szc = SprawozdanieZCentrum(cnt, wwz_id)
        spr = SprawozdanieWord(szc)
        fn = f'./demo_{szc.dane_zlecenia["kodkreskowy"]}.docx'
        if os.path.exists(fn):
            os.unlink(fn)
        spr.generate(fn)

def generuj_opisy_raportow_do_uzupelnienia():
    from plugins import PluginManager

    res = ""

    def zbierz_z_okienka(comp):
        nonlocal res
        if isinstance(comp, InfoText):
            text = comp.init_kwargs.get('text')
            if not empty(text):
                res += text + "\n"
        if hasattr(comp, 'children'):
            for cld in comp.children or []:
                zbierz_z_okienka(cld)

    def zbierz(plugin, menu_path=None):
        nonlocal res
        if menu_path is None:
            menu_path = []
        # print(plugin.keys())
        # print(plugin['dotpath'])
        menu_entry = plugin.get('menu_entry')
        path = plugin.get('path')
        if menu_entry is None:
            if len(menu_path) == 0:
                menu_entry = "•"
            else:
                return
        full_path = menu_path + [menu_entry]
        res += f"# {' » '.join(full_path)}\n"
        res += f"#### {path}\n"

        dialog = getattr(plugin['module'], 'LAUNCH_DIALOG', None)
        if dialog is not None:
            zbierz_z_okienka(dialog)

        res += "\n"
        for cld in plugin.get('children') or []:
            zbierz(cld, full_path)

    pm = PluginManager()
    for plugin in pm.plugins:

        zbierz(plugin)

    with open('./doc/do_opisu_raportow.md', 'w') as f:
        f.write(res)


if __name__ == '__main__':
    print("Alab Reporter Playground")
    # datasources_reporter_auxilary_db_functions()
    # datasources_nocka_test()
    # eksport_kart_klienta()
    # simple_test()
    # test_bgtasks()
    # test_sprawozdanie_word()
    generuj_opisy_raportow_do_uzupelnienia()