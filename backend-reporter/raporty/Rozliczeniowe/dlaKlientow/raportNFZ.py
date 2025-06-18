from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_snr_connection
from datasources.snr import SNR
from datasources.reporter import ReporterDatasource
from api.common import get_db
from decimal import Decimal

from helpers import list_from_space_separated

MENU_ENTRY = 'Raport dla NFZ'

REQUIRE_ROLE = ['C-FIN', 'C-CS', 'C-ROZL']
# REQUIRE_ROLE = 'ADMIN'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport dla NFZ, \nnależy wskazać dla jakiego płatnika ma być wykonany oraz z jakiego laboratorium. Jeśli eksport ma nie być na wszystkich zleceniodawców to można podać symbole zleceniodawców oddzielone spacją.'),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', pokaz_nieaktywne=True),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
    TextInput(field='platnik', title='Płatnik'),
    TextInput(field='zleceniodawcy', title='Zleceniodawcy'),
    Switch(field="filtrowac", title="Podział na lekarzy"),
))
wiersze= [
        {'lp':'1','nazwa':'Badania hematologiczne','kod_badania': '','symbol_badania': '','kod_swiadczenia': '','naglowek': True},
        {'lp':'1','nazwa': 'morfologia krwi obwodowej z płytkami krwi','kod_badania': '1001100006','symbol_badania': 'MORF-PO','kod_swiadczenia': '18-9'},
        {'lp':'2','nazwa': 'morfologia krwi obwodowej z wzorem odsetkowym i płytkami krwi','kod_badania':  '1001100007','symbol_badania': 'MORF','kod_swiadczenia': '18-9'},
        {'lp':'3','nazwa': 'retykulocyty ','kod_badania':  '1001100003','symbol_badania': 'RETI','kod_swiadczenia': '18-9'},
        {'lp':'4','nazwa': 'odczyn opadania krwinek czerwonych (OB) ','kod_badania':  '1001100004','symbol_badania': 'OB','kod_swiadczenia': '18-9'},
        {'lp':'2','nazwa':'Badania biochemiczne i immunochemiczne w surowicy krwi','kod_badania': '','symbol_badania': '','kod_swiadczenia': '','naglowek': True},
        {'lp':'1','nazwa': 'sód ','kod_badania':  '1001200001','symbol_badania': 'NA','kod_swiadczenia': '18-9'},
        {'lp':'2','nazwa': 'potas ','kod_badania':  '1001200002','symbol_badania': 'K','kod_swiadczenia': '18-9'},
        {'lp':'3','nazwa': 'wapń zjonizowany ','kod_badania':  '1001200032','symbol_badania': 'CA++','kod_swiadczenia': '18-9'},
        {'lp':'4','nazwa': 'żelazo ', 'kod_badania': '1001200004','symbol_badania': 'FE','kod_swiadczenia': '18-9'},
        {'lp':'5','nazwa': 'żelazo -  całkowita zdolność wiązania (TIBC)','kod_badania':  '1001200033','symbol_badania': 'TIBC','kod_swiadczenia': '18-9'},
        {'lp':'6','nazwa': 'stężenie transferyny ', 'kod_badania': '1001200005','symbol_badania': 'TRANSF','kod_swiadczenia': '18-9'},
        {'lp':'7','nazwa': 'stężenie hemoglobiny glikowanej (HbA1c)','kod_badania':  '1001100005','symbol_badania': 'HBA1C','kod_swiadczenia': '18-9'},
        {'lp':'8','nazwa': 'mocznik ','kod_badania':  '1001200006','symbol_badania': 'UREA','kod_swiadczenia': '18-9'},
        {'lp':'9','nazwa': 'kreatynina ','kod_badania':  '1001200007','symbol_badania': 'KREA','kod_swiadczenia': '18-9'},
        {'lp':'10','nazwa': 'glukoza ','kod_badania':  '1001200008','symbol_badania': 'GLU','kod_swiadczenia': '18-9'},
        {'lp':'11','nazwa': 'test obciążenia glukozą ','kod_badania':  '1001200009','symbol_badania': 'KRZYWA','kod_swiadczenia': '18-9'},
        {'lp':'12','nazwa': 'białko całkowite ','kod_badania':  '1001200010','symbol_badania': 'TP','kod_swiadczenia': '18-9'},
        {'lp':'13','nazwa': 'proteinogram ','kod_badania':  '1001200011','symbol_badania': 'PROTEIN','kod_swiadczenia': '18-9'},
        {'lp':'14','nazwa': 'albumina ','kod_badania':  '1001200012','symbol_badania': 'ALB','kod_swiadczenia': '18-9'},
        {'lp':'15','nazwa': 'białko C-reaktywne (CRP)', 'kod_badania': '1001600004','symbol_badania': 'CRP-IL','kod_swiadczenia': '18-9'},
        {'lp':'16','nazwa': 'kwas moczowy','kod_badania':  '1001200013','symbol_badania': 'URIC','kod_swiadczenia': '18-9'},
        {'lp':'17','nazwa': 'cholesterol całkowity', 'kod_badania': '1001200014','symbol_badania': 'CHOL','kod_swiadczenia': '18-9'},
        {'lp':'18','nazwa': 'cholesterol-HDL ','kod_badania':  '1001200015','symbol_badania': 'HDL','kod_swiadczenia': '18-9'},
        {'lp':'19','nazwa': 'cholesterol-LDL ','kod_badania':  '1001200016','symbol_badania': 'LDL','kod_swiadczenia': '18-9'},
        {'lp':'20','nazwa': 'triglicerydy (TG)','kod_badania':  '1001200017','symbol_badania': 'TG','kod_swiadczenia': '18-9'},
        {'lp':'21','nazwa': 'bilirubina całkowita ','kod_badania':  '1001200018','symbol_badania': 'BIL-T','kod_swiadczenia': '18-9'},
        {'lp':'22','nazwa': 'bilirubina bezpośrednia','kod_badania':  '1001200019','symbol_badania': 'BIL-D','kod_swiadczenia': '18-9'},
        {'lp':'23','nazwa': 'fosfataza alkaliczna (ALP) ', 'kod_badania': '1001200020','symbol_badania': 'ALP','kod_swiadczenia': '18-9'},
        {'lp':'24','nazwa': 'aminotransferaza asparaginianowa (AST) ','kod_badania':  '1001200021','symbol_badania': 'AST','kod_swiadczenia': '18-9'},
        {'lp':'25','nazwa': 'aminotransferaza alaninowa (ALT)','kod_badania':  '1001200022','symbol_badania': 'ALT','kod_swiadczenia': '18-9'},
        {'lp':'26','nazwa': 'gammaglutamylotranspeptydaza (GGTP) ','kod_badania':  '1001200023','symbol_badania': 'GGTP','kod_swiadczenia': '18-9'},
        {'lp':'27','nazwa': 'amylaza ', 'kod_badania': '1001200024','symbol_badania': 'AMYL','kod_swiadczenia': '18-9'},
        {'lp':'28','nazwa': 'kinaza kreatynowa (CK)','kod_badania':  '1001200025','symbol_badania': 'CK','kod_swiadczenia': '18-9'},
        {'lp':'29','nazwa': 'fosfataza kwaśna całkowita (ACP)','kod_badania':  '1001200026','symbol_badania': 'ACP','kod_swiadczenia': '18-9'},
        {'lp':'30','nazwa': 'czynnik reumatoidalny (RF) ','kod_badania':  '1001200027','symbol_badania': 'RF-IL','kod_swiadczenia': '18-9'},
        {'lp':'31','nazwa': 'miano antystreptolizyn O (ASO) ','kod_badania':  '1001200028','symbol_badania': 'ASO-IL','kod_swiadczenia': '18-9'},
        {'lp':'32','nazwa': 'hormon tyreotropowy (TSH) ','kod_badania':  '1001200029','symbol_badania': 'TSH','kod_swiadczenia': '18-9'},
        {'lp':'33','nazwa': 'antygen HBs-AgHBs ','kod_badania':  '1001200030','symbol_badania': 'HBSAG','kod_swiadczenia': '18-9'},
        {'lp':'34','nazwa': 'VDRL ','kod_badania':  '1001200031','symbol_badania': 'WR','kod_swiadczenia': '18-9'},
        {'lp':'35','nazwa': 'FT3','kod_badania':  '1001200034','symbol_badania': 'FT3','kod_swiadczenia': '18-9'},
        {'lp':'36','nazwa': 'FT4','kod_badania':  '1001200035','symbol_badania': 'FT4','kod_swiadczenia': '18-9'},
        {'lp':'37','nazwa': 'PSA - Antygen swoisty dla stercza całkowity','kod_badania':  '1001200036','symbol_badania': 'TPSA','kod_swiadczenia': '18-9'},
        {'lp':'3','nazwa':'Badanie moczu','kod_badania': '','symbol_badania': '','kod_swiadczenia': '','naglowek': True},
        {'lp':'1','nazwa': 'ogólne badanie moczu z oceną właściwości fizycznych, chemicznych oraz oceną mikroskopową osadu','kod_badania':  '1001300001','symbol_badania': 'MOCZ','kod_swiadczenia': '18-9'},
        {'lp':'2','nazwa': 'ilościowe oznaczanie białka','kod_badania':  '1001300002','symbol_badania': 'BIALK-M','kod_swiadczenia': '18-9'},
        {'lp':'3','nazwa': 'ilościowe oznaczanie glukozy ','kod_badania':  '1001300003','symbol_badania': 'GLUKO-M','kod_swiadczenia': '18-9'},
        {'lp':'4','nazwa': 'ilościowe oznaczanie wapnia ','kod_badania':  '1001300004','symbol_badania': 'CA-M','kod_swiadczenia': '18-9'},
        {'lp':'5','nazwa': 'ilościowe oznaczanie amylazy ','kod_badania':  '1001300005','symbol_badania': 'AMYL-M','kod_swiadczenia': '18-9'},
        {'lp':'4','nazwa':'Badanie kału','kod_badania': '','symbol_badania': '','kod_swiadczenia': '','naglowek': True},
        {'lp':'1','nazwa': 'badanie ogólne ','kod_badania':  '1001400001','symbol_badania': 'KAL-BO','kod_swiadczenia': '18-9'},
        {'lp':'2','nazwa': 'pasożyty ', 'kod_badania': '1001400002','symbol_badania': 'KA-PAS','kod_swiadczenia': '18-9'},
        {'lp':'3','nazwa': 'krew utajona - metodą immunochemiczną ','kod_badania':  '1001400003','symbol_badania': 'KREW-UT','kod_swiadczenia': '18-9'},
        {'lp':'5','nazwa': 'Badania układu krzepnięcia','kod_badania': '','symbol_badania': '','kod_swiadczenia': '','naglowek': True},
        {'lp':'1','nazwa': 'wskaźnik protrombinowy (INR) ','kod_badania':  '1001500001','symbol_badania': 'PT','kod_swiadczenia': '18-9'},
        {'lp':'2','nazwa': 'czas kaolinowo-kefalinowy (APTT) ','kod_badania':  '1001500002','symbol_badania': 'APTT','kod_swiadczenia': '18-9'},
        {'lp':'3','nazwa': 'fibrynogen ','kod_badania':  '1001500003','symbol_badania': 'FIBR','kod_swiadczenia': '18-9'},
        {'lp':'6','nazwa': 'Badania mikrobiologiczne','kod_badania': '','symbol_badania': '','kod_swiadczenia': ''},
        {'lp':'1','nazwa': 'posiew moczu z antybiogramem ','kod_badania':  '1001600001','symbol_badania': 'P-MOCZ','kod_swiadczenia': '18-9'},
        {'lp':'2','nazwa': 'posiew wymazu z gardła z antybiogramem','kod_badania':  '1001600002','symbol_badania': 'P-GDOR','kod_swiadczenia': '18-9'},
        {'lp':'3','nazwa': 'posiew kału w kierunku pałeczek Salmonella i Shigella','kod_badania':  '1001600003','symbol_badania': 'P-SS','kod_swiadczenia': '18-9'},
        {'lp':'7','nazwa':'Badanie elektrokardiograficzne (EKG) w spoczynku','kod_badania':  '1001700001','symbol_badania': '','kod_swiadczenia': '20-9','naglowek': True},
        {'lp':'8','nazwa':'Badania ultrasonograficzne','kod_badania': '','symbol_badania': '','kod_swiadczenia': '','naglowek': True},
        {'lp':'1','nazwa': 'USG tarczycy i przytarczyc','kod_badania':  '1001800002','symbol_badania': '','kod_swiadczenia': '19-9'},
        {'lp':'2','nazwa': 'USG ślinianek','kod_badania':  '1001800003','symbol_badania': '','kod_swiadczenia': '19-9'},
        {'lp':'3','nazwa': 'USG nerek, moczowodów, pęcherza moczowego','kod_badania':  '1001800004','symbol_badania': '','kod_swiadczenia': '19-9'},
        {'lp':'4','nazwa': 'USG brzucha i przestrzeni zaotrzewnowej, w tym wstępnej oceny gruczołu krokowego','kod_badania':  '1001800005','symbol_badania': '','kod_swiadczenia': '19-9'},
        {'lp':'5','nazwa': 'USG obwodowych węzłów chłonnych','kod_badania':  '1001800006','symbol_badania': '','kod_swiadczenia': '19-9'},
        {'lp':'9','nazwa': 'Spirometria','kod_badania':  '1002000001','symbol_badania': '','kod_swiadczenia': '','naglowek': True},
        {'lp':'10','nazwa': 'Zdjęcia radiologiczne','kod_badania': '','symbol_badania': '','kod_swiadczenia': '','naglowek': True},
        {'lp':'1','nazwa': 'zdjęcie klatki piersiowej w projekcji AP i bocznej ','kod_badania':  '1001900001','symbol_badania': '','kod_swiadczenia': '19-9'},
        {'lp':'2','nazwa': 'zdjęcia kostne - w przypadku kręgosłupa, kończyn i miednicy w projekcji AP i bocznej:','kod_badania':  '','symbol_badania': '','kod_swiadczenia': '19-9'},
        {'lp':'2a)','nazwa': 'zdjęcia kostne - w przypadku kręgosłupa w projekcji AP i bocznej (cały kręgosłup)','kod_badania':  '1001900002','symbol_badania': '','kod_swiadczenia': '19-9'},
        {'lp':'2b)','nazwa': 'zdjęcia kostne - w przypadku kręgosłupa w projekcji AP i bocznej (odcinkowe)','kod_badania':  '1001900003','symbol_badania': '','kod_swiadczenia': '19-9'},
        {'lp':'2c)','nazwa': 'zdjęcia kostne - w przypadku kończyn w projekcji AP i bocznej','kod_badania':  '1001900004','symbol_badania': '','kod_swiadczenia': '19-9'},
        {'lp':'2d)','nazwa': 'zdjęcia kostne - w przypadku miednicy w projekcji AP i bocznej','kod_badania':  '1001900005','symbol_badania': '','kod_swiadczenia': '19-9'},
        {'lp':'3','nazwa': 'zdjęcie czaszki ','kod_badania':  '1001900006','symbol_badania': '','kod_swiadczenia': '19-9'},
        {'lp':'4','nazwa': 'zdjęcie zatok ','kod_badania':  '1001900007','symbol_badania': '','kod_swiadczenia': '19-9'},
        {'lp':'5','nazwa': 'zdjęcie przeglądowe jamy brzusznej','kod_badania':  '1001900008','symbol_badania': '','kod_swiadczenia': '19-9'}
]

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    if params['platnik'] is None:
        raise ValidationError("Nie wybrano płatnika")
    params['zleceniodawcy'] = list_from_space_separated(params['zleceniodawcy'], upper=True, also_comma=True, also_newline=True, also_semicolon=True, unique=True)
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
    lekarze = []
    tablica = []
    sql = """
    select
		(w.hs->'lekarzenazwisko') || ' ' || (w.hs->'lekarzeimiona') as "LEKARZ", 
		case when (w.material not in ('SUR', 'OS-F') and w.badanie ='GLU')  then 'KRZYWA' else trim(w.badanie) end as "BADANIE",
		count (W.id) as "ILOSC"
	from wykonania W
		left outer join Platnicy P on W.platnik = P.ID
		left outer join Platnicywlaboratoriach Pwl on PWL.laboratorium = w.laboratorium and PWL.platnik = P.ID and not pwl.del
		left outer join ZleceniodawcyWLaboratoriach ZWL on ZWL.Laboratorium = w.laboratorium and zwl.zleceniodawca = w.zleceniodawca and not zwl.del
		left outer join pozycjekatalogow pk on pk.symbol=w.badanie and pk.katalog = 'BADANIA'
	where 
		w.datarozliczeniowa between %s and %s and w.laboratorium = %s
		and pwl.symbol = %s and not W.bezPlatne and not w.jestpakietem 
		and w.badanie in ('MORF', 'RETI', 'OB', 'NA', 'K', 'CA++', 'FE', 'TIBC', 'TRANSF', 'HBA1C', 'UREA', 'KREA', 'GLU', 'TP', 'PROTEIN', 'ALB', 'CRP-IL', 'URIC', 'CHOL', 'HDL', 'LDL', 'TG', 'BIL-T', 
		'BIL-D', 'ALP', 'AST', 'ALT', 'GGTP', 'AMYL', 'CK', 'ACP', 'RF-IL', 'ASO-IL', 'TSH', 'HBSAG', 'WR', 'FT3', 'FT4', 'TPSA', 'MOCZ', 'BIALK-M', 'GLUKO-M', 'CA-M', 'AMYL-M', 'KAL-BO', 'KA-PAS', 'KREW-UT', 
		'PT', 'APTT', 'FIBR', 'P-MOCZ', 'P-GDOR', 'P-SS')
	group by w.badanie, w.material, w.hs->'lekarzenazwisko', w.hs->'lekarzeimiona'
	order by w.hs->'lekarzenazwisko', w.hs->'lekarzeimiona';
    """
    sql_params = [params['dataod'], params['datado'], lab, params['platnik']]
    print('Zleceniodawcy', params['zleceniodawcy'])
    if len(params['zleceniodawcy']) > 0:
        sql = sql.replace("pwl.symbol = %s", "pwl.symbol = %s and zwl.symbol in %s")
        sql_params.append(tuple(params['zleceniodawcy']))
    print(sql)
    print(sql_params)

    with get_snr_connection() as snr:
        wyniki = snr.dict_select(sql, sql_params)
        for row in wyniki:
            print(row)
            if row['LEKARZ'] not in lekarze:
                lekarze.append(row['LEKARZ'])

        if not params['filtrowac']:
            header = ['Lp.','Wyszczególnienie (badania diagnostyczne)','Kod badań diagnostycznych wg NFZ','Kod świadczenia','Liczba wykonanych badań w okresie sprawozdawczym']
            for wiersz in wiersze:
                ilosc  =  sum(i['ILOSC'] for i in wyniki if i['BADANIE'] == wiersz['symbol_badania'])
                tablica.append([wiersz['lp'],wiersz['nazwa'],wiersz['kod_badania'],wiersz['kod_swiadczenia'],ilosc])
        else :
            header = ['Lekarz','Lp.','Wyszczególnienie (badania diagnostyczne)','Kod badań diagnostycznych wg NFZ','Kod świadczenia','Liczba wykonanych badań w okresie sprawozdawczym']
            for lekarz in lekarze:
                for wiersz in wiersze:
                    ilosc  =  sum(i['ILOSC'] for i in wyniki if i['BADANIE'] == wiersz['symbol_badania'] and i['LEKARZ'] == lekarz)
                    tablica.append([lekarz,wiersz['lp'],wiersz['nazwa'],wiersz['kod_badania'],wiersz['kod_swiadczenia'],ilosc])
        
    res = {
        'type': 'table',
        'header':header,
        'data': tablica
    }
    return res 




