from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task

MENU_ENTRY = 'Weryfikacja faktur podwykonawcy'

REQUIRE_ROLE = ['C-FIN', 'C-ROZL', 'C-CS-OF']

SQL = """
    select
        z.datarejestracji as DATA,
        z.system,
        z.numer as NUMER,
        z.kodkreskowy,
        w.kodkreskowy as kodkreskowy_wykonania,
        P.Symbol as PLATNIK,
        (pac.Nazwisko || ' ' || pac.Imiona) as PACJENT,
        pac.pesel as PESEL,
        pac.dataurodzenia,
        (cast(list(trim(b.symbol) || ' (roz:'|| w.ROZLICZONE || ')' , ', ') as varchar(2000))) as BADANIA
        from Wykonania W
            left outer join zlecenia Z on z.id=w.zlecenie
            left outer join pacjenci pac on pac.id=z.pacjent
            left outer join Platnicy P on W.platnik = P.ID
            left outer join Badania B on W.Badanie = B.ID
            left outer join GrupyBadan GB on B.Grupa = GB.ID
        where
        W.datarejestracji between ? and ? 
        and W.Anulowane is null	and W.Platne = 1 and w.zatwierdzone is not null and w.pracownia = ?
        group by z.datarejestracji, z.system, z.numer, z.kodkreskowy, w.kodkreskowy, p.symbol, pac.Nazwisko, pac.Imiona, pac.pesel, pac.dataurodzenia
        order by z.datarejestracji, z.numer
"""

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="Wykaz pacjentów, których badania były wykonane przed podwykonawców zewnętrznych"),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
    PracowniaSelector(field='pracownia', title='Pracownia', wariant='wysylkowe'),
    LabSelector(multiselect=True, selectall=True, field='laboratoria', title='Laboratoria'),
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)
    for lab in params['laboratoria']:
        task = {
            'type': 'centrum',
            'priority': 1,
            'target': lab,
            'params': params,
            'function': 'raport_pojedynczy'
        }
        report.create_task(task)
    report.save()
    return report


def raport_pojedynczy(task_params):
    params = task_params['params']
    oddnia = params['dataod']
    dodnia = params['datado']
    pracownia = params['pracownia']
    pracownia_id = None
    with get_centrum_connection(task_params['target']) as conn:
        for row in conn.raport_slownikowy("select id from pracownie where symbol=? and del=0", [pracownia]):
            pracownia_id = row['id']
    res = []
    if pracownia_id is not None:
        with get_centrum_connection(task_params['target']) as conn:
            for row in conn.raport_slownikowy(SQL, [oddnia, dodnia, pracownia_id]):
                res.append(row)
    else:
        return {
            'type': 'error',
            'text': 'Lab %s - nie znaleziono pracowni %s' % (task_params['target'], pracownia)
        }
    # if len(res) == 0:
    #     return {
    #         'type': 'error',
    #         'text': 'Lab %s - nic nie znaleziono' % (task_params['target'])
    #     }
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
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            if isinstance(result, list):
                for row in result:
                    wiersze.append([
                        params['target'], row['system'], row['platnik'], row['data'], row['numer'],
                        row['kodkreskowy'], row['kodkreskowy_wykonania'],
                        row['pacjent'], row['pesel'], row['dataurodzenia'], row['badania']
                    ])
            else:
                res['results'].append(result)
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])
    res['progress'] = task_group.progress
    res['results'].append({
        'type': 'table',
        'header': 'Laboratorium,System,Płatnik,Data rej.,Numer,Kod zlecenia,Kod próbki,Pacjent,Pesel,Data ur.,Badania'.split(','),
        'data': prepare_for_json(wiersze)
    })
    return res


"""
Wykaz pacjentów, których badania były wykonane przed podwykonawców zewnętrznych
uzyskany 9-12-2019 12:49:48
Parametry raportu
Wykaz pacjentów, których badania były wykonane przed podwykonawców zewnętrznych
Data początkowa rejestracji: 	01-09-2019
Data końcowa rejestracji: 	03-09-2019
Pracownia: 	Wysyłka do Sanepidu (Pozanań)
Laboratoria:  	CZERNIA 
Zewnętrzne: 
Laboratorium	Płatnik	Data Rej.	Numer	Pacjent	Pesel	Badania


Laboratorium	Płatnik	Data Rej.	Numer	Pacjent	Pesel	Badania
Ostrołęka - Nowy		2019-09-02	74	Rxxxxx Magdalena	95xxxxxx09	DHEA-S (roz:2019-09-02
Ostrołęka - Nowy	OZPROME	2019-09-02	75	Oxxxxx Andrzej	59xzxxxxx97	FPSA (roz:2019-09-03), TPSA (roz:2019-09-03

"""
