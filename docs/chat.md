# Chat Session - 2026-03-02

## Podsumowanie sesji

Kontynuacja sesji z 2026-03-01. Fixy shell_command, ochrona brute force, weryfikacja sensorów.

---

## 1. Fix: shell_command — szablony Jinja nie renderują data:

### Problem
`shell_command` w HA renderuje Jinja (states(), now()), ale **NIE ma dostępu do `data:`** z automatyzacji. Oba shell_commands (`save_hourly_data`, `log_pv_calibration`) używały `data:` → CSV było puste.

### Rozwiązanie
- `save_hourly_data`: inline `states()` bezpośrednio w komendzie (dane z sensorów)
- `log_pv_calibration`: buffer `input_text.pv_calibration_line` — automatyzacja zapisuje CSV line do input_text, shell_command czyta ze `states()`

---

## 2. Ochrona przed brute force

### Problem
IP `77.92.55.156` (TKK.net.pl) — 2400+ prób logowania od 22.02.2026. Brak ochrony — `login_attempts_threshold` nie był ustawiony.

### Rozwiązanie
`login_attempts_threshold: 5` w sekcji `http:` — auto-ban IP po 5 nieudanych próbach.

---

## 3. Weryfikacja sensorów Pstryk

Sensory zarejestrowane poprawnie, ale API Pstryk zwraca błąd 500 (awaria po ich stronie). Sensory pokażą wartości gdy API wróci.

---

## 4. Wykresy RCE z datami

EVAL w `apex_config.title.text` załadowany poprawnie. Wymaga wizualnej weryfikacji w dashboardzie.

---

## Commity sesji

| Hash | Opis |
|------|------|
| `e17312d` | v3.17: Pstryk porównanie taryfowe, fix weekendowy SOC, daty RCE |
| (nowy) | Fix shell_command Jinja + IP ban brute force |

---

## Poprzednie sesje

- **2026-03-01**: Pstryk porównanie taryfowe, weekend smart PV surplus, fix SOC, daty RCE
- **2026-02-26**: Auto-kalibracja PV (EMA), fixy algorytmu baterii — patrz v3.16
