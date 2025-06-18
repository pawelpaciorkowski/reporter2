from api.common import get_db
from dialog import Dialog, Panel, HBox, VBox, TextInput, LabSelector, TabbedView, Tab, InfoText, DateInput, \
    Select, Radio, ValidationError, Switch
from tasks import TaskGroup, Task
from helpers import prepare_for_json, clear_to_ascii
from helpers.notifications import send_sms, send_sms_flush_queue
import os
import re
import json
import openpyxl

MENU_ENTRY = 'Alert SMS'
REQUIRE_ROLE = ['C-ADM']
GRUPY = []
LAUNCH_DIALOG = None
CONFIG_FN = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    '..', '..', '..',
    'config_files', 'alert_sms_grupy_odbiorcow.xlsx',
)


def reload():
    global GRUPY, LAUNCH_DIALOG
    info_text = [
        'Wysyłka informacyjnego sms od Grupy Alab do zdefiniowanej grupy odbiorców.',
        'Max długość wiadomości to 160 znaków, polskie litery zostaną zamienione na odpowiedniki ASCII.',
        'Raport domyślnie pokazuje tylko podgląd wiadomości i listę odbiorców, aby wysłać alert zaznacz',
        'pole "Wyślij na prawdę".',
        'Definicje grup odbiorców w pliku /var/www/reporter/config_files/alert_sms_grupy_odbiorcow.xlsx',
        '- jedna zakładka to jedna grupa odbiorców, nazwiska odbiorców z kolumny A, nr tel z B.'
    ]
    bledy = []
    try:
        nowe_grupy = [{'nazwa': '--- WYBIERZ ---'}]

        wb = openpyxl.load_workbook(CONFIG_FN)
        for ws in wb.worksheets:
            grupa = {'nazwa': ws.title, 'odbiorcy': []}
            for i, row in enumerate(list(ws)):
                if len(row) < 2:
                    continue
                if row[0].value is not None:
                    tel = str(row[1].value or '').strip()
                    if not re.match(r'^\d\d\d\d\d\d\d\d\d$', tel):
                        if i == 0:
                            continue
                        bledy.append('%s: %s - nieprawidłowy nr telefonu (%s)' % (ws.title, row[0].value, tel))
                    else:
                        grupa['odbiorcy'].append((row[0].value, tel))
                else:
                    if row[1].value is not None:
                        bledy.append('%s - pozycja bez nazwiska' % ws.title)
            nowe_grupy.append(grupa)
        GRUPY = nowe_grupy
    except Exception as e:
        bledy.append('Błąd importu: %s' % str(e))
    if len(bledy) > 0:
        info_text += ['', 'BŁĘDY KONFIGURACJI:'] + bledy
        info_text += ['', 'jeśli wystąpiły błędy, wczytana konfiguracja może być nieaktualna!']
    LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
        InfoText(text='\n'.join(info_text)),
        TextInput(field="tresc", title="Treść"),
        Select(field="grupa", title="Grupa odbiorców", values=dict([(g['nazwa'], g['nazwa']) for g in GRUPY])),
        Switch(field="wyslij", title="Wyślij na prawdę (bez zaznaczenia - tylko podgląd)"),
        Switch(field="reload", title="Tylko odśwież konfigurację"),
    ))
    return len(bledy) == 0


def init_plugin():
    reload()


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    if params['reload']:
        ok = reload()
        if ok:
            raise ValidationError('Konfiguracja wczytana.')
        else:
            raise ValidationError('KONFIGURACJA WCZYTANA Z BŁĘDAMI - odśwież stronę żeby zobaczyć')
    if params['grupa'] is None or params['grupa'] == '--- WYBIERZ ---':
        raise ValidationError('Wybierz grupę odbiorców')
    for grupa in GRUPY:
        if grupa['nazwa'] == params['grupa']:
            params['odbiorcy'] = grupa['odbiorcy']
    if 'odbiorcy' not in params:
        raise ValidationError('Nie znaleziono grupy %s' % params['grupa'])
    if len(params['odbiorcy']) == 0:
        raise ValidationError('Pusta grupa odbiorców')
    tresc = (params['tresc'] or '').strip()
    tresc = clear_to_ascii(tresc)
    if len(tresc) < 3 or len(tresc) > 160:
        raise ValidationError('Nieprawidłowa długość wiadomości')
    params['tresc'] = tresc
    report = TaskGroup(__PLUGIN__, params)
    task = {
        'type': 'snr',
        'priority': 1,
        'params': params,
        'function': 'wyslij'
    }
    report.create_task(task)
    report.save()
    return report


def wyslij(task_params):
    params = task_params['params']
    na_prawde = params['wyslij']
    res = []
    res.append({
        'type': 'vertTable',
        'title': 'Wysłana wiadomość' if na_prawde else 'Podgląd wiadomości',
        'data': [{'title': 'Treść', 'value': params['tresc']}],
    })
    res.append({
        'type': 'table',
        'title': 'Odbiorcy',
        'header': 'Nazwisko,Nr telefonu'.split(','),
        'data': prepare_for_json(params['odbiorcy']),
    })
    if na_prawde:
        with get_db() as rep_db:
            rep_db.execute("""
                insert into log_zdarzenia(obj_type, obj_id, typ, opis, parametry)
                values('external_alert_sms', 0, 'send', %s, %s)
            """, [
                __PLUGIN__, json.dumps(prepare_for_json({
                    'task_params': task_params,
                }))
            ])
            rep_db.commit()
        for nazwa, tel in params['odbiorcy']:
            send_sms(tel, params['tresc'], send_now=False)
        send_sms_flush_queue()
    return res
