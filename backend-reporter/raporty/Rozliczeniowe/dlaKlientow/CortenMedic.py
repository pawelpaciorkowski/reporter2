import json

from api.common import get_db
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, generate_barcode_img_tag, get_centrum_connection
from datasources.nocka import NockaDatasource
import random
import string

MENU_ENTRY = 'Corten Medic'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport Corten Medic NFZ + komercyjne. Stały zestaw symboli zleceniodawców'),
    DateInput(field='dataod', title='Data od', default='PZM'),
    DateInput(field='datado', title='Data do', default='KZM'),
))

SQL = """
    select
        extract(year from lab_wykonanie_data_rozliczenia) as rok,
        extract(month from lab_wykonanie_data_rozliczenia) as miesiac,
        lab, zleceniodawca, badanie, 
        count(id) as ilosc
    from wykonania_pelne
    where zleceniodawca in ('PZCOPRA','PZCORTE','PZCORAN','PZCORBR','PZCORPE','PZCORDE','PZCORDO','PZCORGI','PZCORKA','PZCORPO','PZCORNE','PZCOROK','PZCOROT','PZCORPU','PZCORRE','PZCORAL','PZCORCS','PZCORBS','PZCORCP','PZCORWE','PZCORDI','PZCORMP','PZCORMS','PZCORND','PZCORON','PZCOROR','PZCORTO','PZCORPL','PZCORPZ','PZCORPR','PZCORPS','PZCORRH','PZCORST','PZCORSD','PZCORPP','PZCORFI','PZCORUS','PZCORLO','SDZCORT','SDZCORP','SDZCORD','SDZCODO','SDZCOPG','SDZCORK','SDZCOPZ','SDZCORN','SDZCORO','SDZCOPO','SDZCOPL','SDZCORM','CZCOMDE','CZCOMST','CZCOMCS','CZCOMSL','CZCOML','CZCOMPL','CZCOMDO','CZCOMGI','CZCOMIN','CZCOMMP','CZCOMOR','CZCOMPP','CZCOMPS','CZCOMSD','CZCOMPZ','CZCORER','CZCORAD','CZCOKIE','TFZCORT','TKZCORT','CZCORDE','CZCORLA','CZCORPL','CZCORPE','CZCOREN','CZCORAL','CZCORCS','CZCORBS','CZCORWE','CZCORDO','CZCORGI','CZCORIN','CZCORKA','CZCORPZ','CZCORLO','CZCORMS','CZCORMP','CZCORNE','CZCOROK','CZCOROR','CZCORPO','CZCORPY','CZCORSD','CZCORST','CZCORUR','CZCOROT','CZCORPI','CZCORPS','CZCORSC','CZCORRO','CZCOREW','CZCOKRA','CZCOMAK','CZCOMOD','CZCOPAS','JZCORTE','CZCORKP','CZCORDU','OZCORT','QPZCORT','CZCORML','CZCOPSD','CZCOPCS','CZCOPGI','CZCOPOR','CZCOPPL','CZCOPRO','CZCORPR','CZCORDZ','CZCOPST','CZCORSK','EZCORT','CZCODSS','CZCOPOL','CZCOSTR','CZCORC','CZCORPG','CZCOKDZ','CZCOMSZ','CZCONDZ','CZCORMR','CZCORM','CZCORMD','CZCORSS','CNF493','QPNF494','CNF494','QPNF324','LNF324','GNNF324','CNF324','AYNF324','CNF492','CNF490','RENF356','LNF356','GNNF356','ENF356','CNF356','AYNF356','QPNF321','CNF321','ONF317','LNF317','GNNF317','CNF317','CNF491','CNF495','TFNF406','KTNF406','CNF406','CNF416','TKNF336','TFNF336','RENF336','LNF336','KTNF336','GNNF336','CNF336','AYNF336','CNF538','CNF430','CNF350','TFNF527','CNF306','CNF307','QPNF536','QPNF537','QPNF537','CNF474','LFNF500','CNF500','CNF536','CNF537','TKNF347','TFNF347','RENF347','LNF347','KTNF347','GNNF347','CNF347','AYNF347','TKNF346','TFNF346','RENF346','LNF346','KTNF346','GNNF346','CNF346','AYNF346','TFNF415','KTNF415','CNF415','ENF428','CNF428','ONF476','CNF476','AYNF476','TFNF405','KTNF405','CNF405','RENF368','ONF368','LNF368','GNNF368','CNF368','AYNF368','TFNF404','KTNF404','CNF404','QPNF429','CNF429','TFNF413','CNF413','KTNF414','CNF414','TFNF412','KTNF412','CNF412','RENF343','LNF343','GNNF343','CNF343','AYNF343','TKNF344','TFNF344','RENF344','LNF344','KTNF344','GNNF344','CNF344','AYNF344','RENF355','QPNF355','LNF355','GNNF355','CNF355','AYNF355','TFNF475','KTNF475','CNF475','TFNF334','RENF334','KTNF334','GNNF334','CNF334','AYNF334','TKNF345','TFNF345','RENF345','LNF345','KTNF345','GNNF345','CNF345','AYNF345')
    and badanie in ('2019COV', '19COVA', '19COVN', 'COV-GEN')
    and lab_wykonanie_godz_zatw is not null and blad_wykonania is null
    and lab_wykonanie_data_rozliczenia between %s and %s
    group by 1,2,3,4,5
    order by 1,2,3,4,5
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 90)
    task = {
        'type': 'noc',
        'priority': 1,
        'params': params,
        'function': 'raport_noc',
    }
    report.create_task(task)
    report.save()
    return report


def raport_noc(task_params):
    params = task_params['params']
    noc = NockaDatasource()
    cols, rows = noc.select(SQL, [params['dataod'], params['datado']])
    return {
        'type': 'table',
        'header': cols,
        'data': prepare_for_json(rows)
    }
