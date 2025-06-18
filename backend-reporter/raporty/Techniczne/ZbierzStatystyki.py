from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection
from datasources.postgres import PostgresDatasource
import time
import json

class StatystykiDB(PostgresDatasource):
    def __init__(self):
        PostgresDatasource.__init__(self, 'dbname=statystyki user=postgres host=127.0.0.1 port=5433', True)


MENU_ENTRY = 'Zbierz statystyki rejestracji'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='data', title='Data', default='T')
))

REQUIRE_ROLE = 'ADMIN'

SQL = """
select
'$SYSTEM$' as system,
w.id as wykonanie, w.ZLECENIE, coalesce(w.KODKRESKOWY, zl.KODKRESKOWY) as kodkreskowy, 
w.GODZINAREJESTRACJI, w.GODZINA as pobranie, w.DYSTRYBUCJA, w.WYKONANE, w.ZATWIERDZONE,w.PODPISANE,
tz.symbol as typzlecenia,
b.symbol as badanie, m.symbol as material, pr.symbol as pracownia, ap.SYMBOL as aparat,bl.SYMBOL as blad,
pl.symbol as platnik, o.symbol as zleceniodawca, kan.symbol as kanal,
-- list(wz.SYSTEM) as zewnetrzne
null as zewnetrzne

from wykonania w
left join badania b on b.id=w.BADANIE
left join materialy m on m.id=w.MATERIAL
left join pracownie pr on pr.id=w.PRACOWNIA
left join aparaty ap on ap.id=w.APARAT
left join zlecenia zl on zl.id=w.ZLECENIE
left join TYPYZLECEN tz on tz.id=zl.TYPZLECENIA
left join PLATNICY pl on pl.id=zl.PLATNIK
left join ODDZIALY o on o.id=zl.ODDZIAL
left join BLEDYWYKONANIA bl on bl.id=w.BLADWYKONANIA
left join PRACOWNICY prac on prac.id=zl.PRACOWNIKODREJESTRACJI
left join KANALY kan on kan.id=prac.KANALINTERNETOWY
-- left join WYKONANIAZEWNETRZNE wz on wz.WYKONANIE=w.id

where w.ZATWIERDZONE between ? and ?

-- group by 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    stat_db = StatystykiDB()
    sql = """select distinct system, zatwierdzone::date as data from wykonania"""
    daty = []
    laby = []
    daty_laby = []
    for row in stat_db.dict_select(sql):
        lab = row['system']
        data = str(row['data'])
        data_lab = data+lab
        if lab not in laby:
            laby.append(lab)
        if data not in daty:
            daty.append(data)
        daty_laby.append(data_lab)
    licznik = 0
    report = TaskGroup(__PLUGIN__, params)
    for data in daty:
        for lab in laby:
            if lab == 'LUBLIN': # in ['LUBLIN', 'LDSK', 'NOWEMIA', 'CZERNIA', 'BELZYCE', 'ZELAZNA', 'LUBLINC']:
                data_lab = data+lab
                if data_lab not in daty_laby:
                    print('DODAJEMY', data, lab)
                    licznik += 1
                    task = {
                        'type': 'centrum',
                        'priority': 1,
                        'target': lab,
                        'params': {'data': data},
                        'function': 'zbierz',
                        'timeout': 1200,
                    }
                    report.create_task(task)
    print("licznik", licznik)
    # if len(params['laboratoria']) == 0:
    #     raise ValidationError("Nie wybrano żadnego laboratorium")
    # for lab in params['laboratoria']:
    #     task = {
    #         'type': 'centrum',
    #         'priority': 1,
    #         'target': lab,
    #         'params': params,
    #         'function': 'zbierz',
    #         'timeout': 1200,
    #     }
    #     report.create_task(task)
    report.save()
    return report


def zbierz(task_params):
    params = task_params['params']
    target = task_params['target']
    sql = SQL.replace('$SYSTEM$', target)
    data_od = params['data'] + ' 00:00:00.000'
    data_do = params['data'] + ' 23:59:59.999'
    t1 = time.time()
    with get_centrum_connection(target) as conn:
        dane = conn.raport_slownikowy(sql, [data_od, data_do])
    t2 = time.time()
    t = int((t2-t1) * 1000)
    print('Dane zebrane')
    stat_db = StatystykiDB()
    stat_db.insert('log_czasy', {
        'raport': __PLUGIN__,
        'target': target,
        'params': json.dumps(prepare_for_json(params)),
        'duration': t
    })
    stat_db.multi_insert('wykonania', dane)
    print('Dane wrzucone')
    stat_db.commit()
    return {
        'type': 'info',
        'text': '%s %s: %d wykonań' % (target, params['data'], len(dane))
    }