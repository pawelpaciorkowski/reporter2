import datetime
from dialog import Dialog, VBox, TextInput, DateInput, InfoText, Select
from tasks import TaskGroup
from helpers import prepare_for_json
from datasources.awarie import Awarie

MENU_ENTRY = 'Raport awarii urządzeń'

LAUNCH_DIALOG = Dialog(
    title=MENU_ENTRY,
    panel=VBox(
        TextInput(field="model_name", title="Filtruj po nazwie", required=False),
        TextInput(field="symbol", title="Filtruj po symbolu", required=False),
        TextInput(field="serial_number", title="Filtruj po numerze seryjnym", required=False),
        TextInput(field="workshop_name", title="Filtruj po pracowni", required=False),
        TextInput(field="laboratory_name", title="Filtruj po laboratorium", required=False),
        TextInput(field="manufacturer", title="Filtruj po producencie", required=False),
        Select(
            field="device_type",
            title="Rodzaj sprzętu",
            values={
                "": "Filtruj po rodzaju",  # Domyślna opcja: brak wyboru
                "Sprzęt pomocniczy": "Sprzęt pomocniczy",
                "Sprzęt pomiarowy": "Sprzęt pomiarowy",
                "Wyposażenie dodatkowe": "Wyposażenie dodatkowe",
            },
            required=False,
        ),
        DateInput(field="date_from", title="Data zgłoszenia od", required=False),
        DateInput(field="date_to", title="Data zgłoszenia do", required=False),
    )
)

def start_report(params):
    loaded_params = LAUNCH_DIALOG.load_params(params)

    print(f"DEBUG: RAW params before load: {params}")
    print(f"DEBUG: Loaded params from Dialog: {loaded_params}")

    # Pola tekstowe — oczyszczanie z pustych wartości
    text_fields = [
        'model_name', 'symbol', 'serial_number', 'workshop_name',
        'laboratory_name', 'manufacturer', 'device_type'
    ]
    
    for field in [
    'model_name', 'symbol', 'serial_number', 'workshop_name',
    'laboratory_name', 'manufacturer'
    ]:
     value = loaded_params.get(field)
    if isinstance(value, str):
        value = value.strip()
        if value == '':
            value = None
    loaded_params[field] = value

    # Upewniamy się, że device_type jest listą lub None
    device_type = loaded_params.get('device_type')
    if not device_type:
        loaded_params['device_type'] = None

    print(f"DEBUG: Final params used for task: {loaded_params}")

    report = TaskGroup(__PLUGIN__, loaded_params)

    task = {
        'type': 'ick',
        'priority': 0,
        'params': loaded_params,
        'function': 'raport',
    }
    report.create_task(task)
    report.save()

    return report

def raport(task_params):
    print(f"DEBUG: TASK PARAMS W RAPORCIE: {task_params}")

    params = task_params.get('params', {}) if task_params else {}

    awarie = Awarie()

    columns, rows = awarie.lista_awarii(
        model_name=params.get('model_name'),
        symbol=params.get('symbol'),
        serial_number=params.get('serial_number'),
        workshop_name=params.get('workshop_name'),
        laboratory_name=params.get('laboratory_name'),
        manufacturer=params.get('manufacturer'),
        device_type=params.get('device_type'),
        date_from=params.get('date_from'),
        date_to=params.get('date_to'),
    )

    header = [
    'Nazwa urządzenia', 'Symbol', 'Numer seryjny', 'Producent', 'Rodzaj serwisu',
    'Data zgłoszenia', 'Data przybycia', 'Data zakończenia', 'Firma serwisująca', 'Koszt',
    'Czas przestoju (godziny)', 'Nr raportu serwisowego', 'Laboratorium',
    'Pracownia', 'Rodzaj sprzętu'
]


    data = []
    for row in rows:
        row = list(row)

        # Liczymy czas przestoju (data zakończenia - data zgłoszenia)
        data_zgloszenia = row[5]
        data_zakonczenia = row[7]

        if isinstance(data_zgloszenia, str):
            data_zgloszenia = datetime.fromisoformat(data_zgloszenia)
        if isinstance(data_zakonczenia, str):
            data_zakonczenia = datetime.fromisoformat(data_zakonczenia)

        if data_zgloszenia and data_zakonczenia:
            try:
                downtime_hours = (data_zakonczenia - data_zgloszenia).total_seconds() / 3600
                row[10] = round(downtime_hours, 2)
            except Exception as e:
                print(f"Error calculating downtime: {e}")
                row[10] = None
        else:
            row[10] = None


        data.append(row)

    return {
        "type": "table",
        "header": header,
        "data": prepare_for_json(data)
    }
