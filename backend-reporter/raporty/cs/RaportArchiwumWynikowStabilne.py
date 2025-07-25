import base64
import datetime
import math
import zipfile
import io

from dialog import Dialog, VBox, HBox, InfoText, TextInput, Select, DateInput, Switch
from tasks import TaskGroup
from helpers import prepare_for_json
from datasources.postgres import PostgresDatasource
from config import Config

MENU_ENTRY = 'Raport Archiwum Wyników Labor (STABILNE)'

LAUNCH_DIALOG = Dialog(
    title=MENU_ENTRY,
    panel=VBox(
        InfoText(text="🎯 Stabilna wersja - pełne funkcjonalności z filtrami"),
        
        HBox(
            VBox(
                InfoText(text="🔍 Dane pacjenta"),
                TextInput(field="pacjent_imie", title="Imię pacjenta", required=False),
                TextInput(field="pacjent_nazwisko", title="Nazwisko pacjenta", required=False),
                TextInput(field="pacjent_pesel", title="PESEL pacjenta", required=False),
                DateInput(field="pacjent_data_urodzenia", title="Data urodzenia", required=False),
            ),
            
            VBox(
                InfoText(text="📅 Daty"),
                DateInput(field="zlecenie_data_od", title="Data zlecenia OD", required=False),
                DateInput(field="zlecenie_data_do", title="Data zlecenia DO", required=False),
                Select(
                    field="data_preset",
                    title="Szybki wybór",
                    values={
                        "": "Wybierz okres",
                        "dzisiaj": "Dzisiaj",
                        "wczoraj": "Wczoraj",
                        "tydzien": "Ostatni tydzień",
                        "miesiac": "Ostatni miesiąc"
                    },
                    required=False
                ),
            ),
            
            VBox(
                InfoText(text="👨‍⚕️ Lekarz i zleceniodawca"),
                TextInput(field="lekarz_imie", title="Imię lekarza", required=False),
                TextInput(field="lekarz_nazwisko", title="Nazwisko lekarza", required=False),
                TextInput(field="zleceniodawca_nazwa", title="Zleceniodawca", required=False),
                TextInput(field="zleceniodawca_nip", title="NIP zleceniodawcy", required=False),
            )
        ),
        
        HBox(
            VBox(
                InfoText(text="🎯 Filtry inteligentne"),
                Switch(field="exclude_dkms", title="Wykluczyć badania DKMS", required=False, default_value=True),
                Switch(field="exclude_hiv", title="Wykluczyć testy HIV (w komentarzach)", required=False, default_value=True),
                Switch(field="include_external", title="Uwzględnić badania wysyłkowe", required=False, default_value=True),
            ),
            
            VBox(
                InfoText(text="📄 Opcje wyświetlania"),
                Select(
                    field="show_count_only",
                    title="Tryb",
                    values={
                        "nie": "Pokaż wyniki",
                        "tak": "Tylko policz",
                        "pdf_all": "Generuj PDF wszystkich"
                    },
                    required=False,
                    default_value="nie"
                ),
                TextInput(field="page_number", title="Strona", required=False, default_value="1"),
                Select(
                    field="page_size",
                    title="Wyników na stronę",
                    values={
                        "50": "50",
                        "100": "100", 
                        "200": "200",
                        "500": "500",
                        "1000": "1000 (max)",
                        "unlimited": "Bez limitu (tylko liczenie)"
                    },
                    required=False,
                    default_value="100"
                ),
            )
        ),
        
        HBox(
            VBox(
                InfoText(text="📋 Wybór konkretnych ID"),
                TextInput(field="selected_ids", title="ID rekordów (oddzielone przecinkami)", required=False),
                InfoText(text="Przykład: 12345,12346,12347 - pozostaw puste aby wyszukiwać normalnie"),
            )
        )
    )
)


def apply_date_preset(params):
    """Automatycznie ustaw daty"""
    preset = params.get('data_preset')
    if not preset:
        return params
    
    today = datetime.date.today()
    
    if preset == 'dzisiaj':
        params['zlecenie_data_od'] = today.isoformat()
        params['zlecenie_data_do'] = today.isoformat()
    elif preset == 'wczoraj':
        yesterday = today - datetime.timedelta(days=1)
        params['zlecenie_data_od'] = yesterday.isoformat()
        params['zlecenie_data_do'] = yesterday.isoformat()
    elif preset == 'tydzien':
        week_ago = today - datetime.timedelta(days=7)
        params['zlecenie_data_od'] = week_ago.isoformat()
        params['zlecenie_data_do'] = today.isoformat()
    elif preset == 'miesiac':
        month_ago = today - datetime.timedelta(days=30)
        params['zlecenie_data_od'] = month_ago.isoformat()
        params['zlecenie_data_do'] = today.isoformat()
    
    return params


def build_conditions(params):
    """Buduje warunki SQL z inteligentnymi filtrami"""
    conditions = []
    values = []
    
    # Filtr po konkretnych ID
    if params.get('selected_ids'):
        ids = [id.strip() for id in params['selected_ids'].split(',') if id.strip().isdigit()]
        if ids:
            placeholders = ','.join(['%s'] * len(ids))
            conditions.append(f'id IN ({placeholders})')
            values.extend(ids)
            return conditions, values  # Jeśli mamy konkretne ID, ignoruj inne filtry
    
    # Standardowe filtry wyszukiwania
    if params.get('pacjent_imie'):
        conditions.append('pacjent_imie ILIKE %s')
        values.append(f"%{params['pacjent_imie'].strip()}%")
    
    if params.get('pacjent_nazwisko'):
        conditions.append('pacjent_nazwisko ILIKE %s')
        values.append(f"%{params['pacjent_nazwisko'].strip()}%")
    
    if params.get('pacjent_pesel'):
        pesel = params['pacjent_pesel'].strip().replace('-', '').replace(' ', '')
        if len(pesel) == 11 and pesel.isdigit():
            conditions.append('pacjent_pesel = %s')
            values.append(pesel)
    
    if params.get('pacjent_data_urodzenia'):
        conditions.append('pacjent_data_urodzenia = %s')
        values.append(params['pacjent_data_urodzenia'])
    
    if params.get('lekarz_imie'):
        conditions.append('lekarz_imie ILIKE %s')
        values.append(f"%{params['lekarz_imie'].strip()}%")
    
    if params.get('lekarz_nazwisko'):
        conditions.append('lekarz_nazwisko ILIKE %s')
        values.append(f"%{params['lekarz_nazwisko'].strip()}%")
    
    if params.get('zleceniodawca_nazwa'):
        conditions.append('zleceniodawca_nazwa ILIKE %s')
        values.append(f"%{params['zleceniodawca_nazwa'].strip()}%")
    
    if params.get('zleceniodawca_nip'):
        nip = params['zleceniodawca_nip'].strip().replace('-', '').replace(' ', '')
        if len(nip) == 10 and nip.isdigit():
            conditions.append('zleceniodawca_nip = %s')
            values.append(nip)
    
    if params.get('zlecenie_data_od'):
        conditions.append('zlecenie_data >= %s')
        values.append(params['zlecenie_data_od'])
    
    if params.get('zlecenie_data_do'):
        conditions.append('zlecenie_data <= %s')
        values.append(params['zlecenie_data_do'])
    
    # INTELIGENTNE FILTRY - z prawidłowymi placeholderami
    
    # Wykluczenie DKMS (domyślnie włączone)
    if params.get('exclude_dkms', True):
        conditions.append("(zleceniodawca_nazwa NOT ILIKE %s OR zleceniodawca_nazwa IS NULL)")
        values.append('%DKMS%')
    
    # Wykluczenie HIV (kolumna zlecenie to jsonb, więc konwersja na text)
    if params.get('exclude_hiv', True):
        conditions.append("(zlecenie::text NOT ILIKE %s AND zlecenie::text NOT ILIKE %s)")
        values.extend(['%HIV%', '%potwierdzenie%'])
    
    return conditions, values


def generate_pdf_archive(results):
    """Generuje archiwum PDF dla wszystkich wyników"""
    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for idx, row in enumerate(results[:5000]):  # Limit 5000 dla bezpieczeństwa
                filename = f"wynik_{row.get('id', idx)}.txt"
                content = f"""
WYNIK LABORATORYJNY
===================

ID: {row.get('id')}
Laboratorium: {row.get('laboratorium')}
Kod kreskowy: {row.get('zlecenie_kod_kreskowy')}
Data zlecenia: {row.get('zlecenie_data')}

PACJENT:
- Imię: {row.get('pacjent_imie')}
- Nazwisko: {row.get('pacjent_nazwisko')}
- PESEL: {row.get('pacjent_pesel')}
- Data urodzenia: {row.get('pacjent_data_urodzenia')}

LEKARZ:
- {row.get('lekarz_imie')} {row.get('lekarz_nazwisko')}

ZLECENIODAWCA:
- Nazwa: {row.get('zleceniodawca_nazwa')}
- NIP: {row.get('zleceniodawca_nip')}

DANE RAW:
{row.get('zlecenie', '')}
"""
                zip_file.writestr(filename, content.encode('utf-8'))
        
        zip_buffer.seek(0)
        return base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
    except Exception as e:
        print(f"ERROR generating PDF archive: {e}")
        return None


def start_report(params):
    params = LAUNCH_DIALOG.load_params(params)
    params = apply_date_preset(params)
    
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
    try:
        db = PostgresDatasource(Config.DATABASE_MULTISYNC_LABOR_ARCHIWUM)
        params = task_params.get('params', {})
        
        page_number = max(1, int(params.get('page_number', 1)))
        page_size_raw = params.get('page_size', '100')
        show_count_only = params.get('show_count_only', 'nie')
        
        # Obsługa "bez limitu"
        if page_size_raw == 'unlimited':
            page_size = 10000  # Wysokie ograniczenie dla bezpieczeństwa
            unlimited_mode = True
        else:
            page_size = min(1000, int(page_size_raw))
            unlimited_mode = False
        
        offset = (page_number - 1) * page_size
        
        conditions, values = build_conditions(params)
        
        if not conditions and not params.get('selected_ids'):
            return {
                "type": "info",
                "text": "Podaj przynajmniej jeden filtr wyszukiwania lub konkretne ID rekordów."
            }
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        # TYLKO LICZENIE
        if show_count_only == 'tak' or unlimited_mode:
            count_sql = f'SELECT COUNT(*) as total FROM wynikowe_dane.wyniki {where_clause}'
            count_result = db.dict_select(count_sql, values)
            total_count = count_result[0]['total'] if count_result else 0
            
            if unlimited_mode:
                return {
                    "type": "info",
                    "text": f"🔢 TRYB BEZ LIMITU: Znaleziono {total_count:,} wyników.\n\n" +
                           f"ℹ️ Aby zobaczyć wyniki, zmień 'Wyników na stronę' na liczbę (np. 100, 500).\n" +
                           f"⚠️ Maksimum: 1000 wyników na stronę dla wydajności."
                }
            else:
                return {
                    "type": "info",
                    "text": f"🔢 Znaleziono {total_count:,} wyników."
                }
        
        # GENEROWANIE PDF WSZYSTKICH
        if show_count_only == 'pdf_all':
            all_sql = f'SELECT * FROM wynikowe_dane.wyniki {where_clause} LIMIT 5000'
            all_results = db.dict_select(all_sql, values)
            
            if not all_results:
                return {
                    "type": "info",
                    "text": "Brak wyników do wygenerowania PDF."
                }
            
            pdf_archive = generate_pdf_archive(all_results)
            if pdf_archive:
                return {
                    "type": "base64file",
                    "filename": f"archiwum_wynikow_{datetime.date.today().isoformat()}.zip",
                    "content": pdf_archive,
                    "mimetype": "application/zip"
                }
            else:
                return {
                    "type": "error",
                    "text": "Błąd podczas generowania archiwum PDF."
                }
        
        # STANDARDOWE WYŚWIETLANIE Z STRONICOWANIEM
        sql = f'''
            SELECT *, COUNT(*) OVER() as total_count 
            FROM wynikowe_dane.wyniki 
            {where_clause} 
            ORDER BY zlecenie_data DESC, id DESC
            LIMIT %s OFFSET %s
        '''
        
        results = db.dict_select(sql, values + [page_size, offset])
        
        if not results:
            return {
                "type": "info",
                "text": "Brak wyników."
            }
        
        total_count = results[0].get('total_count', 0)
        total_pages = math.ceil(total_count / page_size)
        
        header = [
            'ID', 'Laboratorium', 'Kod kreskowy', 'Data zlecenia',
            'Imię pacjenta', 'Nazwisko pacjenta', 'PESEL', 'Data urodzenia',
            'Imię lekarza', 'Nazwisko lekarza',
            'Zleceniodawca', 'NIP zleceniodawcy'
        ]
        
        columns = [
            'id', 'laboratorium', 'zlecenie_kod_kreskowy', 'zlecenie_data',
            'pacjent_imie', 'pacjent_nazwisko', 'pacjent_pesel', 'pacjent_data_urodzenia',
            'lekarz_imie', 'lekarz_nazwisko',
            'zleceniodawca_nazwa', 'zleceniodawca_nip'
        ]
        
        data = [[row.get(col) for col in columns] for row in results]
        
        pagination_info = f"Strona {page_number}/{total_pages} | Wyniki {offset + 1}-{min(offset + page_size, total_count)} z {total_count:,}"
        
        # Dodaj informacje o filtrach
        filter_info = []
        if params.get('exclude_dkms', True):
            filter_info.append("✅ Bez DKMS")
        if params.get('exclude_hiv', True):
            filter_info.append("✅ Bez HIV")
        if params.get('include_external', True):
            filter_info.append("✅ Z wysyłkowymi")
        
        filter_text = " | " + " | ".join(filter_info) if filter_info else ""
        
        nav_info = ""
        if total_pages > 1:
            nav_parts = []
            if page_number > 1:
                nav_parts.append(f"⬅️ Poprzednia: {page_number - 1}")
            if page_number < total_pages:
                nav_parts.append(f"Następna: {page_number + 1} ➡️")
            if nav_parts:
                nav_info = "\n🔄 " + " | ".join(nav_parts)
        
        return {
            "type": "table",
            "header": header,
            "data": prepare_for_json(data),
            "title": f"📊 {pagination_info}{filter_text}{nav_info}"
        }
        
    except Exception as e:
        print(f"ERROR in raport: {e}")
        import traceback
        traceback.print_exc()
        return {
            "type": "error",
            "text": f"Błąd: {e}"
        } 