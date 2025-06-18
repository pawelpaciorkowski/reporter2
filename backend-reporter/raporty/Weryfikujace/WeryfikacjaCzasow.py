from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, \
    Select, Radio, Switch, ValidationError
from helpers import get_centrum_connection, prepare_for_json
from helpers.validators import validate_date_range
from tasks import TaskGroup, Task
import datetime

MENU_ENTRY = 'Weryfikacja czasów'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="Średnie czasy między zdarzeniami podane w godzinach."),
    LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', pokaz_nieaktywne=True),
    DateInput(field='dataod', title='Data rejestracji od', default='PZM'),
    DateInput(field='datado', title='Data rejestracji do', default='KZM'),
    Switch(field='badania', title='Rozbij na badania'),
    Switch(field='pracownie', title='Rozbij na pracownie'),
    Switch(field='aparaty', title='Rozbij na aparaty'),
    Switch(field='typyzlecen', title='Rozbij na typy zleceń'),
    Switch(field='bezkontroli', title='Bez kontrolnych')
))

ROZBICIA = {
    'badania': [
        ('trim(b.symbol)', 'Badanie'),
        ('b.czasmaksymalny', 'Czas maksymalny'),
    ],
    'pracownie': [
        ('trim(pr.symbol)', 'Pracownia'),
    ],
    'aparaty': [
        ('trim(ap.symbol)', 'Aparat'),
    ],
    'typyzlecen': [
        ('trim(tz.symbol)', 'Typ zlecenia'),
    ],
}

KOL_CZASY_TYT = [
    "Rej.-przyj.",
    "Rej.-zatw.",
    "Pob.-zatw.",
    "Przyj.-zatw.",
    "Rej.-wydr.",
    "Pobr.-wydr.",
    "Przyj.-wydr.",
    "Pobr.-rej.",
]

KOL_CZASY_FB = """
    avg(cast (((w.dystrybucja - w.GodzinaRejestracji) * 24) as decimal(18,1))),
    avg(cast (((w.zatwierdzone - w.GodzinaRejestracji) * 24) as decimal(18,1))),
    avg(cast (((w.zatwierdzone - w.Godzina) * 24) as decimal(18,1))),
    avg(cast (((w.zatwierdzone - w.dystrybucja) * 24) as decimal(18,1))),
    avg(cast (((w.wydrukowane - w.GodzinaRejestracji) * 24) as decimal(18,1))),
    avg(cast (((w.wydrukowane - w.Godzina) * 24) as decimal(18,1))),
    avg(cast (((w.wydrukowane - w.dystrybucja) * 24) as decimal(18,1))),
    avg(cast (((w.GodzinaRejestracji - w.Godzina) * 24) as decimal(18,1)))
"""

KOL_CZASY_PG = """
    cast(avg(cast (((extract(epoch from w.dystrybucja)-extract(epoch from w.GodzinaRejestracji)) / 3600) as decimal(18,0))) as decimal(18,1)),
    cast(avg(cast (((extract(epoch from w.zatwierdzone)-extract(epoch from w.GodzinaRejestracji)) / 3600) as decimal(18,0))) as decimal(18,1)),
    cast(avg(cast (((extract(epoch from w.zatwierdzone)-extract(epoch from w.Godzina)) / 3600) as decimal(18,0))) as decimal(18,1)),
    cast(avg(cast (((extract(epoch from w.zatwierdzone)-extract(epoch from w.dystrybucja)) / 3600) as decimal(18,0))) as decimal(18,1)),
    cast(avg(cast (((extract(epoch from w.wydrukowane)-extract(epoch from w.GodzinaRejestracji)) / 3600) as decimal(18,0))) as decimal(18,1)),
    cast(avg(cast (((extract(epoch from w.wydrukowane)-extract(epoch from w.Godzina)) / 3600) as decimal(18,0))) as decimal(18,1)),
    cast(avg(cast (((extract(epoch from w.wydrukowane)-extract(epoch from w.dystrybucja)) / 3600) as decimal(18,0))) as decimal(18,1)),
    cast(avg(cast (((extract(epoch from w.GodzinaRejestracji)-extract(epoch from w.Godzina)) / 3600) as decimal(18,0))) as decimal(18,1))
"""

SQL = """
    select $ROZBICIA$ count(w.id) as ilosc, $CZASY$
    from wykonania w 
    left join badania b on b.id=w.badanie
    left join pracownie pr on pr.id=w.pracownia
    left join aparaty ap on ap.id=w.aparat
    left join zlecenia zl on zl.id=w.zlecenie
    left join typyzlecen tz on tz.id=zl.typzlecenia
    where w.zatwierdzone between ? and ? and w.bladwykonania is null
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    validate_date_range(params['dataod'], params['datado'], 31)
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
    rozbicia = []
    kolumny = []
    for roz, pola in ROZBICIA.items():
        if params[roz]:
            for (pole, tytul) in pola:
                rozbicia.append(pole)
                kolumny.append(tytul)
    kolumny += ['Ilość'] + KOL_CZASY_TYT
    sql = SQL
    if len(rozbicia) > 0:
        sql = sql.replace('$ROZBICIA$', ','.join(rozbicia) + ',')
        kol_go = ','.join([str(i + 1) for i in range(len(rozbicia))])
        sql += ' group by %s order by %s' % (kol_go, kol_go)
    else:
        sql = sql.replace('$ROZBICIA$', '')
    if params['bezkontroli']:
        sql = sql.replace('w.bladwykonania is null', 'w.bladwykonania is null and tz.symbol not in (\'K\',\'KW\',\'KZ\') and zl.pacjent is not null and w.platnik not in (select id from platnicy where symbol like \'%KONT%\')')
    with get_centrum_connection(task_params['target']) as conn:
        if conn.db_engine == 'postgres':
            sql = sql.replace('$CZASY$', KOL_CZASY_PG)
        else:
            sql = sql.replace('$CZASY$', KOL_CZASY_FB)
        cols, rows = conn.raport_z_kolumnami(sql, [params['dataod'], params['datado']])
    return {
        'type': 'table',
        'header': kolumny,
        'data': prepare_for_json(rows),
    }
