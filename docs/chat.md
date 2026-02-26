# Chat Session - 2026-02-26

## Podsumowanie sesji

Sesja skupiona na optymalizacji algorytmu baterii i auto-kalibracji prognoz PV.

---

## 1. Analiza propozycji "Claudii" (AI agent)

Użytkownik udostępnił dokument analizy algorytmu baterii przygotowany przez agenta AI "Claudia". Ocena propozycji:

| Propozycja | Status | Uwagi |
|-----------|--------|-------|
| Dynamiczne czasy słońca | Odrzucone | Niski wpływ, statyczne wartości wystarczające |
| Recorder 90 dni | Zmienione | auto_purge: false (nieograniczone dane) |
| Dynamiczne progi RCE | Odrzucone | Stałe RCE były martwym kodem (nigdy nieużywane) |
| ML improvements | Odroczone | |
| Predykcja cen RCE | Odrzucone | Ceny podawane dobę wcześniej |
| Feedback loop | Odroczone | |
| Optymalizacja CWU | Wdrożone | Już istniało, dodano drobne usprawnienia |

---

## 2. Auto-kalibracja prognoz PV (EMA)

### Problem
Forecast.Solar systematycznie zawyża prognozy. Hardcoded współczynniki korekcji (0.50-0.90) nie adaptują się do warunków.

### Rozwiązanie
System EMA (Exponential Moving Average) — porównuje prognozę z realną produkcją i automatycznie dostosowuje współczynniki.

### Implementacja
- `input_text.pv_monthly_corrections` — JSON z 12 współczynnikami
- `input_number.pv_raw_forecast_today` — snapshot poranny surowej prognozy
- `sensor.pv_wspolczynnik_korekcji` — dynamiczny z input_text
- 3 automatyzacje: init CSV, snapshot 08:00, kalibracja EMA 21:30
- Wzór: `nowy = 0.7 × stary + 0.3 × (real/forecast)`

---

## 3. Usunięcie martwego kodu RCE

13 stałych (RCE_NEGATIVE, RCE_LOW, itd. + FORECAST_EXCELLENT, itd.) było zdefiniowanych ale nigdy nieużywanych w logice. Usunięto. FORECAST_POOR=12 zachowany (używany w handle_pv_surplus).

---

## 4. Optymalizacja CWU z PV

- Próg nadwyżki PV: 2000W → 1500W
- Dodany warunek: SOC >= Target SOC (priorytet baterii nad CWU)

---

## 5. Fix: handle_pv_surplus() — blok "Zima → MAGAZYNUJ"

### Problem
Blok `if month in [11,12,1,2]: return charge_from_pv` krótko-obwodował algorytm najtańszych godzin RCE. Bateria magazynowała PV w drogich godzinach (0.35-0.47 zł o 8-10h) zamiast sprzedawać i czekać na tanie godziny (0.07-0.25 zł o 12-15h).

### Rozwiązanie
Usunięto blok zimowy. Check "Jutro pochmurno" (forecast < 12 kWh) nadal chroni zimowe dni. Algorytm cheapest_hours decyduje kiedy magazynować vs sprzedawać.

---

## 6. Fix: grid_to_home — nocne cyklowanie baterii

### Problem
W trybie `grid_to_home` bateria cyklicznie ładowała/rozładowywała się w nocy:
1. Ładowanie do target_soc → stop
2. Mode → maximise_self_consumption z max_discharge_power=5000
3. Bateria rozładowuje do domu
4. SOC < target → znowu ładuje
Bug: `discharge_soc_limit = min(target_soc, 20) = 20%` nie chroniło baterii.

### Rozwiązanie
`max_discharge_power=0` w trybie grid_to_home. Dom pobiera z sieci, bateria nietknięta. EPS działa niezależnie.

---

## 7. Recorder — nieograniczone dane

`purge_keep_days: 30` → `auto_purge: false`. Duży dysk RPi, dane zbierają się bez limitu.

---

## Commity sesji

| Hash | Opis |
|------|------|
| `7d00cb4` | Usunięcie martwego kodu RCE + optymalizacja CWU z PV |
| `d9034c2` | Auto-kalibracja prognoz PV (EMA) + dynamiczne współczynniki korekcji |
| `415b684` | Recorder: wyłączenie auto-purge |
| `7b3efc2` | Fix: handle_pv_surplus() — usunięcie bloku "Zima → MAGAZYNUJ" |
| `0e53b2c` | Fix: grid_to_home — max_discharge_power=0 (stop nocnego cyklowania) |
