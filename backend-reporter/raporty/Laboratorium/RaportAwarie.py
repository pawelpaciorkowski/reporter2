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
                "": "Filtruj po rodzaju",
                "Sprzęt pomocniczy": "Sprzęt pomocniczy",
                "Sprzęt pomiarowy": "Sprzęt pomiarowy",
                "Wyposażenie dodatkowe": "Wyposażenie dodatkowe",
            },
            required=False,
        ),
        Select(
            field="failure_type",
            title="Typ awarii",
            values={
                "": "Filtruj po typie awarii",
                "Krytyczna": "Krytyczna",
                "Częściowa": "Częściowa",
            },
            required=False,
        ),
        DateInput(field="date_from", title="Data zgłoszenia od", required=False),
        DateInput(field="date_to", title="Data zgłoszenia do", required=False),
    )
)

def start_report(params):
    loaded_params = LAUNCH_DIALOG.load_params(params)

    for field in [
        'model_name', 'symbol', 'serial_number', 'workshop_name',
        'laboratory_name', 'manufacturer', 'device_type', 'failure_type'
    ]:
        value = loaded_params.get(field)
        if isinstance(value, str):
            value = value.strip()
            if value == '':
                value = None
        loaded_params[field] = value

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
        failure_type=params.get('failure_type'),
        date_from=params.get('date_from'),
        date_to=params.get('date_to'),
    ) or ([], [])

    header = [
        'Nazwa urządzenia', 'Symbol', 'Numer seryjny', 'Producent', 'Rodzaj serwisu',
        'Typ awarii',  
        'Data zgłoszenia', 'Data przybycia', 'Data zakończenia', 'Firma serwisująca', 'Koszt',
        'Czas przestoju (godziny)', 'Nr raportu serwisowego', 'Laboratorium',
        'Pracownia', 'Rodzaj sprzętu'
    ]

    data = []
    for row in rows:
        row = list(row)

        data_zgloszenia = row[5]
        data_zakonczenia = row[7]

        # Bezpieczne parsowanie dat - obsługa błędów dla nieprawidłowych formatów
        if isinstance(data_zgloszenia, str):
            try:
                data_zgloszenia = datetime.datetime.fromisoformat(data_zgloszenia)
            except ValueError:
                # Jeśli nie można sparsować daty (np. tekst "Częściowa"), zostaw jako string
                pass
        
        if isinstance(data_zakonczenia, str):
            try:
                data_zakonczenia = datetime.datetime.fromisoformat(data_zakonczenia)
            except ValueError:
                # Jeśli nie można sparsować daty, zostaw jako string
                pass

        # Oblicz czas przestoju tylko jeśli obie daty to obiekty datetime
        if (data_zgloszenia and data_zakonczenia and 
            isinstance(data_zgloszenia, datetime.datetime) and 
            isinstance(data_zakonczenia, datetime.datetime)):
            try:
                downtime_hours = (data_zakonczenia - data_zgloszenia).total_seconds() / 3600
                row[10] = round(downtime_hours, 2)
            except Exception as e:
                print(f"Błąd przy obliczaniu czasu przestoju: {e}")
                row[10] = None
        else:
            # Jeśli nie można obliczyć czasu przestoju (nieprawidłowe daty), ustaw None
            if len(row) > 10:
                row[10] = None

        data.append(row)

    return {
        "type": "table",
        "header": header,
        "data": prepare_for_json(data if data is not None else []),
        "actions": ["xlsx"]
    }