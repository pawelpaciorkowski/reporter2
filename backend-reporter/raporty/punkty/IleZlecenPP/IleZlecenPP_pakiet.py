from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection
from datasources.snr import SNR
from datasources.hbz import HBZ
from api.common import get_db
from decimal import Decimal
MENU_ENTRY = 'Ile pakietów dla płatnika'

REQUIRE_ROLE = ['C-FIN', 'C-CS', 'PP-S', 'C-PP']
# REQUIRE_ROLE = 'ADMIN'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport ile pakietów gotówkowych zarejestrowano przez iCentrum w punkcie pobrań'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa', default='-7D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
))

SQL = """select
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

def start_report(params):
    laboratoria = []
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)
    for lab in params['laboratoria']:
        lab_task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'zbierz_lab',
        }
        report.create_task(lab_task)
    report.save()
    return report

def zbierz_lab(task_params):
    params = task_params['params']
    oddnia = params['dataod']
    dodnia = params['datado']
    res = []
    sql = SQL
    sql_params = [oddnia, dodnia]
    with get_centrum_connection(task_params['target'], fresh=True) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
        for row in rows:
            res.append([task_params['target']] + row)
    return res

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
    zestaw = []

    kanaly = []
    dni = []

    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            for row in result:
                wiersze.append(prepare_for_json(row))            
                if prepare_for_json(row[1]) not in dni:
                    dni.append(prepare_for_json(row[1]))
                if next((i for i in kanaly if i['symbol'] == prepare_for_json(row[2]) and i['nazwa'] == prepare_for_json(row[3])), None) == None:
                    kanaly.append({'lab':prepare_for_json(row[0]),'symbol':prepare_for_json(row[2]),'nazwa':prepare_for_json(row[3])})

        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])

    for kanal in kanaly:
        wiersz = []
        wiersz.append(kanal['lab'])
        wiersz.append(kanal['symbol'])
        wiersz.append(kanal['nazwa'])
        for dzien in dni:
            ilosc = ''
            wartosc = ''
            for i in wiersze:
                if i[1] == dzien and i[2] == kanal['symbol']:
                    ilosc = i[4]
                    wartosc = i[5]
            wiersz.append(ilosc)
            wiersz.append(wartosc)
        zestaw.append(wiersz)

    iloscPakietow = 0
    wartoscPakietow = 0
    for wiersz in wiersze:
        iloscPakietow = iloscPakietow + wiersz[4]
        if wiersz[5] != None:
            wartoscPakietow = wartoscPakietow + float(wiersz[5])

    headerFull = []
    headerlist = []
    header = []
    header.append({'title':'Laboratorium', 'rowspan' : 2,'fontstyle': 'b'})
    header.append({'title':'Symbol', 'rowspan' : 2,'fontstyle': 'b'})
    header.append({'title':'Nazwa punktu pobrań', 'rowspan' : 2,'fontstyle': 'b'})
    for dzien in dni:
        header.append({'title':dzien, 'rowspan' : 1, 'colspan' : 2,'fontstyle': 'b'})
    headerFull.append(header)
    for dzien in dni:
        headerlist.append({'title':'Ilość'})
        headerlist.append({'title':'Wartość'})
    headerFull.append(headerlist)

    res['progress'] = task_group.progress
    res['results'].append(
            {
                'type': 'table',
                'title': 'Wykaz ile pakietów gotówkowych zarejestrowano przez iCentrum w punkcie pobrań od %s do %s z podziałem na poszczególne dni. Łącznie sprzedano %s pakietów na kwotę %s' % (params['params']['dataod'], params['params']['datado'], str(iloscPakietow) ,str(format(wartoscPakietow,'7.2f'))),
                'header': headerFull,
                'data': zestaw
            })
    return res