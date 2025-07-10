import base64
import io
import zipfile
import tempfile
import os
import traceback
import math
from PyPDF2 import PdfMerger

from dialog import Dialog, VBox, HBox, InfoText, TextInput, Select, Button, DynamicSelect, DateInput, Switch, DynamicSearch
from tasks import TaskGroup
from helpers import prepare_for_json
from datasources.postgres import PostgresDatasource
from config import Config
from flask import send_file

MENU_ENTRY = 'Raport Archiwum Wynikow Labor(Multisync)'

# --- MODYFIKACJA INTERFEJSU UŻYTKOWNIKA ---
LAUNCH_DIALOG = Dialog(
    title=MENU_ENTRY,
    panel=VBox(
        HBox(
            # Sekcja: Wyszukiwanie po pacjencie lub dacie
            VBox(
                InfoText(text="Dane pacjenta i zakres dat"),
                TextInput(
                    field="pacjent_query",
                    title="Imię, Nazwisko, PESEL lub Data urodzenia (po przecinkach)",
                    required=False
                ),
                HBox(
                    DateInput(field='zlecenie_data_od', title='Data zlecenia od', required=False),
                    DateInput(field='zlecenie_data_do', title='Data zlecenia do', required=False),
                    Switch(field='jeden_dzien', title='Tylko jeden dzień')
                ),
                 DynamicSearch(field='zlecenie_id', title='ID zlecenia (szukaj)', source='/api/gui/search/zlecenia_archiwum', required=False),
            ),

            # Sekcja: Dane zlecenia i lekarza
            VBox(
                InfoText(text="Szczegóły zlecenia i lekarza"),
                TextInput(field="zlecenie_kod_kreskowy", title="Kod kreskowy zlecenia", required=False),
                TextInput(field="lekarz_imie", title="Imię lekarza", required=False),
                TextInput(field="lekarz_nazwisko", title="Nazwisko lekarza", required=False),
                TextInput(field="zleceniodawca_nazwa", title="Nazwa zleceniodawcy", required=False),
                TextInput(field="zleceniodawca_kod_lsi", title="Kod LSI zleceniodawcy", required=False),
                TextInput(field="zleceniodawca_nip", title="NIP zleceniodawcy", required=False),
            ),

            # Sekcja: Generowanie plików i filtry
            VBox(
                InfoText(text="Filtry i ustawienia generowania plików"),
                DynamicSelect(
                    field="dostepne_pliki_filter",
                    title="Dostępność oryginalnych plików",
                    required=False,
                    default="wszystkie",
                    options=[]
                ),
                DynamicSelect(
                    field="filter_pdf_available",
                    title="Dostępny PDF",
                    required=False,
                    default="wszystkie",
                    options=[]
                ),
                DynamicSelect(
                    field="filter_cda_available",
                    title="Dostępny CDA",
                    required=False,
                    default="wszystkie",
                    options=[]
                ),
                DynamicSelect(
                    field="generate_pdf",
                    title="Czy chcesz pobrać pliki z wynikami?",
                    required=False,
                    default="nie",
                    options=[]
                ),
                DynamicSelect(
                    field="pdf_mode",
                    title="Rodzaj PDF-a",
                    required=False,
                    default="single",
                    options=[]
                ),
                TextInput(
                    field="selected_ids",
                    title="Wybrane ID (oddzielone przecinkami)",
                    required=False,
                    help_text="Np. 12345,67890,22222"
                ),
                DynamicSelect(
                    field="typ_pliku",
                    title="Typ dokumentu do pobrania",
                    required=False,
                    default="pdf",
                    options=[]
                ),
                DynamicSelect(
                    field="format_cda",
                    title="Format dokumentu CDA (jeśli wybrano CDA/XML)",
                    required=False,
                    default="pades",
                    options=[]
                )
            )
        )
    )
)

def get_dostepne_pliki_filter_options(params):
    return [
        {"label": "Pokaż wszystkie wyniki", "value": "wszystkie"},
        {"label": "Tylko wyniki z oryginalnymi plikami do pobrania", "value": "tak"},
    ]

def get_generate_pdf_options(params):
    return [
        {"label": "Nie – tylko wyświetl wyniki", "value": "nie"},
        {"label": "Tak – pobierz pliki z wynikami", "value": "tak"},
    ]

def get_pdf_mode_options(params):
    return [
        {"label": "Oddzielne pliki PDF (dla każdego wyniku)", "value": "single"},
        {"label": "Jeden zbiorczy plik PDF", "value": "combined"},
    ]

def get_typ_pliku_options(params):
    return [
        {"label": "Raport PDF – zbiorczy lub oddzielne pliki z wynikami badań", "value": "pdf"},
        {"label": "CDA (XML) – oryginalne dokumenty zgodne ze standardem HL7 CDA", "value": "cda"}
    ]

def get_format_cda_options(params):
    return [
        {"label": "📄 PDF – gotowy do wydruku (z podpisem)", "value": "pades"},
        {"label": "🗎 XML – surowy dokument (dla systemów)", "value": "cda"}
    ]

def get_format_cda_options(params):
    return [
        {"label": "📄 PDF – gotowy do wydruku (z podpisem)", "value": "pades"},
        {"label": "🗎 XML – surowy dokument (dla systemów)", "value": "cda"}
    ]

def get_filter_pdf_available_options(params):
    return [
        {"label": "Wszystkie", "value": "wszystkie"},
        {"label": "Tylko z PDF", "value": "tak"},
        {"label": "Tylko bez PDF", "value": "nie"},
    ]

def get_filter_cda_available_options(params):
    return [
        {"label": "Wszystkie", "value": "wszystkie"},
        {"label": "Tylko z CDA", "value": "tak"},
        {"label": "Tylko bez CDA", "value": "nie"},
    ]

def assign_widget_data(dialog):
    field_map = {
        "generate_pdf": get_generate_pdf_options,
        "pdf_mode": get_pdf_mode_options,
        "typ_pliku": get_typ_pliku_options,
        "format_cda": get_format_cda_options,
        "dostepne_pliki_filter": get_dostepne_pliki_filter_options,
        "filter_pdf_available": get_filter_pdf_available_options,
        "filter_cda_available": get_filter_cda_available_options
    }
    for field_name, function in field_map.items():
        widget = dialog.get_field_by_name(field_name)
        if widget:
            widget.get_widget_data = function

assign_widget_data(LAUNCH_DIALOG)

def start_report(params):
    if params.get('action') == 'clear_filters':
        return {"type": "clear"}

    params = LAUNCH_DIALOG.load_params(params)
    
    if params.get('jeden_dzien'):
        params['zlecenie_data_do'] = params['zlecenie_data_od']

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

# --- NOWA FUNKCJA DO GENEROWANIA ZBIORCZEGO PDF ---
def raport_pdf_zbiorczy(task_params):
    db = PostgresDatasource(Config.DATABASE_MULTISYNC2)
    ids = task_params['params']['ids']
    
    try:
        merger = PdfMerger()
        
        # Pobieranie PDFów w paczkach, aby nie przeciążyć bazy
        batch_size = 20
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            pdf_result = db.dict_select('SELECT wynikowe_dane.generuj_pdf_z_wynikami(%s) AS pdf_base64', [batch_ids])
            if pdf_result and pdf_result[0].get('pdf_base64'):
                pdf_bytes = base64.b64decode(pdf_result[0]['pdf_base64'])
                merger.append(io.BytesIO(pdf_bytes))

        output_buffer = io.BytesIO()
        merger.write(output_buffer)
        merger.close()

        return {
            "type": "base64file",
            "filename": "raport_zbiorczy_wyniki.pdf",
            "content": base64.b64encode(output_buffer.getvalue()).decode("utf-8"),
            "mimetype": "application/pdf"
        }
    except Exception as e:
        traceback.print_exc()
        return {"type": "info", "text": f"Błąd podczas generowania zbiorczego PDF: {e}"}


def raport(task_params):
    db = PostgresDatasource(Config.DATABASE_MULTISYNC)
    params = task_params.get('params', {})
    generate_pdf = params.get('generate_pdf') == 'tak'
    selected_ids = params.get('selected_ids')
    file_type = params.get("typ_pliku", "pdf")
    format_cda = params.get("format_cda", "cda")

    if generate_pdf:
        if not selected_ids:
            return {"type": "info", "text": "Nie wybrano żadnych ID do pobrania."}

        ids = [int(id_.strip()) for id_ in selected_ids.split(',') if id_.strip().isdigit()]
        if not ids:
            return {"type": "info", "text": "Brak prawidłowych ID do pobrania."}

        try:
            files = []
            if file_type == "cda":
                sql = "SELECT id, zlecenie FROM wynikowe_dane.wyniki WHERE id = ANY(%s)"
                results = db.dict_select(sql, [ids])
                if not results:
                    return {"type": "info", "text": f"Nie znaleziono wyników dla podanych ID w bazie danych."}
                for row in results:
                    id_ = row.get("id")
                    zlecenie = row.get("zlecenie", {})
                    pre = zlecenie.get("PREPROCESSED", {})
                    if format_cda == "cda":
                        cda_hex = pre.get("PADES", {}).get("CDA")
                        filename = f"wynik_{id_}.xml"
                        mimetype = "text/xml"
                    else:
                        cda_hex = pre.get("PADES", {}).get("PDF")
                        filename = f"wynik_{id_}.pdf"
                        mimetype = "application/pdf"
                    if not cda_hex:
                        continue
                    try:
                        if cda_hex.startswith("\\x"):
                            cda_bytes = bytes.fromhex(cda_hex[2:])
                        else:
                            cda_bytes = base64.b64decode(cda_hex)
                    except Exception:
                        cda_bytes = cda_hex.encode("utf-8")
                    files.append({
                        "filename": filename,
                        "content": base64.b64encode(cda_bytes).decode("utf-8"),
                        "mimetype": mimetype
                    })
            elif file_type == "pdf":
                pdf_mode = params.get("pdf_mode", "single")
                if pdf_mode == "combined":
                    pdf_result = db.dict_select('SELECT wynikowe_dane.generuj_pdf_z_wynikami(%s) AS pdf_base64', [ids])
                    if not pdf_result or not pdf_result[0].get('pdf_base64'):
                        return {"type": "info", "text": "Nie udało się wygenerować PDF-a lub brak danych."}
                    files.append({
                        "filename": "raport_wyniki.pdf",
                        "content": pdf_result[0]['pdf_base64'],
                        "mimetype": "application/pdf"
                    })
                else:
                    for id_ in ids:
                        result = db.dict_select('SELECT wynikowe_dane.generuj_pdf_z_wynikami(%s) AS pdf_base64', [[id_]])
                        if result and result[0].get("pdf_base64"):
                            files.append({
                                "filename": f"raport_{id_}.pdf",
                                "content": result[0]['pdf_base64'],
                                "mimetype": "application/pdf"
                            })

            if not files:
                return {"type": "info", "text": f"Nie udało się wygenerować żadnych plików ({file_type})."}

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
                "filename": f"raporty_{file_type}.zip",
                "content": base64.b64encode(zip_content).decode("utf-8"),
                "mimetype": "application/zip"
            }

        except Exception as e:
            traceback.print_exc()
            return {"type": "info", "text": f"Błąd podczas generowania plików: {e}"}

    # --- MODYFIKACJA LOGIKI WYSZUKIWANIA I PAGINACJI ---
    conditions = []
    values = []
    
    page = int(params.get('page', 1))
    limit = int(params.get('pageSize', 20)) # Use pageSize from frontend
    offset = (page - 1) * limit
    print(f"DEBUG: page={page}, limit={limit}, offset={offset}")

    if not any([
        params.get('pacjent_query'), params.get('zlecenie_data_od'), params.get('zlecenie_data_do'),
        params.get('zlecenie_kod_kreskowy'), params.get('lekarz_imie'), params.get('lekarz_nazwisko'),
        params.get('zleceniodawca_nazwa'), params.get('zleceniodawca_kod_lsi'), params.get('zleceniodawca_nip'),
        params.get('zlecenie_id'),
        params.get('filter_pdf_available') != 'wszystkie',
        params.get('filter_cda_available') != 'wszystkie'
    ]):
        return {"type": "info", "text": "Musisz podać przynajmniej jeden filtr, aby uruchomić wyszukiwanie."}

    if params.get('zlecenie_id'):
        conditions.append('id = %s')
        values.append(params['zlecenie_id'])

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
                values.extend([f"%{term}%", f"%{term}%"])

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
        
    if params.get('dostepne_pliki_filter') == 'tak':
        conditions.append("((zlecenie->'PREPROCESSED'->'PADES'->'PDF') IS NOT NULL OR (zlecenie->'PREPROCESSED'->'PADES'->'CDA') IS NOT NULL))")

    if params.get('filter_pdf_available') == 'tak':
        conditions.append("(zlecenie->'PREPROCESSED'->'PADES'->'PDF') IS NOT NULL")
    elif params.get('filter_pdf_available') == 'nie':
        conditions.append("(zlecenie->'PREPROCESSED'->'PADES'->'PDF') IS NULL")

    if params.get('filter_cda_available') == 'tak':
        conditions.append("(zlecenie->'PREPROCESSED'->'PADES'->'CDA') IS NOT NULL")
    elif params.get('filter_cda_available') == 'nie':
        conditions.append("(zlecenie->'PREPROCESSED'->'PADES'->'CDA') IS NULL")

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    # Zapytanie o całkowitą liczbę rekordów
    count_sql = f"SELECT count(*) as total FROM wynikowe_dane.wyniki {where_clause}"
    print(f"DEBUG: count_sql={count_sql}, values={values}")
    total_records = db.dict_select(count_sql, values)[0]['total']
    total_pages = math.ceil(total_records / limit)

    # Zapytanie o dane dla bieżącej strony
    sql = f"""SELECT *,
                (zlecenie->'PREPROCESSED'->'PADES'->'PDF') IS NOT NULL AS czy_jest_pdf_pades,
                (zlecenie->'PREPROCESSED'->'PADES'->'CDA') IS NOT NULL AS czy_jest_cda_pades
              FROM wynikowe_dane.wyniki {where_clause} 
              ORDER BY id DESC
              LIMIT %s OFFSET %s"""
    
    paginated_values = values + [limit, offset]
    print(f"DEBUG: paginated_sql={sql}, paginated_values={paginated_values}")
    results = db.dict_select(sql, paginated_values)
    print(f"DEBUG: results from DB={results}")

    if not results:
        return {
            "type": "info",
            "text": "Brak danych spełniających podane kryteria. Spróbuj poszerzyć zakres dat lub zmienić filtry.",
            "progress": 1
        }

    header = [
        'ID', 'Dostępny PDF', 'Dostępny CDA', 'Tabela źródłowa', 'Laboratorium', 'Dane zlecenia (RAW)', 'Kod kreskowy zlecenia',
        'Numer wewnętrzny zlecenia (recno)', 'Numer rekordu zlecenia (rekno)', 'Data zlecenia',
        'Imię pacjenta', 'Nazwisko pacjenta', 'Data urodzenia pacjenta', 'PESEL pacjenta',
        'Imię lekarza', 'Nazwisko lekarza', 'Numer lekarza',
        'Kod LSI zleceniodawcy', 'Nazwa zleceniodawcy', 'NIP zleceniodawcy'
    ]

    columns = [
        'id', 'czy_jest_pdf_pades', 'czy_jest_cda_pades', 'common_table_name', 'laboratorium', 'zlecenie',
        'zlecenie_kod_kreskowy', 'zlecenie_recno', 'zlecenie_rekno', 'zlecenie_data',
        'pacjent_imie', 'pacjent_nazwisko', 'pacjent_data_urodzenia', 'pacjent_pesel',
        'lekarz_imie', 'lekarz_nazwisko', 'lekarz_numer',
        'zleceniodawca_kod_lsi', 'zleceniodawca_nazwa', 'zleceniodawca_nip'
    ]

    data = [[row.get(col) for col in columns] for row in results]
    
    all_ids = [row['id'] for row in results]

    # --- ZWRACANIE WYNIKÓW Z PAGINACJĄ I AKCJAMI ---
    final_result = {
        "type": "complex",
        "results": [
            {
                "type": "table",
                "header": header,
                "data": prepare_for_json(data)
            }
        ],
        "actions": [],
        "progress": 1
    }

    if total_pages > 1:
        final_result['results'].append({
            'type': 'pagination',
            'current_page': page,
            'total_pages': total_pages,
            'action': 'run_report'
        })
        
    if all_ids:
        final_result['actions'].append({
            'type': 'button',
            'label': 'Pobierz wszystkie wyniki z tej strony jako PDF',
            'action': 'run_function',
            'function': 'raport_pdf_zbiorczy',
            'params': {'ids': all_ids}
        })

    return final_result
