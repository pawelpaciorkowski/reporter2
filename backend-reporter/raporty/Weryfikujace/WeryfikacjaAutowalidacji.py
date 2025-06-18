from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    PlatnikSearch, ZleceniodawcaSearch, ValidationError, Switch
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection
from datasources.centrum import Centrum

MENU_ENTRY = 'Weryfikacja autowalidacji'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(
        text="""Raport wg dat rejestracji, tylko badania z regułami. Dla stępińskiej używana jest baza raportowa.
             W przypadku raportu na poziomie wykonań zwracane są wszystkie badania z podanego zakresu,
             w przypadku raportu na poziomie wyników - wszystkie parametry, które mogą być automatycznie zaakceptowane lub zatwierdzone.
             Ze względów wydajnościowych wynik raportu jest ograniczony do 20000 wierszy. Jeśli nie są zwracane wszystkie potrzebne dane, należy
             zawęzić zakres za pomocą filtrów.
             Raport obejmuje badania z grupy pracowni WEWN, z pominięciem badań z grupy TECHNIC."""),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium'),
    Switch(field='bazatest', title='Baza testowa autowalidacji'),
    DateInput(field='data', title='Data', default='-1D'),
    Switch(field='wyniki', title='Pokaż wyniki (a nie tylko wykonania)'),
    TextInput(field='filtr_badania', title='Pokaż tylko badania (symbole oddzielone spacjami)'),
    TextInput(field='filtr_pracownie', title='Pokaż tylko pracownie (symbole oddzielone spacjami)'),
    TextInput(field='filtr_aparaty', title='Pokaż tylko analizatory (symbole oddzielone spacjami)'),
))

SQL_WYKONANIA = """
    select first 20000 zl.datarejestracji as "Data", zl.numer as "Nr zlecenia",
        trim(prac.symbol) as "Pracownia", trim(ap.symbol) as "Aparat",
        trim(bad.symbol) as "Symbol badania", bad.nazwa as "Nazwa badania",
        case when w.autowykonane=1 then 1 else 0 end as "Autoakceptacja",    
        case when w.autozatwierdzone=1 then 1 else 0 end as "Autozatwierdzenie",    
        case when w.autowykonane=-1 then 1 else 0 end as "Bez autoakceptacji",    
        case when w.autozatwierdzone=-1 then 1 else 0 end as "Bez autozatwierdzenia",
        trim(plec.symbol) as "Płeć",
        WiekPacjenta(zl.datarejestracji, pac.dataurodzenia, null, '') as "Wiek"
    from zlecenia zl
    left join wykonania w on w.zlecenie=zl.id
    left join badania bad on bad.id=w.badanie
    left join pracownie prac on prac.id=w.pracownia
    left join grupybadan gb on gb.id=bad.grupa
    left join grupypracowni gp on gp.id=prac.grupa
    left join aparaty ap on ap.id=w.aparat
    left join pacjenci pac on pac.id=zl.pacjent
    left join plci plec on plec.id=pac.plec
    where $WHERE$
    order by 1, 2
"""

SQL_WYNIKI = """
    select first 20000 zl.datarejestracji as "Data", zl.numer as "Nr zlecenia",
        trim(prac.symbol) as "Pracownia", trim(ap.symbol) as "Aparat",
        trim(bad.symbol) as "Symbol badania", bad.nazwa as "Nazwa badania",
        trim(par.symbol) as "Symbol parametru", par.nazwa as "Nazwa parametru",
        coalesce(nor.opis, nor.dlugiopis) as "Wartości referencyjne", par.format as "Format i jednostka",
        y.wynikliczbowy as "Wynik liczbowy",
        y.wyniktekstowy as "Wynik tekstowy",
        case when w.autowykonane=1 then 1 else 0 end as "Autoakceptacja",    
        case when w.autozatwierdzone=1 then 1 else 0 end as "Autozatwierdzenie",    
        case when w.autowykonane=-1 then 1 else 0 end as "Bez autoakceptacji",    
        case when w.autozatwierdzone=-1 then 1 else 0 end as "Bez autozatwierdzenia",
        trim(plec.symbol) as "Płeć",
        WiekPacjenta(zl.datarejestracji, pac.dataurodzenia, null, '') as "Wiek",
        case 
            when nor.kiedyzatwierdzanie=1 then 'nie pozwalać'
            when nor.kiedyzatwierdzanie=2 then 'gdy w normie'
            when nor.kiedyzatwierdzanie=3 then 'gdy nie krytyczne'
            when nor.kiedyzatwierdzanie=4 then 'pozwalać w zakresie'             
        end as "Zbiorowe zatwierdzania",
        nor.zatwierdzanieod as "Wartości autozatw. OD",
        nor.zatwierdzaniedo as "wartości autozatw. DO",
        par.deltacheckdol as "Delta check różn w górę",
        par.deltacheckgora as "Delta check różn w dół",
        par.deltacheckiledni as "Delta check ilość dni"
    from zlecenia zl
    left join wykonania w on w.zlecenie=zl.id
    left join wyniki y on y.wykonanie=w.id
    left join badania bad on bad.id=w.badanie
    left join pracownie prac on prac.id=w.pracownia
    left join grupybadan gb on gb.id=bad.grupa
    left join grupypracowni gp on gp.id=prac.grupa
    left join aparaty ap on ap.id=w.aparat
    left join parametry par on par.id=y.parametr
    left join normy nor on nor.id=y.norma
    left join pacjenci pac on pac.id=zl.pacjent
    left join plci plec on plec.id=pac.plec
    where $WHERE$
    order by 1, 2, bad.kolejnosc, bad.symbol, par.kolejnosc, par.symbol
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'raport_pojedynczy'
    }
    report.create_task(task)
    report.save()
    return report


def raport_pojedynczy(task_params):
    params = task_params['params']
    sql = SQL_WYKONANIA
    where = ['zl.datarejestracji=?']
    sql_params = [params['data']]
    if params['wyniki']:
        sql = SQL_WYNIKI
    if params['bazatest']:
        cnt = Centrum(adres='2.0.205.233', alias='/var/lib/firebird/autowalidacja.ib')
        conn = cnt.connection()
    else:
        conn = get_centrum_connection(task_params['target'])
    with conn:
        filtry = {}
        for typ_filtra, pole in zip(('badania', 'pracownie', 'aparaty'), ('badanie', 'pracownia', 'aparat')):
            for val in (params.get('filtr_%s' % typ_filtra) or '').upper().replace(',', ' ').split(' '):
                if val.strip() != '':
                    cols, rows = conn.raport_z_kolumnami("select id from " + typ_filtra + " where symbol=? and del=0",
                                                         [val.strip()])
                    if len(rows) > 0:
                        if pole not in filtry:
                            filtry[pole] = []
                        filtry[pole].append(rows[0][0])
        for pole, idents in filtry.items():
            where.append('w.%s in (%s)' % (pole, ','.join([str(id) for id in idents])))
        where += ['w.zatwierdzone is not null', 'w.bladwykonania is null', 'w.anulowane is null',
                  '(GB.Symbol <> \'TECHNIC\' or GB.symbol is null)', 'gp.symbol =\'WEWN\'']
        sql = sql.replace('$WHERE$', ' and '.join(where))
        print(sql)
        cols, rows = conn.raport_z_kolumnami(sql, sql_params)
        return {
            'type': 'table',
            'title': task_params['target'],
            'header': cols,
            'data': prepare_for_json(rows)
        }
