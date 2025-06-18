from datasources.snrkonf import SNRKonf
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Radio, ValidationError, Switch
from tasks import TaskGroup, Task
from outlib.xlsx import ReportXlsx
from helpers import prepare_for_json, slugify
from datasources.snr import SNR
import base64
import datetime

MENU_ENTRY = 'Ceny obowiązujące'

ADD_TO_ROLE = ['R-DYR', 'C-CS', 'R-PM']

LAUNCH_DIALOG = Dialog(title='Eksport cen obowiązujących z SNR', panel=VBox(
    InfoText(text='W przypadku eksportu po symbolach można podać symbole w postaci PŁATNIK:ZLECENIODAWCA jeśli są potrzebne cenniki dla konkretnych zleceniodawców'),
    TextInput(field='umowy', title='Umowy (oddzielone spacjami)', textarea=True),
    TextInput(field='symbole',
              title='lub symbole (oddzielone spacjami), przy podaniu symboli eksporty na konkretne laby',
              textarea=True),
    DateInput(field='data', title='Data obowiązywania', default='T'),
    Switch(field='pominzle', title='Pomiń badania techniczne i pakiety', default=True),
), hide_download=True)

SQL_POJEDYNCZEGO = """
    select ocirp.badanie as "Badanie", ocirp.nazwa as "Nazwa", ocirp.cenadlaplatnika as "Cena dla płatnika",
    case when ocirp.pozaumowa then 'T' else '' end as "Poza umową",
    um.identyfikatorwrejestrze as "Umowa", um.datawystawienia as "Umowa wystawiona", um.oddnia as "Umowa od", um.dodnia as "Umowa do",
    an.identyfikatorwrejestrze as "Aneks", an.datawystawienia as "Aneks wystawiony", an.oddnia as "Aneks od", an.dodnia as "Aneks do",
    case when ocirp.cennik is not null then ocirp.cennik || ' - ' || cen.nazwa else null end as "Cennik",
    ocirp.materialy as "Materiały", ocirp.typyzlecen as "Typy zleceń", ocirp.analizatory as "Analizatory"
    
    from podajobowiazujacecenyiregulyplatnika(%s, %s, %s, %s) ocirp
    left join umowy um on um.id=ocirp.umowa
    left join umowy an on an.id=ocirp.aneks
    left join cenniki cen on cen.symbol=ocirp.cennik
    order by ocirp.kolejnosc
"""

SQL_BADANIA = """
    select trim(symbol) as symbol, nazwa, 
    trim(hs->'grupa') as grupa, trim(hs->'grupadorejestracji') as grupadorejestracji,
	trim(hs->'rodzaj') as rodzaj,
	hs->'pakiet'
    from badania
    where not del
    order by symbol
"""


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)
    umowy = []
    symbole = []
    for (fld, val_list) in zip(['umowy', 'symbole'], [umowy, symbole]):
        if params[fld] is not None:
            values = params[fld].replace("\r\n", "\n").replace("\n", " ").replace(",", " ").upper().split(" ")
            for val in values:
                if len(val) > 0:
                    val_list.append(val)
    if len(umowy) + len(symbole) == 0:
        raise ValidationError("Nie podano żadnej umowy ani symbolu")
    if params['data'] is None:
        raise ValidationError("Nie podano daty obowiązywania")
    for (fld, val_list) in zip(['umowy', 'symbole'], [umowy, symbole]):
        for val in val_list:
            task = {
                'type': 'snr',
                'priority': 1,
                'params': {
                    'tryb': fld,
                    'szukaj': val,
                    'data': params['data'],
                    'pominzle': params['pominzle'],
                },
                'function': 'raport_pojedynczy',
            }
            report.create_task(task)
    report.save()
    return report


def raport_pojedynczy(task_params):
    params = task_params['params']
    snr = SNRKonf()
    platnicy = []
    dane_platnikow = {}
    res = []
    pomin_badania = []
    if params['pominzle']:
        for row in snr.dict_select(SQL_BADANIA):
            if row['grupa'] in ['PAKIET', 'TECHNIC'] or row['rodzaj'] == 'P':
                pomin_badania.append(row['symbol'])
    if params['tryb'] == 'umowy':
        for row in snr.dict_select("""select id, nazwa, nip, hs->'umowa' as umowa 
                from platnicy where not del and hs->'umowa'=%s""", [params['szukaj']]):
            platnicy.append((row['id'], None))
            dane_platnikow[row['id']] = (row['nazwa'], row['nip'], row['umowa'], None)
    elif params['tryb'] == 'symbole':
        platnik = params['szukaj']
        zleceniodawca = None
        if ':' in platnik:
            tab = platnik.split(':')
            platnik = tab[0]
            zleceniodawca = tab[1]
        id_zleceniodawcy = None
        for row in snr.dict_select("""select pl.id, pl.nazwa, pl.nip, pl.hs->'umowa' as umowa, pwl.laboratorium
                from platnicywlaboratoriach pwl 
                left join platnicy pl on pl.id=pwl.platnik
                where not pwl.del and pwl.symbol=%s""", [platnik]):
            nazwa_zleceniodawcy = None
            for subrow in snr.dict_select("""select zl.id, zl.nazwa from zleceniodawcywlaboratoriach zwl
                left join zleceniodawcy zl on zl.id=zwl.zleceniodawca
                where zwl.symbol=%s and zwl.laboratorium=%s and zl.platnik=%s""", [zleceniodawca, row['laboratorium'], row['id']]):
                    id_zleceniodawcy = subrow['id']
                    nazwa_zleceniodawcy = subrow['nazwa']
            ident = row['id']
            if id_zleceniodawcy is not None:
                ident += ':' + id_zleceniodawcy
            platnicy.append((ident, row['laboratorium']))
            dane_platnikow[ident] = (row['nazwa'], row['nip'], row['umowa'], nazwa_zleceniodawcy)
    else:
        res.append({
            'type': 'error',
            'text': 'Nieznany tryb wyszukiwania',
        })
    if len(platnicy) == 0:
        res.append({
            'type': 'error',
            'text': 'Nie znaleziono płatnika %s' % params['szukaj'],
        })
    else:
        for i, (platnik, lab) in enumerate(platnicy):
            if len(platnicy) == 1:
                fn = 'CenyObowiazujace_%s_%s.xlsx' % (slugify(params['szukaj']).upper(), params['data'])
            else:
                fn = 'CenyObowiazujace_%s_%s_%d.xlsx' % (slugify(params['szukaj']).upper(), params['data'], i + 1)
            if ':' in platnik:
                [id_platnik, id_zleceniodawca] = platnik.split(':')
            else:
                id_platnik = platnik
                id_zleceniodawca = None
            cols, all_rows = snr.select(SQL_POJEDYNCZEGO, [id_platnik, params['data'], id_zleceniodawca, lab])
            rows = []
            for row in all_rows:
                if row[0] not in pomin_badania:
                    rows.append(row)
            if len(rows) > 0:
                info = 'Ceny obowiązujące dla %s - %s - %s - %s dnia %s' % (dane_platnikow[platnik] + (params['data'],))
                if lab is not None:
                    info += ' (lab %s)' % lab
                rep = ReportXlsx({'results': [
                    {
                        'type': 'info',
                        'text': info,
                    },
                    {
                        'type': 'table',
                        'header': cols,
                        'data': prepare_for_json(rows),
                        'params': prepare_for_json(params)
                    }]})
                res.append({
                    'type': 'download',
                    'content': base64.b64encode(rep.render_as_bytes()).decode(),
                    'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'filename': fn,
                })
            else:
                kom = 'Płatnik %s' % params['szukaj']
                if lab is not None:
                    kom += ' (lab %s)' % lab
                kom += ' - brak cen'
                res.append({
                    'type': 'warning',
                    'text': kom,
                })
    return res
