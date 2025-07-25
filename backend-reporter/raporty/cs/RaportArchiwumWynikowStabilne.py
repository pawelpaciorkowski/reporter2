import base64
import datetime
import math

from dialog import Dialog, VBox, HBox, InfoText, TextInput, Select, DateInput
from tasks import TaskGroup
from helpers import prepare_for_json
from datasources.postgres import PostgresDatasource
from config import Config

MENU_ENTRY = 'Raport Archiwum Wyników Labor (STABILNE)'

LAUNCH_DIALOG = Dialog(
    title=MENU_ENTRY,
    panel=VBox(
        InfoText(text="Stabilna wersja - naprawione wyszukiwanie i stronicowanie"),
        
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
                        "tydzien": "Ostatni tydzień"
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
            TextInput(field="page_number", title="Strona", required=False, default_value="1"),
            Select(
                field="page_size",
                title="Wyników na stronę",
                values={
                    "50": "50",
                    "100": "100", 
                    "200": "200",
                    "500": "500"
                },
                required=False,
                default_value="100"
            ),
            Select(
                field="show_count_only",
                title="Tryb",
                values={
                    "nie": "Pokaż wyniki",
                    "tak": "Tylko policz"
                },
                required=False,
                default_value="nie"
            ),
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
    
    return params


def build_conditions(params):
    """Buduje warunki SQL"""
    conditions = []
    values = []
    
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
    
    return conditions, values


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
        page_size = min(1000, int(params.get('page_size', 100)))
        offset = (page_number - 1) * page_size
        show_count_only = params.get('show_count_only', 'nie') == 'tak'
        
        conditions, values = build_conditions(params)
        
        if not conditions:
            return {
                "type": "info",
                "text": "Podaj przynajmniej jeden filtr wyszukiwania."
            }
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        if show_count_only:
            count_sql = f'SELECT COUNT(*) as total FROM wynikowe_dane.wyniki {where_clause}'
            count_result = db.dict_select(count_sql, values)
            total_count = count_result[0]['total'] if count_result else 0
            return {
                "type": "info",
                "text": f"Znaleziono {total_count:,} wyników."
            }
        
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
        
        nav_info = ""
        if total_pages > 1:
            nav_parts = []
            if page_number > 1:
                nav_parts.append(f"Poprzednia: strona {page_number - 1}")
            if page_number < total_pages:
                nav_parts.append(f"Następna: strona {page_number + 1}")
            if nav_parts:
                nav_info = " | " + " | ".join(nav_parts)
        
        return {
            "type": "table",
            "header": header,
            "data": prepare_for_json(data),
            "title": f"📊 {pagination_info}{nav_info}"
        }
        
    except Exception as e:
        print(f"ERROR in raport: {e}")
        import traceback
        traceback.print_exc()
        return {
            "type": "error",
            "text": f"Błąd: {e}"
        } 