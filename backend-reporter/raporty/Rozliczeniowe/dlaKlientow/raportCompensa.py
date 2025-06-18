import json
from datasources.mop import MopDatasource
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty, get_snr_connection
from datasources.reporter import ReporterDatasource
from tasks.db import redis_conn

MENU_ENTRY = 'Raport Compensa'

REQUIRE_ROLE = ['C-FIN', 'C-CS', 'C-ROZL']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport z ilości wykonanych badań dla Compensy'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
))

BADANIA = {
    'HBE-AG': ('CO350-00', 'zapalenie wątroby typu B Antygen (HBeAg)'),
    'TRANSF': ('CO373-00', 'Transferyna'),
    'ATPO': ('CO376-00', 'Przeciwciała anty TPO (przeciw peroksydazie tarczycowej) przeciwciała przeciwtarczycowe'),
    'CEA': ('CO378-00', 'Antygen karcynoembrionalny (CEA)'),
    'D-DIMER': ('CO378-01', 'Produkty degradacji fibryny D-dimery'),
    'KATECHO': ('CO382-00', 'Katecholaminy w moczu'),
    'FIBR': ('CO384-00', 'Fibrynogen'),
    'CERULOP': ('CO390-00', 'Ceruloplazmina'),
    'TEST-F': ('CO402-00', 'Testosteron wolny'),
    'TESTOST': ('CO403-00', 'Testosteron całkowity'),
    'RF-IL': ('CO430-00', 'Czynnik reumatoidalny (RF)'),
    'TYREO': ('CO432-00', 'Tyreoglobulina Tg'),
    'CL': ('CO435-00', 'Chlorki we krwi'),
    'CL-M': ('CO436-00', 'Chlorki w moczu'),
    'T4': ('CO436-01', 'Tyroksyna całkowita (TT4)'),
    'FT4': ('CO439-00', 'Tyroksyna wolna (fT4)'),
    'WAALER': ('CO440-00', 'Odczyn Waalera-Rosego'),
    'TSH': ('CO443-00', 'Hormon stymulujący gruczoł tarczowy (TSH)'),
    'AST': ('CO450-00', 'Aminotransferaza asparaginowa (ASpaT) (AST) (SCOT)'),
    'CA++': ('CO330-00', 'Wapń zjonizowany'),
    'UPIEL': ('CO214-01', 'Inne świadczenia medyczne (np. Pobranie materiału do badań)'),
    'BIL': ('CO249-00', 'Bilirubina pośrednia'),
    'EBV-G/EBV-M': ('CO665-00', 'Wirus Epstein-Barr EBV (mononukleoza) kapsyd wirusa (VGA)'),
    'PLYTKI': ('CO002-04', 'Płytki krwi manualnie'),
    'IGG': ('CO784-02', 'Immunoglobuliny IgG całkowite/nieswoiste'),
    'IGM': ('CO784-03', 'Immunoglobuliny IgM całkowite/nieswoiste'),
    'ALT': ('CO460-00', 'Aminotransferaza alaninowa (ALaT) (ALT) (SGPT)'),
    'CHOL': ('CO465-00', 'Cholesterol  całkowity'),
    'TG': ('CO478-00', 'Trójglicerydy'),
    'T3': ('CO480-00', 'Trójjodotyronina T3 całkowita (TT-3)'),
    'FT3': ('CO481-00', 'Trójjodotyronina wolna (fT3)'),
    'TROP-I': ('CO484-00', 'Troponina ilościowo'),
    '-17OHKS': ('CO491-00', 'Hydroksykortykosteroidy 17-(17-OHCS)'),
    'WSNITY': ('CO510-00', 'Tyrozyna'),
    'UREA': ('CO520-00', 'Mocznik we krwi'),
    'UREA-M': ('CO520-01', 'Mocznik w moczu'),
    'CU': ('CO525-00', 'Miedź'),
    'INS': ('CO525-01', 'Insulina całkowita'),
    'FKORTDM': ('CO530-00', 'Kortyzol wolny w moczu'),
    'KORT': ('CO533-00', 'Kortyzol całkowity we krwi'),
    'FE': ('CO540-00', 'Żelazo'),
    'URIC': ('CO550-00', 'Kwas moczowy we krwi'),
    'TIBC': ('CO550-01', 'Badanie zdolności wiązania żelaza (TIBC/UIBC)'),
    'CK': ('CO550-02', 'Kinaza kreatynowa (CK), (CPK) całkowita'),
    'URIC-M': ('CO550-11', 'Kwas moczowy w moczu'),
    'CK-MM': ('CO552-00', 'Kinaza kreatynowa (CK), (CPK) izoenzymy'),
    'CK-MB': ('CO553-00', 'Kinaza kreatynowa (CK), (CPK) tylko frakcja MB'),
    'KREA': ('CO565-00', 'Kreatynina we krwi'),
    'VMADZM': ('CO585-01', 'Kwas walininomigdałowy (VMA) w moczu'),
    'WR': ('CO592-00', 'Badanie w kierunku kiły Odczyn Wassermana (WR) USR VDRL'),
    'KWMLEKO': ('CO605-00', 'Kwas mlekowy - we krwi'),
    'WIT-B12': ('CO607-00', 'Witamina B12'),
    'PT': ('CO610-00', 'Czas protrombinowy (PT/wskaźnik Quicka/INR)'),
    'LDH': ('CO615-01', 'Dehydrogenaza mleczanowa (LDH)'),
    'KRZT-A': ('CO615-02', 'Przeciwciało przeciw Krztusiec Bordetella  przeciwciała  (IgA / IgG / IgM)'),
    'KRZT-G': ('CO615-02', 'Przeciwciało przeciw Krztusiec Bordetella  przeciwciała  (IgA / IgG / IgM)'),
    'KRZT-M': ('CO615-02', 'Przeciwciało przeciw Krztusiec Bordetella  przeciwciała  (IgA / IgG / IgM)'),
    'BORWB-G': ('CO617-00',
                'Przeciwciała przeciw Borelioza Borrelia burgdorferi (Choroba z Lyme) test potwierdzający (np. Western Blot lub immunoblot)'),
    'BOREL-G': (
    'CO618-00', 'Przeciwciała przeciw Borelioza Borrelia burgdorferi (Choroba z Lyme) (IgG / IgM), metodą Elisa'),
    'BORWB-M': ('CO617-00',
                'Przeciwciała przeciw Borelioza Borrelia burgdorferi (Choroba z Lyme) test potwierdzający (np. Western Blot lub immunoblot)'),
    'BOREL-M': (
    'CO618-00', 'Przeciwciała przeciw Borelioza Borrelia burgdorferi (Choroba z Lyme) (IgG / IgM), metodą Elisa'),
    'BRU-A': ('CO622-00', 'Przeciwciało przeciw Brucella (IgA / IgG / IgM)'),
    'BRU-G': ('CO622-00', 'Przeciwciało przeciw Brucella (IgA / IgG / IgM)'),
    'BRU-M': ('CO622-00', 'Przeciwciało przeciw Brucella (IgA / IgG / IgM)'),
    'DHEA': ('CO626-00', 'Dehydroepiandrosteron (DHEA)'),
    'DHEA-S': ('CO627-00', 'Dehydroepiandrosteron - siarczan (DHEA-S)'),
    'ZN': ('CO630-00', 'Cynk Krew'),
    'CHLT-G': ('CO631-00', 'Przeciwciało przeciw Chlamydia Trachomatis (IgG / IgM)'),
    'CHLT-M': ('CO631-00', 'Przeciwciało przeciw Chlamydia Trachomatis (IgG / IgM)'),
    'CHLT-M': ('CO632-00', 'Przeciwciała przeciw Chlamydia Trachomatis IgM'),
    'CMV-G': ('CO645-01', 'Przeciwciała przeciw cytomegalowirusowi (anty-CMV) (IgG / IgM)'),
    'CMV-M': ('CO645-01', 'Przeciwciała przeciw cytomegalowirusowi (anty-CMV) (IgG / IgM)'),
    'OB': ('CO652-00', 'Szybkość opadania krwinek (OB, odczyn Biernackiego), automatycznie'),
    'PB': ('CO655-00', 'Ołów Krew'),
    'EBV-EA': ('CO663-00', 'Wirus Epstein-Barr EBV (mononukleoza) antygen wczesny (EA) (IgG / IgM)'),
    'A-EBNAG': ('CO664-00', 'Wirus Epstein-Barr EBV (mononukleoza) antygen jądrowy (EBNA) (IgG / IgM)'),
    'ERYTPOE': ('CO668-00', 'Erytropoetyna'),
    'FRANCIS': ('CO668-01', 'Przeciwciało przeciw Francisella Tularensis ) (IgG / IgM)'),
    'E2': ('CO670-00', 'Estradiol E2'),
    'LAMBLIE': ('CO674-00', 'Giardia lamblia metoda ELISA z kału'),
    'HELI-G': ('CO677-00', 'Przeciwciała przeciw Helicobacter Pylori (IgG / IgA) we krwi'),
    'HELI-A': ('CO677-00', 'Przeciwciała przeciw Helicobacter Pylori (IgG / IgA) we krwi'),
    'ESTR-TP': ('CO677-01', 'Estriol E3'),
    'ESTRON': ('CO679-00', 'Estron E1'),
    'C-PEP': ('CO681-00', 'Peptyd C'),
    'LIPAZA': ('CO690-00', 'Lipaza'),
    'AHIV': ('CO701-01', 'Przeciwciała p/ludzkiemu wirusowi niedoboru odporności HIV 1'),
    'B-HCG': ('CO703-00', 'Gonadotropina kosmówkowa (HCG-beta/hCG)'),
    'AHBC-T': ('CO704-00', 'Zapalenie wątroby typu B, przeciwciała przeciw rdzeniowi wirusa (HBcAb), całkowite'),
    'AHBC-M': ('CO705-00', 'Zapalenie wątroby typu B, przeciwciała przeciw rdzeniowi wirusa (HBcAb), przeciwciała IgM'),
    'HBSAG': ('CO706-00', 'Zapalenie wątroby typu B, Antygen HBs (HbsAg/HBs), przeciwciała p/HBs (anty-HBs)'),
    'AHBS': ('CO706-00', 'Zapalenie wątroby typu B, Antygen HBs (HbsAg/HBs), przeciwciała p/HBs (anty-HBs)'),
    'AHAV': ('CO708-00', 'Zapalenie wątroby typu A, przeciwciało przeciw (HAAb) całkowite'),
    'AHAVM': ('CO709-00', 'Zapalenie wątroby typu A, przeciwciało przeciw (HAAb), przeciwciała IgM'),
    #    'P-GRZYB': ('CO7102-00', 'Posiew grzyby (pleśniowe lub drożdżaki), izolacja, wstępna identyfikacja wyizolowanych szczepów, inne preparaty (poza krwią)'),
    'BILTLU': ('CO715-00', 'Tłuszcze różnicowanie w kale ilościowo'),
    'HDL': ('CO718-00', 'Cholesterol HDL'),
    'LIPID': ('CO719-00', 'Lipidogram  (CHOL +HDL + LDL + TG)'),
    'FERR': ('CO728-00', 'Ferrytyna'),
    'APTT': ('CO730-00', 'Czas tromboplastynowy, czas kaolinowo-kefalinowy (APTT)'),
    'TT': ('CO730-02', 'Czas trombinowy TT'),
    'MG': ('CO735-00', 'Magnez we krwi'),
    'SWIN-G': ('CO735-01', 'Przeciwciało przeciw Świnka (IgG / IgM)'),
    'MG-M': ('CO735-11', 'Magnez w moczu'),
    'MYC-G': ('CO738-00', 'Przeciwciało przeciw Mykoplazma Mycoplazma Pneumoniae (IgG / IgM)'),
    'MYC-M': ('CO738-00', 'Przeciwciało przeciw Mykoplazma Mycoplazma Pneumoniae (IgG / IgM)'),
    'KWFOL': ('CO746-00', 'Foliowy kwas we krwi'),
    'AROTA': ('CO759-00', 'Przeciwciało rotawirus'),
    'RUB-G': ('CO762-00', 'Przeciwciało przeciw Różyczka (Rubella) (IgG / IgM)'),
    'RUB-M': ('CO762-00', 'Przeciwciało przeciw Różyczka (Rubella) (IgG / IgM)'),
    'ODRA': ('CO765-00', 'Przeciwciało przeciw Odra (IgG / IgM)'),
    'SAL-AGM': ('CO768-00', 'Przeciwciało przeciw Salmonella (IgA / IgG / IgM)'),
    'TOX-G': ('CO777-00', 'Przeciwciała przeciw Toksoplazmoza Toxoplazma Gondi IgG'),
    'TOX-M': ('CO778-00', 'Przeciwciała przeciw Toksoplazmoza Toxoplazma Gondi IgM'),
    'IGA': ('CO784-01', 'Immunoglobuliny IgA całkowite/nieswoiste'),
    'IGE': ('CO785-00', 'Immunoglobuliny IgE całkowite/nieswoiste'),
    'VZV-IGG': ('CO787-00', 'Przeciwciało Varicella-zoster (ospa wietrzna)'),
    'YER-A': ('CO793-00', 'Przeciwciało przeciw Yersinia (IgA / IgG / IgM)'),
    'YER-G': ('CO793-00', 'Przeciwciało przeciw Yersinia (IgA / IgG / IgM)'),
    'YER-M': ('CO793-00', 'Przeciwciało przeciw Yersinia (IgA / IgG / IgM)'),
    'ATG': ('CO800-00', 'Przeciwciała przeciwtarczycowe anty TG (przeciw tyreoglobulinie)'),
    'AHCV': ('CO803-00', 'Przeciwciała p/HCV (anty-HCV ) Zapalenie wątroby typu C'),
    'HCV-RB': ('CO804-00', 'Zapalenie wątroby typu C test potwierdzający (np. immunoblot)'),
    'CANCA': ('CO849-00', 'Przeciwciała p/cytoplazmie ANCA (pANCA, cANCA, aANCA)'),
    'PANCA': ('CO849-00', 'Przeciwciała p/cytoplazmie ANCA (pANCA, cANCA, aANCA)'),
    'MIOGL': ('CO874-00', 'Mioglobina'),
    'BTA': ('CO880-00', 'Odczyn Coombsa bezpośredni Test w kierunku antyglobulin ludzkich, bezpośredni'),
    'GRUPA': ('CO900-00', 'Grupa krwi i alloprzeciwciała odpornościowe (anty Rh i inne)'),
    'OSMOLAR': ('CO930-01', 'Osmolalność krwi'),
    'OSMO-M': ('CO935-00', 'Osmolalność moczu'),
    'GLUKO-M': ('CO945-00', 'Glukoza w moczu'),
    'GLU': ('CO947-00', 'Glukoza cukier na czczo we krwi'),
    'PTH': ('CO970-00', 'Parathormon (hormon przytarczyc)  ( PTH)'),
    'GGTP': ('CO977-00', 'Próby wątrobowe: Gammaglutarylotransferaza /glutamylotranspeptydaza (GGTP/GGT)'),
    'KAL-BO': ('CO999-00', 'Badanie ogólne kału'),
    'OSAD': ('CO000-01', 'Osad moczu'),
    'FSH': ('CO001-01', 'Gonadotropina FSH'),
    'MOCZ': ('CO002-02', 'Mocz - badanie ogólne'),
    'LH': ('CO002-03', 'Gonadotropina hormon luteinizujacy (LH)'),
    'HAPTOG': ('CO010-01', 'Haptoglobina ilościowo'),
    'CHOLIN': ('CO013-00', 'Cholinoesteraza, Acetylocholinoesteraza'),
    'MORF': ('CO027-00', 'Morfologia krwi obwodowej  z rozmazem automatycznym lub ręcznym'),
    'HBA1C': ('CO036-00', 'Hemoglobina glikozylowana (HbA1c)'),
    'ANA': ('CO038-00', 'Przeciwciała przeciwjądrowe (ANA)'),
    'ALB': ('CO040-01', 'Albumina we krwi'),
    'MIKRALB': ('CO043-00', 'Albumina w moczu, mikroalbumina'),
    'RETI': ('CO044-01', 'Retikulocyty'),
    'P-SS': ('CO045-02', 'Posiew kału Salmonella i Shigella'),
    'P-KAL-O': ('CO046-00',
                'Posiew kału w warunkach tlenowych, dodatkowe patogeny, izolacja i wstępna identyfikacja wyizolowanych szczepów, każda płytka'),
    'ACP': ('CO060-001', 'Fosfataza kwaśna całkowita (ACP)'),
    'ASO-IL': ('CO060-02', 'Antystreptolizyna ASO'),
    'ACP-S': ('CO066-00', 'Fosfataza kwaśna sterczowa (PAP)'),
    'ALP': ('CO075-01', 'Fosfataza zasadowa (alkaliczna) (ALP/ALK)'),
    'ALDOLAZ': ('CO085-01', 'Aldolaza'),
    'P-MOCZ': ('CO086-01', 'Posiew w kierunku bakterii mocz'),
    'ALDOST': ('CO088-00', 'Aldosteron'),
    'HOMOCYS': ('CO090-01', 'Homocysteina'),
    'P': ('CO100-00', 'Fosfor nieorganiczny (fosforany) we krwi'),
    'PR-DERM': ('CO101-00',
                'Posiew grzyby (pleśniowe lub drożdżaki), izolacja, wstępna identyfikacja wyizolowanych szczepów, skóra, włosy lub paznokcie'),
    'ANTYTRP': ('CO103-00', 'Alfa-1-antytrypsyna całkowita'),
    'AFP': ('CO105-00', 'Alfa-fetoproteina w surowicy (AFP)'),
    'P-M': ('CO105-01', 'Fosfor nieorganiczony (fosforany) w moczu'),
    'P-MYCU': ('CO109-00', 'Posiew wymaz antybiogram w kierunku mykoplazmy każdy preparat'),
    'CHLP-AT': ('CO110-00', 'Posiew wymaz antybiogram w kierunku Chlamydii każdy preparat'),
    'CHLT-AT': ('CO110-00', 'Posiew wymaz antybiogram w kierunku Chlamydii każdy preparat'),
    'TBC-PBK': ('CO116-00',
                'Posiew antybiogram w kierunku gruźlicy lub innych bakterii kwasoopornych (np. TB AFB mycobacteria) każdy preparat izolacja i  wstępna identyfikacja wyizolowanych szczepów'),
    'PORF-IL': ('CO119-00', 'Porfiryny w moczu'),
    'K': ('CO132-00', 'Potas we krwi'),
    'K-M': ('CO133-00', 'Potas w moczu'),
    'CRP-IL': ('CO140-01', 'Białko C-reaktywne (CRP)'),
    'CRP-HS': ('CO141-01', 'Białko C-reaktywne o wysokiej czułości (hsCRP)'),
    'PRG': ('CO144-00', 'Progesteron'),
    'PRL': ('CO146-01', 'Prolaktyna (PRL)'),
    'AMYL-M': ('CO150-01', 'Amylaza w moczu'),
    'MVADZM': ('CO150-02', 'Homowanilinowy kwas (HVA)'),
    'AMYL': ('CO150-12', 'Amylaza we krwi'),
    'TPSA': ('CO153-00', 'Antygen sterczowy PSA całkowity'),
    'FPSA': ('CO154-00', 'Antygen sterczowy PSA wolny'),
    'TP': ('CO155-00', 'Białko całkowite we krwi'),
    'KARBAM': ('CO156-01', 'Karbamazepina (całkowita)'),
    'BIALK-M': ('CO156-02', 'Białko w moczu'),
    'ANDRO': ('CO157-00', 'Androstendion'),
    'CYKLOSP': ('CO158-00', 'Cyklosporyna'),
    'C3/C4': ('CO161-00', 'Dopełniacz  każdy składnik'),
    'DIGOKS': ('CO162-00', 'Digoksyna'),
    'ANGIO2': ('CO163-00', 'Angiotensyna II, Poziom enzymu konwertującego angiotensyny'),
    'WALPRO': ('CO164-00', 'Kwas walproinowy'),
    'PROTEIN': ('CO165-00', 'Elektroforeza białek (proteinogram)'),
    'APO-A1': ('CO172-01', 'Apolipoproteina (Al, B)'),
    'OWSIKI': ('CO172-02', 'Badanie w kierunku owsicy (np. preparat na taśmie celofanowej)'),
    'KA-PAS': ('CO177-00', 'Badanie kału w kierunku jaj pasożytów'),
    'CZ-II': ('CO210-01', 'Krzepnięcie, czynnik II, protrombina oznaczenie specyficzne'),
    '17-OHPG': ('CO215-06', '17-OH progesteron'),
    'B2-MIK': ('CO232-00', 'Beta-2 mikroglobulina'),
    'KWZOLC': ('CO239-00', 'Kwasy żółciowe  całkowite'),
    'RENINA': ('CO244-00', 'Renina Aktywność reninowa osocza (ARO)'),
    'BIL-T': ('CO247-00', 'Bilirubina całkowita'),
    'BIL-D': ('CO248-00', 'Bilirubina bezpośrednia'),
    'SEROT': ('CO260-00', 'Serotonina'),
    'SHBG': ('CO270-00', 'Globulina wiążąca hormony płciowe  (SHBG)'),
    'KREW-UT': ('CO270-01', 'Badanie kału na Krew utajoną'),
    'NA': ('CO295-00', 'Sód we krwi'),
    'ATROM-3': ('CO300-00', 'Antytrombina III'),
    'NA-M': ('CO300-01', 'Sód w moczu'),
    'CA15-3': ('CO300-02', 'Antygen CA 15-3 ( 15-3)'),
    'CA19-9': ('CO301-00', 'CA19-9'),
    'CA125': ('CO304-00', 'Antygen CA 125 (CA125)'),
    'WIT-DTO': ('CO306-00', 'Witamina D-25(OH)D'),
    'WIT-D3': ('CO307-00', 'Witamina D-1,25(OH)2D'),
    'KALCYT': ('CO308-00', 'Kalcytonina CT'),
    'CA-M': ('CO310-00', 'Wapń całkowity w moczu'),
    'CA': ('CO310-01', 'Wapń całkowity w surowicy'),
    'CLOS-AB': ('CO324-00', 'Clostridium difficile (toksyna/toksyny)'),
    'CA-DM': ('CO340-00', 'Wapń w moczu dobowym'),
    'HBSAG': ('CO340-01', 'zapalenie wątroby typu B Antygen HBs (HbsAg/HBs)'),
    'LDL-WYL': ('CO720-00', 'Cholesterol LDL'),
    'P-BAL': ('CO070-01', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach tlenowych'),
    'P-BALM': ('CO070-01', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach tlenowych'),
    'P-CAMP': ('CO070-01', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach tlenowych'),
    'P-DDO': ('CO070-01', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach tlenowych'),
    'P-DDOM': ('CO070-01', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach tlenowych'),
    'P-DERMA': ('CO070-01', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach tlenowych'),
    'P-DMP': ('CO070-01', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach tlenowych'),
    'P-DMPP': ('CO070-01', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach tlenowych'),
    'P-DMPS': ('CO070-01', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach tlenowych'),
    'P-ECOLI': ('CO070-01', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach tlenowych'),
    'P-EHEC': ('CO070-01', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach tlenowych'),
    'P-GDO': ('CO070-01', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach tlenowych'),
    'P-GDOM': ('CO070-01', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach tlenowych'),
    'P-GDON': ('CO070-01', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach tlenowych'),
    'P-GDOR': ('CO070-01', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach tlenowych'),
    'P-GRON': ('CO070-01', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach tlenowych'),
    'P-GRZKR': ('CO7102-00',
                'Posiew grzyby (pleśniowe lub drożdżaki), izolacja, wstępna identyfikacja wyizolowanych szczepów, inne preparaty (poza krwią)'),
    'P-GRZPR': ('CO7102-00',
                'Posiew grzyby (pleśniowe lub drożdżaki), izolacja, wstępna identyfikacja wyizolowanych szczepów, inne preparaty (poza krwią)'),
    'P-GRZYB': ('CO7102-00',
                'Posiew grzyby (pleśniowe lub drożdżaki), izolacja, wstępna identyfikacja wyizolowanych szczepów, inne preparaty (poza krwią)'),
    'P-GRZYD': ('CO7102-00',
                'Posiew grzyby (pleśniowe lub drożdżaki), izolacja, wstępna identyfikacja wyizolowanych szczepów, inne preparaty (poza krwią)'),
    'P-GRZYI': ('CO7102-00',
                'Posiew grzyby (pleśniowe lub drożdżaki), izolacja, wstępna identyfikacja wyizolowanych szczepów, inne preparaty (poza krwią)'),
    'P-GRZYJ': ('CO7102-00',
                'Posiew grzyby (pleśniowe lub drożdżaki), izolacja, wstępna identyfikacja wyizolowanych szczepów, inne preparaty (poza krwią)'),
    'P-GRZYK': ('CO7102-00',
                'Posiew grzyby (pleśniowe lub drożdżaki), izolacja, wstępna identyfikacja wyizolowanych szczepów, inne preparaty (poza krwią)'),
    'P-GRZYN': ('CO7102-00',
                'Posiew grzyby (pleśniowe lub drożdżaki), izolacja, wstępna identyfikacja wyizolowanych szczepów, inne preparaty (poza krwią)'),
    'P-GRZYP': ('CO7102-00',
                'Posiew grzyby (pleśniowe lub drożdżaki), izolacja, wstępna identyfikacja wyizolowanych szczepów, inne preparaty (poza krwią)'),
    'P-GRZYU': ('CO7102-00',
                'Posiew grzyby (pleśniowe lub drożdżaki), izolacja, wstępna identyfikacja wyizolowanych szczepów, inne preparaty (poza krwią)'),
    'P-JU': ('CO070-01', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach tlenowych'),
    'PB-CEWN': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-CLOS': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-DDO': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-DMP': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-GDO': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-JU': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-KAL': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-KREP': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-KREW': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-NAST': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-NOS': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-OGO': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-OKO': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-ORTO': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-PJC': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-PMR': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-POS': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-PRKR': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-RANA': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-ROPA': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-SKOR': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-STOM': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-UCHO': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-UCHR': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-WYDZ': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-ZMS': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-ZMST': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
    'PB-ZMW': ('CO073-00', 'Wymaz posiew i antybiogram  z różnych materiałów w warunkach beztlenowych'),
}


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    validate_date_range(params['dataod'], params['datado'], 90)
    wewn = []
    rep = ReporterDatasource()
    for row in rep.dict_select("""select symbol, nazwa from laboratoria where aktywne and wewnetrzne"""):
        # if row['symbol'] not in wewn:
        #     wewn.append(row['symbol'])
        if next((i for i in wewn if i['symbol'] == row['symbol']), None) == None:
            wewn.append({'nazwa': row['nazwa'], 'symbol': row['symbol']})
    zewn = []
    for row in rep.dict_select(
            """select symbol, nazwa from laboratoria where aktywne and zewnetrzne and adres is not null and adres != ''"""):
        if next((i for i in zewn if i['symbol'] == row['symbol']), None) == None:
            zewn.append({'nazwa': row['nazwa'], 'symbol': row['symbol']})
        # if row['symbol'] not in zewn:
        #     zewn.append(row['symbol'])

    for lab in wewn:
        task = {
            'type': 'snr',
            'priority': 1,
            'target': lab['symbol'],
            'params': {
                'dataod': params['dataod'],
                'datado': params['datado'],
                'lab_nazwa': lab['nazwa']
            },
            'function': 'raport_snr'
        }
        report.create_task(task)
    for lab in zewn:
        task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab['symbol'][:7],
            'params': {
                'dataod': params['dataod'],
                'datado': params['datado'],
                'lab_nazwa': lab['nazwa']
            },
            'function': 'raport_lab'
        }
        report.create_task(task)
    report.save()
    return report


# hs: lekarzenumer, lekarzeimiona, lekarzenazwisko; pacjencidataurodzenia

def raport_snr(task_params):
    lab = task_params['target']
    params = task_params['params']
    sql = """
    select
		w.datarejestracji as "DATA",
		w.hs->'numer' as "NR",
		w.hs->'pacjencinazwisko' as "PACN",
		w.hs->'pacjenciimiona' as "PACI",
		w.hs->'pacjencipesel' as "PACP",
		w.hs->'pacjencidataurodzenia' as "PACDU",
		w.hs->'lekarzeimiona' as "LEK0",
		w.hs->'lekarzenazwisko' as "LEK1",
		w.hs->'lekarzenumer' as "LEK2",
		w.badanie as "BS",
		w.nazwa as "BN",
		w.nettodlaplatnika as "CENA"
		
	from Wykonania W
		left outer join zleceniodawcy z on W.Zleceniodawca = Z.ID
		left outer join Platnicy P on W.platnik = P.ID
		left outer join pozycjekatalogow pk on pk.symbol=w.badanie and pk.katalog = 'BADANIA'
	where
		w.datarozliczeniowa between
		and not W.bezPlatne and not w.jestpakietem and w.hs->'platnikzlecenia' like '%COMP%' and (pk.hs->'grupa') is distinct from 'TECHNIC' and p.nazwa like '%Compensa %' and (pk.hs->'grupa') is distinct from 'ANTYB' and (pk.hs->'grupa') is distinct from 'IDENT' 
	order by
		w.datarejestracji ,w.hs->'numer', w.badanie
    """
    sql = sql.replace('w.datarozliczeniowa between',
                      """w.datarozliczeniowa between '%s' and '%s' and w.laboratorium = '%s'""" % (
                      params['dataod'], params['datado'], lab))
    res = []
    with get_snr_connection() as snr:
        wyniki = snr.dict_select(sql)
        for row in wyniki:
            (proc_id, proc_nazwa) = BADANIA.get(row['BS'], ('', ''))
            res.append([
                lab,
                prepare_for_json(row['DATA']),
                row['NR'],
                row['PACN'],
                row['PACI'],
                row['PACP'],
                row['PACDU'],
                ' '.join([row['LEK%d' % i] for i in range(3) if row['LEK%d' % i] is not None]),
                row['BS'],
                row['BN'],
                proc_id,
                proc_nazwa,
                prepare_for_json(row['CENA']),
                params['lab_nazwa']
            ])
    return res


def raport_lab(task_params):
    lab = task_params['target'][:7]
    params = task_params['params']
    with get_centrum_connection(lab) as conn:
        sql = """
            select
                Z.DataRejestracji as DATA,
                Z.Numer as NR,
                PAC.Nazwisko      as PACN,
                PAC.Imiona        as PACI,
                PAC.PESEL         as PACP,
                PAC.DataUrodzenia as PACDU,
                LEK.Imiona as LEK0,
                LEK.Nazwisko as LEK1,
                LEK.Numer as LEK2,
                BAD.Symbol as BS,
                BAD.Nazwa  as BN,
                W.Cena   as CENA
            from Wykonania W
                left outer join Zlecenia Z on W.Zlecenie = Z.ID
                left outer join Oddzialy PP on Z.Oddzial = PP.ID
                left outer join Platnicy PL on W.Platnik = PL.ID
                left outer join Pacjenci PAC on W.Pacjent = PAC.ID
                left outer join Lekarze LEK on LEK.ID=Z.Lekarz
                left outer join Badania BAD on W.Badanie = BAD.ID
                left outer join grupybadan GBAD on GBAD.id=BAD.Grupa
                left outer join Materialy MAT on W.Material = MAT.ID
            where
                W.Rozliczone between ? and ? and
                W.Platne = 1 and W.Anulowane is Null and PL.Symbol like '%COMP%' and GBAD.Symbol <> 'TECHNIC' and pl.nazwa like '%Compensa %' and (bad.rodzaj not in ('2', '3') or bad.rodzaj is null)
            order by
                Z.Datarejestracji,Z.Numer, BAD.Symbol
        """
        rows = conn.raport_slownikowy(sql, [params['dataod'], params['datado']])
    res = []
    for row in rows:
        (proc_id, proc_nazwa) = BADANIA.get((row['bs'] or '').strip(), ('', ''))
        res.append([
            lab,
            prepare_for_json(row['data']),
            row['nr'],
            row['pacn'],
            row['paci'],
            row['pacp'],
            row['pacdu'],
            ' '.join([row['lek%d' % i] for i in range(3) if row['lek%d' % i] is not None]),
            (row['bs'] or '').strip(),
            row['bn'],
            proc_id,
            proc_nazwa,
            prepare_for_json(row['cena']),
            params['lab_nazwa']
        ])
    print(prepare_for_json(res))
    return prepare_for_json(res)


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': ['xlsx']
    }
    wiersze = []
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            for wiersz in result:
                wiersze.append([
                    str(wiersz[0]) + "_" + str(wiersz[1]) + "_" + str(wiersz[2]),
                    wiersz[4],
                    wiersz[3],
                    wiersz[5],
                    wiersz[6],
                    wiersz[7],
                    wiersz[8],
                    wiersz[9],
                    wiersz[10],
                    wiersz[11],
                    wiersz[12],
                    '',
                    '',
                    '',
                    wiersz[1],
                    wiersz[13]])
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])
    res['results'].append({
        'type': 'table',
        'header': 'ID usługi;Imię Pacjenta;Nazwisko Pacjenta;PESEL Pacjenta;Data ur. pacjenta;Lekarz zlecający;Symbol badania;Nazwa badania;Kod procedury;Nazwa procedury;Cena;Opłata COMPENSA;Rzpoznanie medyczne Kod ICD-10;Opłata Klienta;Data Wizyty;Miejsce wizyty'.split(
            ';'),
        'data': wiersze,
    })
    res['progress'] = task_group.progress
    return res
