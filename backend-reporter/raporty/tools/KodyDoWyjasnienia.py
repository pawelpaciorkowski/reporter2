import datetime
import time

from api.auth import login_required
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError, Switch
from helpers.validators import validate_date_range
from datasources.reporter import ReporterExtraDatasource
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection, empty, odpiotrkuj

MENU_ENTRY = 'Kody do wyjaśnienia'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    TabbedView(field='tab', desc_title='Typ raportu', children=[
        Tab(title='Pobierz kody', value='pobierz',
            panel=VBox(
                DateInput(field='dataod', title='Data początkowa', default='-7D'),
                DateInput(field='datado', title='Data końcowa', default='-1D'),
            )
            ),
        Tab(title='Szukaj kodów', value='szukaj',
            panel=VBox(
                InfoText(
                    text='Proszę wprowadzać szukane kody oddzielone spacją lub enterem. Można wprowadzać czytnikiem. Znaki "=" zostaną zignorowane.'),
                TextInput(field='kodys', title='Kody kreskowe', autofocus=True, textarea=True),
            )
            ),
        Tab(title='Zapisz kody', default=True, value='zapisz',
            panel=VBox(
                InfoText(
                    text='Proszę wprowadzać kody do zapisania oddzielone spacją lub enterem. Można wprowadzać czytnikiem. Znaki "=" zostaną zignorowane.'),
                TextInput(field='kodyz', title='Kody kreskowe', autofocus=True, textarea=True),
                TextInput(field='komentarz', title='Komentarz', textarea=True),
            )
            )
    ]),
))


def filtruj_kody(kody):
    res = []
    if kody is not None:
        for kod in kody.replace('\r\n', '\n').replace('\n', ' ').replace('\t', ' ').replace('=', '').split(' '):
            if (len(kod)) > 5 and kod not in res:
                res.append(kod)
    return res


def start_report(params):
    @login_required
    def get_login(user_login):
        return user_login

    params = LAUNCH_DIALOG.load_params(params)
    params['login'] = get_login()
    report = TaskGroup(__PLUGIN__, params)
    if params['tab'] == 'pobierz':
        validate_date_range(params['dataod'], params['datado'], 366)
        report.create_task({
            'type': 'ick',
            'priority': 1,
            'params': params,
            'function': 'report_pobierz',
        })
    elif params['tab'] == 'szukaj':
        params['kody'] = filtruj_kody(params['kodys'])
        if len(params['kody']) == 0:
            raise ValidationError('Wprowadź co najmniej 1 kod do wyszukania')
        print(params)
        report.create_task({
            'type': 'ick',
            'priority': 1,
            'params': params,
            'function': 'report_pobierz',
        })
    elif params['tab'] == 'zapisz':
        params['kody'] = filtruj_kody(params['kodyz'])
        if len(params['kody']) == 0:
            raise ValidationError('Wprowadź co najmniej 1 kod do zapisania')
        report.create_task({
            'type': 'ick',
            'priority': 1,
            'params': params,
            'function': 'report_zapisz',
        })
    report.save()
    return report


def formatuj_znalezione(dane):
    res_txt = []
    res_html = []
    res = {}
    bg_level = 0
    if dane is not None:
        for k, v in dane.items():
            res_txt.append('%s: %s' % (k, v))
            res_html.append('<strong>%s:</strong> %s' % (k, v))
            if 'HL7' in k:
                bg_level = max(bg_level, 1)
            if 'nocka' in k:
                bg_level = max(bg_level, 2)
            if 'zatw' in v and 'błąd' not in v:
                bg_level = max(bg_level, 3)
    res['html'] = '<br />'.join(res_html)
    res['value'] = '\n'.join(res_txt)
    if bg_level > 0:
        res['background'] = ['', '#50baff', '#f6fc3c', '#3cfc45'][bg_level]
    return res


def report_pobierz(task_params):
    params = task_params['params']
    db = ReporterExtraDatasource()
    if params['tab'] == 'pobierz':
        sql = """
            select p.kod as "Kod kreskowy", o.created_at as "Zapisany", o.created_by as "Zapisany przez", 
                o.description as "Komentarz", p.znalezione as "Znalezione"
            from worekkodow_operacja o
            left join worekkodow_pozycja p on p.operacja=o.id
            where o.created_at between %s and %s
        """
        sql_params = [params['dataod'], params['datado'] + ' 23:59:59']
        cols, rows = db.select(sql, sql_params)
        res_rows = []
        for row in rows:
            row = list(row)
            row[4] = formatuj_znalezione(row[4])
            res_rows.append(row)
        return {
            'type': 'table',
            'header': cols,
            'data': prepare_for_json(res_rows),
        }
    elif params['tab'] == 'szukaj':
        sql = """select p.kod as "Kod kreskowy", o.created_at as "Zapisany", o.created_by as "Zapisany przez", 
                        o.description as "Komentarz", p.znalezione as "Znalezione"
            from worekkodow_pozycja p 
            left join worekkodow_operacja o on o.id=p.operacja
            where p.kod in %s"""
        sql_params = [tuple(params['kody'])]
        lefts_sql = []
        lefts_sql_params = []
        for kod in params['kody']:
            left = kod[:9]
            if left not in lefts_sql_params:
                lefts_sql.append('left(p.kod, 9)=%s')
                lefts_sql_params.append(left)
        if len(lefts_sql_params) > 0:
            sql += ' or (' + ' or '.join(lefts_sql) + ')'
            sql_params += lefts_sql_params
        cols, rows = db.select(sql, sql_params)
        res_rows = []
        for row in rows:
            row = list(row)
            row[4] = formatuj_znalezione(row[4])
            if row[0] in params['kody']:
                row.append('T')
            else:
                row.append('')
            res_rows.append(row)
        cols.append("Dokładne dopasowanie")
        return {
            'type': 'table',
            'header': cols,
            'data': prepare_for_json(res_rows),
        }
    else:
        raise RuntimeError(params['tab'])


def report_zapisz(task_params):
    params = task_params['params']
    db = ReporterExtraDatasource(read_write=True)
    oper_id = db.insert('worekkodow_operacja', {
        'created_at': 'NOW',
        'created_by': params['login'],
        'description': params['komentarz'],
    })
    for kod in params['kody']:
        db.insert('worekkodow_pozycja', {
            'operacja': oper_id,
            'kod': kod,
        })
    db.commit()
    return {'type': 'info', 'text': 'Zapisano %d kodów' % len(params['kody'])}
