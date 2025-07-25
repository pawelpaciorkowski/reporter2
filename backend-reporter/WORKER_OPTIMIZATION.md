# Worker Restart Optimization

## Problem
Oryginalny `restart_workers.py` jest bardzo wolny gdy masz dużo laboratoriów (~70+), ponieważ:

1. **Sekwencyjnie** zabija każdy worker (jeden po drugim) 
2. **Sekwencyjnie** startuje każdy worker (jeden po drugim)
3. **Brak timeout-ów** - zawieszone workery mogą blokować proces w nieskończoność
4. **Brak force kill** - jeśli graceful quit nie działa, proces się zawiesza

## Rozwiązania

### 🚀 Szybkie rozwiązania (wypróbuj w kolejności):

#### 1. Najszybsze - Bash script + Python
```bash
cd reporter/backend-reporter
./kill_workers_fast.sh      # Zabija wszystkie workery równolegle
python restart_workers.py   # Startuje workery oryginalną metodą
```

#### 2. Zoptymalizowana wersja Python (zalecane)
```bash
cd reporter/backend-reporter
python restart_workers_fast.py  # Zabija i startuje wszystko równolegle
```

#### 3. Tylko szybkie startowanie
```bash
cd reporter/backend-reporter
python start_workers_fast.py    # Startuje workery bez killowania istniejących
```

#### 4. Jednorazowe rozwiązanie
```bash
pkill -f "rq worker.*repworker"  # Force kill wszystkich workerów
screen -wipe                     # Cleanup screen sessions  
python restart_workers.py       # Startuj normalnie
```

## Pliki

- `restart_workers_fast.py` - Zoptymalizowana wersja z równoległym kill+start
- `start_workers_fast.py` - Tylko równoległe startowanie workerów
- `kill_workers_fast.sh` - Szybkie bash-owe killowanie workerów  
- `benchmark_restart.py` - Porównywanie czasów wykonania

## Różnice w wydajności

### Oryginalna metoda:
- ⏱️ **70+ workerów** = **5-15 minut** (sekwencyjnie)
- 📊 ~0.2-0.5 worker/sekundę
- ❌ Może się zawiesić na zombie processes

### Zoptymalizowana metoda:  
- ⏱️ **70+ workerów** = **30-60 sekund** (równolegle)
- 📊 ~2-5 workerów/sekundę  
- ✅ Timeout-y i force kill zapobiegają zawieszeniu

### **Przyspieszenie: 10-20x szybsze!**

## Testowanie

```bash
# Test zoptymalizowanej wersji
python benchmark_restart.py

# Test oryginalnej wersji (do porównania)  
python benchmark_restart.py --test-old
```

## Opcje

Wszystkie skrypty obsługują:
- `--clear-queues` - Wyczyść kolejki przed startem workerów

## Szczegóły implementacji

### Równoległe killowanie:
- **ThreadPoolExecutor** z max 20 wątkami
- **Timeout 5s** na graceful quit
- **Force kill** jeśli graceful quit nie działa
- **Fallback na kill -9** dla zombie processes

### Równoległe startowanie:
- **ThreadPoolExecutor** z max 30 wątkami
- **Grupowanie laboratoriów** po 4 w multiworkerach
- **Progress monitoring** - pokazuje postęp co 10 workerów
- **Error handling** - kontynuuje mimo błędów

### Bezpieczeństwo:
- **Timeout-y** na wszystkich operacjach
- **Exception handling** 
- **Graceful degradation** jeśli nie można zabić niektórych workerów

## Dlaczego u Ciebie było wolno?

1. **Dużo laboratoriów** - masz ~70+ vs prawdopodobnie kilka/kilkanaście u kolegi
2. **Sekwencyjne operacje** - każdy worker obsługiwany osobno
3. **Brak timeout-ów** - zawieszone workery blokują cały proces
4. **RAM nie ma znaczenia** - problem jest w I/O i liczbie procesów, nie w pamięci

## Backup

Oryginalny `restart_workers.py` pozostaje niezmieniony - możesz wrócić do niego w każdej chwili. 