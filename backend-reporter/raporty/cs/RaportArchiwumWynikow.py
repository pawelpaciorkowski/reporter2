import base64
import io

from dialog import Dialog, VBox, HBox, InfoText, TextInput, Select, Button, DynamicSelect
from tasks import TaskGroup
from helpers import prepare_for_json
from datasources.postgres import PostgresDatasource
from config import Config
from flask import send_file

MENU_ENTRY = 'Raport Archiwum Wyników (Multisync)'

LAUNCH_DIALOG = Dialog(title=MENU_ENTRY, panel=VBox(
    InfoText(text="Wyszukaj wyniki po podanych danych. Uwaga na ilość danych!"),
    HBox(
        VBox(
            TextInput(field="pacjent_query", title="Imię, Nazwisko, PESEL lub Data urodzenia (po przecinkach)", required=False),
            TextInput(field="zlecenie_data_od", title="Data zlecenia od (RRRR-MM-DD)", required=False),
            TextInput(field="zlecenie_data_do", title="Data zlecenia do (RRRR-MM-DD)", required=False),
        ),
        VBox(
            TextInput(field="zlecenie_kod_kreskowy", title="Kod kreskowy zlecenia", required=False),
            TextInput(field="lekarz_imie", title="Imię Lekarza", required=False),
            TextInput(field="lekarz_nazwisko", title="Nazwisko Lekarza", required=False),
            TextInput(field="zleceniodawca_nazwa", title="Nazwa Zleceniodawcy", required=False),
            TextInput(field="zleceniodawca_kod_lsi", title="Kod LSI Zleceniodawcy", required=False),
            TextInput(field="zleceniodawca_nip", title="NIP Zleceniodawcy", required=False),
        ),
        VBox(
            DynamicSelect(field="generate_pdf", title="Czy wygenerować PDF?", required=False, default='nie', options=[]),
            DynamicSelect(field="pdf_mode", title="Rodzaj PDF-a", required=False, default='single', options=[]),
            TextInput(field="selected_ids", title="Wybrane ID (przecinek oddzielone)", required=False),
        )
    )
))


def get_generate_pdf_options(params):
    return [
        {"label": "Nie", "value": "nie"},
        {"label": "Tak", "value": "tak"},
    ]

def get_pdf_mode_options(params):
    return [
        {"label": "Osobne PDF-y", "value": "single"},
        {"label": "Zbiorczy PDF", "value": "combined"},
    ]

def assign_widget_data(dialog):
    for field_name in ["generate_pdf", "pdf_mode"]:
        widget = dialog.get_field_by_name(field_name)
        if widget is not None:
            if field_name == "generate_pdf":
                widget.get_widget_data = get_generate_pdf_options
            elif field_name == "pdf_mode":
                widget.get_widget_data = get_pdf_mode_options

assign_widget_data(LAUNCH_DIALOG)


def start_report(params):
    if params.get('action') == 'clear_filters':
        return {"type": "clear"}

    params = LAUNCH_DIALOG.load_params(params)
    report = TaskGroup(__PLUGIN__, params)

    task = {
        'type': 'ick',
        'priority': 0,
        'params': params,
        'function': 'raport',
    }
    report.create_task(task)
    report.save()
    return report


def raport(task_params):
    db = PostgresDatasource(Config.DATABASE_MULTISYNC2)
    params = task_params.get('params', {})

    generate_pdf = params.get('generate_pdf') == 'tak'
    selected_ids = params.get('selected_ids')

    print(f"Received params: {params}")  # Logowanie wszystkich parametrów
    print(f"Selected IDs received in backend: {selected_ids}")  # Logowanie selected_ids

    if generate_pdf:
        if not selected_ids:
            return {"type": "info", "text": "Nie wybrano żadnych ID do pobrania PDF-a."}
        
        ids = [int(id_.strip()) for id_ in selected_ids.split(',') if id_.strip().isdigit()]
        if not ids:
            return {"type": "info", "text": "Brak prawidłowych ID do pobrania."}

        pdf_mode = params.get("pdf_mode", "single")

        try:
            if pdf_mode == "combined":
                # Jeden PDF zbiorczy
                pdf_result = db.dict_select('SELECT wynikowe_dane.generuj_pdf_z_wynikami(%s) AS pdf_base64', [ids])
                if not pdf_result or not pdf_result[0].get('pdf_base64'):
                    return {"type": "info", "text": "Nie udało się wygenerować PDF-a lub brak danych."}

                return {
                    "type": "base64file",
                    "filename": "raport_wyniki.pdf",
                    "content": pdf_result[0]['pdf_base64'],
                    "mimetype": "application/pdf",
                }

            elif pdf_mode == "single":
                files = []
                for id_ in ids:
                    result = db.dict_select('SELECT wynikowe_dane.generuj_pdf_z_wynikami(%s) AS pdf_base64', [[id_]])
                    if result and result[0].get("pdf_base64"):
                        files.append({
                            "filename": f"raport_{id_}.pdf",
                            "content": result[0]['pdf_base64'],
                            "mimetype": "application/pdf"
                        })

                if not files:
                    return {"type": "info", "text": "Nie udało się wygenerować żadnego PDF-a."}

                if len(files) == 1:
                    return files[0]

                import zipfile
                import tempfile
                import os

                with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
                    with zipfile.ZipFile(tmp_zip.name, 'w') as zipf:
                        for file in files:
                            decoded = base64.b64decode(file['content'])
                            zipf.writestr(file['filename'], decoded)

                    tmp_zip.seek(0)
                    with open(tmp_zip.name, "rb") as f:
                        zip_content = f.read()

                    os.unlink(tmp_zip.name)

                return {
                    "type": "base64file",
                    "filename": "raporty_wyniki.zip",
                    "content": base64.b64encode(zip_content).decode("utf-8"),
                    "mimetype": "application/zip"
                }

            else:
                return {"type": "info", "text": f"Nieznany tryb PDF: {pdf_mode}"}

        except Exception as e:
            return {"type": "info", "text": f"Błąd podczas generowania PDF-a: {e}"}


    conditions = []
    values = []
    
    
    if not generate_pdf and not any([
        params.get('pacjent_query'),
        params.get('zlecenie_data_od'),
        params.get('zlecenie_data_do'),
        params.get('zlecenie_kod_kreskowy'),
        params.get('lekarz_imie'),
        params.get('lekarz_nazwisko'),
        params.get('zleceniodawca_nazwa'),
        params.get('zleceniodawca_kod_lsi'),
        params.get('zleceniodawca_nip')
    ]):
     return {"type": "info", "text": "Musisz podać przynajmniej jeden filtr, aby uruchomić wyszukiwanie."}


    search_terms = []
    if params.get('pacjent_query'):
        search_terms = [term.strip() for term in params['pacjent_query'].split(',') if term.strip()]

    for term in search_terms:
        if term.isdigit() and len(term) == 11:
            conditions.append('pacjent_pesel = %s')
            values.append(term)
        elif '-' in term and len(term) == 10:
            conditions.append('pacjent_data_urodzenia = %s')
            values.append(term)
        else:
            conditions.append('(pacjent_imie ILIKE %s OR pacjent_nazwisko ILIKE %s)')
            values.append(f"%{term}%")
            values.append(f"%{term}%")

    if params.get('zlecenie_kod_kreskowy'):
        conditions.append('zlecenie_kod_kreskowy = %s')
        values.append(params['zlecenie_kod_kreskowy'])
    if params.get('lekarz_imie'):
        conditions.append('lekarz_imie ILIKE %s')
        values.append(f"%{params['lekarz_imie']}%")
    if params.get('lekarz_nazwisko'):
        conditions.append('lekarz_nazwisko ILIKE %s')
        values.append(f"%{params['lekarz_nazwisko']}%")
    if params.get('zleceniodawca_nazwa'):
        conditions.append('zleceniodawca_nazwa ILIKE %s')
        values.append(f"%{params['zleceniodawca_nazwa']}%")
    if params.get('zleceniodawca_kod_lsi'):
        conditions.append('zleceniodawca_kod_lsi = %s')
        values.append(params['zleceniodawca_kod_lsi'])
    if params.get('zleceniodawca_nip'):
        conditions.append('zleceniodawca_nip = %s')
        values.append(params['zleceniodawca_nip'])
    if params.get('zlecenie_data_od'):
        conditions.append('zlecenie_data >= %s')
        values.append(params['zlecenie_data_od'])
    if params.get('zlecenie_data_do'):
        conditions.append('zlecenie_data <= %s')
        values.append(params['zlecenie_data_do'])

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    sql = f'SELECT * FROM wynikowe_dane.wyniki {where_clause} LIMIT 1000'
    results = db.dict_select(sql, values)

    if not results:
        return {"type": "info", "text": "Brak danych w wyniku zapytania."}

    header = [
        'ID', 'Tabela źródłowa', 'Laboratorium', 'Dane zlecenia (RAW)', 'Kod kreskowy zlecenia',
        'Numer wewnętrzny zlecenia (recno)', 'Numer rekordu zlecenia (rekno)', 'Data zlecenia',
        'Imię pacjenta', 'Nazwisko pacjenta', 'Data urodzenia pacjenta', 'PESEL pacjenta',
        'Imię lekarza', 'Nazwisko lekarza', 'Numer lekarza',
        'Kod LSI zleceniodawcy', 'Nazwa zleceniodawcy', 'NIP zleceniodawcy'
    ]

    columns = [
        'id', 'common_table_name', 'laboratorium', 'zlecenie',
        'zlecenie_kod_kreskowy', 'zlecenie_recno', 'zlecenie_rekno', 'zlecenie_data',
        'pacjent_imie', 'pacjent_nazwisko', 'pacjent_data_urodzenia', 'pacjent_pesel',
        'lekarz_imie', 'lekarz_nazwisko', 'lekarz_numer',
        'zleceniodawca_kod_lsi', 'zleceniodawca_nazwa', 'zleceniodawca_nip'
    ]

    data = [[row.get(col) for col in columns] for row in results]

    return {
        "type": "table",
        "header": header,
        "data": prepare_for_json(data)
    }

