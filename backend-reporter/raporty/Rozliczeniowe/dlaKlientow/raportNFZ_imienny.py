from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_snr_connection
from datasources.snr import SNR
from datasources.reporter import ReporterDatasource
from api.common import get_db
from decimal import Decimal
MENU_ENTRY = 'Raport Imienny dla NFZ'

REQUIRE_ROLE = ['C-FIN', 'C-CS', 'C-ROZL']
# REQUIRE_ROLE = 'ADMIN'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport Imienny dla NFZ, \nnależy wskazać dla jakiego płatnika ma być wykonany oraz z jakiego laboratorium'),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
    TextInput(field='platnik', title='Płatnik'),
))
badania = [
{'symbol': 'MORF-PO','kod': '1001100006'},
{'symbol': 'MORF','kod': '1001100007'},
{'symbol': 'RETI','kod': '1001100003'},
{'symbol': 'OB','kod': '1001100004'},
{'symbol': 'NA','kod': '1001200001'},
{'symbol': 'K','kod': '1001200002'},
{'symbol': 'CA++','kod': '1001200032'},
{'symbol': 'FE','kod': '1001200004'},
{'symbol': 'TIBC','kod': '1001200033'},
{'symbol': 'TRANSF','kod': '1001200005'},
{'symbol': 'HBA1C','kod': '1001100005'},
{'symbol': 'UREA','kod': '1001200006'},
{'symbol': 'KREA','kod': '1001200007'},
{'symbol': 'GLU','kod': '1001200008'},
{'symbol': 'KRZYWA','kod': '1001200009'},
{'symbol': 'TP','kod': '1001200010'},
{'symbol': 'PROTEIN','kod': '1001200011'},
{'symbol': 'ALB','kod': '1001200012'},
{'symbol': 'CRP-IL','kod': '1001600004'},
{'symbol': 'UA','kod': '1001200013'},
{'symbol': 'CHOL','kod': '1001200014'},
{'symbol': 'HDL','kod': '1001200015'},
{'symbol': 'LDL','kod': '1001200016'},
{'symbol': 'TG','kod': '1001200017'},
{'symbol': 'BIL-T','kod': '1001200018'},
{'symbol': 'BIL-D','kod': '1001200019'},
{'symbol': 'ALP','kod': '1001200020'},
{'symbol': 'AST','kod': '1001200021'},
{'symbol': 'ALT','kod': '1001200022'},
{'symbol': 'GGTP','kod': '1001200023'},
{'symbol': 'AMYL','kod': '1001200024'},
{'symbol': 'CK','kod': '1001200025'},
{'symbol': 'ACP','kod': '1001200026'},
{'symbol': 'RF-IL','kod': '1001200027'},
{'symbol': 'ASO-IL','kod': '1001200028'},
{'symbol': 'TSH','kod': '1001200029'},
{'symbol': 'HBSAG','kod': '1001200030'},
{'symbol': 'WR','kod': '1001200031'},
{'symbol': 'FT3','kod': '1001200034'},
{'symbol': 'FT4','kod': '1001200035'},
{'symbol': 'TPSA','kod': '1001200036'},
{'symbol': 'MOCZ','kod': '1001300001'},
{'symbol': 'BIALK-M','kod': '1001300002'},
{'symbol': 'GLUKO-M','kod': '1001300003'},
{'symbol': 'CA-M','kod': '1001300004'},
{'symbol': 'AMYL-M','kod': '1001300005'},
{'symbol': 'KAL-BO','kod': '1001400001'},
{'symbol': 'KA-PAS','kod': '1001400002'},
{'symbol': 'KREW-UT','kod': '1001400003'},
{'symbol': 'PT','kod': '1001500001'},
{'symbol': 'APTT','kod': '1001500002'},
{'symbol': 'FIBR','kod': '1001500003'},
{'symbol': 'P-MOCZ','kod': '1001600001'},
{'symbol': 'P-GDOR','kod': '1001600002'},
{'symbol': 'P-SS','kod': '1001600003'},
]

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    if params['platnik'] is None:
        raise ValidationError("Nie wybrano płatnika")
    # validate_date_range(params['dataod'], params['datado'], 31)
    rep = ReporterDatasource()
   
    task = {
        'type': 'snr',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_lab',
    }
    report.create_task(task)
    report.save()
    return report

def raport_lab(task_params):
    lab = task_params['target']
    params = task_params['params']
    tablica = []
    sql = """
        select
            w.hs->'pacjencinazwisko' as "NAZWISKO",
            w.hs->'pacjencipesel' as "PESEL",
            w.hs->'pacjenciimiona' as "IMIONA",
            pk.hs->'kod' as "KOD",
            case when (w.material not in ('SUR', 'OS-F') and w.badanie ='GLU')  then 'KRZYWA' else w.badanie end as "BADANIE",
            w.datarozliczeniowa AS "ROZLICZONE", 
            count (W.id) as "ILOSC"
        from wykonania W
            left outer join Platnicy P on W.platnik = P.ID
            left outer join Platnicywlaboratoriach Pwl on PWL.laboratorium = w.laboratorium and PWL.platnik = P.ID and not pwl.del
            left outer join pozycjekatalogow pk on pk.symbol=w.badanie and pk.katalog = 'BADANIA'
        where 
            w.datarozliczeniowa between '%s' and '%s' 
            and pwl.symbol = '%s' and not W.bezPlatne
            and w.badanie in ('MORF', 'RETI', 'OB', 'NA', 'K', 'CA++', 'FE', 'TIBC', 'TRANSF', 'HBA1C', 'UREA', 'KREA', 'TP', 'PROTEIN', 'ALB', 'CRP-IL', 'UA', 'CHOL', 'HDL', 'LDL', 'TG', 'BIL-T', 
            'BIL-D', 'ALP', 'AST', 'ALT', 'GGTP', 'AMYL', 'CK', 'ACP', 'RF-IL', 'ASO-IL', 'TSH', 'HBSAG', 'WR', 'FT3', 'FT4', 'TPSA', 'MOCZ', 'BIALK-M', 'GLUKO-M', 'CA-M', 'AMYL-M', 'KAL-BO', 'KA-PAS', 'KREW-UT', 
            'PT', 'APTT', 'FIBR', 'P-MOCZ', 'P-GDOR', 'P-SS', 'GLU')
        group by w.hs->'pacjencinazwisko', w.hs->'pacjencipesel', w.hs->'pacjenciimiona', w.badanie, w.material, w.datarozliczeniowa, pk.hs->'kod'

    """ % (params['dataod'], params['datado'], params['platnik'])


    with get_snr_connection() as snr:
        wyniki = snr.dict_select(sql)
        for row in wyniki:
            kod_badania = next((i['kod'] for i in badania if i['symbol'] == row['BADANIE']), None)
            tablica.append([
                prepare_for_json(row['ROZLICZONE']),
                kod_badania,
                row['ILOSC'],
                '',
                row['PESEL'],
                row['NAZWISKO'],
                row['IMIONA'],'',''])
        

    return {
        'type': 'table',
        'header':'Data wykonania badania,Kod badania,Ilość badań,Rozpoznania ICD10,PESEL,Nazwisko,Imię,PESEL opiekuna,Cukrzyca lub przewlekła choroba układu krążenia'.split(','),
        'data': tablica
    }




