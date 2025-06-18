from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError
from tasks import TaskGroup, Task
from helpers import prepare_for_json, generate_barcode_img_tag, get_centrum_connection
from datasources.ick import IckDatasource
import random
import string

MENU_ENTRY = 'Rabaty jednorazowe'

RABATY = {
    '5%RMAR': 'Rabat 5%',
    '10%RMAR': 'Rabat 10%',
    '15%RMAR': 'Rabat 15%',
    '20%RMAR': 'Rabat 20%',
    '25%RMAR': 'Rabat 25%',
    '30%RMAR': 'Rabat 30%',
    '35%RMAR': 'Rabat 35%',
    '40%RMAR': 'Rabat 40%',
    '45%RMAR': 'Rabat 45%',
    '50%RMAR': 'Rabat 50%',
    'VOUCHER': 'Rabat 100% (VOUCHER)',
}

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    TabbedView(field='tab', children=[
        Tab(title='Nowy kod rabatowy', value='nowy', panel=VBox(
            InfoText(
                text='Wybierz rabat dla pacjenta, a w pole uwagi wpisz powód wystawienia kodu rabatowego. Powody będą widoczne tylko w zestawieniu wystawionych kodów.'),
            Select(field="statuspacjenta", title="Status pacjenta", values=RABATY, default='10%RMAR'),
            TextInput(field="uwagi", title="Uwagi")
        )),
        Tab(title='Sprawdź kod', value='sprawdz', panel=VBox(
            TextInput(field="kod", title="Kod rabatowy")
        )),
        Tab(title='Zestawienie', value='zestawienie', panel=VBox(
            InfoText(
                text='Zestawienie kodów rabatowych można wykonać wg daty wygenerowania kodów (wtedy będą widoczne również kody niewykorzystane) albo wg daty użycia kodów w punktach. Aby uzyskać szczegóły zlecenia, do którego użyto danego kodu, należy go sprawdzić w zakładce "Sprawdź kod".'),
            DateInput(field='dataod', title='Data początkowa', default='PZM'),
            DateInput(field='datado', title='Data końcowa', default='KZM'),
            Radio(field="wariant", values={
                "generacja": "Wg daty wygenerowania kodów",
                "uzycie": "Wg daty użycia kodów"
            }, default="generacja")
        ))
    ]),
))


def start_report(params, user_login):
    params = LAUNCH_DIALOG.load_params(params)
    print('startReport', __PLUGIN__, params)
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'ick',
        'priority': 1,
        'params': params,
        'user': user_login,
    }
    if params['tab'] == 'nowy':
        if params['statuspacjenta'] == 'VOUCHER' and user_login not in ('mkra', 'dciba'):
            raise ValidationError("Nie możesz wystawić tego rabatu")
        task['function'] = 'nowy_kod_rabatowy'
        task['priority'] = 0
    elif params['tab'] == 'sprawdz':
        task['function'] = 'sprawdz_kod_rabatowy'
    elif params['tab'] == 'zestawienie':
        task['function'] = 'zestawienie_kodow'
    else:
        raise ValidationError('Nieprawidłowy wybór')
    report.create_task(task)
    report.save()
    return report


def nowy_kod_rabatowy(task_params):
    params = task_params['params']
    ick = IckDatasource(read_write=True)
    nazwa_statusu = RABATY[params['statuspacjenta']]
    kod = None
    while kod is None:
        kod = 'R' + ''.join(random.choice(string.ascii_uppercase) for i in range(9))
        for row in ick.dict_select("select id from zlecenia where zleceniodawca='RABAT' and kod_zlecenia=%s", [kod]):
            kod = None
    zlec = {
        'zleceniodawca': 'RABAT',
        'kod_zlecenia': kod,
        'identyfikator': kod,  # Tu może być coś dłuższego - do celów śledczych
        'platne': True,
        'wycofane': False,
        'badania': '',
        'status_pacjenta': params['statuspacjenta'],
        'uwagi_wewnetrzne': params['uwagi'],
        'pracownik': task_params['user'],
        'ts_utw': 'NOW',
    }
    zlec_id = ick.insert('zlecenia', zlec)
    if zlec_id is not None:
        ick.commit()
        html = '<div><p>Wygenerowano kod rabatowy %s. Przekaż go pacjentowi. Poniższą informację wraz z kodem kreskowym możesz wysłac e-mailem.</p>' % nazwa_statusu
        html += '<p style="font-size: 1.2em">Twój jednorazowy kod rabatowy %s to <strong>%s</strong>.<br />' % (
            nazwa_statusu, kod)
        html += 'Pokaż go w dowolnym punkcie pobrań Alab Laboratoria przed rejestracją zlecenia aby otrzymać rabat.<br />'
        html += '<table style="text-align: center"><tbody>'
        html += '<tr><td>%s</td></tr>' % generate_barcode_img_tag(kod)
        html += '<tr><td>%s</td></tr>' % kod
        html += '</tbody></table></p>'
        html += '</div>'
        return {
            'type': 'html',
            'html': html
        }
    else:
        return {'type': 'html', 'html': 'Wystąpił błąd'}


def sprawdz_kod_rabatowy(task_params):
    params = task_params['params']
    ick = IckDatasource()
    res = ick.dict_select("select * from zlecenia where zleceniodawca='RABAT' and kod_zlecenia=%s", [params['kod']])
    if len(res) == 0:
        return {
            'type': 'warning',
            'text': 'Nie znaleziono kodu rabatowego'
        }
    dane = res[0]
    rows = [
        {'title': 'Kod rabatowy', 'value': dane['kod_zlecenia']},
        {'title': 'Wygenerowany', 'value': dane['ts_utw']},
        {'title': 'Wygenerowany przez', 'value': dane['pracownik']}
    ]
    if dane['ts_rej'] is not None:
        rows.append({'title': 'Wykorzystany', 'value': dane['ts_rej']})
        if dane['ic_system'] is not None:
            zl_id = dane['ic_id']
            rows.append({'title': 'Laboratorium', 'value': dane['ic_system']})
            with get_centrum_connection(dane['ic_system'], fresh=True) as conn:
                res = conn.raport_slownikowy("""select z.kodkreskowy, z.numer, z.datarejestracji, zl.symbol, zl.nazwa,
                    st.symbol as stsymbol, st.nazwa as stnazwa,
                    pr.nazwisko as pracownik,
                    kan.symbol as ksymbol,
                    kan.nazwa as knazwa,
                    (cast(list(distinct(trim(b.symbol)), ' ') as varchar(2000))) as badania,
                    sum(coalesce(wyk.cena, 0)) as cena
                    from zlecenia z
                    left join oddzialy zl on zl.id=z.oddzial
                    left join statusypacjentow st on st.id=z.statuspacjenta
                    left outer join wykonania wyk on wyk.zlecenie=z.id
                    left join pracownicy pr on pr.id=z.pracownikodrejestracji
                    left join kanaly kan on kan.id=pr.kanalinternetowy
                    left join badania b on b.id=wyk.badanie
                    where z.id=?
                    group by 1,2,3,4,5,6,7,8,9,10""", [zl_id])
                if len(res) > 0:
                    zl = res[0]
                    rows.append({'title': 'Zleceniodawca', 'value': '%s - %s' % (zl['symbol'], zl['nazwa'])})
                    rows.append({'title': 'Kanał', 'value': '%s - %s' % (zl['ksymbol'], zl['knazwa'])})
                    rows.append({'title': 'Rejestrator', 'value': zl['pracownik']})
                    rows.append({'title': 'Status pacjenta', 'value': '%s - %s' % (zl['stsymbol'], zl['stnazwa'])})
                    rows.append({'title': 'Nr i data zlecenia', 'value': '%s / %s' % (zl['numer'], zl['datarejestracji'])})
                    rows.append({'title': 'Kod kreskowy zlecenia', 'value': zl['kodkreskowy']})
                    rows.append({'title': 'Badania', 'value': zl['badania']})
                    rows.append({'title': 'Cena', 'value': zl['cena']})
    else:
        rows.append({'value': 'Kod nie został jeszcze wykorzystany'})
    return {
        'type': 'vertTable',
        'data': prepare_for_json(rows)
    }


def zestawienie_kodow(task_params):
    params = task_params['params']
    ick = IckDatasource()
    sql = """select kod_zlecenia, ts_utw, status_pacjenta, pracownik, uwagi_wewnetrzne, ts_rej, ic_system from zlecenia where zleceniodawca='RABAT'"""
    if params['wariant'] == 'generacja':
        sql += " and ts_utw between %s and %s "
    elif params['wariant'] == 'uzycie':
        sql += " and ts_rej between %s and %s "
    else:
        raise ValidationError('wariant')
    sql += " order by ts_utw, ts_rej"
    cols, rows = ick.select(sql, [params['dataod'], params['datado']])
    return {
        'type': 'table',
        'header': 'Kod rabatowy,Utworzony,Rabat,Pracownik,Uwagi,Wykorzystany,Wykorzystany w lab.'.split(','),
        'data': prepare_for_json(rows)
    }


# RNPMXNKDAL
