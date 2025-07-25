import datetime
from dataclasses import dataclass, field
from typing import List, Dict

from dialog import Dialog, VBox, LabSelector, PracowniaSelector, InfoText, DateInput, ValidationError, Switch
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup

MENU_ENTRY = 'Weryfikacja faktur podwykonawcy2'

REQUIRE_ROLE = ['C-FIN', 'C-ROZL', 'C-CS-OF']

CONDITIONS = """
and W.Anulowane is null	and W.Platne = 1 and w.zatwierdzone is not null
"""
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
        trim(b.symbol) as badanie,
        w.rozliczone as data_rozliczenia,
        b2.symbol || ':' ||  b2.nazwa as BLEDY,
        p2.symbol || ':' ||  p2.nazwa as ANULOWANIE
        from Wykonania W
            left outer join zlecenia Z on z.id=w.zlecenie
            left outer join pacjenci pac on pac.id=z.pacjent
            left outer join Platnicy P on W.platnik = P.ID
            left outer join Badania B on W.Badanie = B.ID
            left outer join GrupyBadan GB on B.Grupa = GB.ID
            left outer join bledywykonania b2 on b2.id = w.bladwykonania 
            left join powodyanulowania p2 on p2.id = w.powodanulowania 
        where
        W.datarejestracji between ? and ?
        %s
        and w.pracownia = ?
        order by z.datarejestracji, z.numer
"""


@dataclass
class OrderDetail:
    pesel: str
    birth_date: str
    system: str
    patient: str
    order_barcode: str
    payer: str


@dataclass
class Common:
    order_number: int
    order_date: str
    settlement_date: str
    test_barcode: str


@dataclass
class TestDetails:
    order_details: OrderDetail
    common: Common
    examination: str
    error: str
    cancel: str

    def is_error(self):
        return self.error or self.cancel


@dataclass
class Order:
    order_details: OrderDetail
    tests: List[TestDetails] = field(default_factory=list)


@dataclass
class ReportRow:
    lab: str
    order: OrderDetail
    test: TestDetails


LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="Wykaz pacjentów, których badania były wykonane przed podwykonawców zewnętrznych"),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
    PracowniaSelector(field='pracownia', title='Pracownia', wariant='wysylkowe'),
    LabSelector(multiselect=True, selectall=True, field='laboratoria', title='Laboratoria'),
    Switch(field='wszystkie_badania', title='Wszystkie badania', default=False), ))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)
    for lab in params['laboratoria']:
        task = {'type': 'centrum', 'priority': 1, 'target': lab, 'params': params, 'function': 'raport_pojedynczy'}
        report.create_task(task)
    report.save()
    return report


def prepare_sql(wszystkie_badania: bool) -> str:
    if wszystkie_badania:
        return SQL % ''
    else:
        return SQL % CONDITIONS


def raport_pojedynczy(task_params):
    params = task_params['params']
    oddnia = params['dataod']
    dodnia = params['datado']
    pracownia = params['pracownia']
    wszystkie_badania = params['wszystkie_badania']
    pracownia_id = None

    sql = prepare_sql(wszystkie_badania)

    with get_centrum_connection(task_params['target']) as conn:
        for row in conn.raport_slownikowy("select id from pracownie where symbol=? and del=0", [pracownia]):
            pracownia_id = row['id']
    res = []
    if pracownia_id is not None:
        with get_centrum_connection(task_params['target']) as conn:
            for row in conn.raport_slownikowy(sql, [oddnia, dodnia, pracownia_id]):
                res.append(row)
    else:
        return {'type': 'error', 'text': 'Lab %s - nie znaleziono pracowni %s' % (task_params['target'], pracownia)}
    # if len(res) == 0:
    #     return {
    #         'type': 'error',
    #         'text': 'Lab %s - nic nie znaleziono' % (task_params['target'])
    #     }
    return res


def prepare_data(result):
    dane = {}
    for row in result:
        order_details = OrderDetail(pesel=row['pesel'], birth_date=row['dataurodzenia'], system=row['system'],
                                    patient=row['pacjent'], order_barcode=row['kodkreskowy'], payer=row['platnik'])
        if order_details.order_barcode not in dane:
            dane[order_details.order_barcode] = Order(order_details=order_details)

        common = Common(order_number=row['numer'], order_date=row['data'], test_barcode=row['kodkreskowy_wykonania'],
                        settlement_date=row['data_rozliczenia'])
        test_details = TestDetails(order_details=order_details, common=common,
                                   examination=row['badanie'].strip() + f"(roz:{common.settlement_date if common.settlement_date else ''}" + ')',
                                   error=row['bledy'] if row['bledy'] else '',
                                   cancel=row['anulowanie'] if row['anulowanie'] else '')
        dane[order_details.order_barcode].tests.append(test_details)
    return dane


def serialize(data: List[TestDetails], lab) -> list:
    result = []
    for test in data:
        r = ReportRow(lab=lab, order=test.order_details, test=test)
        result.append(r)
    a = [[r.lab, r.order.system, r.order.payer, str(r.test.common.order_date), r.test.common.order_number, \
             r.order.order_barcode, r.test.common.test_barcode, r.order.patient, r.order.pesel, str(r.test.order_details.birth_date), \
           r.test.examination, r.test.cancel , r.test.error] for r in result]
    return a


def group_data(dane: Dict[str, Order]):
    rows = []
    for order in dane:
        for test in dane[order].tests:
            if order == '6214376420':
                print(1)
            t = test
            dodane_albo_jest = 0
            if not rows:
                rows.append(t)
                continue
            for r in rows:

                # już jest
                if t == r:
                    dodane_albo_jest = 1
                    print(f'już jest {r}')
                    break
                # to samo zlecenie inne badania - dodanie
                if t.order_details.order_barcode==r.order_details.order_barcode and t.common == r.common:
                    r.examination += f', {t.examination}'
                    r.error += t.error
                    r.cancel += t.cancel
                    dodane_albo_jest = 1
                    print(f'to samo zleceie inne badanie {r}')
                    break

                # to samo zlecenie np poprawki błędów
                if t.order_details.order_barcode == r.order_details.order_barcode and t.examination == r.examination:
                    dodane_albo_jest = 1
                    print(f'błąd pominiecie {r}')
                    if not t.is_error() and t.common.order_date > r.common.order_date:
                        rows.remove(r)
                        rows.append(t)
            if not dodane_albo_jest:
                rows.append(t)

    return rows


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {'errors': [], 'results': [], 'actions': ['xlsx']}
    wiersze = []
    for job_id, params, status, result in task_group.get_tasks_results():
        lab = params['target']
        if status == 'finished' and result is not None:
            if isinstance(result, list):
                data = prepare_data(result)

                # wiersze.append([  #     params['target'], row['system'], row['platnik'], row['data'], row['numer'],
                #     row['kodkreskowy'], row['kodkreskowy_wykonania'],
                #     row['pacjent'], row['pesel'], row['dataurodzenia'], row['badania'], row['anulowanie'], row['bledy']
                # ])
            else:
                res['results'].append(result)
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])
        d = group_data(data)
        # d = group_data({d: data[d] for d in data if d == '6196569360'})
        wiersze += serialize(d, lab)

    res['progress'] = task_group.progress
    res['results'].append({'type': 'table',
                           'header': 'Laboratorium,System,Płatnik,Data rej.,Numer,Kod zlecenia,Kod próbki,Pacjent,Pesel,Data ur.,Badania, Anulowania, Błendy'.split(
                               ','), 'data': prepare_for_json(wiersze)})
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
test_data1 = {'6222161540': Order(
    order_details=OrderDetail(pesel='00222809209', birth_date=datetime.date(2000, 2, 28), system='ZAWODZI',
                              patient='Piłka Natalia', order_barcode='6222161540', payer='F-SKIN '),
    tests=[
        TestDetails(
            order_details=OrderDetail(pesel='00222809209', birth_date=datetime.date(2000, 2, 28), system='ZAWODZI',
                                      patient='Piłka Natalia', order_barcode='6222161540', payer='F-SKIN '),
            common=Common(order_number=2543, order_date=datetime.date(2025, 4, 5),
                          settlement_date=datetime.date(2025, 4, 9), test_barcode='62221615431'), examination='F-24',
            error='', cancel=''),
        TestDetails(
            order_details=OrderDetail(pesel='00222809209', birth_date=datetime.date(2000, 2, 28), system='ZAWODZI',
                                      patient='Piłka Natalia', order_barcode='6222161540', payer='F-SKIN '),
            common=Common(order_number=2106, order_date=datetime.date(2025, 4, 7), settlement_date=None, test_barcode=None),
            examination='F-24', error='', cancel='BR:Błędna rejestracja')])}

test_data2 = {'6196569360':Order(order_details=OrderDetail(pesel='82050206568', birth_date=datetime.date(1982, 5, 2), system='KOPERNI', patient='Szmurło Agata', order_barcode='6196569360', payer='F-KOPE '), tests=[TestDetails(order_details=OrderDetail(pesel='82050206568', birth_date=datetime.date(1982, 5, 2), system='KOPERNI', patient='Szmurło Agata', order_barcode='6196569360', payer='F-KOPE '), common=Common(order_number=2423, order_date=datetime.date(2025, 4, 1), settlement_date=datetime.date(2025, 4, 18), test_barcode='6223173100'), examination='WILLEBR', error='', cancel=''), TestDetails(order_details=OrderDetail(pesel='82050206568', birth_date=datetime.date(1982, 5, 2), system='KOPERNI', patient='Szmurło Agata', order_barcode='6196569360', payer='F-KOPE '), common=Common(order_number=2423, order_date=datetime.date(2025, 4, 1), settlement_date=datetime.date(2025, 4, 18), test_barcode='6223173180'), examination='WILL-AG', error='', cancel='')])}

d = [
[
'ZAWODZI',
'ZAWODZI',
'F-SKIN ',
'2025-04-05',
2543,
'6222161540',
'62221615431',
'Piłka Natalia',
'00222809209',
'2000-02-28',
'F-24 (roz:2025-04-09)',
'',
''
],
[
'ZAWODZI',
'KOPERNI',
'F-KOPE ',
'2025-04-01',
2423,
'6196569360',
'6223173100',
'Szmurło Agata',
'82050206568',
'1982-05-02',
'WILLEBR (roz:2025-04-18)',
'',
''
],
[
'ZAWODZI',
'KOPERNI',
'F-KOPE ',
'2025-04-01',
2423,
'6196569360',
'6223173180',
'Szmurło Agata',
'82050206568',
'1982-05-02',
'WILL-AG (roz:2025-04-18)',
'',
''
]]


def test_1():
    result = group_data(test_data1)
    assert len(result) == 1
    assert not result[0].is_error()


def test_2():
    result = group_data(test_data2)
    assert len(result) == 2
    assert not result[1].is_error()


def test_3():
    data = {**test_data1, **test_data2}
    result = group_data(data)
    assert len(result) == 3


def test_4():
    data = {**test_data1, **test_data2}
    result = group_data(data)
    a = serialize(result, 'ZAWODZI')
    assert a == d
