from config import Config
from datasources.postgres import PostgresDatasource
from dialog import Dialog, VBox, TextInput, ValidationError
from helpers.validators import validate_pesel
from tasks import TaskGroup
from helpers import prepare_for_json, empty

MENU_ENTRY = 'Czy był PESEL MultiSync?'
REQUIRE_ROLE = ['C-CS']
ADD_TO_ROLE = ['R-MDO', 'C-CS', 'L-PRAC']


LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    TextInput(field='pesel', title='PESEL'),
))

SQL = 'select * from raporty_reporter.czy_przetwarzamy_dane_osobowe(%s)'


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if empty(params['pesel']):
        raise ValidationError("Podaj pesel")
    else:
        params['pesel'] = validate_pesel(params['pesel'])
    task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'function': 'raport_pesele',
    }
    report.create_task(task)
    report.save()
    return report


def tables_from_multisync(task_params):
    result = []
    res = []
    pesel = task_params['params']['pesel']
    db = PostgresDatasource(Config.DATABASE_MULTISYNC)

    adres = telefon = email = zew = False
    data = db.dict_select(SQL, [pesel])
    if len(data) == 0:
        result.append({
            'type': 'info', 'text': 'MULTISYNC: Nie znaleziono pacjenta o podanym pesel',
        })
        return result
    else:
        cols = list([k for k in data[0].keys() if k != 'wyciek'])
        for d in data:
            row = [d[v] for v in cols]
            for indx,r in enumerate(row):
                if isinstance(r,bool):
                    row[indx] = 'Tak' if r else 'Nie'
            res.append(row)
            if d['jest_adres']:
                adres = True
            if d['jest_telefon']:
                telefon = True
            if d['jest_email']:
                email = True
            if d['systemy_zewnetrzne']:
                zew = True

        result.append({
            'type': 'vertTable',
            'title': f'MULTISYNC: PESEL: {pesel}',
            'data': [
                {'title': 'w bazach laboratoryjnych', 'value': 'Tak' if len(data) > 0 else 'Nie'},
                {'title': 'był adres', 'value': 'Tak' if adres else 'Nie'},
                {'title': 'był telefon', 'value': 'Tak' if telefon else 'Nie'},
                {'title': 'był email', 'value': 'Tak' if email else 'Nie'},
                {'title': 'dane z systemów klientów', 'value': 'Tak' if zew else 'Nie'},
                # {'title': 'w wyciekach danych', 'value': ', '.join(wycieki) if len(wycieki) > 0 else 'NIE'},

            ]
        })
        result.append({
            'type': 'table', 'title': 'MULTISYNC: W bazach',
            'header': cols,
            'data': prepare_for_json(res)
        })
    return result

def raport_pesele(task_params):
    return tables_from_multisync(task_params)