from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Switch, Radio, ValidationError
from tasks import TaskGroup, Task
from helpers import prepare_for_json, get_centrum_connection

MENU_ENTRY = 'Wykaz notatek'

REQUIRE_ROLE = ['L-KIER', 'L-PRAC', 'H-ROZL']

LAUNCH_DIALOG = Dialog(title="Wykaz wybranych notatek: wewnętrznych, drukowanych lub komentarzy", panel=VBox(
    InfoText(
        text='Określ zakres wykonywanego raportu'),
    HBox(VBox(
        DateInput(field='oddnia', title='Data początkowa', default='PZM'),
        DateInput(field='dodnia', title='Data końcowa', default='KZM'),
        Switch(field='tylkoniezamkniete', title='Tylko niewykonane (bez względu na datę)'),
        Switch(field='aparaty', title='Pokaż aparaty')
        # TODO: blokowanie dat switchem
    ), VBox(
        LabSelector(multiselect=False, field='laboratorium', title='Laboratorium', pokaz_nieaktywne=True),
        TextInput(field='platnik', title='Część wspólna w symbolu płatnika'),
    ), VBox(
        InfoText(text='Jaki wykaz chcesz uzyskać'),
        Radio(field='typ_notatki', desc_title='Wykaz', values={
            'komentarz': 'Komentarzy',
            'notwew': 'Notatek Wewnętrznych',
            'notzew': 'Notatek Zewnętrznych (drukowanych)'
        }, default='komentarz'),
    )),
))


def start_report(params):  # TODO: chyba permissions sprawdzamy albo w api albo oddzielną funkcją
    # TODO: zwracać jakiś identyfikator, po którym będzie się można do tego dostać
    params = LAUNCH_DIALOG.load_params(params)
    print('startReport', __PLUGIN__, params)
    report = TaskGroup(__PLUGIN__, params)
    if params['laboratorium'] is None:
        raise ValidationError("Nie wybrano laboratorium")
    task = {
        'type': 'centrum',
        'priority': 1,
        'target': params['laboratorium'],
        'params': params,
        'function': 'do_report'
    }
    report.create_task(task)
    report.save()
    return report


def do_report(task_params):
    params = task_params['params']
    sql = """
    	select 
    		z.numer as NR,
    		z.datarejestracji as DATA,
    		z.kodkreskowy,
    		z.ZewnetrznyIdentyfikator,
    		o.symbol as PP,
    		pl.symbol as PL,
    		T.Symbol AS TZ,
    		(PC.Nazwisko || ' ' || PC.Imiona || ' ' || coalesce(cast(PC.PESEL as varchar(20)),'')) as PACJENT,  
    		(L.Nazwisko || ' ' || L.Imiona) AS LEKARZ,
    		z.opis as OPIS,
    		z.KOMENTARZ as KOM """
    if params['aparaty']:
        sql += " ,list(distinct ap.symbol) as aparaty "
    sql += """
    	from zlecenia z 
    		left outer join ODDZIALY o on o.id =z.ODDZIAL   
    		left outer JOIN Pacjenci PC on PC.ID = Z.PACJENT
    		left outer JOIN TypyZlecen T ON T.ID = Z.TypZlecenia
    		left outer join Lekarze L on Z.Lekarz = L.ID
    		left outer JOIN Platnicy PL on z.Platnik = PL.ID"""
    if params['aparaty']:
        sql += """ left join wykonania w on w.zlecenie=z.id
    		left join aparaty ap on ap.id=w.aparat """
    sql += " WHERE "
    sql_params = []
    if params['tylkoniezamkniete']:
        sql += "z.pozamknieciu ='0' and "
    else:
        sql += "Z.DataRejestracji BETWEEN ? and ? and "
        sql_params.append(params['oddnia'])
        sql_params.append(params['dodnia'])
    if (params['platnik'] or '').strip() != '':
        sql += ' pl.symbol like ? and '
        sql_params.append('%' + params['platnik'].strip().upper() + '%')
    if params['typ_notatki'] == 'komentarz':
        sql += " z.komentarz <> ''"
    else:
        sql += "(z.opis not like '$&' and z.opis <> '') "
    sql += " and t.symbol <> 'K' and pc.nazwisko is not null "
    if params['aparaty']:
        sql += "  GROUP BY 1,2,3,4,5,6,7,8,9,10,11 "
    sql += " ORDER BY Z.DataRejestracji, Z.Numer "

    res = []
    with get_centrum_connection(task_params['target']) as conn:
        for row in conn.raport_slownikowy(sql, sql_params):
            notatka = ''
            if params['typ_notatki'] == 'komentarz':
                notatka = row['kom']
            else:
                opis = (row['opis'] or '').split('$&')
                if params['typ_notatki'] == 'notzew':
                    notatka = opis[0]
                elif params['typ_notatki'] == 'notwew':
                    notatka = opis[1] if len(opis) > 1 else ''
            res_row = [row['data'], row['nr'], row['kodkreskowy'], row['zewnetrznyidentyfikator'], row['tz'],
                row['pl'], row['pp'], row['pacjent'], row['lekarz']]
            if params['aparaty']:
                res_row.append(row['aparaty'])
            res_row.append(notatka)
            res.append(res_row)
    header = 'Data Rejestracji,Numer,Kod kreskowy,Nr zewn.,Typ zlecenia,Płatnik,Zleceniodawca,Pacjent,Lekarz'.split(',')
    if params['aparaty']:
        header.append('Aparaty')
    header.append('Wybrany typ notatek')
    return {
        'results': [
            {
                'type': 'table',
                'header': header,
                'data': prepare_for_json(res)
            }
        ],
        'actions': ['xlsx', 'pdf'],
    }

# kod kreskowy, nr zew, aparat