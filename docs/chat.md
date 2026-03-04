# Chat Session - 2026-03-04

## Podsumowanie sesji

Optymalizacja algorytmu baterii: usunięcie short-circuitów, survival_soc dla nocnego ładowania.

---

## 1. Fix: shell_command — szablony Jinja

`shell_command` nie ma dostępu do `data:` z automatyzacji. Fix:
- `save_hourly_data`: inline `states()` w komendzie
- `log_pv_calibration`: buffer `input_text.pv_calibration_line`

---

## 2. Ochrona przed brute force

- `login_attempts_threshold: 5` w `http:` — auto-ban IP po 5 próbach
- IP `77.92.55.156` (TKK.net.pl) — 2400+ prób od 22.02.2026

---

## 3. Fix: usunięcie "Jutro pochmurno → MAGAZYNUJ"

Blok w `handle_pv_surplus()` krótko-obwodował algorytm najtańszych godzin RCE. Powodował magazynowanie PV o 9h (RCE 0.50) zamiast sprzedaży i magazynowania o 11-13h (RCE 0.05). Usunięty — algorytm najtańszych godzin sam obsługuje pochmurne jutro przez wyższy target_soc.

---

## 4. Nocne ładowanie: survival_soc

### Problem
Bateria ładowała się nocą do 60-70% (target_soc). O 11h (najtańsze RCE) bateria wciąż na 30-40% — mało miejsca na darmowe PV.

### Rozwiązanie
Nowa funkcja `get_first_cheap_pv_hour()` — pobiera ceny RCE jutro, znajduje najwcześniejszą tanią godzinę.

`survival_soc = soc_min + (hours_gap × 1.2 kWh / 15 kWh × 100)`

Przykład (marzec, first_cheap=11h):
- hours_gap = 11 - 6 = 5h
- survival_soc = 15% + 40% = 55%
- Bateria rano zasila dom w L1, o 11h jest bliska soc_min
- PV ładuje pustą baterię od 15% do 80% za darmo

Próg: PV forecast ≥ 10 kWh. Poniżej → ładuj normalnie.

---

## 5. Dashboard: dynamiczne daty na wykresach RCE

EVAL JavaScript w `apex_config.title.text` — "Ceny RCE (04.03.2026)" zamiast "Ceny RCE (Dziś)". Działa poprawnie.

---

## 6. Testy algorytmu baterii (pytest)

Kompleksowe testy `battery_algorithm.py` — 79 testów, 0 failures.

### Naprawione testy (4)
- `test_rce_thresholds` → `test_forecast_poor_threshold` (usunięte stałe RCE)
- `test_forecast_thresholds` → `test_battery_critical_threshold` (usunięte stałe FORECAST)
- `test_cloudy_tomorrow_store` → `test_cloudy_tomorrow_uses_cheapest_hours` (usunięty short-circuit)
- `test_winter_store` → `test_normal_rce_goes_through_cheapest_hours` (usunięty short-circuit)

### Nowe klasy testowe (5 klas, 26 testów)
- **TestCalculateCheapestHoursToStore** (6): identyfikacja najtańszych godzin, current_hour_not_cheap, cheap_stores_expensive_sells, battery_full, no_rce_data, after_sunset_tomorrow
- **TestGetFirstCheapPvHour** (5): earliest_cheap_hour, no_rce_data, no_forecast, winter/summer sunrise exclusion
- **TestSurvivalSoc** (5): high_pv_uses_survival, low_pv_uses_full_target, midnight_forecast_today, soc_at_survival_stops, excellent_pv_grid_to_home
- **TestDailyCycleIntegration** (5): night_survival_morning_drain, first_cheap_hour_stores, expensive_before_cheap_sells, ultra_low_rce_override, full_cycle_night_to_cheap
- **TestCheapestHoursEdgeCases** (5): same_price, single_hour, survival_soc_clamp, weekend_no_survival, plnmwh_conversion

---

## Commity sesji

| Hash | Opis |
|------|------|
| `1d164cc` | Fix shell_command Jinja + IP ban brute force |
| (nowy) | Fix "Jutro pochmurno" + survival_soc nocne ładowanie |

---

## Poprzednie sesje

- **2026-03-01**: Pstryk porównanie taryfowe, weekend smart PV surplus, fix SOC
- **2026-02-26**: Auto-kalibracja PV (EMA), fixy algorytmu baterii — patrz v3.16
