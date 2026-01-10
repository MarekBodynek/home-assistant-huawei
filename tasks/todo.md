# Plan testowania integralności i wydajności automatyzacji

## Cel
Sprawdzenie integralności (poprawności składni, spójności referencji) i wydajności (logiki decyzyjnej) automatyzacji Home Assistant dla systemu zarządzania baterią Huawei Luna 2000.

---

## 1. Walidacja składni YAML

- [ ] **1.1** Walidacja `automations_battery.yaml` - poprawność YAML
- [ ] **1.2** Walidacja `automations.yaml` - poprawność YAML
- [ ] **1.3** Walidacja `automations_errors.yaml` - poprawność YAML
- [ ] **1.4** Walidacja `template_sensors.yaml` - poprawność YAML
- [ ] **1.5** Walidacja `input_numbers.yaml`, `input_boolean.yaml`, `input_text.yaml`

---

## 2. Walidacja referencji encji

- [ ] **2.1** Sprawdzenie czy wszystkie entity_id w automatyzacjach istnieją w template_sensors lub input_*
- [ ] **2.2** Sprawdzenie spójności device_id (Huawei Solar, Aquarea)
- [ ] **2.3** Weryfikacja serwisów HA (huawei_solar.*, switch.*, number.*, etc.)

---

## 3. Testy logiki algorytmu baterii (battery_algorithm.py)

- [ ] **3.1** Test `get_tariff_zone()` - poprawność stref G12w
- [ ] **3.2** Test `validate_data()` - walidacja danych wejściowych
- [ ] **3.3** Test `calculate_power_balance()` - bilans mocy
- [ ] **3.4** Test `decide_strategy()` - logika decyzyjna SOC/taryfa/prognoza
- [ ] **3.5** Test `calculate_cheapest_hours_to_store()` - optymalizacja RCE
- [ ] **3.6** Test `handle_pv_surplus()` - nadwyżka PV
- [ ] **3.7** Test `handle_power_deficit()` - deficyt mocy
- [ ] **3.8** Test `should_charge_from_grid()` - decyzja ładowania
- [ ] **3.9** Test `check_arbitrage_opportunity()` - arbitraż wieczorny
- [ ] **3.10** Test edge cases: SOC krytyczne (<5%), temperatura baterii, weekend

---

## 4. Testy logiki calculate_daily_strategy.py

- [ ] **4.1** Test `is_weekend_or_holiday()` - święta polskie
- [ ] **4.2** Test `get_tariff_zone()` - strefy taryfowe
- [ ] **4.3** Test `predict_consumption_24h()` - predykcja zużycia ML
- [ ] **4.4** Test obliczania Target SOC dla różnych scenariuszy

---

## 5. Testy automatyzacji

- [ ] **5.1** Test triggery czasowe (poprawne godziny)
- [ ] **5.2** Test warunki (conditions) - spójność logiki
- [ ] **5.3** Test akcje - poprawne service calls
- [ ] **5.4** Weryfikacja timeoutów i pętli (wybudzanie baterii)

---

## 6. Testy template sensors

- [ ] **6.1** Test sensor `strefa_taryfowa` - poprawność G12w
- [ ] **6.2** Test binary_sensor `dzien_roboczy` - weekendy i święta
- [ ] **6.3** Test sensory cenowe RCE - progi, percentyle

---

## 7. Stworzenie infrastruktury testowej

- [ ] **7.1** Stworzenie `package.json` z zależnościami testowymi
- [ ] **7.2** Stworzenie testów jednostkowych dla algorytmu Python
- [ ] **7.3** Stworzenie walidatora YAML dla automatyzacji HA

---

## Review (po zakończeniu)

_Do uzupełnienia po zakończeniu testów_

---
