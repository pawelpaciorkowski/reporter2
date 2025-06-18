from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, ValidationError, Switch
from datasources.nocka import NockaDatasource, nocka_sprawdz_kompletnosc # noqa # pylint: disable=unused-import
from helpers import prepare_for_json, Kalendarz
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task

MENU_ENTRY = 'Ile badań pracownie 2'

REQUIRE_ROLE = ['C-FIN']

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="""Raport z liczby wykonanych badań w laboratoriach z rozbiciem na pracownie, grupy badań i grupy płatników.
            Raport wykonywany z bazy raportowej, uzupełnianej w nocy danymi na poprzedni dzień. Ceny dla zleceń niegotówkowych
            podawane są w miarę możliwości z SNR, a jeśli nie ma to z cennika wzorcowego.
            Kolumna SNR braki oznacza dla ilu wykonań z danego wiersza nie znaleziono odpowiedników w SNR - taka sytuacja
            jest możliwa w przypadku problemów z połączeniem, bazy której nie rozliczamy centralnie lub gdy jest zatrzymana synchronizacja do SNR bieżących badań w okresie rozliczeń.
            Uwaga! Cena wg cennika wzorcowego jest podawana zawsze dla badań oznaczonych jako płatne, nawet jeśli jest to badanie zlecone między laboratoriami.
            W przypadku braku danych z danego laboratorium i dnia zostanie wyświetlone odpowiednie ostrzeżenie."""),
    DateInput(field='dataod', title='Data początkowa', default='-1D'),
    DateInput(field='datado', title='Data końcowa', default='-1D'),
    TextInput(field='badanie', title='Pojedyncze badanie (symbol)'),
    TextInput(field='platnik_nip', title='NIP'),
    LabSelector(multiselect=True, field='laboratoria', title='Laboratoria', wewnetrzne=True),
    Switch(field='pokaz_badania', title='Grupuj po badaniach (a nie po grupach)'),
    Switch(field='pokaz_aparat', title='Podział na aparaty')
))


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if len(params['laboratoria']) == 0:
        raise ValidationError("Nie wybrano żadnego laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)
    if len(params['laboratoria']) > 10:
        if params['dataod'] != params['datado'] and params['badanie'] in (None, '') and params['platnik_nip'] in (None, ''):
            try:
                validate_date_range(params['dataod'], params['datado'], 31)
            except ValidationError:
                raise ValidationError("Zbyt szeroki zakres - wybierz do 10 labów lub max 7 dni lub pojedyncze badanie lub NIP")
    check_task = {
        'type': 'noc',
        'priority': 0,
        'params': params,
        'function': 'nocka_sprawdz_kompletnosc'
    }
    main_task = {
        'type': 'noc',
        'priority': 1,
        'params': params,
        'function': 'zbierz',
    }
    report.create_task(check_task)
    report.create_task(main_task)
    report.save()
    return report


def zbierz(task_params):
    ds = NockaDatasource()
    params = task_params['params']
    header = 'Laboratorium,Pracownia,Grupa badań,Grupa płatników,Data,Ilość,Suma lab,Suma SNR,Braki SNR,Suma cen.wzor.,Suma cen płatnika'.split(',')
    fields = ['w.lab', 'w.pracownia', 'w.grupa_badan', 'w.grupa_platnika_zlecenia', 'w.lab_wykonanie_data_rozliczenia', 'count(w.id)']
    fields += ['sum(w.lab_cena)', 'sum(w.snr_nettodlaplatnika)', 'sum(case when w.snr_id is null then 1 else 0 end)', 'sum(wzor.cena)', 'sum(sc.cena)']
    where = ['w.lab in %s', 'w.lab_wykonanie_data_rozliczenia between %s and %s']
    sql_params = [tuple(params['laboratoria']), params['dataod'], params['datado']]
    groupby = [1,2,3,4,5]
    orderby = [1,2,3,4,5]
    if params['badanie'] not in (None, ''):
        where.insert(0, "w.badanie=%s")
        sql_params.insert(0, params['badanie'])
    if params['pokaz_badania']:
        header[2] = 'Badanie'
        fields[2] = 'w.badanie'
    if params['pokaz_aparat']:
        header.insert(2, 'Aparat')
        fields.insert(2, 'w.aparat')
        groupby.append(6)
        orderby.append(6)
    if params['platnik_nip'] not in (None, ''):
        where.append("""w.lab_wykonanie_platnik in (select lab_id from slowniki sl
            where sl.slownik='platnicy' and sl.parametry->>'nip'=%s and sl.lab=w.lab)""")
        sql_params.append(params['platnik_nip'])
    where += ['w.lab_platne and not w.lab_techniczne_lub_kontrola']
    sql = "select " + ", ".join(fields)
    sql += "\nfrom Wykonania_Pelne w"
    sql += "\nleft join cennik_wzorcowy wzor on wzor.badanie=w.badanie"
    sql += "\nleft join snr_platnicywlaboratoriach pwl on pwl.lab=w.lab and pwl.symbol=w.platnik_wykonania"
    sql += "\nleft join snr_ceny sc on sc.platnik=pwl.platnik and sc.badanie=w.badanie"
    sql += "\nwhere " + " and ".join(where)
    sql += "\ngroup by " + ", ".join([str(n) for n in groupby])
    sql += "\norder by " + ", ".join([str(n) for n in orderby])
    cols, rows = ds.select(sql, sql_params)
    return {
        'type': 'table',
        'header': header,
        'data': prepare_for_json(rows),
    }
