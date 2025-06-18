import re

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError, Switch, Preset
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty

MENU_ENTRY = 'Policz wyniki'
REQUIRE_ROLE = ['C-CS']
ADD_TO_ROLE = ['R-MDO', 'L-PRAC']

PODZIAL_TYTUL = {
    'pracownia': 'Pracownia',
    'zleceniodawca': 'Zleceniodawca',
    'material': 'Materiał',
}

PODZIAL_POLE = {
    'pracownia': 'trim(p.symbol)',
    'zleceniodawca': 'trim(o.symbol)',
    'material': 'trim(mat.symbol)',
}

LAUNCH_DIALOG = Dialog(title="Policz wyniki", panel=HBox(
    VBox(
        LabSelector(field="laboratoria", title="Laboratoria", multiselect=True),
        InfoText(text="""Raport zliczający zatwierdzone wyniki wskazanych badań dla każdego parametru.
            Dla parametrów tekstowych zliczane są różne wyniki, dla liczbowych - flagi.
            Raport wykonywany wg dat zatwierdzenia. Można wyfiltrować wyniki dla jednego zleceniodawcy."""),
        HBox(
            DateInput(field='dataod', title='Data początkowa', default='-1D'),
            DateInput(field='datado', title='Data końcowa', default='-1D'),
        ),
        TextInput(field="badania", title="Symbole badań (obowiązkowe, oddzielone spacją)"),
        TextInput(field="metoda", title="Symbol metody"),
        TextInput(field="parametr", title="Symbol parametru"),
        TextInput(field="zleceniodawca", title="Symbol zleceniodawcy"),
        TextInput(field="platnik", title="Symbol płatnika"),
        Switch(field="ukryte", title="Pokaż ukryte"),
        Select(field="podzial", title="Podział", values=PODZIAL_TYTUL)
        # Switch(field="podzial_zlec", title="Podział na zleceniodawców, zamiast pracowni"),
    )
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    validate_date_range(params['dataod'], params['datado'], max_days=366)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    for fld in 'badania metoda parametr zleceniodawca'.split(' '):
        params[fld] = (params.get(fld) or '').strip().upper()
    badania = []
    for symbol in params['badania'].replace(',', ' ').split(' '):
        if len(symbol) > 0 and len(symbol) <= 7 and re.match('^[A-Z0-9_-]+$', symbol):
            badania.append(symbol)
    if len(badania) == 0:
        raise ValidationError("Nie podano żadnego badania")
    params['badania'] = badania
    report = TaskGroup(__PLUGIN__, params)
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
    sql_params = [str(params['dataod']) + ' 0:00:00', str(params['datado']) + ' 23:59:59']
    sql_badania = "select id from badania where symbol in (%s)" % ','.join(["'%s'" % s for s in params['badania']])
    with get_centrum_connection(task_params['target']) as conn:
        id_badan = [row['id'] for row in conn.raport_slownikowy(sql_badania, [tuple(params['badania'])])]
        sql = """
            select $PODZIAL$, b.symbol, m.symbol, ap.symbol, par.symbol,
                case when y.wynikliczbowy is not null then (
                    case when (y.flaganormy is null or y.flaganormy=0) then 'N' 
                        when y.flaganormy=1 then 'L'
                        when y.flaganormy=2 then 'H'
                        else '-' end             
                ) else y.wyniktekstowy end,
                cast(w.zatwierdzone as date),
                count(w.id)
            from wykonania w
                left join badania b on b.id=w.badanie
                left join metody m on m.id=w.metoda
                left join aparaty ap on ap.id=w.aparat
                left join zlecenia z on z.id=w.zlecenie
                left join typyzlecen tz on tz.id=z.typzlecenia
                left join pracownie p on p.id=w.pracownia
                left join oddzialy o on o.id=z.oddzial
                left join wyniki y on y.wykonanie=w.id
                left join parametry par on par.id=y.parametr
                left join materialy mat on mat.id=w.material
            where
                w.zatwierdzone between ? and ?
                and w.badanie in ($BADANIA$)
                and tz.symbol not in ('K', 'KZ', 'KW')
                and w.bladwykonania is null
                and w.anulowane is null
                and y.id is not null
                and y.ukryty = 0
        """
        if len(id_badan) == 0:
            raise ValidationError("Nie znaleziono ani jednego badania")
        sql = sql.replace('$BADANIA$', ','.join([str(b) for b in id_badan]))
        if params['metoda'] != '':
            sql += " and m.symbol=? "
            sql_params.append(params['metoda'])
        if params['parametr'] != '':
            sql += " and par.symbol=? "
            sql_params.append(params['parametr'])
        if params.get('zleceniodawca') not in (None, ''):
            sql += " and z.oddzial in (select id from oddzialy where symbol=?)"
            sql_params.append(params['zleceniodawca'])
        if params.get('platnik') not in (None, ''):
            sql += " and z.platnik in (select id from platnicy where symbol=?)"
            sql_params.append(params['platnik'])
        if params.get('ukryte'):
            sql = sql.replace('and y.ukryty = 0', '')
        sql = sql.replace('$PODZIAL$', PODZIAL_POLE[params['podzial']])
        sql += """
            group by 1, 2, 3, 4, 5, 6, 7
            order by 1, 2, 3, 4, 5, 6, 7
        """
        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
        return rows


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
            }
        ]
    }
    start_params = None
    for job_id, params, status, result in task_group.get_tasks_results():
        if status == 'finished' and result is not None:
            header = ',Badanie,Metoda,Aparat,Parametr,Wynik,Zatwierdzone,Ilość'.split(',')
            header[0] = PODZIAL_TYTUL[params['params']['podzial']]
            res['results'].append({
                'type': 'table',
                'title': params['target'],
                'header': header,
                'data': prepare_for_json(result)
            })
            if start_params is None:
                start_params = params['params']
        elif status == 'failed':
            res['errors'].append("%s - błąd połączenia" % params['target'])
    res['progress'] = task_group.progress
    return res
