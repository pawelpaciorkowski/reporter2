import base64
import io
import zipfile
import tempfile
import os
import traceback

from dialog import Dialog, VBox, HBox, InfoText, TextInput, Select, Button, DynamicSelect, DateInput
from tasks import TaskGroup
from helpers import prepare_for_json
from datasources.postgres import PostgresDatasource
from config import Config
from flask import send_file

MENU_ENTRY = 'Raport Archiwum Wyników Labor (Multisync) vol2 test'

LAUNCH_DIALOG = Dialog(
    title=MENU_ENTRY,
    panel=VBox(
       

        HBox(
            # Sekcja: Wyszukiwanie po pacjencie lub dacie
            VBox(
                InfoText(text="Dane pacjenta i zakres dat"),
                TextInput(
                    field="pacjent_imie",
                    title="Imię pacjenta",
                    required=False,
                    default=""
                ),
                TextInput(
                    field="pacjent_nazwisko",
                    title="Nazwisko pacjenta",
                    required=False,
                    default=""
                ),
                TextInput(
                    field="pacjent_pesel",
                    title="PESEL pacjenta",
                    required=False,
                    default=""
                ),
                DateInput(
                    field="pacjent_data_urodzenia",
                    title="Data urodzenia pacjenta",
                    required=False,
                    default=""
                ),
                DateInput(
                    field="zlecenie_data_od",
                    title="Data zlecenia od",
                    required=False,
                    default=""
                ),
                DateInput(
                    field="zlecenie_data_do",
                    title="Data zlecenia do",
                    required=False,
                    default=""
                ),
            ),

            # Sekcja: Dane zlecenia i lekarza
            VBox(
                InfoText(text="Szczegóły zlecenia i lekarza"),
                TextInput(field="zlecenie_kod_kreskowy", title="Kod kreskowy zlecenia", required=False, default=""),
                TextInput(field="lekarz_imie", title="Imię lekarza", required=False, default=""),
                TextInput(field="lekarz_nazwisko", title="Nazwisko lekarza", required=False, default=""),
                TextInput(field="zleceniodawca_nazwa", title="Nazwa zleceniodawcy", required=False, default=""),
                TextInput(field="zleceniodawca_kod_lsi", title="Kod LSI zleceniodawcy", required=False, default=""),
                TextInput(field="zleceniodawca_nip", title="NIP zleceniodawcy", required=False, default=""),
            ),

            # Sekcja: Generowanie plików
            VBox(
                InfoText(text="Ustawienia generowania plików"),
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
                    default="",
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



def get_generate_pdf_options(params):
    return [
        {"label": "Nie – tylko wyświetl wyniki", "value": "nie"},
        {"label": "Tak – pobierz pliki z aktualnej strony", "value": "tak"},
        {"label": "Tak – pobierz wszystkie wyniki ze wszystkich stron", "value": "wszystkie"},
        {"label": "Tak – pobierz z zaznaczonych checkboxów w tabeli", "value": "zaznaczone"},
    ]


def get_pdf_mode_options(params):
    return [
        {"label": "Oddzielne pliki PDF (dla każdego wyniku)", "value": "single"},
        {"label": "Jeden zbiorczy plik PDF", "value": "combined"},
    ]


def get_typ_pliku_options(params):
    return [
        {
            "label": "Raport PDF – zbiorczy lub oddzielne pliki z wynikami badań",
            "value": "pdf"
        },
        {
            "label": "CDA (XML) – oryginalne dokumenty zgodne ze standardem HL7 CDA",
            "value": "cda"
        }
    ]


def get_format_cda_options(params):
    return [
        {
            "label": "📄 PDF – gotowy do wydruku (z podpisem)",
            "value": "pades"
        },
        {
            "label": "🗎 XML – surowy dokument (dla systemów)",
            "value": "cda"
        }
    ]


def assign_widget_data(dialog):
    for field_name in ["generate_pdf", "pdf_mode", "typ_pliku", "format_cda"]:
        widget = dialog.get_field_by_name(field_name)
        if widget is not None:
            if field_name == "generate_pdf":
                widget.get_widget_data = get_generate_pdf_options
            elif field_name == "pdf_mode":
                widget.get_widget_data = get_pdf_mode_options
            elif field_name == "typ_pliku":
                widget.get_widget_data = get_typ_pliku_options
            elif field_name == "format_cda":
                widget.get_widget_data = get_format_cda_options

assign_widget_data(LAUNCH_DIALOG)

def start_report(params):
    if params.get('action') == 'clear_filters':
        return {"type": "clear"}

    # Obsługa paginacji
    page = int(params.get('page', 1))
    page_size = int(params.get('page_size', 50))
    fetch_all = params.get('fetch_all', 'false')
    offset = int(params.get('offset', 0))  # Dodaj obsługę offset
    
    params = LAUNCH_DIALOG.load_params(params)
    params['page'] = page
    params['page_size'] = page_size
    params['fetch_all'] = fetch_all
    params['offset'] = offset  # Przekaż offset
    
    print(f"DEBUG - start_report: page={page}, page_size={page_size}, fetch_all={fetch_all}, offset={offset}")
    
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
    db = PostgresDatasource(Config.DATABASE_MULTISYNC_LABOR_ARCHIWUM)
    params = task_params.get('params', {})
    print(f"DEBUG - Wszystkie parametry otrzymane: {params}")
    print(f"DEBUG - generate_pdf wartość: {params.get('generate_pdf')}")
    
    generate_pdf = params.get('generate_pdf') == 'tak'
    generate_all_from_page = params.get('generate_pdf') == 'wszystkie'
    generate_selected = params.get('generate_pdf') == 'zaznaczone'
    generate_background = params.get('generate_pdf') == 'background'
    
    print(f"DEBUG - generate_pdf={generate_pdf}, generate_all_from_page={generate_all_from_page}, generate_selected={generate_selected}, generate_background={generate_background}")
    selected_ids = params.get('selected_ids')
    file_type = params.get("typ_pliku", "pdf")
    format_cda = params.get("format_cda", "cda")
    
    # Obsługa paginacji - pobierz wszystkie dane za jednym razem
    fetch_all = params.get('fetch_all', False)  # Nowy parametr
    page = int(params.get('page', 1))
    page_size = int(params.get('page_size', 50))
    offset = (page - 1) * page_size
    
    print(f"DEBUG - Paginacja: page={page}, page_size={page_size}, offset={offset}, fetch_all={fetch_all}")

    conditions = []
    values = []
    
    
    # Sprawdzenie czy podano przynajmniej dwa filtry
    active_filters = [
        params.get('pacjent_imie'),
        params.get('pacjent_nazwisko'),
        params.get('pacjent_pesel'),
        params.get('pacjent_data_urodzenia'),
        params.get('zlecenie_data_od'),
        params.get('zlecenie_data_do'),
        params.get('zlecenie_kod_kreskowy'),
        params.get('lekarz_imie'),
        params.get('lekarz_nazwisko'),
        params.get('zleceniodawca_nazwa'),
        params.get('zleceniodawca_kod_lsi'),
        params.get('zleceniodawca_nip')
    ]
    
    active_filters_count = sum(1 for filter_value in active_filters if filter_value)
    
    # Specjalna logika: jeśli podano tylko NIP, pozwól na wyszukiwanie
    only_nip_filter = (active_filters_count == 1 and params.get('zleceniodawca_nip'))
    
    if not generate_pdf and not generate_all_from_page and not generate_selected and active_filters_count < 2 and not only_nip_filter:
        return {
            "type": "info", 
            "text": "Musisz podać przynajmniej dwa filtry, aby uruchomić wyszukiwanie. Wypełnij co najmniej dwa pola w formularzu."
        }


    # Wyszukiwanie po danych pacjenta
    if params.get('pacjent_imie'):
        conditions.append('pacjent_imie ILIKE %s')
        values.append(f"%{params['pacjent_imie']}%")
    
    if params.get('pacjent_nazwisko'):
        conditions.append('pacjent_nazwisko ILIKE %s')
        values.append(f"%{params['pacjent_nazwisko']}%")
    
    if params.get('pacjent_pesel'):
        conditions.append('pacjent_pesel = %s')
        values.append(params['pacjent_pesel'])
    
    if params.get('pacjent_data_urodzenia'):
        conditions.append('(pacjent_data_urodzenia = %s OR pacjent_data_urodzenia::text = %s OR DATE(pacjent_data_urodzenia) = %s)')
        values.append(params['pacjent_data_urodzenia'])
        values.append(params['pacjent_data_urodzenia'])
        values.append(params['pacjent_data_urodzenia'])

    if params.get('zlecenie_kod_kreskowy'):
        conditions.append('zlecenie_kod_kreskowy ILIKE %s')
        values.append(f"%{params['zlecenie_kod_kreskowy']}%")
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
        conditions.append('zleceniodawca_kod_lsi ILIKE %s')
        values.append(f"%{params['zleceniodawca_kod_lsi']}%")
    if params.get('zleceniodawca_nip'):
        conditions.append('zleceniodawca_nip ILIKE %s')
        values.append(f"%{params['zleceniodawca_nip']}%")
    if params.get('zlecenie_data_od'):
        conditions.append('zlecenie_data >= %s')
        values.append(params['zlecenie_data_od'])
    if params.get('zlecenie_data_do'):
        conditions.append('zlecenie_data <= %s')
        values.append(params['zlecenie_data_do'])

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    # Zapytanie o całkowitą liczbę wyników
    count_sql = f'''SELECT COUNT(*) as total FROM wynikowe_dane.wyniki {where_clause}'''
    count_result = db.dict_select(count_sql, values)
    total_count = count_result[0]['total'] if count_result else 0
    
    # Zapytanie o dane - pobierz wszystkie lub z paginacją
    if fetch_all:
        # Pobierz wszystkie dane za jednym razem
        sql = f'''SELECT id, common_table_name, laboratorium, zlecenie_kod_kreskowy, 
                  zlecenie_recno, zlecenie_rekno, zlecenie_data, pacjent_imie, pacjent_nazwisko, 
                  pacjent_data_urodzenia, pacjent_pesel, lekarz_imie, lekarz_nazwisko, lekarz_numer,
                  zleceniodawca_kod_lsi, zleceniodawca_nazwa, zleceniodawca_nip 
                  FROM wynikowe_dane.wyniki {where_clause} 
                  ORDER BY id'''
        print(f"DEBUG - Pobieranie WSZYSTKICH danych: {sql}")
        print(f"DEBUG - Wartości SQL: {values}")
        results = db.dict_select(sql, values)
    else:
        # Pobierz dane z paginacją
        sql = f'''SELECT id, common_table_name, laboratorium, zlecenie_kod_kreskowy, 
                  zlecenie_recno, zlecenie_rekno, zlecenie_data, pacjent_imie, pacjent_nazwisko, 
                  pacjent_data_urodzenia, pacjent_pesel, lekarz_imie, lekarz_nazwisko, lekarz_numer,
                  zleceniodawca_kod_lsi, zleceniodawca_nazwa, zleceniodawca_nip 
                  FROM wynikowe_dane.wyniki {where_clause} 
                  ORDER BY id
                  LIMIT %s OFFSET %s'''
        print(f"DEBUG - Pobieranie danych z paginacją: {sql}")
        print(f"DEBUG - Wartości SQL: {values + [page_size, offset]}")
        results = db.dict_select(sql, values + [page_size, offset])
    
    print(f"DEBUG - Liczba zwróconych wyników: {len(results) if results else 0}")
    
    # Debugowanie - sprawdźmy kilka przykładowych dat z bazy
    if not results and any('pacjent_data_urodzenia' in condition for condition in conditions):
        debug_sql = "SELECT DISTINCT pacjent_data_urodzenia, pacjent_imie, pacjent_nazwisko FROM wynikowe_dane.wyniki WHERE pacjent_data_urodzenia IS NOT NULL LIMIT 10"
        debug_results = db.dict_select(debug_sql, [])
        print(f"DEBUG - Przykładowe daty urodzenia w bazie: {debug_results}")

    if not results or len(results) == 0:
        return {
            "type": "info",
            "text": "Brak danych spełniających podane kryteria. Spróbuj poszerzyć zakres dat lub zmienić filtry."
        }

    header = [
        'ID', 'Tabela źródłowa', 'Laboratorium', 'Kod kreskowy zlecenia',
        'Numer wewnętrzny zlecenia (recno)', 'Numer rekordu zlecenia (rekno)', 'Data zlecenia',
        'Imię pacjenta', 'Nazwisko pacjenta', 'Data urodzenia pacjenta', 'PESEL pacjenta',
        'Imię lekarza', 'Nazwisko lekarza', 'Numer lekarza',
        'Kod LSI zleceniodawcy', 'Nazwa zleceniodawcy', 'NIP zleceniodawcy'
    ]

    columns = [
        'id', 'common_table_name', 'laboratorium', 'zlecenie_kod_kreskowy',
        'zlecenie_recno', 'zlecenie_rekno', 'zlecenie_data',
        'pacjent_imie', 'pacjent_nazwisko', 'pacjent_data_urodzenia', 'pacjent_pesel',
        'lekarz_imie', 'lekarz_nazwisko', 'lekarz_numer',
        'zleceniodawca_kod_lsi', 'zleceniodawca_nazwa', 'zleceniodawca_nip'
    ]

    data = [[row.get(col) for col in columns] for row in results]

    # Informacje o paginacji
    if fetch_all:
        # Jeśli pobrano wszystkie dane, podziel je na strony
        total_pages = (len(data) + page_size - 1) // page_size if data else 0
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        current_page_data = data[start_idx:end_idx]
    else:
        # Standardowa paginacja
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0
        current_page_data = data
    
    if generate_pdf or generate_all_from_page or generate_selected or generate_background:
        # Sprawdź czy to generowanie w tle
        if generate_background:
            print(f"DEBUG - Generowanie w tle - przekierowuję do standardowego generowania")
            # Dla generowania w tle, przekieruj do standardowego generowania
            # (opcja w tle nie jest jeszcze w pełni zaimplementowana)
            if generate_all_from_page or generate_selected:
                # Jeśli wybrano "wszystkie" lub "zaznaczone", użyj tych ID
                if generate_all_from_page:
                    sql = f'''SELECT id FROM wynikowe_dane.wyniki {where_clause} ORDER BY id'''
                    results = db.dict_select(sql, values)
                    if not results:
                        return {"type": "info", "text": "Brak danych do pobrania."}
                    ids = [row['id'] for row in results]
                else:  # generate_selected
                    if not selected_ids:
                        return {"type": "info", "text": "Nie zaznaczono żadnych ID do pobrania."}
                    ids = [int(id_.strip()) for id_ in selected_ids.split(',') if id_.strip().isdigit()]
            else:
                # Standardowo użyj ID z aktualnej strony
                if fetch_all:
                    start_idx = (page - 1) * page_size
                    end_idx = start_idx + page_size
                    current_page_ids = [row['id'] for row in results[start_idx:end_idx]]
                    ids = current_page_ids
                else:
                    if not selected_ids:
                        return {"type": "info", "text": "Nie wybrano żadnych ID do pobrania."}
                    ids = [int(id_.strip()) for id_ in selected_ids.split(',') if id_.strip().isdigit()]
            
            print(f"DEBUG - Generowanie w tle dla {len(ids)} ID - kontynuuję standardowe generowanie")
            # Kontynuuj standardowe generowanie zamiast zwracać komunikat
        
        # Standardowa logika dla generowania synchronicznego
        if generate_all_from_page:
            # Pobierz wszystkie ID z wszystkich danych (bez paginacji)
            sql = f'''SELECT id FROM wynikowe_dane.wyniki {where_clause} 
                      ORDER BY id'''
            results = db.dict_select(sql, values)
            if not results:
                return {"type": "info", "text": "Brak danych do pobrania."}
            ids = [row['id'] for row in results]
            print(f"DEBUG - Automatycznie pobrano {len(ids)} ID ze wszystkich danych")
        elif generate_selected:
            # Pobierz ID z zaznaczonych checkboxów
            if not selected_ids:
                return {"type": "info", "text": "Nie zaznaczono żadnych ID do pobrania. Zaznacz checkboxy przy wybranych wierszach."}
            ids = [int(id_.strip()) for id_ in selected_ids.split(',') if id_.strip().isdigit()]
            if not ids:
                return {"type": "info", "text": "Brak prawidłowych zaznaczonych ID do pobrania."}
            print(f"DEBUG - Pobrano {len(ids)} zaznaczonych ID: {ids}")
        else:
            # Standardowa logika dla wybranych ID (z aktualnej strony)
            if fetch_all:
                # Jeśli pobrano wszystkie dane, użyj ID z aktualnej strony
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                current_page_ids = [row['id'] for row in results[start_idx:end_idx]]
                ids = current_page_ids
                print(f"DEBUG - Pobrano {len(ids)} ID z aktualnej strony: {ids}")
            else:
                # Użyj ID z pola tekstowego
                if not selected_ids:
                    return {"type": "info", "text": "Nie wybrano żadnych ID do pobrania."}
                ids = [int(id_.strip()) for id_ in selected_ids.split(',') if id_.strip().isdigit()]
                if not ids:
                    return {"type": "info", "text": "Brak prawidłowych ID do pobrania."}

        try:
            print(f"DEBUG - Rozpoczynam generowanie plików dla {len(ids)} ID")
            print(f"DEBUG - Typ pliku: {file_type}, PDF mode: {params.get('pdf_mode', 'single')}")
            
            # Limit liczby plików do generowania (zabezpieczenie przed przeciążeniem)
            max_files = 1000
            if len(ids) > max_files:
                print(f"DEBUG - Przekroczono limit plików: {len(ids)} > {max_files}")
                return {"type": "info", "text": f"Za dużo wyników do pobrania ({len(ids)}). Maksymalnie można pobrać {max_files} plików na raz."}
            
            files = []

            if file_type == "cda":
                print(f"DEBUG - Generowanie plików CDA dla {len(ids)} ID")
                sql = "SELECT id, zlecenie FROM wynikowe_dane.wyniki WHERE id = ANY(%s)"
                results = db.dict_select(sql, [ids])
                if not results:
                    print(f"DEBUG - Nie znaleziono wyników CDA dla ID: {ids[:10]}...")
                    return {"type": "info", "text": f"Nie znaleziono wyników dla podanych ID w bazie danych."}
                
                print(f"DEBUG - Znaleziono {len(results)} wyników CDA")
                processed_count = 0
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
                        print(f"DEBUG - Brak danych CDA dla ID {id_}")
                        continue 
                    try:
                        if cda_hex.startswith("\\x"):
                            cda_bytes = bytes.fromhex(cda_hex[2:])
                        else:
                            cda_bytes = base64.b64decode(cda_hex)
                    except Exception as e:
                        print(f"DEBUG - Błąd dekodowania CDA dla ID {id_}: {e}")
                        cda_bytes = cda_hex.encode("utf-8") 
                    files.append({
                        "filename": filename,
                        "content": base64.b64encode(cda_bytes).decode("utf-8"),
                        "mimetype": mimetype
                    })
                    processed_count += 1
                    if processed_count % 100 == 0:
                        print(f"DEBUG - Przetworzono {processed_count}/{len(results)} plików CDA")
                
                print(f"DEBUG - Wygenerowano {len(files)} plików CDA")
            elif file_type == "pdf":
                print(f"DEBUG - Generowanie plików PDF dla {len(ids)} ID")
                pdf_mode = params.get("pdf_mode", "single")
                print(f"DEBUG - PDF mode: {pdf_mode}")
                
                if pdf_mode == "combined":
                    print(f"DEBUG - Generowanie połączonego PDF dla wszystkich {len(ids)} ID")
                    # Optymalizacja: jeden wywołanie dla wszystkich ID
                    pdf_result = db.dict_select('SELECT wynikowe_dane.generuj_pdf_z_wynikami(%s) AS pdf_base64', [ids])
                    if not pdf_result or not pdf_result[0].get('pdf_base64'):
                        print(f"DEBUG - Błąd generowania połączonego PDF")
                        return {"type": "info", "text": "Nie udało się wygenerować PDF-a lub brak danych."}
                    print(f"DEBUG - Pomyślnie wygenerowano połączony PDF")
                    files.append({
                        "filename": "raport_wyniki.pdf",
                        "content": pdf_result[0]['pdf_base64'],
                        "mimetype": "application/pdf"
                    })
                else:
                    print(f"DEBUG - Generowanie pojedynczych PDF-ów w trybie batch")
                    # Optymalizacja: batch processing dla pojedynczych PDF-ów
                    batch_size = 50  # Przetwarzaj po 50 ID na raz
                    total_batches = (len(ids) + batch_size - 1) // batch_size
                    print(f"DEBUG - Przetwarzanie {len(ids)} ID w {total_batches} partiach po {batch_size}")
                    
                    for i in range(0, len(ids), batch_size):
                        batch_num = i // batch_size + 1
                        batch_ids = ids[i:i + batch_size]
                        print(f"DEBUG - Przetwarzanie partii {batch_num}/{total_batches} ({len(batch_ids)} ID)")
                        
                        # Wywołaj funkcję dla całej partii
                        result = db.dict_select('SELECT wynikowe_dane.generuj_pdf_z_wynikami(%s) AS pdf_base64', [batch_ids])
                        if result and result[0].get("pdf_base64"):
                            # Jeśli funkcja zwraca jeden plik dla partii, dodaj go
                            print(f"DEBUG - Pomyślnie wygenerowano PDF dla partii {batch_num}")
                            files.append({
                                "filename": f"raport_batch_{batch_num}.pdf",
                                "content": result[0]['pdf_base64'],
                                "mimetype": "application/pdf"
                            })
                        else:
                            # Jeśli funkcja nie obsługuje batch, wywołaj dla każdego ID osobno
                            print(f"DEBUG - Batch nie działa, generowanie pojedynczych PDF-ów dla partii {batch_num}")
                            for j, id_ in enumerate(batch_ids):
                                print(f"DEBUG - Generowanie PDF dla ID {id_} ({j+1}/{len(batch_ids)} w partii {batch_num})")
                                single_result = db.dict_select('SELECT wynikowe_dane.generuj_pdf_z_wynikami(%s) AS pdf_base64', [[id_]])
                                if single_result and single_result[0].get("pdf_base64"):
                                    files.append({
                                        "filename": f"raport_{id_}.pdf",
                                        "content": single_result[0]['pdf_base64'],
                                        "mimetype": "application/pdf"
                                    })
                                    print(f"DEBUG - Pomyślnie wygenerowano PDF dla ID {id_}")
                                else:
                                    print(f"DEBUG - Błąd generowania PDF dla ID {id_}")
                
                print(f"DEBUG - Wygenerowano {len(files)} plików PDF")
            
            if not files:
                print(f"DEBUG - Brak plików do spakowania")
                return {"type": "info", "text": f"Nie udało się wygenerować żadnych plików ({file_type})."}

            print(f"DEBUG - Tworzenie archiwum ZIP z {len(files)} plików")
            # Optymalizacja: kompresja ZIP z lepszymi ustawieniami
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
                print(f"DEBUG - Tymczasowy plik ZIP: {tmp_zip.name}")
                with zipfile.ZipFile(tmp_zip.name, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                    for i, file in enumerate(files):
                        print(f"DEBUG - Dodawanie pliku {i+1}/{len(files)}: {file['filename']}")
                        decoded = base64.b64decode(file['content'])
                        zipf.writestr(file['filename'], decoded)
                print(f"DEBUG - Archiwum ZIP utworzone, rozmiar: {os.path.getsize(tmp_zip.name)} bajtów")
                tmp_zip.seek(0)
                with open(tmp_zip.name, "rb") as f:
                    zip_content = f.read()
                os.unlink(tmp_zip.name)
                print(f"DEBUG - Tymczasowy plik usunięty")

            print(f"DEBUG - Kodowanie ZIP do base64")
            zip_base64 = base64.b64encode(zip_content).decode("utf-8")
            print(f"DEBUG - Rozmiar base64: {len(zip_base64)} znaków")

            return {
                "type": "base64file",
                "filename": f"raporty_{file_type}_{len(files)}_plikow.zip",
                "content": zip_base64,
                "mimetype": "application/zip"
            }

        except Exception as e:
            print(f"DEBUG - Błąd podczas generowania plików: {e}")
            traceback.print_exc()
            return {"type": "info", "text": f"Błąd podczas generowania plików: {e}"}


    return {
        "type": "table",
        "header": header,
        "data": prepare_for_json(current_page_data),
        "show_checkboxes": True,  # Flaga dla frontendu
        "actions": ["xlsx"],  # Dodaj akcję Excel
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_count": total_count if not fetch_all else len(data),
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        },
        "all_data": prepare_for_json(data) if fetch_all else None  # Wszystkie dane dla cache'a
    }
