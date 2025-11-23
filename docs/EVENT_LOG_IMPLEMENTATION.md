# Event Log System - Instrukcja wdrożenia

## Przegląd systemu

System Event Log umożliwia strukturalne logowanie zdarzeń w Home Assistant z zachowaniem historii 5 ostatnich zdarzeń. Każde zdarzenie zawiera:
- **Timestamp** - data i czas zdarzenia
- **Level** - poziom (INFO, WARNING, ERROR)
- **Category** - kategoria (DECISION, CHARGE, DISCHARGE, SAFETY, PRICE, ERROR)
- **Message** - opis zdarzenia

## Architektura

```
┌─────────────────────────────────────────────────────────────┐
│                    EVENT LOG SYSTEM                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  battery_algorithm.py                                        │
│  ┌──────────────────┐                                        │
│  │  log_decision()  │──────────────────┐                     │
│  └──────────────────┘                  │                     │
│                                        ▼                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              INPUT TEXT HELPERS (Rotacja)             │   │
│  │  event_log_1 ─► event_log_2 ─► ... ─► event_log_5    │   │
│  │  (najnowsze)                          (najstarsze)    │   │
│  └──────────────────────────────────────────────────────┘   │
│                          │                                   │
│         ┌────────────────┼────────────────┐                 │
│         ▼                ▼                ▼                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Template   │  │ Automations │  │  Dashboard  │         │
│  │  Sensors    │  │ (Telegram)  │  │  (Widget)   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Komponenty

### 1. Input Text Helpers (`input_text.yaml`)

5 slotów do przechowywania zdarzeń w formacie JSON:

```yaml
# Format JSON
{"ts":"2025-11-23T14:30:00","lvl":"INFO","cat":"DECISION","msg":"L2 22-06: Ładuj z sieci"}
```

| Entity ID | Opis |
|-----------|------|
| `input_text.event_log_1` | Najnowsze zdarzenie |
| `input_text.event_log_2` | Drugie zdarzenie |
| `input_text.event_log_3` | Trzecie zdarzenie |
| `input_text.event_log_4` | Czwarte zdarzenie |
| `input_text.event_log_5` | Najstarsze zdarzenie |

### 2. Template Sensors (`template_sensors.yaml`)

| Sensor | Opis |
|--------|------|
| `sensor.event_log_ostatnie_zdarzenie` | Parsuje i wyświetla ostatnie zdarzenie |
| `sensor.event_log_historia` | Statystyki (liczba zdarzeń, błędów, ostrzeżeń) |
| `sensor.event_log_markdown` | Formatowana lista dla Markdown card |

### 3. Funkcja `log_decision()` (`battery_algorithm.py`)

Główna funkcja logująca wywoływana po każdej decyzji algorytmu:

```python
def log_decision(data, balance, strategy, result):
    # Automatycznie określa:
    # - Level: INFO/WARNING/ERROR na podstawie treści
    # - Category: DECISION/CHARGE/DISCHARGE/SAFETY/PRICE/ERROR
    # - Rotuje sloty (5→wyrzuć, 4→5, 3→4, 2→3, 1→2, new→1)
```

### 4. Automatyzacje (`automations_errors.yaml`)

| Automatyzacja | Opis |
|---------------|------|
| `[EVENT LOG] Telegram alert - błąd` | Wysyła Telegram przy ERROR |
| `[EVENT LOG] Telegram alert - ostrzeżenie` | Wysyła Telegram przy WARNING |
| `[EVENT LOG] System log - ważne zdarzenia` | Loguje ERROR/WARNING do system_log |
| `[EVENT LOG] Reset dzienny` | Resetuje sloty 2-5 o północy |
| `[EVENT LOG] Manualny wpis testowy` | Do testowania (uruchom ręcznie) |

### 5. Dashboard Widget (`lovelace_huawei.yaml`)

- Markdown card z historią zdarzeń
- Entities card ze statusem

---

## Instrukcja wdrożenia

### Krok 1: Restart Home Assistant

Po dodaniu plików konfiguracyjnych wymagany jest restart:

```bash
# Docker
docker restart homeassistant

# Lub przez UI
# Settings → System → Restart
```

### Krok 2: Weryfikacja encji

Po restarcie sprawdź czy encje zostały utworzone:

```
Developer Tools → States → Szukaj: event_log
```

Powinny być widoczne:
- `input_text.event_log_1` ... `input_text.event_log_5`
- `sensor.event_log_ostatnie_zdarzenie`
- `sensor.event_log_historia`
- `sensor.event_log_markdown`

### Krok 3: Test manualny

1. Otwórz **Developer Tools → Services**
2. Wywołaj usługę:
   ```yaml
   service: automation.trigger
   target:
     entity_id: automation.event_log_manualny_wpis_testowy
   ```
3. Sprawdź `input_text.event_log_1` - powinien zawierać testowy wpis

### Krok 4: Weryfikacja automatyzacji

```
Settings → Automations → Szukaj: EVENT LOG
```

Powinno być 5 automatyzacji:
- `[EVENT LOG] Telegram alert - błąd`
- `[EVENT LOG] Telegram alert - ostrzeżenie`
- `[EVENT LOG] System log - ważne zdarzenia`
- `[EVENT LOG] Reset dzienny`
- `[EVENT LOG] Manualny wpis testowy`

### Krok 5: Test algorytmu

1. Uruchom algorytm baterii (automatycznie co godzinę lub ręcznie)
2. Sprawdź `input_text.event_log_1` - powinien zawierać nowe zdarzenie
3. Sprawdź Dashboard - widget Event Log powinien wyświetlać historię

---

## Kategorie zdarzeń

| Kategoria | Opis | Kiedy używana |
|-----------|------|---------------|
| `DECISION` | Główna decyzja algorytmu | Domyślna dla decyzji |
| `CHARGE` | Start/stop ładowania | mode: charge_from_grid/charge_from_pv |
| `DISCHARGE` | Start/stop rozładowania | mode: discharge_to_grid |
| `SAFETY` | Alarm bezpieczeństwa | Temperatura baterii |
| `PRICE` | Alert cenowy | Wykrycie niskiej/wysokiej ceny RCE |
| `ERROR` | Błąd systemu | Słowa: BŁĄD, ERROR |

## Poziomy zdarzeń

| Level | Opis | Telegram |
|-------|------|----------|
| `INFO` | Normalne zdarzenie | Nie wysyła |
| `WARNING` | Ostrzeżenie | Wysyła (jeśli level ≤ WARNING) |
| `ERROR` | Błąd | Zawsze wysyła |

---

## Rozwiązywanie problemów

### Problem: Encje `event_log_*` nie istnieją

**Rozwiązanie:**
1. Sprawdź składnię YAML: `Settings → System → Validate configuration`
2. Restart Home Assistant
3. Sprawdź logi: `Settings → System → Logs`

### Problem: Template sensors pokazują "unknown"

**Rozwiązanie:**
1. Upewnij się, że `input_text.event_log_1` ma poprawny JSON
2. Zresetuj do początkowej wartości:
   ```yaml
   service: input_text.set_value
   target:
     entity_id: input_text.event_log_1
   data:
     value: '{"ts":"","lvl":"INFO","cat":"INIT","msg":"System uruchomiony"}'
   ```

### Problem: Telegram nie wysyła powiadomień

**Rozwiązanie:**
1. Sprawdź `input_boolean.telegram_notifications_enabled` = on
2. Sprawdź `input_select.telegram_notification_level`
3. Sprawdź konfigurację Telegram Bot w `configuration.yaml`

### Problem: Event Log nie rotuje

**Rozwiązanie:**
1. Sprawdź czy `log_decision()` jest wywoływana (linia 133 w battery_algorithm.py)
2. Sprawdź logi Python script: `Settings → System → Logs`

---

## Rozszerzenia (opcjonalne)

### Więcej slotów (np. 10 zamiast 5)

1. Dodaj `input_text.event_log_6` ... `input_text.event_log_10` w `input_text.yaml`
2. Zaktualizuj `log_decision()` - pętla `range(1, 11)`
3. Zaktualizuj template sensors

### Export do pliku

Dodaj automatyzację zapisującą do pliku:

```yaml
- alias: "[EVENT LOG] Export do pliku"
  trigger:
    - platform: time
      at: "23:59:00"
  action:
    - service: shell_command.export_event_log
```

### Integracja z InfluxDB

Dla długoterminowej historii rozważ integrację z InfluxDB/Grafana.

---

## Pliki zmodyfikowane

| Plik | Zmiany |
|------|--------|
| `config/input_text.yaml` | +5 input_text (event_log_1..5) |
| `config/template_sensors.yaml` | +3 sensors (event_log_*) |
| `config/python_scripts/battery_algorithm.py` | log_decision() implementacja |
| `config/automations_errors.yaml` | +5 automatyzacji EVENT LOG |
| `config/lovelace_huawei.yaml` | +2 karty dashboard |

---

## Changelog

### v1.0.0 (2025-11-23)
- Inicjalna implementacja systemu Event Log
- 5 slotów z rotacją FIFO
- Integracja z Telegram (ERROR/WARNING)
- Dashboard widget (Markdown + Entities)
- Automatyzacje (reset dzienny, system_log)
