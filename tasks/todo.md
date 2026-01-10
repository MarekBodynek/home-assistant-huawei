# Plan testowania integralności i wydajności automatyzacji

## Cel
Sprawdzenie integralności (poprawności składni, spójności referencji) i wydajności (logiki decyzyjnej) automatyzacji Home Assistant dla systemu zarządzania baterią Huawei Luna 2000.

---

## 1. Walidacja składni YAML

- [x] **1.1** Walidacja `automations_battery.yaml` - poprawność YAML
- [x] **1.2** Walidacja `automations.yaml` - poprawność YAML
- [x] **1.3** Walidacja `automations_errors.yaml` - poprawność YAML
- [x] **1.4** Walidacja `template_sensors.yaml` - poprawność YAML
- [x] **1.5** Walidacja `input_numbers.yaml`, `input_boolean.yaml`, `input_text.yaml`

---

## 2. Walidacja referencji encji

- [x] **2.1** Sprawdzenie czy wszystkie entity_id w automatyzacjach istnieją w template_sensors lub input_*
- [x] **2.2** Sprawdzenie spójności device_id (Huawei Solar, Aquarea)
- [x] **2.3** Weryfikacja serwisów HA (huawei_solar.*, switch.*, number.*, etc.)

---

## 3. Testy logiki algorytmu baterii (battery_algorithm.py)

- [x] **3.1** Test `get_tariff_zone()` - poprawność stref G12w
- [x] **3.2** Test `validate_data()` - walidacja danych wejściowych
- [x] **3.3** Test `calculate_power_balance()` - bilans mocy
- [x] **3.4** Test `decide_strategy()` - logika decyzyjna SOC/taryfa/prognoza
- [x] **3.5** Test sezon grzewczy - zawsze ładuj
- [x] **3.6** Test dobra prognoza PV - nie ładuj
- [x] **3.7** Test słaba prognoza PV - ładuj
- [x] **3.8** Test weekend energetyczny - self consumption
- [x] **3.9** Test edge cases: SOC krytyczne (<5%), temperatura baterii, weekend

---

## 4. Testy logiki calculate_daily_strategy.py

- [x] **4.1** Test `is_weekend_or_holiday()` - święta polskie (w tym ruchome 2024-2026)
- [x] **4.2** Test `get_tariff_zone()` - strefy taryfowe G12w
- [x] **4.3** Test `predict_consumption_24h()` - predykcja zużycia ML
- [x] **4.4** Test obliczania Target SOC dla różnych scenariuszy
- [x] **4.5** Test limitów bezpieczeństwa 20-80% i zaokrąglania do 5%

---

## 5. Testy automatyzacji

- [x] **5.1** Test triggery czasowe (poprawne godziny)
- [x] **5.2** Test warunki (conditions) - spójność logiki
- [x] **5.3** Test akcje - poprawne service calls
- [x] **5.4** Weryfikacja pętli (wybudzanie baterii) - ostrzeżenie o braku until

---

## 6. Testy template sensors

- [x] **6.1** Test sensor `strefa_taryfowa` - poprawność G12w dla 24h
- [x] **6.2** Test binary_sensor `dzien_roboczy` - weekendy i święta polskie
- [x] **6.3** Test binary_sensor `okno_cwu` - okna czasowe CWU
- [x] **6.4** Test binary_sensor `sezon_grzewczy` - próg 12°C
- [x] **6.5** Testy edge cases - granice godzin (00:00, 06:00, 13:00, 15:00, 22:00)

---

## 7. Stworzenie infrastruktury testowej

- [x] **7.1** Stworzenie `package.json` z zależnościami testowymi
- [x] **7.2** Stworzenie testów jednostkowych dla algorytmu Python (27 testów)
- [x] **7.3** Stworzenie testów dla daily strategy (25 testów)
- [x] **7.4** Stworzenie testów dla template sensors (41 testów)
- [x] **7.5** Stworzenie walidatora YAML dla automatyzacji HA
- [x] **7.6** Stworzenie testów automatyzacji (9 PASS)

---

## Review

### Wyniki testów

| Kategoria | PASS | WARN | FAIL |
|-----------|------|------|------|
| Walidacja YAML | 12 | 1 | 0 |
| Testy automatyzacji | 9 | 4 | 0 |
| Testy Python (łącznie) | 93 | 0 | 0 |
| **RAZEM** | **114** | **5** | **0** |

### Komendy testowe

```bash
npm run test          # Wszystkie testy
npm run test:yaml     # Tylko walidacja YAML
npm run test:python   # Tylko testy Python
npm run test:battery  # Tylko algorytm baterii
npm run test:strategy # Tylko daily strategy
npm run test:sensors  # Tylko template sensors
```

### Ostrzeżenia (do rozważenia)

1. **scenes.yaml** - plik jest pusty (nie używany)
2. **Automatyzacje wybudzania** - mają pętle `repeat` bez warunku `until` (potencjalnie nieskończone)
3. **Algorytm nie wywołuje pyscript bezpośrednio** - prawdopodobnie wywołany pośrednio przez inną automatyzację

### Wnioski

1. **Integralność YAML** - wszystkie pliki mają poprawną składnię
2. **Logika algorytmu** - poprawnie obsługuje:
   - Strefy taryfowe G12w (L1/L2)
   - Weekendy i święta polskie (w tym ruchome)
   - Sezon grzewczy i temperaturę
   - Prognozę PV i ceny RCE
   - Edge cases (SOC krytyczne <5%, temperatura baterii)
3. **Automatyzacje** - mają unikalne ID, poprawne triggery i akcje
4. **Template sensors** - poprawna logika stref, świąt, okien CWU

### Pliki testowe

```
tests/
├── conftest.py              # Konfiguracja pytest
├── test_automations.js      # Testy automatyzacji (Node.js)
├── test_battery_algorithm.py # Testy algorytmu baterii (27 testów)
├── test_daily_strategy.py   # Testy daily strategy (25 testów)
├── test_template_sensors.py # Testy template sensors (41 testów)
├── validate_entities.js     # Walidacja encji (Node.js)
└── validate_yaml.js         # Walidacja YAML (Node.js)
```

---
