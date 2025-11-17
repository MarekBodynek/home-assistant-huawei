# Moduł Machine Learning - Zarządzanie Energią
## Projekt architektury i implementacji

**Autor:** Claude Code
**Data:** 2025-11-17
**Wersja:** 1.0

---

## 1. STRESZCZENIE WYKONAWCZE

Moduł ML (Machine Learning) to inteligentny system predykcji i optymalizacji zarządzania energią w systemie fotowoltaicznym z baterią Huawei Luna 15kWh.

### Cele główne:
1. **Predykcja zużycia energii** - przewidywanie zapotrzebowania na energię z dokładnością >85%
2. **Predykcja produkcji PV** - przewidywanie produkcji z paneli słonecznych (lepsze niż Forecast.Solar)
3. **Rekomendacje zarządzania baterią** - optymalizacja ładowania/rozładowania w oparciu o ML
4. **Uczenie się wzorców** - adaptacja do rzeczywistych wzorców użycia energii w gospodarstwie

### Wartość biznesowa:
- **Oszczędności:** 15-25% redukcja kosztów energii (vs algorytm regułowy)
- **Autonomia:** Samouczący się system bez konieczności ręcznej konfiguracji progów
- **Dokładność:** Predykcje oparte na rzeczywistych danych historycznych, nie na szacunkach

---

## 2. ARCHITEKTURA SYSTEMU

### 2.1 Struktura plików

```
config/
├── custom_components/
│   └── energy_ml/                    # Nowy custom component
│       ├── __init__.py               # Inicjalizacja komponentu
│       ├── manifest.json             # Metadata komponentu
│       ├── const.py                  # Stałe i konfiguracja
│       ├── coordinator.py            # DataUpdateCoordinator
│       ├── sensor.py                 # Sensory ML
│       ├── config_flow.py            # Konfiguracja UI
│       │
│       ├── data/                     # Moduł zbierania danych
│       │   ├── __init__.py
│       │   ├── collector.py          # Zbieranie danych z recorder
│       │   ├── preprocessor.py       # Preprocessing i czyszczenie
│       │   └── feature_engineering.py # Feature engineering
│       │
│       ├── models/                   # Modele ML
│       │   ├── __init__.py
│       │   ├── consumption_model.py  # Model predykcji zużycia
│       │   ├── production_model.py   # Model predykcji produkcji PV
│       │   ├── battery_optimizer.py  # Optymalizator baterii
│       │   └── model_manager.py      # Zarządzanie modelami
│       │
│       ├── ml/                       # Core ML utilities
│       │   ├── __init__.py
│       │   ├── trainer.py            # Trenowanie modeli
│       │   ├── predictor.py          # Predykcje
│       │   └── evaluator.py          # Ewaluacja modeli
│       │
│       └── storage/                  # Persystencja
│           ├── __init__.py
│           ├── model_storage.py      # Zapis/odczyt modeli
│           └── cache.py              # Cache predykcji
│
├── ml_data/                          # Dane ML (gitignored)
│   ├── models/                       # Wytrenowane modele (.pkl)
│   ├── cache/                        # Cache predykcji
│   └── logs/                         # Logi trenowania
│
└── python_scripts/
    └── ml_integration.py             # Skrypt integracji z battery_algorithm.py
```

### 2.2 Przepływ danych

```
┌─────────────────────────────────────────────────────────────────┐
│                     HOME ASSISTANT RECORDER                      │
│           (Historia 30 dni: sensory, weather, taryfy)            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────────┐
         │   DATA COLLECTOR              │
         │   - Pobiera dane z recorder   │
         │   - Agreguje co 1h            │
         │   - Czyści dane (NaN, outliers)│
         └───────────┬───────────────────┘
                     │
                     ▼
         ┌───────────────────────────────┐
         │   FEATURE ENGINEERING         │
         │   - Kalendarzowe (DoW, hour)  │
         │   - Pogodowe (temp, clouds)   │
         │   - Lagi (1h, 24h, 7d ago)    │
         │   - Średnie kroczące (3h, 6h) │
         │   - Strefa taryfowa           │
         └───────────┬───────────────────┘
                     │
         ┌───────────┴────────────┐
         │                        │
         ▼                        ▼
┌─────────────────┐      ┌──────────────────┐
│ CONSUMPTION     │      │ PRODUCTION       │
│ MODEL           │      │ MODEL            │
│ (RandomForest)  │      │ (GradientBoost)  │
│                 │      │                  │
│ Input:          │      │ Input:           │
│ - Hour, DoW     │      │ - Solar angle    │
│ - Temp, Season  │      │ - Clouds forecast│
│ - Workday       │      │ - Historical PV  │
│ - PC status     │      │ - Temp           │
│                 │      │                  │
│ Output:         │      │ Output:          │
│ - kWh next 24h  │      │ - kWh next 24h   │
└────────┬────────┘      └────────┬─────────┘
         │                        │
         └────────────┬───────────┘
                      │
                      ▼
         ┌────────────────────────────┐
         │ BATTERY OPTIMIZER          │
         │ - Oblicza bilans energii   │
         │ - Optymalizuje Target SOC  │
         │ - Rekomenduje ładowanie    │
         └────────────┬───────────────┘
                      │
                      ▼
         ┌────────────────────────────┐
         │ ML SENSORS                 │
         │ - sensor.ml_consumption_*  │
         │ - sensor.ml_production_*   │
         │ - sensor.ml_battery_target │
         │ - sensor.ml_confidence     │
         └────────────┬───────────────┘
                      │
                      ▼
         ┌────────────────────────────┐
         │ BATTERY ALGORITHM          │
         │ (battery_algorithm.py)     │
         │ - Używa predykcji ML       │
         │ - Fallback: Forecast.Solar │
         └────────────────────────────┘
```

---

## 3. DANE WEJŚCIOWE (FEATURES)

### 3.1 Dane historyczne (z recorder)

**Źródło:** Home Assistant Recorder (SQLite, 30 dni historii)

#### 3.1.1 Sensory energii:
- `sensor.akumulatory_stan_pojemnosci` - SOC baterii (%)
- `sensor.inwerter_moc_wejsciowa` - Moc PV (W)
- `sensor.pomiar_mocy_moc_czynna` - Moc z/do sieci (W)
- `sensor.inwerter_dzienna_produkcja` - Produkcja PV dzienna (kWh)
- `sensor.akumulatory_moc_ladowania_rozladowania` - Moc baterii (W)

#### 3.1.2 Sensory pogody:
- `sensor.temperatura_zewnetrzna` - Temperatura (°C)
- `weather.forecast_dom` - Prognoza pogody (cloudiness, precipitation)

#### 3.1.3 Sensory taryfowe:
- `sensor.strefa_taryfowa` - L1/L2
- `sensor.pstryk_current_sell_price` - Cena RCE (zł/kWh)
- `binary_sensor.dzien_roboczy` - Dzień roboczy/święto

#### 3.1.4 Sensory PC/CWU:
- `binary_sensor.sezon_grzewczy` - Sezon grzewczy on/off
- `binary_sensor.pc_co_aktywne` - Pompa ciepła CO aktywna
- `binary_sensor.okno_cwu` - Okno CWU aktywne

### 3.2 Feature Engineering

#### 3.2.1 Cechy kalendarzowe:
```python
- hour: int (0-23)               # Godzina dnia
- day_of_week: int (0-6)         # Dzień tygodnia (0=poniedziałek)
- is_weekend: bool               # Weekend
- is_workday: bool               # Dzień roboczy (wykrywa święta!)
- month: int (1-12)              # Miesiąc
- season: int (0-3)              # Sezon (0=zima, 1=wiosna, 2=lato, 3=jesień)
- week_of_year: int (1-52)       # Tydzień roku
```

#### 3.2.2 Cechy pogodowe:
```python
- temp_outdoor: float            # Temperatura zewnętrzna (°C)
- temp_1h_ago: float             # Temperatura 1h temu
- temp_24h_ago: float            # Temperatura 24h temu
- temp_change_1h: float          # Zmiana temperatury (delta)
- cloudiness: float (0-1)        # Zachmurzenie (z weather forecast)
- precipitation_prob: float      # Prawdopodobieństwo opadów
- is_heating_season: bool        # Sezon grzewczy (temp < 12°C)
```

#### 3.2.3 Cechy energetyczne (lagi):
```python
- consumption_1h_ago: float      # Zużycie 1h temu (kWh)
- consumption_24h_ago: float     # Zużycie 24h temu (kWh)
- consumption_7d_ago: float      # Zużycie 7 dni temu (kWh)
- consumption_avg_3h: float      # Średnie zużycie 3h (kWh)
- consumption_avg_24h: float     # Średnie zużycie 24h (kWh)

- production_1h_ago: float       # Produkcja 1h temu (kWh)
- production_24h_ago: float      # Produkcja 24h temu (kWh)
- production_7d_ago: float       # Produkcja 7 dni temu (kWh)
- production_avg_3h: float       # Średnia produkcja 3h (kWh)

- soc_1h_ago: float              # SOC 1h temu (%)
- soc_24h_ago: float             # SOC 24h temu (%)
```

#### 3.2.4 Cechy taryfowe i PC:
```python
- tariff_zone: int (0/1)         # 0=L2 (tania), 1=L1 (droga)
- rce_price: float               # Cena RCE (zł/kWh)
- pc_co_active: bool             # Pompa ciepła CO aktywna
- cwu_window_active: bool        # Okno CWU aktywne
```

#### 3.2.5 Cechy słoneczne (astronomiczne):
```python
- solar_elevation: float         # Wysokość słońca (stopnie)
- solar_azimuth: float           # Azymut słońca (stopnie)
- daylight_hours: float          # Długość dnia (godziny)
- minutes_since_sunrise: int     # Minuty od wschodu słońca
- minutes_to_sunset: int         # Minuty do zachodu słońca
```

**Łącznie:** ~40-50 features

---

## 4. MODELE MACHINE LEARNING

### 4.1 Model predykcji zużycia energii (Consumption Model)

**Algorytm:** RandomForestRegressor (sklearn)

**Input features (top 20 najważniejszych):**
1. `hour` - Godzina dnia (najważniejsza!)
2. `day_of_week` - Dzień tygodnia
3. `is_workday` - Dzień roboczy
4. `consumption_24h_ago` - Zużycie 24h temu (wzorzec dzienny)
5. `consumption_7d_ago` - Zużycie 7 dni temu (wzorzec tygodniowy)
6. `consumption_avg_3h` - Średnie zużycie 3h
7. `temp_outdoor` - Temperatura zewnętrzna
8. `is_heating_season` - Sezon grzewczy
9. `pc_co_active` - Pompa ciepła aktywna
10. `cwu_window_active` - Okno CWU
11. `tariff_zone` - Strefa taryfowa
12. `month` - Miesiąc
13. `is_weekend` - Weekend
14. `temp_change_1h` - Zmiana temperatury
15. `consumption_1h_ago` - Zużycie 1h temu

**Output:**
- `consumption_next_1h` - Zużycie w następnej 1h (kWh)
- `consumption_next_6h` - Zużycie w następnych 6h (kWh)
- `consumption_next_24h` - Zużycie w następnych 24h (kWh)

**Hyperparametry:**
```python
RandomForestRegressor(
    n_estimators=100,           # 100 drzew
    max_depth=15,                # Głębokość drzewa
    min_samples_split=10,        # Min próbek do podziału
    min_samples_leaf=5,          # Min próbek w liściu
    random_state=42,
    n_jobs=-1                    # Użyj wszystkich rdzeni
)
```

**Metryki:**
- MAE (Mean Absolute Error) < 0.5 kWh
- RMSE (Root Mean Squared Error) < 0.8 kWh
- R² score > 0.85

### 4.2 Model predykcji produkcji PV (Production Model)

**Algorytm:** GradientBoostingRegressor (sklearn)

**Input features (top 15 najważniejszych):**
1. `solar_elevation` - Wysokość słońca (kluczowa!)
2. `solar_azimuth` - Azymut słońca
3. `cloudiness` - Zachmurzenie
4. `production_24h_ago` - Produkcja 24h temu
5. `production_7d_ago` - Produkcja 7 dni temu
6. `hour` - Godzina dnia
7. `month` - Miesiąc (sezon)
8. `temp_outdoor` - Temperatura
9. `precipitation_prob` - Prawdopodobieństwo opadów
10. `production_avg_3h` - Średnia produkcja 3h
11. `daylight_hours` - Długość dnia
12. `minutes_since_sunrise` - Minuty od wschodu
13. `production_1h_ago` - Produkcja 1h temu

**Output:**
- `production_next_1h` - Produkcja w następnej 1h (kWh)
- `production_next_6h` - Produkcja w następnych 6h (kWh)
- `production_next_24h` - Produkcja w następnych 24h (kWh)

**Hyperparametry:**
```python
GradientBoostingRegressor(
    n_estimators=150,
    learning_rate=0.05,
    max_depth=10,
    min_samples_split=10,
    min_samples_leaf=5,
    subsample=0.8,
    random_state=42
)
```

**Metryki:**
- MAE < 1.0 kWh
- RMSE < 1.5 kWh
- R² score > 0.80

**Porównanie z Forecast.Solar:**
- Cel: Accuracy improvement > 20% vs Forecast.Solar

### 4.3 Battery Optimizer (Optymalizator baterii)

**Algorytm:** Rule-based optimizer z ML predictions

**Input:**
- `ml_consumption_24h` - Predykcja zużycia (z ML)
- `ml_production_24h` - Predykcja produkcji (z ML)
- `current_soc` - Obecny SOC (%)
- `tariff_schedule` - Harmonogram taryf
- `rce_prices` - Ceny RCE na 24h

**Output:**
- `optimal_target_soc` - Optymalny Target SOC (%)
- `charging_hours` - Rekomendowane godziny ładowania
- `discharging_strategy` - Strategia rozładowania
- `confidence_score` - Pewność predykcji (0-1)

**Algorytm:**
```python
def optimize_battery(consumption_24h, production_24h, current_soc, tariff_schedule):
    """
    1. Oblicz bilans energii na 24h
       energy_balance = production_24h - consumption_24h

    2. Jeśli deficyt energii (production < consumption):
       - Oblicz ile kWh brakuje
       - Znajdź najtańsze okna L2 na ładowanie
       - Oblicz Target SOC = current_soc + (energy_deficit / battery_capacity) * 100
       - Maksymalnie 80% (limit Huawei)

    3. Jeśli nadwyżka energii (production > consumption):
       - Priorytet: magazynuj w najtańsze godziny RCE
       - Target SOC = min(70%, current_soc + surplus * 0.7)

    4. Uwzględnij sezon grzewczy:
       - Zima: Target SOC + 10% (PC potrzebuje więcej energii)
       - Lato: Target SOC - 5% (niższe zużycie)

    5. Confidence score:
       - High (>0.8): R² models > 0.85, dane kompletne
       - Medium (0.6-0.8): R² models 0.70-0.85
       - Low (<0.6): Brak danych, fallback do Forecast.Solar
    """
```

---

## 5. TRENOWANIE MODELI

### 5.1 Harmonogram trenowania

**Automatyczne trenowanie:**
- **Codziennie o 01:00** - Retrain modeli na nowych danych (ostatnie 30 dni)
- **Co tydzień w niedzielę o 02:00** - Full retrain + hyperparameter tuning
- **Po 7 dniach od instalacji** - Pierwszy pełny trening (wymagane minimum danych)

**Warunki trenowania:**
- Minimum 7 dni danych historycznych (168h)
- Maksymalnie 20% brakujących danych (wypełnienie przez interpolację)
- Dane z ostatnich 30 dni (720h)

### 5.2 Proces trenowania

```python
def train_models():
    """
    1. Zbierz dane z recorder (30 dni)
    2. Preprocessing:
       - Usuń outliers (> 3σ)
       - Wypełnij brakujące dane (linear interpolation)
       - Normalizacja (StandardScaler dla numerical features)
    3. Feature engineering (oblicz wszystkie features)
    4. Split danych:
       - Train: 80% (24 dni)
       - Test: 20% (6 dni)
    5. Trenowanie:
       - Consumption model (RandomForest)
       - Production model (GradientBoosting)
    6. Ewaluacja:
       - Oblicz MAE, RMSE, R²
       - Zapisz metryki do logs
    7. Persystencja:
       - Zapisz modele (.pkl) do ml_data/models/
       - Zapisz metryki do ml_data/logs/
    8. Aktualizuj sensory confidence
    """
```

### 5.3 Walidacja i monitoring

**Continuous monitoring:**
- Codziennie porównuj predykcje z rzeczywistością
- Oblicz rolling MAE (ostatnie 7 dni)
- Jeśli MAE > threshold → Retrain modeli

**Alert conditions:**
- MAE > 1.5 kWh (consumption) → Powiadomienie
- MAE > 2.0 kWh (production) → Powiadomienie
- R² < 0.70 → Automatyczny retrain

---

## 6. SENSORY HOME ASSISTANT

### 6.1 Sensory predykcji zużycia

**Sensor:** `sensor.ml_consumption_next_1h`
- **Nazwa:** "ML: Zużycie energii następna 1h"
- **Unit:** kWh
- **Update:** Co 15 min
- **Attributes:**
  - `confidence`: 0.0-1.0 (pewność predykcji)
  - `model_version`: "v1.2.3"
  - `last_trained`: "2025-11-17 01:00:00"
  - `mae`: 0.45 (błąd średni)

**Sensor:** `sensor.ml_consumption_next_6h`
- **Nazwa:** "ML: Zużycie energii następne 6h"
- **Unit:** kWh
- **Update:** Co 30 min

**Sensor:** `sensor.ml_consumption_next_24h`
- **Nazwa:** "ML: Zużycie energii następne 24h"
- **Unit:** kWh
- **Update:** Co 1h

### 6.2 Sensory predykcji produkcji PV

**Sensor:** `sensor.ml_production_next_1h`
- **Nazwa:** "ML: Produkcja PV następna 1h"
- **Unit:** kWh
- **Update:** Co 15 min

**Sensor:** `sensor.ml_production_next_6h`
- **Nazwa:** "ML: Produkcja PV następne 6h"
- **Unit:** kWh
- **Update:** Co 30 min

**Sensor:** `sensor.ml_production_next_24h`
- **Nazwa:** "ML: Produkcja PV następne 24h"
- **Unit:** kWh
- **Update:** Co 1h
- **Attributes:**
  - `forecast_solar_24h`: 25.3 (porównanie z Forecast.Solar)
  - `improvement`: "+3.2 kWh (+12.6%)" (poprawa vs Forecast.Solar)

### 6.3 Sensory optymalizacji baterii

**Sensor:** `sensor.ml_battery_target_soc`
- **Nazwa:** "ML: Optymalny Target SOC"
- **Unit:** %
- **Update:** Co 1h
- **Attributes:**
  - `reason`: "Jutro pochmurno (12 kWh PV) - ładuj do 75%"
  - `energy_balance_24h`: "-8.5 kWh" (deficyt energii)
  - `charging_hours`: [22, 23, 0, 1, 2, 3, 4, 5]
  - `confidence`: 0.87

**Sensor:** `sensor.ml_confidence_score`
- **Nazwa:** "ML: Pewność predykcji"
- **Unit:** %
- **State:** 87% (0-100)
- **Attributes:**
  - `consumption_model_r2`: 0.89
  - `production_model_r2`: 0.83
  - `data_completeness`: 0.95 (95% danych dostępnych)
  - `days_since_training`: 2

**Sensor:** `sensor.ml_energy_balance_24h`
- **Nazwa:** "ML: Bilans energii (24h)"
- **Unit:** kWh
- **State:** -8.5 (negatywne = deficyt, pozytywne = nadwyżka)
- **Attributes:**
  - `consumption_24h`: 32.5 kWh
  - `production_24h`: 24.0 kWh
  - `battery_capacity_needed`: 8.5 kWh
  - `target_soc_recommendation`: 75%

### 6.4 Sensory diagnostyczne

**Sensor:** `sensor.ml_model_status`
- **Nazwa:** "ML: Status modeli"
- **State:** "OK" / "Training" / "Warning" / "Error"
- **Attributes:**
  - `consumption_model`: "OK"
  - `production_model`: "OK"
  - `last_training`: "2025-11-17 01:00:00"
  - `next_training`: "2025-11-18 01:00:00"
  - `training_duration`: "45s"
  - `data_points_used`: 720

**Sensor:** `sensor.ml_accuracy_rolling_7d`
- **Nazwa:** "ML: Dokładność (7 dni)"
- **Unit:** %
- **State:** 91% (accuracy)
- **Attributes:**
  - `consumption_mae_7d`: 0.42 kWh
  - `production_mae_7d`: 0.89 kWh
  - `predictions_count_7d`: 168
  - `improvement_vs_baseline`: "+18.5%"

---

## 7. INTEGRACJA Z BATTERY ALGORITHM

### 7.1 Modyfikacja `battery_algorithm.py`

**Dodać na początku pliku:**
```python
# ============================================
# ML INTEGRATION
# ============================================

USE_ML_PREDICTIONS = True  # Włącz/wyłącz ML

def get_ml_predictions():
    """Pobierz predykcje z modeli ML"""
    try:
        ml_consumption_24h = float(get_state('sensor.ml_consumption_next_24h') or 0)
        ml_production_24h = float(get_state('sensor.ml_production_next_24h') or 0)
        ml_target_soc = int(float(get_state('sensor.ml_battery_target_soc') or 0))
        ml_confidence = float(get_state('sensor.ml_confidence_score') or 0) / 100

        return {
            'consumption_24h': ml_consumption_24h,
            'production_24h': ml_production_24h,
            'target_soc': ml_target_soc,
            'confidence': ml_confidence,
            'available': ml_confidence > 0.6  # Minimum confidence
        }
    except Exception as e:
        return {'available': False}
```

**Modyfikacja funkcji `collect_input_data()`:**
```python
def collect_input_data():
    # ... existing code ...

    data = {
        # ... existing fields ...

        # ML predictions
        'ml_predictions': get_ml_predictions() if USE_ML_PREDICTIONS else {'available': False}
    }

    return data
```

**Modyfikacja funkcji `calculate_daily_strategy()`:**
```python
# W python_scripts/calculate_daily_strategy.py

def calculate_target_soc():
    """Oblicza Target SOC używając ML jeśli dostępne"""

    # Pobierz predykcje ML
    ml_preds = get_ml_predictions()

    if ml_preds['available'] and ml_preds['confidence'] > 0.7:
        # Użyj rekomendacji ML
        target_soc = ml_preds['target_soc']
        reason = f"ML: {ml_preds['consumption_24h']:.1f} kWh zużycie, {ml_preds['production_24h']:.1f} kWh produkcja (confidence: {ml_preds['confidence']:.0%})"
    else:
        # Fallback: użyj Forecast.Solar (obecna logika)
        forecast_tomorrow = float(get_state('sensor.prognoza_pv_jutro') or 0)
        # ... existing logic ...
        reason = f"Forecast.Solar: {forecast_tomorrow:.1f} kWh (ML niedostępny)"

    # Zapisz Target SOC
    hass.services.call('input_number', 'set_value', {
        'entity_id': 'input_number.battery_target_soc',
        'value': target_soc
    })

    return target_soc, reason
```

### 7.2 Fallback strategy

**Priorytety źródeł danych:**
1. **ML predictions** (jeśli confidence > 0.7)
2. **Forecast.Solar** (jeśli ML niedostępny)
3. **Fallback statyczny** (wartości bezpieczne)

**Warunki użycia ML:**
- `sensor.ml_confidence_score` > 70%
- `sensor.ml_model_status` == "OK"
- Predykcje nie starsze niż 2h

---

## 8. INSTALACJA I KONFIGURACJA

### 8.1 Wymagania

**Zależności Python:**
```
scikit-learn>=1.3.0
numpy>=1.24.0
pandas>=2.0.0
joblib>=1.3.0
```

**Dodać do `config/configuration.yaml`:**
```yaml
# ML Energy Management
energy_ml:
  enabled: true
  auto_train: true
  train_schedule: "01:00:00"  # Codziennie o 01:00
  min_data_days: 7             # Minimum 7 dni danych
  confidence_threshold: 0.7    # Minimum 70% confidence
```

### 8.2 Instalacja

**Metoda 1: HACS (przyszłość)**
- TODO: Dodać do HACS repository

**Metoda 2: Manualna (teraz)**
```bash
# 1. Skopiuj folder custom_components/energy_ml do config/
cp -r custom_components/energy_ml /config/custom_components/

# 2. Zainstaluj zależności
pip install scikit-learn numpy pandas joblib

# 3. Restart Home Assistant
ha core restart

# 4. Dodaj integrację przez UI
Configuration → Integrations → Add Integration → "Energy ML"
```

### 8.3 Pierwszy trening

**Po instalacji:**
1. Poczekaj 7 dni na zebranie danych historycznych
2. Automatyczny trening wystartuje o 01:00
3. Sprawdź sensory:
   - `sensor.ml_model_status` → "OK"
   - `sensor.ml_confidence_score` → >70%
4. Włącz integrację w `battery_algorithm.py`:
   ```python
   USE_ML_PREDICTIONS = True
   ```

---

## 9. ROADMAP I PRZYSZŁE ROZSZERZENIA

### Faza 1: MVP (v1.0) - 2 tygodnie
- ✅ Architektura systemu
- ⬜ Data collector + preprocessing
- ⬜ Feature engineering
- ⬜ Consumption model (RandomForest)
- ⬜ Production model (GradientBoosting)
- ⬜ Battery optimizer
- ⬜ Sensory HA
- ⬜ Integracja z battery_algorithm.py
- ⬜ Dokumentacja użytkownika

### Faza 2: Optymalizacja (v1.1) - 1 tydzień
- ⬜ Hyperparameter tuning
- ⬜ Feature selection (SelectKBest)
- ⬜ Cross-validation
- ⬜ Ensemble models (stacking)

### Faza 3: Zaawansowane (v2.0) - przyszłość
- ⬜ LSTM dla szeregów czasowych
- ⬜ Reinforcement Learning dla optymalizacji baterii
- ⬜ Multi-model ensemble
- ⬜ Online learning (aktualizacja modeli co godzinę)
- ⬜ Predykcja cen RCE
- ⬜ Optymalizacja arbitrażu (buy low, sell high)
- ⬜ UI dashboard dla monitoringu ML
- ⬜ A/B testing (ML vs regułowy)

### Faza 4: Inteligentne funkcje (v3.0)
- ⬜ Anomaly detection (wykrywanie awarii paneli/baterii)
- ⬜ Predictive maintenance (predykcja degradacji baterii)
- ⬜ Smart charging (optymalizacja cykli ładowania)
- ⬜ Energy forecasting API (eksport predykcji dla innych systemów)

---

## 10. METRYKI SUKCESU

### 10.1 KPI (Key Performance Indicators)

**Dokładność predykcji:**
- ✅ Consumption MAE < 0.5 kWh
- ✅ Production MAE < 1.0 kWh
- ✅ R² score > 0.85

**Oszczędności finansowe:**
- ✅ Redukcja kosztów energii > 15% (vs algorytm regułowy)
- ✅ Lepsze wykorzystanie taniej taryfy L2
- ✅ Więcej arbitrażu w szczycie wieczornym

**Autonomia systemu:**
- ✅ Brak konieczności ręcznej konfiguracji progów
- ✅ Automatyczna adaptacja do wzorców użycia
- ✅ Self-healing (automatyczny retrain przy spadku accuracy)

**Niezawodność:**
- ✅ Uptime > 99.5%
- ✅ Fallback do Forecast.Solar jeśli ML fail
- ✅ Brak błędów w logach przez 7 dni

### 10.2 Monitoring

**Dashboard (Lovelace):**
```yaml
# Dodać do lovelace_huawei.yaml

- type: vertical-stack
  title: "🤖 Machine Learning"
  cards:
    - type: entities
      entities:
        - sensor.ml_consumption_next_24h
        - sensor.ml_production_next_24h
        - sensor.ml_battery_target_soc
        - sensor.ml_confidence_score
        - sensor.ml_energy_balance_24h

    - type: history-graph
      title: "Predykcje vs Rzeczywistość"
      hours_to_show: 48
      entities:
        - sensor.ml_consumption_next_1h
        - sensor.pomiar_mocy_moc_czynna  # Rzeczywiste zużycie
        - sensor.ml_production_next_1h
        - sensor.inwerter_moc_wejsciowa  # Rzeczywista produkcja

    - type: gauge
      entity: sensor.ml_confidence_score
      name: "Pewność predykcji"
      min: 0
      max: 100
      severity:
        green: 80
        yellow: 60
        red: 0
```

---

## 11. BEZPIECZEŃSTWO I PRYWATNOŚĆ

### 11.1 Dane lokalne
- **Wszystkie dane ML przechowywane lokalnie** w `/config/ml_data/`
- **Brak wysyłania danych do chmury**
- **Modele trenowane lokalnie** (brak zewnętrznych API)

### 11.2 Backup modeli
```yaml
# Dodać do automations.yaml
- id: ml_models_backup
  alias: "[ML] Backup modeli (co tydzień)"
  trigger:
    - platform: time
      at: "03:00:00"
  condition:
    - condition: time
      weekday: sun  # Tylko w niedzielę
  action:
    - service: shell_command.backup_ml_models
```

```yaml
# Dodać do configuration.yaml
shell_command:
  backup_ml_models: 'tar -czf /backup/ml_models_$(date +\%Y\%m\%d).tar.gz /config/ml_data/models/'
```

### 11.3 Gitignore
```gitignore
# Dodać do .gitignore
config/ml_data/
*.pkl
*.joblib
*.h5
```

---

## 12. FAQ

**Q: Czy ML zastąpi obecny algorytm regułowy?**
A: Nie, ML jest **dodatkiem**. Algorytm regułowy pozostaje jako fallback.

**Q: Ile danych historycznych potrzeba?**
A: Minimum **7 dni** do treningu, optymalne **30 dni**.

**Q: Czy ML działa offline?**
A: Tak, wszystko działa **lokalnie** bez Internetu (po pobraniu prognozy pogody).

**Q: Czy ML zwiększa obciążenie CPU?**
A: Trenowanie: ~1 minuta CPU raz dziennie. Predykcje: <1s co 15 min. **Minimalny wpływ.**

**Q: Co jeśli ML się pomyli?**
A: Fallback do Forecast.Solar + safety limits w battery_algorithm.py (SOC 20-80%).

**Q: Czy mogę wyłączyć ML?**
A: Tak, ustaw `USE_ML_PREDICTIONS = False` w battery_algorithm.py.

---

## 13. KONTAKT I WSPARCIE

**Dokumentacja:** `/config/ML_MODULE_DESIGN.md` (ten plik)
**Logi:** `/config/ml_data/logs/`
**Issues:** Zgłaszaj problemy w komentarzach do kodu

**Autor:** Claude Code
**Licencja:** MIT
**Wersja:** 1.0 (2025-11-17)

---

**KONIEC DOKUMENTU**
