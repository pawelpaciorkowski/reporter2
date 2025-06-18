from dialog import Dialog, VBox, LabSelector, InfoText, DateInput, ValidationError, Switch, TextInput
from datasources.nocka import NockaDatasource
from helpers import prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup

MENU_ENTRY = 'Obrót na osobę w punkcie'

REQUIRE_ROLE = ['C-FIN']


LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="""
        Raport przedstwia obrót wygenerowany przez osobę, w danym punkcie pobrań
        oraz w podanym zakresie czasu"""),
    DateInput(field='dataod', title='Data początkowa', default='-1D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria', wewnetrzne=True),
    TextInput(field='kanal', title='Pojedyncze wyniki dla pojedyńczego kanału'),
    # TextInput(field='login', title='Podedyńcze wyniki dla pracownika'),
    Switch(field="wykresdzienny", title="Pokaż rozkład dzienny")
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)

    if len(params['laboratoria']) == 0 and not params['kanal']:
        raise ValidationError("Nie wybrano żadnego laboratorium")

    validate_date_range(params['dataod'], params['datado'], 31)
    if len(params['laboratoria']) > 10:
        if params['dataod'] != params['datado']:
            try:
                validate_date_range(params['dataod'], params['datado'], 7)
            except ValidationError:
                raise ValidationError("Zbyt szeroki zakres - wybierz do 10 labów lub max 7 dni")

    main_task = {
        'type': 'noc',
        'priority': 1,
        'params': params,
        'function': 'zbierz',
    }
    report.create_task(main_task)
    report.save()
    return report


def zbierz(task_params):
    ds = NockaDatasource()
    params = task_params['params']
    header = 'Labolatorium, Kanał, Login, Obrót'.split(',')
    fields = ['lab', 'kanal', "substring(pracownikrejestracjizlecenia,position('$' in pracownikrejestracjizlecenia)+1) as login", 'sum(lab_cena)']
    where = ['lab_zlecenie_data between %s and %s', 'lab_pracownik_rejestracji is not null', 'lab_kanal is not null']
    sql_params = [params['dataod'], params['datado']]
    groupby = [1, 2, 3]
    orderby = [1, 2, 3]

    # Filtr na labalatoriach
    if params['laboratoria']:
        where.append('lab in %s')
        sql_params.append(tuple(params['laboratoria']))

    # Filtr na kanalach
    if params['kanal']:
        where.append('kanal = %s')
        sql_params.append(params['kanal'])

    # if params['login']:
    #     where.append('pracownikrejestracjizlecenia = %s')
    #     sql_params.append(params['login'])

    # Grupowanie po dniach
    if params['wykresdzienny']:
        header.insert(0, 'Data,')
        fields.insert(0, 'lab_zlecenie_data')
        groupby.append(len(groupby)+1)
        orderby.append(len(orderby) + 1)

    sql = "select " + ", ".join(fields)
    sql += "\nfrom wykonania_pelne_aktualne"
    sql += "\nwhere " + " and ".join(where)
    sql += "\ngroup by " + ", ".join([str(n) for n in groupby])
    sql += "\norder by " + ", ".join([str(n) for n in orderby])
    print(sql, sql_params)
    cols, rows = ds.select(sql, sql_params)
    return {
        'type': 'table',
        'header': header,
        'data': prepare_for_json(rows),
    }
