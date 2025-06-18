from datasources.snrkonf import SNRKonf
from datasources.kakl import karta_klienta
from datasources.mop import MopDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, BadanieSearch, \
    Select, Radio, ValidationError, LabSearch, PlatnikSearch
from helpers import get_centrum_connection, prepare_for_json, obejdz_slownik
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from raporty.info._hl7ctl import ZlaczkiKlienta
from tasks.db import redis_conn
import json

MENU_ENTRY = 'Badaniach'

REQUIRE_ROLE = ['C-CS', 'C-PP', 'C-ROZL']

LAUNCH_DIALOG = Dialog(title="Wszystko o badaniu", panel=VBox(
    BadanieSearch(field='badanie', title='Badanie', width='600px'),
    LabSearch(field='laboratorium', title='w laboratorium', width='600px'),
    PlatnikSearch(field='platnik', title='dla płatnika', width='600px'),
))

HELP = """
Wyszukiwanie badań z bazy SNR. Informacje o metodach i ... z bazy wzorcowej. W zależności od uprawnień mogą być
widoczne ceny.
"""

def start_report(params, user_labs_available):
    params = LAUNCH_DIALOG.load_params(params)
    params['labs_available'] = user_labs_available
    bad = params['badanie']
    lab = params['laboratorium']
    pla = params['platnik']
    if bad is None and lab is None and pla is None:
        raise ValidationError("Nie wybrano nic.")
    report = TaskGroup(__PLUGIN__, params)
    if bad is not None:
        task = {
            'type': 'snr',
            'priority': 1,
            'params': params,
            'function': 'raport_snr'
        }
        report.create_task(task)
    if lab is not None:
        task = {
            'type': 'centrum',
            'priority': 0,
            'params': params,
            'target': lab,
            'function': 'raport_centrum'
        }
        report.create_task(task)
    report.save()
    return report


def raport_snr(task_params):
    params = task_params['params']
    snr = SNRKonf()
    res = snr.dict_select("""
        select b.symbol, b.nazwa, b.hs->'grupa' as grupa, b.hs->'pracownia' as pracownia,
            b.hs->'kod' as kod, b.hs->'rodzaj' as rodzaj, b.hs->'dorozliczen' as dorozliczen,
            b.hs->'rejestrowac' as rejestrowac, b.hs->'zerowacceny' as zerowacceny,
            b.hs->'bezrejestracji' as bezrejestracji
        from badania b 
        where b.symbol=%s
    """, [params['badanie']])[0]
    dane = [
        {'title': 'Symbol / grupa', 'value': '%s / %s' % (res['symbol'], res['grupa'])},
        {'title': 'Nazwa', 'value': res['nazwa']},
    ]
    uwagi = []
    for fld, podp in [
        ('rodzaj', 'Rodzaj'),
        ('kod', 'Kod'),
        ('pracownia', 'Pracownia')
    ]:
        if res[fld] is not None:
            dane.append({'title': podp, 'value': res[fld]})
    if res['zerowacceny'] == '1':
        uwagi.append('zeruje ceny składowych')
    # if res['rejestrowac'] == '1':
    #     pass
    # if res['bezrejestracji'] == '1':
    #     uwagi.append('zeruje ceny składowych') TODO chw o co tu chodzi, WIT_D+K ma oba pola = 1
    if res['rodzaj'] == 'P':
        skl = snr.dict_select("""
            select bwp.badanie, bwp.material, bwp.hs,
            b.nazwa as badanie_nazwa, m.nazwa as material_nazwa
            from badaniawpakietach bwp 
            left join badania b on b.symbol=bwp.badanie
            left join materialy m on m.symbol=bwp.material
            where bwp.pakiet=%s 
            and not bwp.del and not b.del and not m.del
            order by bwp.kolejnosc, b.kolejnosc, m.kolejnosc
        """, [params['badanie']])
        if len(skl) > 0:
            skl = ["%s:%s (%s:%s)" % (s['badanie'], s['material'] or '', s['badanie_nazwa'], s['material_nazwa'] or '') for s in skl]
            dane.append({'title': 'Składowe', 'value': "\n".join(skl)})
    else:
        pak = snr.dict_select("""
            select bwp.pakiet, bwp.hs,
            b.nazwa as pakiet_nazwa
            from badaniawpakietach bwp 
            left join badania b on b.symbol=bwp.pakiet
            where bwp.badanie=%s 
            and not bwp.del and not b.del
            order by b.kolejnosc, bwp.kolejnosc
        """, [params['badanie']])
        if len(pak) > 0:
            pak = ["%s (%s)" % (s['pakiet'], s['pakiet_nazwa']) for s in pak]
            dane.append({'title': 'W pakietach', 'value': "\n".join(pak)})



    if len(uwagi) > 0:
        dane.append({'title': 'Uwagi', 'value': '; '.join(uwagi)})

    return {
        'type': 'vertTable',
        'title': 'Badanie w SNR',
        'data': dane
    }

# select * from badaniawpakietach where pakiet='WIT_D+K' order by kolejnosc
#
# select * from materialywbadaniach  limit 10

                    # '"pacownia"=>"XROZL ", "dorozliczen"=>"1", "rejestrowac"=>"1", "zerowacceny"=>"1", "wspolrzednax"=>"22", "wspolrzednay"=>"243", "bezrejestracji"=>"1"'}

def raport_centrum(task_params):
    params = task_params['params']
    res = []
    with get_centrum_connection(task_params['target']) as conn:
        cols, rows = conn.raport_z_kolumnami("""
            select mat.symbol as "Materiał", mat.nazwa as "Mat. nazwa",
                gr.symbol as "Grupa do rejestracji", gr.nazwa as "Gr. nazwa",
                mwb.kolejnosc as "Kolejność",
                case when mwb.ukryty = 1 then 'TAK' else '' end as "Ukryty"
            from badania b
            left join MATERIALYWBADANIACH mwb on mwb.badanie=b.ID
            left join MATERIALY mat on mat.id=mwb.MATERIAL
            left join GRUPYDOREJESTRACJI gr on gr.id=mwb.GRUPA
            where b.symbol=? and b.del=0 and mwb.del=0 and mat.del=0
            order by mwb.ukryty, mwb.kolejnosc, mat.KOLEJNOSC
        """, [params['badanie']])
        if len(rows) > 0:
            res.append({
                'type': 'table',
                'title': '%s - materiały w badaniach' % task_params['target'],
                'header': cols,
                'data': prepare_for_json(rows)
            })
    return res
