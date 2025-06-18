import decimal

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, Switch, \
    Select, Radio, ValidationError
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task

MENU_ENTRY = 'Raport ze sprzedaży gotówkowej'

REQUIRE_ROLE = ['C-FIN', 'R-PM']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa', default='-1D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
    Switch(field='podzial_statusy', title='Podział na statusy pacjenta (rabaty)'),
    Switch(field='podzial_badania', title='Podział na badania'),
    Switch(field='podzial_grupy_badan', title='Podział na grupy badań'),
    Switch(field='podzial_rejestracja', title='Podział na daty rejestracji'),
    Switch(field='podzial_komentarze', title='Podział na komentarze zleceń'),
))

INNER_SQL = """
    select P.symbol as zleceniodawca, P.Nazwa as zleceniodawca_nazwa, 
    S.nazwa as status, B.Symbol as badanie, GB.symbol as grupa_badan, Z.komentarz,
    W.Datarejestracji,
    Z.id as zlecenie,
    count(w.id) as ilosc_wykonan,
    sum(case when b.pakiet=0 then 1 else 0 end) as ilosc_badan,
    sum(case when b.pakiet=0 then 0 else 1 end) as ilosc_pakietow,
    sum(case when w.pakiet is not null then 1 else 0 end) as ilosc_skladowych,
    sum(w.cena) as wartosc
    from wykonania W
        left outer join Zlecenia Z on w.zlecenie = z.id
        left outer join Oddzialy P on z.oddzial = p.id
        left outer join Badania B on w.badanie = b.id
        left outer join GrupyBadan GB on GB.Id = B.Grupa
        left outer join Taryfy T on w.taryfa = T.id
        left outer join StatusyPacjentow S on Z.StatusPacjenta = S.id
    where
        W.Datarejestracji between ? and ?
        and W.Platne = 1 and W.Anulowane is Null and (GB.Symbol != 'TECHNIC' or GB.Symbol is null) and T.symbol = 'X-GOTOW'
    group by 1,2,3,4,5,6,7,8
    order by 1,3,4,5,6,8
"""

PODPISY = {
    'zleceniodawca': "Zleceniodawca",
    'zleceniodawca_nazwa': "Zleceniodawca (nazwa)",
    'datarejestracji': "Data rej.",
    'status': "Status pacjenta",
    'badanie': "Badanie",
    'grupa_badan': "Grupa badań",
    'komentarz': "Komentarz",
    'ilosc_wykonan': "Ilość bad/pak",
    'ilosc_badan': "Ilość badań",
    'ilosc_pakietow': "Ilość pakietów",
    'ilosc_skladowych': "Ilość składowych",
    'ilosc_zl': "Ilość zleceń",
    'wartosc': "Wartość",
}


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
    lab = task_params['target']
    fields = ['a.zleceniodawca', 'a.zleceniodawca_nazwa']
    if params['podzial_rejestracja']:
        fields.append('a.datarejestracji')
    if params['podzial_statusy']:
        fields.append('a.status')
    if params['podzial_badania']:
        fields.append('a.badanie')
    if params['podzial_grupy_badan']:
        fields.append('a.grupa_badan')
    if params['podzial_komentarze']:
        fields.append('a.komentarz')
    fields += ['sum(a.ilosc_wykonan) as ilosc_wykonan', 'sum(a.ilosc_badan) as ilosc_badan',
               'sum(a.ilosc_pakietow) as ilosc_pakietow', 'sum(a.ilosc_skladowych) as ilosc_skladowych']
    group_by_offset = 5
    if not params['podzial_badania'] and not params['podzial_grupy_badan']:
        fields += ['count(distinct a.zlecenie) as ilosc_zl']
        group_by_offset += 1
    fields += ['sum(a.wartosc) as wartosc']
    sql = "select " + ", ".join(fields) + " from ("
    sql += INNER_SQL + ") a "
    sql += " group by " + ", ".join(fields[:-group_by_offset])
    sql += " order by " + ", ".join(fields[:-group_by_offset])
    with get_centrum_connection(lab) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, [params['dataod'], params['datado']])
    cols = [PODPISY.get(c, c) for c in cols]
    ilosc, wartosc = 0, decimal.Decimal(0)
    for row in rows:
        ilosc += row[-group_by_offset]
        wartosc += (row[-group_by_offset+1] or decimal.Decimal(0))
    return [
        {
            'type': 'table',
            'title': lab,
            'header': cols,
            'data': prepare_for_json(rows),
        },
        {
            'type': 'info',
            'text': '%s łącznie: %d badań / %.02f PLN' % (lab, ilosc, float(wartosc))
        }
    ]


def get_result(ident):
    task_group = TaskGroup.load(ident)
    if task_group is None:
        return None
    res = {
        'errors': [],
        'results': [],
        'actions': [
            'xlsx',
            {
                'type': 'xlsx',
                'label': 'Excel (płaska tabela)',
                'flat_table': True,
                'flat_table_header': 'Laboratorium',
            },
        ]
    }
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            for subres in result:
                res['results'].append(subres)
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])
    res['progress'] = task_group.progress
    return res
