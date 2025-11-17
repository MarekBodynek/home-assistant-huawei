# Instrukcja Wdrożenia - Moduł ML Energy Management

**Data:** 2025-11-17
**Wersja:** 1.0 (Faza 1 - Data Collection)
**Dla:** Developer / Administrator systemu

---

## 🎯 CEL WDROŻENIA

Zainstalować i uruchomić moduł `energy_ml` w Home Assistant, który będzie zbierać dane historyczne do trenowania modeli Machine Learning.

**Czas wdrożenia:** ~15 minut
**Wymagane umiejętności:** Podstawowa znajomość Home Assistant, SSH, command line

---

## ✅ WYMAGANIA WSTĘPNE

### 1. System

- **Home Assistant:** Core 2023.1+ (zalecane: latest)
- **Recorder:** Włączony i skonfigurowany (min. 7 dni historii)
- **Python:** 3.11+ (domyślnie w HA)
- **Dostęp:** SSH do hosta z Home Assistant

### 2. Zależności Python

Moduł wymaga następujących bibliotek (automatycznie instalowane przez HA):

```
scikit-learn>=1.3.0
numpy>=1.24.0
pandas>=2.0.0
joblib>=1.3.0
```

### 3. Sensory Home Assistant

Moduł zbiera dane z następujących sensorów (muszą istnieć):

**Krytyczne (wymagane):**
- `sensor.akumulatory_stan_pojemnosci` - Battery SOC (%)
- `sensor.inwerter_moc_wejsciowa` - PV power (W)
- `sensor.pomiar_mocy_moc_czynna` - Grid power (W)
- `sensor.temperatura_zewnetrzna` - Temperature (°C)

**Opcjonalne (zalecane):**
- `sensor.pstryk_current_sell_price` - RCE price
- `binary_sensor.dzien_roboczy` - Workday sensor
- `binary_sensor.sezon_grzewczy` - Heating season
- `binary_sensor.pc_co_aktywne` - Heat pump status
- `sun.sun` - Sun sensor (built-in)

### 4. Przestrzeń dyskowa

- **Minimum:** 100 MB
- **Zalecane:** 500 MB (dla 30 dni danych)

---

## 📦 INSTALACJA

### Krok 1: Pobranie kodu

```bash
# SSH do hosta z Home Assistant
ssh user@192.168.0.106

# Przejdź do katalogu Home Assistant
cd /home/user/home-assistant-huawei

# Pull najnowszych zmian
git fetch origin
git checkout claude/ml-energy-consumption-01FW6TyULCkzw8kqY4Pj2WuS
git pull origin claude/ml-energy-consumption-01FW6TyULCkzw8kqY4Pj2WuS
```

### Krok 2: Weryfikacja plików

```bash
# Sprawdź czy wszystkie pliki są na miejscu
ls -la config/custom_components/energy_ml/

# Powinno pokazać:
# total XXX
# drwxr-xr-x 4 user user 4096 Nov 17 12:00 .
# drwxr-xr-x 8 user user 4096 Nov 17 12:00 ..
# -rw-r--r-- 1 user user 6XXX Nov 17 12:00 __init__.py
# -rw-r--r-- 1 user user  XXX Nov 17 12:00 const.py
# -rw-r--r-- 1 user user  XXX Nov 17 12:00 manifest.json
# -rw-r--r-- 1 user user  XXX Nov 17 12:00 services.yaml
# drwxr-xr-x 2 user user 4096 Nov 17 12:00 data
# drwxr-xr-x 2 user user 4096 Nov 17 12:00 storage

# Sprawdź katalog danych
ls -la config/ml_data/

# Jeśli nie istnieje, stwórz:
mkdir -p config/ml_data/{collected,models,logs}
```

### Krok 3: Weryfikacja konfiguracji

```bash
# Sprawdź czy energy_ml jest w configuration.yaml
grep -A2 "energy_ml" config/configuration.yaml

# Powinno pokazać:
# # Energy ML - Machine Learning for Battery Management
# energy_ml:
```

### Krok 4: Weryfikacja recorder

```bash
# Sprawdź konfigurację recordera
grep -A5 "recorder:" config/configuration.yaml

# Upewnij się że purge_keep_days >= 7 (zalecane: 30)
# recorder:
#   purge_keep_days: 30
#   db_url: sqlite:////config/home-assistant_v2.db
```

### Krok 5: Restart Home Assistant

```bash
# Opcja 1: Docker restart (szybsze)
docker restart homeassistant

# Opcja 2: Przez HA CLI (jeśli dostępne)
ha core restart

# Opcja 3: Przez UI
# Settings → System → Restart
```

**Czas restartu:** ~30-60 sekund

---

## 🔍 WERYFIKACJA INSTALACJI

### Krok 1: Sprawdź logi startowe

```bash
# Przeczytaj logi HA
tail -n 100 config/home-assistant.log | grep energy_ml

# Szukaj kluczowych linii:
# ✅ [custom_components.energy_ml] Energy ML component initialized
# ✅ [custom_components.energy_ml] Energy ML services registered
# ✅ [custom_components.energy_ml] Starting Energy ML data collection
# ✅ [custom_components.energy_ml] Scheduled data collection every 1 hours

# Jeśli widzisz błędy:
tail -n 200 config/home-assistant.log | grep -i "error\|warning" | grep energy_ml
```

### Krok 2: Weryfikacja serwisów

**Przez UI:**
1. Otwórz Home Assistant: http://192.168.0.106:8123
2. Developer Tools → Services
3. Znajdź domenę: `energy_ml`
4. Powinny być 3 serwisy:
   - `energy_ml.collect_historical_data`
   - `energy_ml.collect_and_process`
   - `energy_ml.get_storage_stats`

**Przez command line:**

```bash
# Wywołaj API HA (wymaga long-lived access token)
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8123/api/services

# Szukaj "energy_ml" w odpowiedzi
```

### Krok 3: Test serwisu statystyk

**Przez UI:**
1. Developer Tools → Services
2. Service: `energy_ml.get_storage_stats`
3. Call Service
4. Sprawdź powiadomienie (Notifications bell icon)

**Oczekiwany rezultat:**
```
Energy ML Storage Statistics

Data files: 0
Model files: 0
Log files: 0
Total size: 0.00 MB
```

---

## 🚀 PIERWSZE URUCHOMIENIE

### Krok 1: Zbierz dane historyczne (30 dni)

**Przez UI (ZALECANE):**

1. Developer Tools → Services
2. Service: `energy_ml.collect_and_process`
3. Service Data (YAML):
   ```yaml
   days: 30
   ```
4. **Call Service**

**Przez automation (alternatywa):**

```yaml
# config/automations.yaml
- id: ml_first_data_collection
  alias: "[ML] Pierwszy zbiór danych"
  trigger:
    - platform: homeassistant
      event: start
  condition:
    # Uruchom tylko raz
    - condition: template
      value_template: >
        {{ states('input_boolean.ml_initial_collection_done') == 'off' }}
  action:
    - service: energy_ml.collect_and_process
      data:
        days: 30
    - service: input_boolean.turn_on
      target:
        entity_id: input_boolean.ml_initial_collection_done
```

### Krok 2: Monitoruj zbieranie

```bash
# Śledź logi w real-time
tail -f config/home-assistant.log | grep energy_ml

# Szukaj sekwencji:
# [energy_ml] Service called: collect_and_process (days=30)
# [energy_ml] Step 1/4: Collecting historical data...
# [energy_ml] Collecting historical data from 2025-10-18 to 2025-11-17 (30 days, 13 sensors)
# [energy_ml] Collected XXX records for sensor.akumulatory_stan_pojemnosci
# [energy_ml] Historical data collected: XXX rows, YY columns
# [energy_ml] Step 2/4: Aggregating to hourly intervals...
# [energy_ml] Hourly data: 720 rows
# [energy_ml] Step 3/4: Cleaning and preprocessing...
# [energy_ml] Removed X outliers from battery_soc
# [energy_ml] Data cleaning complete: 720 rows, YY columns, quality: 95.0%
# [energy_ml] Step 4/4: Engineering features...
# [energy_ml] Added calendar features
# [energy_ml] Added lag features for 4 columns
# [energy_ml] Added rolling features for 4 columns
# [energy_ml] Added solar features
# [energy_ml] Added energy balance features
# [energy_ml] Added interaction features
# [energy_ml] Feature engineering complete: 720 rows, 40+ features
# [energy_ml] Features saved: /config/ml_data/collected/features_data_YYYYMMDD_HHMMSS.csv
# [energy_ml] Data collection complete: 720 rows, 45 features, quality: 95.3%
```

**Czas wykonania:** 30-60 sekund (zależnie od ilości danych w recorder)

### Krok 3: Weryfikacja zebranych danych

```bash
# Sprawdź czy pliki CSV zostały utworzone
ls -lh config/ml_data/collected/

# Powinno pokazać:
# -rw-r--r-- 1 user user  XXX Nov 17 12:30 features_data_20251117_123000.csv

# Podgląd danych
head -n 5 config/ml_data/collected/features_data_*.csv

# Sprawdź liczbę linii (powinno być ~720 dla 30 dni)
wc -l config/ml_data/collected/features_data_*.csv
```

### Krok 4: Analiza danych (opcjonalnie)

```bash
# Zainstaluj csvkit (jeśli nie ma)
pip3 install csvkit

# Podgląd statystyk
csvstat config/ml_data/collected/features_data_*.csv

# Pokaż kolumny
head -n 1 config/ml_data/collected/features_data_*.csv | tr ',' '\n' | nl
```

---

## 📊 WERYFIKACJA JAKOŚCI DANYCH

### Sprawdź kompletność danych

```bash
# Przeczytaj logi z ostatniego zbierania
grep "Data collection complete" config/home-assistant.log | tail -1

# Szukaj:
# Data collection complete: 720 rows, 45 features, quality: XX.X%
```

**Oczekiwane wartości:**
- **Rows:** 720 (30 dni × 24h) ± 10%
- **Features:** 40-50 (zależnie od dostępnych sensorów)
- **Quality:** > 70% (min), > 90% (idealnie)

### Sprawdź missing data

```python
# Opcjonalnie: Python analysis
python3 << 'EOF'
import pandas as pd
import glob

# Znajdź najnowszy plik
files = glob.glob('/config/ml_data/collected/features_data_*.csv')
latest = max(files, key=lambda x: x.split('_')[-2] + x.split('_')[-1])

# Wczytaj
df = pd.read_csv(latest, index_col=0, parse_dates=True)

# Statystyki
print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")
print(f"\nMissing data:")
print(df.isna().sum().sort_values(ascending=False).head(10))
print(f"\nData types:")
print(df.dtypes.value_counts())
EOF
```

---

## 🔧 TROUBLESHOOTING

### Problem 1: "Module not found: energy_ml"

**Objaw:**
```
[homeassistant] Unable to set up dependencies of energy_ml
```

**Diagnoza:**
```bash
# Sprawdź czy katalog istnieje
ls -la config/custom_components/energy_ml/

# Sprawdź manifest.json
cat config/custom_components/energy_ml/manifest.json
```

**Rozwiązanie:**
```bash
# Upewnij się że wszystkie pliki są na miejscu
cd /home/user/home-assistant-huawei
git pull origin claude/ml-energy-consumption-01FW6TyULCkzw8kqY4Pj2WuS

# Restart HA
docker restart homeassistant
```

### Problem 2: "No historical data collected"

**Objaw:**
```
[energy_ml] No historical data collected
[energy_ml] No data collected
```

**Diagnoza:**
```bash
# Sprawdź czy recorder działa
grep "recorder" config/home-assistant.log | tail -20

# Sprawdź czy sensory istnieją
grep "sensor.akumulatory_stan_pojemnosci" config/home-assistant.log | tail -5
```

**Rozwiązanie:**

1. **Sprawdź recorder:**
   ```yaml
   # configuration.yaml
   recorder:
     purge_keep_days: 30  # Min. 7 dni
     db_url: sqlite:////config/home-assistant_v2.db
   ```

2. **Sprawdź sensory:**
   - Otwórz Developer Tools → States
   - Znajdź: `sensor.akumulatory_stan_pojemnosci`
   - Sprawdź czy ma historię (Graph icon)

3. **Zmniejsz zakres:**
   ```yaml
   # Spróbuj zbierać tylko 7 dni
   days: 7
   ```

### Problem 3: "Data quality too low"

**Objaw:**
```
[energy_ml] Data validation failed: Data quality too low: 65% (minimum: 70%)
```

**Diagnoza:**
```bash
# Sprawdź szczegóły preprocessing
grep "Preprocessing stats" config/home-assistant.log | tail -1
```

**Rozwiązanie:**

1. **Poczekaj na więcej danych** (min. 7 dni od instalacji HA)

2. **Usuń problematyczne sensory:**
   ```python
   # config/custom_components/energy_ml/const.py
   # Zakomentuj sensory których nie ma:
   SENSORS_TO_COLLECT = {
       "battery_soc": "sensor.akumulatory_stan_pojemnosci",
       "pv_power": "sensor.inwerter_moc_wejsciowa",
       # "rce_price": "sensor.pstryk_current_sell_price",  # ZAKOMENTOWANE
   }
   ```

3. **Obniż próg jakości (nie zalecane):**
   ```python
   # config/custom_components/energy_ml/const.py
   MAX_MISSING_DATA_PERCENT = 0.30  # Było: 0.20
   ```

### Problem 4: "Import error: sklearn/pandas/numpy"

**Objaw:**
```
ModuleNotFoundError: No module named 'sklearn'
```

**Rozwiązanie:**
```bash
# Zainstaluj zależności w środowisku HA
docker exec -it homeassistant bash
pip3 install scikit-learn numpy pandas joblib
exit

# Restart HA
docker restart homeassistant
```

### Problem 5: "Permission denied: /config/ml_data/"

**Objaw:**
```
PermissionError: [Errno 13] Permission denied: '/config/ml_data/collected/'
```

**Rozwiązanie:**
```bash
# Ustaw prawidłowe uprawnienia
sudo chown -R user:user config/ml_data/
sudo chmod -R 755 config/ml_data/

# Lub stwórz katalogi ręcznie jako user
mkdir -p config/ml_data/{collected,models,logs}
```

---

## 📈 MONITORING PRODUKCYJNY

### Automatyczna weryfikacja (zalecane)

**Dodaj automation do monitoringu:**

```yaml
# config/automations.yaml
- id: ml_health_check
  alias: "[ML] Health Check"
  trigger:
    - platform: time
      at: "12:00:00"  # Codziennie w południe
  action:
    - service: energy_ml.get_storage_stats

    # Sprawdź czy są dane
    - condition: template
      value_template: >
        {{ states('sensor.ml_data_files') | int > 0 }}

    # Jeśli brak danych - powiadom
    - choose:
        - conditions:
            - condition: template
              value_template: >
                {{ states('sensor.ml_data_files') | int == 0 }}
          sequence:
            - service: persistent_notification.create
              data:
                title: "⚠️ ML: Brak danych"
                message: "Moduł ML nie zebrał jeszcze żadnych danych. Uruchom serwis energy_ml.collect_and_process"
```

### Logi produkcyjne

```bash
# Rotacja logów
# Dodaj do crontab:
0 2 * * 0 find /home/user/home-assistant-huawei/config/ml_data/collected/ -type f -mtime +30 -delete
```

### Backup

```yaml
# config/automations.yaml
- id: ml_weekly_backup
  alias: "[ML] Weekly Backup"
  trigger:
    - platform: time
      at: "03:00:00"
  condition:
    - condition: time
      weekday: sun
  action:
    - service: shell_command.backup_ml_data

# config/configuration.yaml
shell_command:
  backup_ml_data: 'tar -czf /backup/ml_data_$(date +\%Y\%m\%d).tar.gz /config/ml_data/'
```

---

## 🎯 NEXT STEPS

### Po 7 dniach zbierania danych

Gdy będziemy mieć minimum 7 dni danych (720 godzin), wdrożymy **Fazę 2: Trenowanie modeli**.

**Co będzie zawierać Faza 2:**

1. **ML Models:**
   - `models/consumption_model.py` - RandomForest
   - `models/production_model.py` - GradientBoosting
   - `models/battery_optimizer.py` - Optimizer

2. **ML Core:**
   - `ml/trainer.py` - Trenowanie
   - `ml/predictor.py` - Predykcje
   - `ml/evaluator.py` - Metryki

3. **Sensory HA:**
   - `sensor.ml_consumption_next_24h`
   - `sensor.ml_production_next_24h`
   - `sensor.ml_battery_target_soc`
   - `sensor.ml_confidence_score`

4. **Automatyczne trenowanie:**
   - Codziennie o 01:00 - retrain
   - Co niedzielę o 02:00 - full retrain

**Oszacowany czas implementacji Fazy 2:** 3-5 dni

---

## 📞 WSPARCIE TECHNICZNE

### Logi diagnostyczne

```bash
# Pełne logi energy_ml
grep energy_ml config/home-assistant.log > /tmp/energy_ml_debug.log

# Ostatnie 100 linii z timestamp
tail -100 config/home-assistant.log | grep energy_ml | awk '{print $1, $2, $NF}'

# Błędy i warningi
grep -E "ERROR|WARNING" config/home-assistant.log | grep energy_ml
```

### Dokumentacja

1. **Projekt architektury:** `/ML_MODULE_DESIGN.md` (71 stron)
2. **Instrukcja użytkownika:** `/ML_DATA_COLLECTOR_README.md`
3. **Ten dokument:** `/DEPLOYMENT_GUIDE.md`

### Kontakt

- **Issues:** GitHub repository
- **Logs:** `/config/home-assistant.log`
- **Data:** `/config/ml_data/collected/`

---

## ✅ CHECKLIST WDROŻENIA

Przejdź przez tę checklistę aby upewnić się że wszystko działa:

- [ ] Kod pobrany z Git (`claude/ml-energy-consumption-01FW6TyULCkzw8kqY4Pj2WuS`)
- [ ] Pliki `energy_ml` istnieją w `/config/custom_components/`
- [ ] Katalog `/config/ml_data/` utworzony z poprawnymi uprawnieniami
- [ ] `energy_ml:` dodane do `configuration.yaml`
- [ ] Home Assistant zrestartowany
- [ ] Logi pokazują: "Energy ML component initialized"
- [ ] Logi pokazują: "Energy ML services registered"
- [ ] Serwisy widoczne w Developer Tools → Services
- [ ] `energy_ml.get_storage_stats` działa
- [ ] `energy_ml.collect_and_process` wywołany (days: 30)
- [ ] Zbieranie zakończone bez błędów
- [ ] Plik CSV utworzony w `/config/ml_data/collected/`
- [ ] Dane zawierają ~720 linii (30 dni)
- [ ] Data quality > 70%
- [ ] Automatyczne zbieranie co 1h działa

**Jeśli wszystko ✅ - WDROŻENIE ZAKOŃCZONE!** 🎉

---

## 📊 PRZYKŁAD POPRAWNEGO WDROŻENIA

### Terminal output (success):

```bash
$ docker restart homeassistant
homeassistant

$ tail -f config/home-assistant.log | grep energy_ml
2025-11-17 12:00:15 INFO [custom_components.energy_ml] Energy ML component initialized
2025-11-17 12:00:15 INFO [custom_components.energy_ml] Energy ML services registered
2025-11-17 12:00:16 INFO [custom_components.energy_ml] Starting Energy ML data collection
2025-11-17 12:00:16 INFO [custom_components.energy_ml] Scheduled data collection every 1 hours
2025-11-17 12:05:30 INFO [custom_components.energy_ml] Service called: collect_and_process (days=30)
2025-11-17 12:05:30 INFO [custom_components.energy_ml] Step 1/4: Collecting historical data...
2025-11-17 12:05:45 INFO [custom_components.energy_ml] Historical data collected: 720 rows, 13 columns
2025-11-17 12:05:45 INFO [custom_components.energy_ml] Step 2/4: Aggregating to hourly intervals...
2025-11-17 12:05:46 INFO [custom_components.energy_ml] Hourly data: 720 rows
2025-11-17 12:05:46 INFO [custom_components.energy_ml] Step 3/4: Cleaning and preprocessing...
2025-11-17 12:05:48 INFO [custom_components.energy_ml] Data cleaning complete: 720 rows, 13 columns, quality: 94.5%
2025-11-17 12:05:48 INFO [custom_components.energy_ml] Step 4/4: Engineering features...
2025-11-17 12:05:52 INFO [custom_components.energy_ml] Feature engineering complete: 720 rows, 45 features
2025-11-17 12:05:52 INFO [custom_components.energy_ml] Features saved: /config/ml_data/collected/features_data_20251117_120552.csv
2025-11-17 12:05:52 INFO [custom_components.energy_ml] Data collection complete: 720 rows, 45 features, quality: 94.5%

$ ls -lh config/ml_data/collected/
total 256K
-rw-r--r-- 1 user user 250K Nov 17 12:05 features_data_20251117_120552.csv

$ wc -l config/ml_data/collected/features_data_20251117_120552.csv
721 config/ml_data/collected/features_data_20251117_120552.csv
# 721 = 720 rows + 1 header

✅ WDROŻENIE ZAKOŃCZONE SUKCESEM!
```

---

**Autor:** Claude Code
**Data:** 2025-11-17
**Wersja:** 1.0
**Status:** Production Ready ✅

