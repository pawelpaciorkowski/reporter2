from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection
from api.common import get_db

MENU_ENTRY = 'Sprzedaż gotówkowa'
REQUIRE_ROLE = ['C-FIN', 'C-ROZL', 'C-PP']
REQUIRE_ROLE = 'ADMIN' # TODO: usunąć po implementacji


LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text='Raport generowany jest wg dat rejestracji'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria'),
    DateInput(field='dataod', title='Data początkowa', default='PZM'),
    DateInput(field='datado', title='Data końcowa', default='KZM'),
    # TODO: zmienić na BadanieSearch i GrupaBadanSearch
    TextInput(field='badanie', title='Tylko badanie o podanym symbolu'),
    TextInput(field='grupa', title='Tylko grupa badań o podanym symbolu'),
    Switch(field='podzial_statusy', title='Rozdział na statusy (rabaty)'),
    Switch(field='podzial_badania', title='Rozdział na badania'),
    Switch(field='podzial_grupy', title='Rozdział na grupy badań'),
))

"""

laboratorium - płatnik symbol (?) - płatnik (laboratorium) - kryterium podziału (?) - liczba badań - wartość badań
"""

def start_report(params):
    laboratoria = []
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    for lab in params['laboratoria']:
        if lab == '*':
            with get_db() as db:
                for row in db.select("select * from laboratoria where aktywne and laboratorium"):
                    if row['symbol'] not in laboratoria:
                        laboratoria.append(row['symbol'])
        else:
            if lab not in laboratoria:
                laboratoria.append(lab)
    for lab in laboratoria:
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
    lab = task_params['target']
    sql = """
    select P.symbol as SYMBOLP, P.Nazwa as NAZWAP, count (W.id) as ILOSC, sum(w.cena) as WARTOSC
                        from wykonania W
                                left outer join Zlecenia Z on w.zlecenie = z.id
                                left outer join Oddzialy P on z.oddzial = p.id
                                left outer join Badania B on w.badanie = b.id
                                left outer join GrupyBadan GB on GB.Id = B.Grupa
                                left outer join Taryfy T on w.taryfa = T.id
                        where
                                W.Datarejestracji between ? and ?
                                and GB.Symbol = ?
                                and W.Platne = 1 and W.Anulowane is Null  and (GB.Symbol != \'TECHNIC\' or GB.Symbol is null) and T.symbol = \'X-GOTOW\' and (b.pakiet = \'0\' or (b.pakiet = \'1\' and w.cena is not null))
                        group by P.symbol, P.Nazwa
                        order by P.Symbol;
    """
    with get_centrum_connection(lab) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, [params['dataod'], params['datado'], params['grupa']])
        return rows
    # TODO: dostosować do innych wariantów


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
            for row in result:
                wiersze.append([params['target']] + row)
        if status == 'failed':
            res['errors'].append('%s - błąd połączenia' % params['target'])
    res['progress'] = task_group.progress
    res['results'].append({
        'type': 'table',
        'header': 'Laboratorium,Zl.Sym.,Zleceniodawca,Ilość,Wartość',
        'data': prepare_for_json(wiersze)
    })
    return res


"""
if ($_GET['badania'] != 'tak') {
    $sql  = 'select P.symbol as SYMBOLP, P.Nazwa as NAZWAP, count (W.id) as ILOSC, sum(w.cena) as WARTOSC
                        from wykonania W
                                left outer join Zlecenia Z on w.zlecenie = z.id
                                left outer join Oddzialy P on z.oddzial = p.id
                                left outer join Badania B on w.badanie = b.id
                                left outer join GrupyBadan GB on GB.Id = B.Grupa
                                left outer join Taryfy T on w.taryfa = T.id
                        where
                                W.Datarejestracji between \''.$od.'\' and \''.$do.'\'
                                and W.Platne = 1 and W.Anulowane is Null  and (GB.Symbol != \'TECHNIC\' or GB.Symbol is null) and T.symbol = \'X-GOTOW\' and (b.pakiet = \'0\' or (b.pakiet = \'1\' and w.cena is not null))
                        group by P.symbol, P.Nazwa
                        order by P.Symbol; ';

        $sqlS  = 'select P.symbol as SYMBOLP, P.Nazwa as NAZWAP, S.nazwa as NAZWAS, count (W.id) as ILOSC, sum(w.cena) as WARTOSC
                        from wykonania W
                                left outer join Zlecenia Z on w.zlecenie = z.id
                                left outer join Oddzialy P on z.oddzial = p.id
                                left outer join Badania B on w.badanie = b.id
                                left outer join GrupyBadan GB on GB.Id = B.Grupa
                                left outer join Taryfy T on w.taryfa = T.id
                                left outer join StatusyPacjentow S on Z.StatusPacjenta = S.id
                        where
                                W.Datarejestracji between \''.$od.'\' and \''.$do.'\'
                                and W.Platne = 1 and W.Anulowane is Null and (GB.Symbol != \'TECHNIC\' or GB.Symbol is null) and T.symbol = \'X-GOTOW\' and (b.pakiet = \'0\' or (b.pakiet = \'1\' and w.cena is not null))
                        group by P.symbol, P.Nazwa, S.nazwa
                        order by P.Symbol, S.nazwa; ';
        $sqlG  = 'select P.symbol as SYMBOLP, P.Nazwa as NAZWAP, GB.nazwa as NAZWAS, count (W.id) as ILOSC, sum(w.cena) as WARTOSC
                        from wykonania W
                                left outer join Zlecenia Z on w.zlecenie = z.id
                                left outer join Oddzialy P on z.oddzial = p.id
                                left outer join Badania B on w.badanie = b.id
                                left outer join GrupyBadan GB on GB.Id = B.Grupa
                                left outer join Taryfy T on w.taryfa = T.id
                        where
                                W.Datarejestracji between \''.$od.'\' and \''.$do.'\'
                                and W.Platne = 1 and W.Anulowane is Null and (GB.Symbol != \'TECHNIC\' or GB.Symbol is null) and T.symbol = \'X-GOTOW\' and (b.pakiet = \'0\' or (b.pakiet = \'1\' and w.cena is not null))
                        group by P.symbol, P.Nazwa, GB.nazwa
                        order by P.Symbol, GB.nazwa; ';

} else {
        $sql  = 'select P.symbol as SYMBOLP, P.Nazwa as NAZWAP, B.Symbol as SYMBOLB, count (W.id) as ILOSC, sum(w.cena) as WARTOSC
                        from wykonania W
                                left outer join Zlecenia Z on w.zlecenie = z.id
                                left outer join Oddzialy P on z.oddzial = p.id
                                left outer join Badania B on w.badanie = b.id
                                left outer join GrupyBadan GB on GB.Id = B.Grupa
                                left outer join Taryfy T on w.taryfa = T.id
                        where
                                W.Datarejestracji between \''.$od.'\' and \''.$do.'\'
                                and W.Platne = 1 and W.Anulowane is Null and (GB.Symbol != \'TECHNIC\' or GB.Symbol is null) and T.symbol = \'X-GOTOW\' and (b.pakiet = \'0\' or (b.pakiet = \'1\' and w.cena is not null))
                        group by P.symbol, P.Nazwa, B.Symbol
                        order by P.Symbol, B.Symbol; ';


"""