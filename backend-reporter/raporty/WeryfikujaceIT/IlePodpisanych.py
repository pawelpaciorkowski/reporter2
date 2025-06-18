from datasources.centrum import CentrumWzorcowa
from datasources.snr import SNR
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, PracowniaSelector, TabbedView, Tab, InfoText, \
    DateInput, TimeInput,\
    Select, Radio, ValidationError, Switch, DateTimeInput
from helpers import get_centrum_connection, prepare_for_json, divide_chunks, empty, Kalendarz
from helpers.validators import validate_date_range, validate_symbol
from datasources.snrkonf import SNRKonf
from datasources.helper import HelperDb
from tasks import TaskGroup, Task
import datetime
from helpers.connections import get_centra, get_db_engine

MENU_ENTRY = 'Ile podpisanych'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    LabSelector(field='lab', title='Laboratorium', multiselect=False),
    TextInput(field='fragment', title='Fragment nazwy pliku'),
    DateInput(field='dc_data', title='Wygenerowane od (data)', default='T'),
    TextInput(field='dc_godzina', title='Wygenerowane od (godzina)', default='8:00'),
    Switch(field='wszystkie', title="Pokaż wszystkie pliki")
))

def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    kal = Kalendarz()
    dzis = kal.data('T')
    validate_date_range(params['dc_data'], dzis, 7)
    if empty(params['dc_godzina']):
        params['dc_godzina'] = '0'
    if ':' not in params['dc_godzina']:
        params['dc_godzina'] += ':00'
    if empty(params['fragment']):
        params['fragment'] = None
    czas = '%s %s' % (params['dc_data'], params['dc_godzina'])
    params['dc'] = kal.parsuj_czas(czas).strftime('%Y-%m-%d %H:%M:%S')
    if czas is None:
        raise ValidationError("Nieprawidłowy czas %s" % czas)
    report = TaskGroup(__PLUGIN__, params)
    task = {
        "type": "centrum",
        "priority": 1,
        "target": params['lab'],
        "params": params,
        "function": "raport_lab",
    }
    report.create_task(task)
    report.save()
    return report



def raport_lab(task_params):
    params = task_params['params']
    res = []
    sql = """
        select wwz.plik, wwz.podpisany, wcwz.plik, zl.numer, zl.datarejestracji, zl.kodkreskowy,
            prac.nazwisko, wwz.odebral, wwz.odebrany
        from wydrukiwzleceniach wwz 
        left join wydrukicdawzleceniach wcwz on wcwz.wydruk=wwz.id and wcwz.del=0
        left join zlecenia zl on zl.id=wwz.zlecenie
        left join pracownicy prac on prac.id=coalesce(wwz.pracownikodwydrukowania, wwz.pc)
        where wwz.odebrany >= %s and wwz.del=0
    """
    sql_params = [params['dc']]
    if params['fragment'] is not None:
        sql = sql.replace('and wwz.del=0', 'and wwz.plik like %s and wwz.del=0')
        sql_params.append('%' + params['fragment'] + '%')
    with get_centrum_connection(task_params['target']) as conn:
        _, rows = conn.raport_z_kolumnami(sql, sql_params)
    ile_plikow = 0
    ile_podpisanych = 0
    ile_cda = 0
    braki = []
    for row in rows:
        brak = []
        ile_plikow += 1
        if row[1] == 1:
            ile_podpisanych += 1
        else:
            brak.append('brak podpisu')
        if row[2] is not None:
            ile_cda += 1
        else:
            brak.append('brak CDA')
        if len(brak) > 0 or params['wszystkie']:
            braki.append([row[0], row[6], row[7], row[8], row[3], row[4], row[5], ', '.join(brak)])
    res.append({
        'type': 'vertTable',
        'data': prepare_for_json([
            {'title': 'Ilość wygenerowanych PDF-ów', 'value': str(ile_plikow)},
            {'title': 'Ilość podpisanych', 'value': str(ile_podpisanych)},
            {'title': 'Ilość CDA', 'value': str(ile_cda)},
        ])
    })
    if len(braki) > 0:
        res.append({
            'type': 'table',
            'title': 'Dokumenty' if params['wszystkie'] else 'Dokumenty z problemami',
            'header': 'Plik,Pracownik,Odebrał,Odebrany,Numer zlecenia,Data zlecenia,Kod zlecenia,Problemy'.split(','),
            'data': prepare_for_json(braki)
        })
    return res
