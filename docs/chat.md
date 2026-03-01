# Chat Session - 2026-03-01

## Podsumowanie sesji

Sesja skupiona na porównaniu taryfowym Pstryk vs G12w, fixach weekendowej logiki baterii i poprawkach dashboardu.

---

## 1. Porównanie taryfowe: Pstryk (dynamiczna) vs G12w

### Cel
Monitoring i porównanie kosztów energii gdybyśmy byli na taryfie dynamicznej Pstryk vs aktualna G12w.

### Wzór Pstryk
`(RCE/1000 + 0.08 marża + 0.07 dystrybucja + 0.005 akcyza) × 1.23 VAT`

### Implementacja
- 5 template sensors: `pstryk_cena_dynamiczna`, `g12w_cena_teraz`, `pstryk_oszczednosc_za_kwh/dzienna/miesieczna`
- 4 input_numbers: koszty dzienne/miesięczne per taryfa
- Automatyzacja godzinowa (xx:59): kalkulacja importu × cena per taryfa, akumulacja
- Resety: dzienne (00:00), miesięczne (1. dnia)

### Break-even
- L1: Pstryk tańszy gdy RCE < 788 PLN/MWh
- L2: Pstryk tańszy gdy RCE < 479 PLN/MWh

---

## 2. Weekend: smart PV surplus z algorytmem RCE

### Problem
Weekendowa logika zawsze zwracała `discharge_to_home` — marnowała okazje sprzedaży PV w drogich godzinach RCE.

### Rozwiązanie
Nadwyżka PV → `handle_pv_surplus()` (algorytm najtańszych godzin RCE) — identycznie jak w dni robocze. Brak nadwyżki → `discharge_to_home` jak dotychczas.

---

## 3. Fix: weekendowy próg ochronny SOC

### Problem
Bateria rozładowywała się przez całą noc weekendową (discharge_to_home) aż do soc_min (14-15%). Potem awaryjne ładowanie z sieci 5kW.

### Przyczyna
Weekendowa logika nie sprawdzała poziomu SOC — zawsze `discharge_to_home` gdy brak surplus.

### Rozwiązanie
Nowy próg: gdy SOC <= `soc_min + 10%` (25% w marcu) i brak PV → `grid_to_home` (dom z sieci, bateria nietknięta). Zapobiega głębokiemu rozładowaniu w nocy.

---

## 4. Dashboard: dynamiczne daty na wykresach RCE

- "Ceny RCE (Dziś)" → "Ceny RCE (DD.MM.YYYY)"
- "Ceny RCE (Jutro)" → "Ceny RCE (DD.MM.YYYY)"
- EVAL JavaScript w apex_config.title.text

---

## Commity sesji

| Hash | Opis |
|------|------|
| `99d979c` | Weekend: smart PV surplus z algorytmem najtańszych godzin RCE |
| (nowy) | Pstryk porównanie taryfowe + fix weekendowy SOC + daty RCE + docs v3.17 |

---

## Poprzednia sesja (2026-02-26)

Pełna historia w `docs/DOKUMENTACJA_KOMPLETNA.md` sekcja v3.16:
- Auto-kalibracja PV (EMA)
- Usunięcie martwego kodu RCE
- Optymalizacja CWU z PV
- Fix: handle_pv_surplus() — blok "Zima → MAGAZYNUJ"
- Fix: grid_to_home — nocne cyklowanie baterii
- Recorder: auto_purge: false
