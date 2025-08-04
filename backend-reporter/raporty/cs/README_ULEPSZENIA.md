# Instrukcja instalacji i testowania ulepszeń

## 📋 Podsumowanie zmian

Zaimplementowano wszystkie wymagane funkcjonalności w pliku `RaportArchiwumWynikowStabilne.py`:

✅ **Generowanie raportu z jednego wybranego dnia**  
✅ **Wybór ID z listy zamiast wpisywania**  
✅ **Stronicowanie bez limitu danych**  
✅ **Generowanie PDF dla wszystkich znalezionych rekordów**  

## 🚀 Instalacja

### Krok 1: Backup
```bash
# Utwórz kopię zapasową obecnego raportu
cp reporter/backend-reporter/raporty/cs/RaportArchiwumWynikowStabilne.py \
   reporter/backend-reporter/raporty/cs/RaportArchiwumWynikowStabilne_BACKUP.py
```

### Krok 2: Sprawdź plik
Upewnij się, że plik `RaportArchiwumWynikowStabilne.py` zawiera wszystkie nowe funkcjonalności.

### Krok 3: Restart serwisu (jeśli potrzebne)
```bash
# Jeśli używasz systemd
sudo systemctl restart reporter

# Lub jeśli używasz innego systemu
# Sprawdź dokumentację swojego systemu
```

## 🧪 Testowanie

### Test 1: Generowanie raportu z jednego dnia

1. **Otwórz raport**: "Raport Archiwum Wyników Labor (STABILNE)"
2. **Wybierz preset**: "Jeden wybrany dzień"
3. **Wprowadź datę**: np. dzisiejsza data
4. **Kliknij "Wyszukaj"**
5. **Oczekiwany wynik**: Wyniki tylko z wybranego dnia

### Test 2: Wybór ID z listy

1. **Wykonaj wyszukiwanie** z dowolnymi filtrami
2. **Sprawdź pole "Wybrane ID rekordów"** - powinna pojawić się lista
3. **Wybierz konkretne ID** z listy
4. **Wybierz tryb**: "Generuj PDF wybranych ID"
5. **Kliknij "Wyszukaj"**
6. **Oczekiwany wynik**: Archiwum ZIP z PDF dla wybranego ID

### Test 3: Stronicowanie bez limitu

1. **Ustaw filtry wyszukiwania** (np. szeroki zakres dat)
2. **Wybierz rozmiar strony**: "Bez limitu (tylko liczenie)"
3. **Kliknij "Wyszukaj"**
4. **Oczekiwany wynik**: Informacja o całkowitej liczbie wyników
5. **Sprawdź opcję**: "Generuj PDF wszystkich"

### Test 4: Generowanie PDF wszystkich

1. **Wykonaj wyszukiwanie** z dowolnymi filtrami
2. **Wybierz tryb**: "Generuj PDF wszystkich"
3. **Wybierz tryb PDF**: "Oddzielne pliki" lub "Jeden zbiorczy plik"
4. **Wybierz typ pliku**: "PDF" lub "CDA/XML"
5. **Kliknij "Wyszukaj"**
6. **Oczekiwany wynik**: Archiwum ZIP z plikami PDF/XML

### Test 5: Przyciski akcji

1. **Wyświetl wyniki** w tabeli
2. **Sprawdź przyciski**: "📄 Generuj PDF wszystkich" i "📋 Generuj PDF wybranych"
3. **Kliknij jeden z przycisków**
4. **Oczekiwany wynik**: Automatyczne przełączenie na tryb generowania PDF

## 🔍 Diagnostyka

### Sprawdzenie logów
```bash
# Sprawdź logi aplikacji
tail -f /var/log/reporter/application.log

# Lub jeśli używasz innego systemu logowania
# Sprawdź dokumentację swojego systemu
```

### Sprawdzenie bazy danych
```sql
-- Sprawdź czy funkcja generowania PDF istnieje
SELECT EXISTS (
    SELECT 1 FROM information_schema.routines 
    WHERE routine_name = 'generuj_pdf_z_wynikami'
);

-- Sprawdź strukturę tabeli wyników
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'wyniki' 
AND table_schema = 'wynikowe_dane';
```

### Sprawdzenie uprawnień
```bash
# Sprawdź czy aplikacja ma dostęp do bazy danych
psql -h localhost -U reporter -d laboratorium_archiwum -c "SELECT 1;"
```

## ⚠️ Znane problemy i rozwiązania

### Problem 1: Brak funkcji generowania PDF
**Objawy**: Błąd "function wynikowe_dane.generuj_pdf_z_wynikami does not exist"
**Rozwiązanie**: 
- Sprawdź czy funkcja istnieje w bazie danych
- Skontaktuj się z administratorem bazy danych

### Problem 2: Puste wyniki w liście ID
**Objawy**: Lista ID jest pusta po wyszukiwaniu
**Rozwiązanie**:
- Sprawdź czy wyszukiwanie zwróciło wyniki
- Sprawdź czy wyniki zawierają pole 'id'

### Problem 3: Błąd generowania PDF
**Objawy**: "Błąd podczas generowania archiwum PDF"
**Rozwiązanie**:
- Sprawdź logi aplikacji
- Sprawdź czy wyniki zawierają dane do generowania PDF
- Sprawdź uprawnienia do zapisu plików tymczasowych

### Problem 4: Wolne generowanie PDF
**Objawy**: Długi czas generowania PDF
**Rozwiązanie**:
- Zmniejsz liczbę wyników (użyj filtrów)
- Użyj trybu "Jeden zbiorczy plik" zamiast "Oddzielne pliki"

## 📞 Wsparcie

### Logi do zbierania
W przypadku problemów zbierz następujące informacje:

1. **Logi aplikacji** z czasu wystąpienia problemu
2. **Parametry wyszukiwania** (filtry, daty, etc.)
3. **Liczba wyników** zwróconych przez wyszukiwanie
4. **Typ błędu** (jeśli występuje)
5. **Wersja aplikacji** i systemu operacyjnego

### Kontakt
W przypadku problemów skontaktuj się z zespołem deweloperskim z następującymi informacjami:
- Opis problemu
- Logi aplikacji
- Parametry wyszukiwania
- Oczekiwane vs. rzeczywiste zachowanie

## 🔄 Migracja z wersji multisync

### Porównanie funkcjonalności

| Funkcjonalność | Wersja multisync | Wersja stabilna |
|----------------|------------------|-----------------|
| Wpisywanie ID | ✅ Ręczne | ❌ Usunięte |
| Wybór ID | ❌ Brak | ✅ Lista z opisami |
| Jeden dzień | ❌ Brak | ✅ Preset + pole daty |
| Bez limitu | ❌ Brak | ✅ Tryb liczenia |
| PDF wszystkich | ❌ Brak | ✅ Pełna obsługa |
| Przyciski akcji | ❌ Brak | ✅ W tabeli wyników |

### Plan migracji

1. **Faza 1**: Testowanie nowej wersji równolegle
2. **Faza 2**: Migracja użytkowników testowych
3. **Faza 3**: Migracja wszystkich użytkowników
4. **Faza 4**: Usunięcie starej wersji

### Kompatybilność wsteczna
- Wszystkie funkcje z wersji multisync są zachowane
- Nowe funkcjonalności są opcjonalne
- Możliwość stopniowej migracji 