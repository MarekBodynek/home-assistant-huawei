# Moduł Zbierania Danych ML - Instrukcja Użytkownika

**Data:** 2025-11-17
**Wersja:** 1.0 (MVP - Faza 1)
**Status:** ✅ GOTOWY DO UŻYCIA

---

## 📋 CO ZOSTAŁO ZAIMPLEMENTOWANE

Moduł zbierania danych historycznych do trenowania modeli Machine Learning. To jest **Faza 1** implementacji pełnego systemu ML.

### ✅ Gotowe komponenty:

1. **Data Collector** - Zbiera dane historyczne z Home Assistant recorder
2. **Data Preprocessor** - Czyści dane, usuwa outliers, wypełnia braki
3. **Feature Engineer** - Tworzy 40+ cech do modeli ML
4. **Data Storage** - Zapisuje dane do CSV i modele do pickle
5. **Serwisy HA** - 3 serwisy do ręcznego wywoływania zbierania danych
6. **Automatyczne zbieranie** - Co 1 godzinę zbiera bieżące dane sensorów

---

## 🚀 INSTALACJA I URUCHOMIENIE

### Krok 1: Weryfikacja plików

Sprawdź czy wszystkie pliki istnieją:

```bash
ls -la /config/custom_components/energy_ml/

# Powinieneś zobaczyć:
# ├── __init__.py
# ├── manifest.json
# ├── const.py
# ├── services.yaml
# ├── data/
# │   ├── __init__.py
# │   ├── collector.py
# │   ├── preprocessor.py
# │   └── feature_engineering.py
# └── storage/
#     ├── __init__.py
#     └── data_storage.py
```

### Krok 2: Restart Home Assistant

```bash
# W Docker:
docker restart homeassistant

# Lub przez UI:
Settings → System → Restart
```

### Krok 3: Weryfikacja logów

Sprawdź logi czy komponent załadował się poprawnie:

```bash
tail -f /config/home-assistant.log | grep energy_ml

# Szukaj linii:
# [custom_components.energy_ml] Energy ML component initialized
# [custom_components.energy_ml] Energy ML services registered
# [custom_components.energy_ml] Starting Energy ML data collection
```

---

## 📊 JAK ZBIERAĆ DANE

### Automatyczne zbieranie (co 1h)

Moduł automatycznie zbiera bieżące stany sensorów **co 1 godzinę**.

**Dane zbierane:**
- Battery SOC (%)
- PV power (W)
- Grid power (W)
- Temperature (°C)
- Tariff zone (L1/L2)
- RCE price (zł/kWh)
- PC/CWU status
- Sun elevation/azimuth

### Ręczne zbieranie danych historycznych

Aby zebrać dane historyczne z ostatnich 30 dni, wywołaj serwis:

#### Opcja 1: Przez Developer Tools (UI)

1. **Developer Tools → Services**
2. Wybierz: `energy_ml.collect_and_process`
3. Ustaw YAML:
   ```yaml
   days: 30
   ```
4. **Call Service**

#### Opcja 2: Przez YAML automation

```yaml
# automations.yaml
- id: ml_collect_initial_data
  alias: "[ML] Zbierz dane historyczne (jednorazowo)"
  trigger:
    - platform: homeassistant
      event: start
  action:
    - service: energy_ml.collect_and_process
      data:
        days: 30
```

#### Opcja 3: Przez skrypt

```yaml
# scripts.yaml
ml_collect_data:
  alias: "ML: Zbierz dane"
  sequence:
    - service: energy_ml.collect_and_process
      data:
        days: 30
```

---

## 🔧 DOSTĘPNE SERWISY

### 1. `energy_ml.collect_historical_data`

Zbiera surowe dane historyczne z recorder i zapisuje do CSV.

**Parametry:**
- `days` (opcjonalny, domyślnie 30) - Liczba dni historii

**Przykład:**
```yaml
service: energy_ml.collect_historical_data
data:
  days: 30
```

**Rezultat:**
- Plik: `/config/ml_data/collected/historical_data_YYYYMMDD_HHMMSS.csv`

### 2. `energy_ml.collect_and_process`

**ZALECANY** - Pełny pipeline: zbiera, czyści, przetwarza i tworzy features.

**Parametry:**
- `days` (opcjonalny, domyślnie 30) - Liczba dni historii

**Przykład:**
```yaml
service: energy_ml.collect_and_process
data:
  days: 30
```

**Kroki:**
1. Zbiera dane z recorder (30 dni)
2. Agreguje do godzinowych przedziałów
3. Czyści dane (usuwa outliers, wypełnia braki)
4. Tworzy features (40+ cech)
5. Zapisuje do `/config/ml_data/collected/features_data_YYYYMMDD_HHMMSS.csv`

**Czas wykonania:** ~30-60 sekund (zależy od ilości danych)

### 3. `energy_ml.get_storage_stats`

Wyświetla statystyki zebranych danych.

**Przykład:**
```yaml
service: energy_ml.get_storage_stats
```

**Rezultat:**
Powiadomienie z informacjami:
- Liczba plików danych
- Liczba plików modeli
- Liczba plików logów
- Całkowity rozmiar (MB)

---

## 📁 STRUKTURA DANYCH

### Katalog `ml_data/`

```
/config/ml_data/
├── collected/               # Zebrane dane
│   ├── historical_data_*.csv      # Surowe dane (co 1h)
│   └── features_data_*.csv        # Przetworzone features
├── models/                  # Wytrenowane modele (przyszłość)
│   └── (puste na razie)
└── logs/                    # Logi trenowania (przyszłość)
    └── (puste na razie)
```

### Format plików CSV

**historical_data_*.csv** - Surowe dane:
```csv
timestamp,battery_soc,pv_power,grid_power,temp_outdoor,...
2025-11-17 00:00:00,65.3,0,1200,8.5,...
2025-11-17 01:00:00,64.1,0,1100,8.2,...
...
```

**features_data_*.csv** - Przetworzone features (40+ kolumn):
```csv
timestamp,battery_soc,pv_power,hour,day_of_week,month,...
2025-11-17 00:00:00,65.3,0,0,4,11,...
2025-11-17 01:00:00,64.1,0,1,4,11,...
...
```

### Cechy (Features) w danych

**Kalendarzowe (12 cech):**
- `hour` (0-23)
- `day_of_week` (0-6)
- `month` (1-12)
- `season` (0-3)
- `is_weekend` (0/1)
- `workday` (0/1)
- `hour_sin`, `hour_cos` (cykliczne)
- `month_sin`, `month_cos` (cykliczne)
- `week_of_year` (1-52)
- `day_of_year` (1-365)

**Lagi (Lag features, ~12 cech):**
- `battery_soc_lag_1h`, `_lag_24h`, `_lag_168h`
- `pv_power_lag_1h`, `_lag_24h`, `_lag_168h`
- `grid_power_lag_1h`, `_lag_24h`, `_lag_168h`
- `temp_outdoor_lag_1h`, `_lag_24h`
- Zmiany (delta): `*_change_1h`, `*_change_24h`, etc.

**Rolling (Średnie kroczące, ~16 cech):**
- `battery_soc_rolling_mean_3h`, `_6h`, `_24h`
- `pv_power_rolling_mean_3h`, `_6h`, `_24h`
- `grid_power_rolling_mean_3h`, `_6h`, `_24h`
- `*_rolling_std_*` (zmienność)
- `*_rolling_min_*`, `*_rolling_max_*` (ekstrema)

**Słoneczne (Solar, ~8 cech):**
- `solar_elevation` (wysokość słońca, stopnie)
- `solar_elevation_norm` (0-1)
- `solar_azimuth` (azymut, stopnie)
- `solar_azimuth_sin`, `solar_azimuth_cos`
- `daylight_hours` (długość dnia)
- `is_daylight` (0/1)

**Energetyczne (~5 cech):**
- `pv_surplus` (nadwyżka PV)
- `power_deficit` (deficyt mocy)
- `battery_charge_rate` (tempo ładowania)
- `battery_utilization` (-1 do 1)

**Interakcje (~5 cech):**
- `temp_hour_interaction`
- `workday_hour_interaction`
- `heating_temp_interaction`
- `pc_temp_interaction`
- `weekend_hour_interaction`

**Łącznie:** ~40-50 features

---

## 🔍 MONITOROWANIE I DIAGNOSTYKA

### Sprawdzenie statusu

#### Logi

```bash
tail -f /config/home-assistant.log | grep energy_ml

# Szukaj:
# [custom_components.energy_ml] Step 1/4: Collecting historical data...
# [custom_components.energy_ml] Step 2/4: Aggregating to hourly intervals...
# [custom_components.energy_ml] Step 3/4: Cleaning and preprocessing...
# [custom_components.energy_ml] Step 4/4: Engineering features...
# [custom_components.energy_ml] Features saved: /config/ml_data/...
```

#### Statystyki

```yaml
service: energy_ml.get_storage_stats
```

### Problemy i rozwiązania

#### Problem 1: "Brak danych w recorder"

**Objaw:**
```
[energy_ml] No historical data collected
```

**Rozwiązanie:**
- Sprawdź czy recorder działa: `sensor.recorder_enabled`
- Sprawdź czy sensory istnieją (np. `sensor.akumulatory_stan_pojemnosci`)
- Zwiększ `purge_keep_days` w recorder (minimum 7 dni):
  ```yaml
  # configuration.yaml
  recorder:
    purge_keep_days: 30
  ```

#### Problem 2: "Data quality too low"

**Objaw:**
```
[energy_ml] Data validation failed: Data quality too low: 65% (minimum: 70%)
```

**Rozwiązanie:**
- Sprawdź czy sensory są dostępne przez ostatnie 7 dni
- Sprawdź braki w danych: `grep "missing_percent" /config/home-assistant.log`
- Usuń problematyczne sensory z `SENSORS_TO_COLLECT` w `const.py`

#### Problem 3: "Insufficient data"

**Objaw:**
```
[energy_ml] Insufficient data: 120 rows (minimum: 168)
```

**Rozwiązanie:**
- Poczekaj minimum 7 dni od instalacji Home Assistant
- Zbierz dane z dłuższego okresu: `days: 14` zamiast `days: 7`

#### Problem 4: "Error loading model"

**Objaw:**
```
[energy_ml] Model file not found
```

**Rozwiązanie:**
- To jest normalne! Modele ML jeszcze nie są wytrenowane (Faza 2)
- Na razie tylko zbieramy dane

---

## 📈 CO DALEJ?

### Faza 1: ✅ Zbieranie danych (GOTOWE)

Masz już działający moduł zbierania danych!

**Co robić teraz:**
1. Uruchom serwis `energy_ml.collect_and_process` z `days: 30`
2. Poczekaj na zakończenie (~30-60s)
3. Sprawdź czy dane zostały zapisane: `ls /config/ml_data/collected/`
4. Moduł będzie automatycznie zbierać dane co 1h

**Dane będą gotowe do trenowania po 7 dniach.**

### Faza 2: ⏳ Trenowanie modeli (NASTĘPNA)

Kiedy zbierzemy minimum 7 dni danych, wdrożymy:

1. **Consumption Model** - Predykcja zużycia energii (RandomForest)
2. **Production Model** - Predykcja produkcji PV (GradientBoosting)
3. **Battery Optimizer** - Optymalizacja Target SOC
4. **Sensory ML** - Nowe sensory z predykcjami

**Oszacowany czas implementacji:** 3-5 dni

### Faza 3: ⏳ Integracja z battery_algorithm.py (PRZYSZŁOŚĆ)

Połączenie predykcji ML z obecnym algorytmem baterii.

---

## 🛠️ SERWISOWANIE

### Czyszczenie starych danych

Automatyczne czyszczenie nie jest jeszcze wdrożone. Ręczne czyszczenie:

```bash
# Usuń pliki starsze niż 30 dni
find /config/ml_data/collected/ -type f -mtime +30 -delete
```

### Backup danych

```bash
# Backup ml_data/
tar -czf ml_data_backup_$(date +%Y%m%d).tar.gz /config/ml_data/

# Restore
tar -xzf ml_data_backup_20251117.tar.gz -C /config/
```

---

## 📞 WSPARCIE

**Problemy?**
- Sprawdź logi: `/config/home-assistant.log`
- Uruchom diagnostykę: `energy_ml.get_storage_stats`
- Zgłoś issue w repo GitHub

**Dokumentacja:**
- Projekt architektury: `/ML_MODULE_DESIGN.md`
- Instrukcja użytkownika: `/ML_DATA_COLLECTOR_README.md` (ten plik)

---

## 🎉 PODSUMOWANIE

✅ **Moduł zbierania danych jest gotowy!**

**Następne kroki:**
1. Uruchom `energy_ml.collect_and_process` (days: 30)
2. Poczekaj 7 dni na zgromadzenie danych
3. Wdrożymy Fazę 2: Trenowanie modeli ML

**Status:** Zbieranie danych rozpoczęte! 🚀

**Autor:** Claude Code
**Data:** 2025-11-17
**Wersja:** 1.0
