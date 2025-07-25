import base64
import datetime
import math

from dialog import Dialog, VBox, HBox, InfoText, TextInput, Select, DateInput
from tasks import TaskGroup
from helpers import prepare_for_json
from datasources.postgres import PostgresDatasource
from config import Config

MENU_ENTRY = 'Raport Archiwum Wyników Labor (PROSTSZE)'

LAUNCH_DIALOG = Dialog(
    title=MENU_ENTRY,
    panel=VBox(
        InfoText(text="Uproszczona wersja do debugowania"),
        
        TextInput(field="pacjent_pesel", title="PESEL pacjenta", required=False),
        TextInput(field="pacjent_nazwisko", title="Nazwisko pacjenta", required=False),
        DateInput(field="zlecenie_data_od", title="Data zlecenia OD", required=False),
        DateInput(field="zlecenie_data_do", title="Data zlecenia DO", required=False),
        
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


def start_report(params):
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
    try:
        db = PostgresDatasource(Config.DATABASE_MULTISYNC_LABOR_ARCHIWUM)
        params = task_params.get('params', {})
        
        show_count_only = params.get('show_count_only', 'nie') == 'tak'
        
        # Podstawowe warunki
        conditions = []
        values = []
        
        if params.get('pacjent_pesel'):
            pesel = params['pacjent_pesel'].strip().replace('-', '').replace(' ', '')
            if len(pesel) == 11 and pesel.isdigit():
                conditions.append('pacjent_pesel = %s')
                values.append(pesel)
        
        if params.get('pacjent_nazwisko'):
            conditions.append('pacjent_nazwisko ILIKE %s')
            values.append(f"%{params['pacjent_nazwisko'].strip()}%")
        
        if params.get('zlecenie_data_od'):
            conditions.append('zlecenie_data >= %s')
            values.append(params['zlecenie_data_od'])
        
        if params.get('zlecenie_data_do'):
            conditions.append('zlecenie_data <= %s')
            values.append(params['zlecenie_data_do'])
        
        # Sprawdź czy są jakieś filtry
        if not conditions:
            return {
                "type": "info",
                "text": "Podaj przynajmniej jeden filtr wyszukiwania."
            }
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        print(f"DEBUG Simple - conditions: {conditions}")
        print(f"DEBUG Simple - values: {values}")
        
        # Jeśli tylko liczenie
        if show_count_only:
            count_sql = f'SELECT COUNT(*) as total FROM wynikowe_dane.wyniki {where_clause}'
            print(f"DEBUG Count SQL: {count_sql}")
            print(f"DEBUG Count VALUES: {values}")
            
            count_result = db.dict_select(count_sql, values)
            total_count = count_result[0]['total'] if count_result else 0
            
            return {
                "type": "info",
                "text": f"Znaleziono łącznie {total_count:,} wyników."
            }
        
        # Główne zapytanie - proste
        sql = f'''
            SELECT id, laboratorium, zlecenie_kod_kreskowy, zlecenie_data,
                   pacjent_imie, pacjent_nazwisko, pacjent_pesel,
                   zleceniodawca_nazwa
            FROM wynikowe_dane.wyniki 
            {where_clause} 
            ORDER BY zlecenie_data DESC, id DESC
            LIMIT 100
        '''
        
        print(f"DEBUG Main SQL: {sql}")
        print(f"DEBUG Main VALUES: {values}")
        
        results = db.dict_select(sql, values)
        
        if not results:
            return {
                "type": "info",
                "text": "Brak wyników."
            }
        
        header = ['ID', 'Laboratorium', 'Kod kreskowy', 'Data zlecenia', 
                 'Imię', 'Nazwisko', 'PESEL', 'Zleceniodawca']
        
        columns = ['id', 'laboratorium', 'zlecenie_kod_kreskowy', 'zlecenie_data',
                  'pacjent_imie', 'pacjent_nazwisko', 'pacjent_pesel', 'zleceniodawca_nazwa']
        
        data = [[row.get(col) for col in columns] for row in results]
        
        return {
            "type": "table",
            "header": header,
            "data": prepare_for_json(data),
            "title": f"Znaleziono {len(results)} wyników"
        }
        
    except Exception as e:
        print(f"ERROR in raport: {e}")
        import traceback
        traceback.print_exc()
        return {
            "type": "error",
            "text": f"Błąd: {e}"
        } 