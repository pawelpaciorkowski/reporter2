from docutils.nodes import field

from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, Switch, \
    ValidationError
from helpers.validators import validate_date_range, validate_symbol
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, get_bank_krwi_connection, get_snr_connection, slugify, \
    empty

MENU_ENTRY = "Zestawienie rozpoznań"

ROZPOZNANIA = {
    'Rak piersi': ['%rak%piersi%', '%carcinoma%mammae%'],
    'Rak jelita grubego': ['%rak%jelita grubego%'],
}

opisy_rozpoznan = []
for nazwa, teksty in ROZPOZNANIA.items():
    opis = "  " + nazwa + ": "
    opis += " lub ".join([tekst.replace('%', '...') for tekst in teksty])
    opisy_rozpoznan.append(opis)

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="""
        Zestawienie rozpoznań z baz histopatologicznych wykonywane jest na podstawie opisów wyników.
        Nowe rozpoznania należy zgłaszać przez dział administracyjny Alab Plus, powinno być przy tym wzięte
        pod uwagę, że rozpoznania mogą być wpisywane w różnych językach, formie gramatycznej i szyku zdań.
        Obecnie wyszukiwane rozpoznania:
    """ + "\n".join(opisy_rozpoznan)),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', tylko_histopatologia=True),
    DateInput(field='data_od', title='Zatwierdzone od', default='PZM'),
    DateInput(field='data_do', title='Zatwierdzone do', default='KZM'),
    TextInput(field='platnik', title="Płatnik (symbol)"),
    TextInput(field='zleceniodawca', title="Zleceniodawca (symbol)"),
    *[Switch(field=slugify(rozp), title=rozp) for rozp in ROZPOZNANIA.keys()]
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError('Wybierz lab')
    validate_date_range(params['data_od'], params['data_do'], 366)
    for fld in ('platnik', 'zleceniodawca'):
        if not empty(params[fld]):
            validate_symbol(params[fld])
        else:
            params[fld] = None
    if params['platnik'] is None and params['zleceniodawca'] is None:
        raise ValidationError("Podaj płatnika lub zleceniodawcę")
    if len([rozp for rozp in ROZPOZNANIA.keys() if params[slugify(rozp)]]) == 0:
        raise ValidationError("Wybierz przynajmniej jedno rozpoznanie")
    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_lab'
    }
    report.create_task(task)
    report.save()
    return report


def raport_lab(task_params):
    params = task_params['params']
    sql = """
        select z.kodkreskowy, ap.nazwa as aparat, w.zatwierdzone, y.opis 
        from wykonania w 
        left join zlecenia z on z.id=w.zlecenie 
        left join wyniki y on y.wykonanie=w.id
        left join badania b on b.id=w.badanie 
        left join aparaty ap on ap.id=w.aparat 
        where w.zatwierdzone between ? and ?
        and $KLIENT$
        and ($OPISY$)
    """
    # y.opis ilike '%rak%piersi%' or y.opis ilike '%rak%jelita grubego%'
    sql_params = [params['data_od'], params['data_do']+' 23:59:59']
    where_klient = []
    where_opisy = []
    if not empty(params['platnik']):
        where_klient.append('w.platnik in (select id from platnicy where symbol=?)')
        sql_params.append(params['platnik'])
    if not empty(params['zleceniodawca']):
        where_klient.append('z.oddzial in (select id from oddzialy where symbol=?)')
        sql_params.append(params['zleceniodawca'])
    for rozp, teksty in ROZPOZNANIA.items():
        if params[slugify(rozp)]:
            for tekst in teksty:
                where_opisy.append('lower(y.opis) like ?')
                sql_params.append(tekst.lower())
    sql = sql.replace('$KLIENT$', ' and '.join(where_klient))
    sql = sql.replace('$OPISY$', ' or '.join(where_opisy))
    with get_centrum_connection(task_params['target']) as conn:
        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
        return {
            'type': 'table',
            'header': cols,
            'data': prepare_for_json(rows)
        }