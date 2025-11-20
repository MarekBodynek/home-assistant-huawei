# 📱 System Powiadomień Telegram

## Przegląd

System powiadomień zintegrowany z Telegram umożliwia otrzymywanie wszystkich alertów i raportów z Home Assistant bezpośrednio na Telegram. System wspiera **4 poziomy priorytetów** z konfigurowalnymi filtrami.

---

## 🚀 Szybki Start

### 1. Utwórz bota Telegram

1. Otwórz Telegram i znajdź `@BotFather`
2. Wyślij: `/newbot`
3. Podaj nazwę: `Home Assistant Battery Monitor` (lub dowolną)
4. Podaj username: `ha_battery_monitor_bot` (musi kończyć się na `_bot`)
5. **Zapisz token API** (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### 2. Uzyskaj Chat ID

1. Wyślij wiadomość do swojego nowego bota (dowolną)
2. Otwórz w przeglądarce:
   ```
   https://api.telegram.org/bot<TWÓJ_TOKEN>/getUpdates
   ```
3. Znajdź Chat ID w odpowiedzi JSON:
   ```json
   "chat": {"id": 123456789, ...}
   ```

### 3. Skonfiguruj secrets.yaml

Dodaj do pliku `config/secrets.yaml`:

```yaml
telegram_bot_token: "TWÓJ_TOKEN_Z_KROKU_1"
telegram_chat_id: "TWÓJ_CHAT_ID_Z_KROKU_2"
```

**UWAGA:** Plik `secrets.yaml` powinien być w `.gitignore` (nie commituj tokenów!)

### 4. Restart Home Assistant

Po dodaniu tokenów do `secrets.yaml`, zrestartuj Home Assistant.

---

## ⚙️ Konfiguracja

### Pliki konfiguracyjne

System składa się z następujących plików:

| Plik | Opis |
|------|------|
| `configuration.yaml` | Konfiguracja Telegram bot i notify platform |
| `input_boolean.yaml` | Przełączniki włączania/wyłączania powiadomień |
| `input_select.yaml` | Wybór minimalnego poziomu priorytetów |
| `scripts.yaml` | Scentralizowany skrypt `send_notification` |
| `secrets.yaml` | Tokeny i Chat ID (NIE commitować!) |

### Input Helpers

#### 🔘 Przełączniki (input_boolean)

```yaml
input_boolean.telegram_notifications_enabled:
  name: "Telegram - Powiadomienia włączone"
  initial: true
```

- **Włączone (ON):** Wszystkie powiadomienia (zgodne z priorytetem) trafiają na Telegram
- **Wyłączone (OFF):** Telegram wyłączony, tylko persistent notifications

```yaml
input_boolean.persistent_notifications_enabled:
  name: "Persistent Notifications włączone"
  initial: true
```

- **Włączone (ON):** Powiadomienia w UI Home Assistant
- **Wyłączone (OFF):** Tylko Telegram (nie zalecane)

#### 📊 Poziom priorytetów (input_select)

```yaml
input_select.telegram_notification_level:
  options:
    - "DEBUG"    # Wszystkie powiadomienia (raporty, logi)
    - "INFO"     # Standardowe informacje i wyższe
    - "WARNING"  # Ostrzeżenia i krytyczne
    - "CRITICAL" # Tylko krytyczne alerty
  initial: "INFO"
```

**Przykłady:**
- Ustawienie na `INFO`: Dostaniesz INFO + WARNING + CRITICAL
- Ustawienie na `CRITICAL`: Dostaniesz tylko CRITICAL

---

## 🎯 Poziomy Priorytetów

### 🔴 CRITICAL - Krytyczne alerty

**Formatowanie:** 🚨 **Pogrubiony tytuł i treść**

**Przykłady:**
- 🚨 Bateria krytycznie niska (SOC < 5%)
- 🔥 Temperatura baterii >43°C
- ❄️ Temperatura baterii <0°C
- 🚨 Błąd krytyczny systemu
- ⚠️ Awaryjne ładowanie (SOC < 15%)

**Kiedy wysyłane:**
- Zagrożenie bezpieczeństwa
- Awarie wymagające natychmiastowej reakcji
- Krytyczne błędy systemu

---

### 🟠 WARNING - Ostrzeżenia

**Formatowanie:** ⚠️ **Pogrubiony tytuł**, normalna treść

**Przykłady:**
- ⚠️ Temperatura baterii >40°C
- ⚠️ Bateria niska w strefie L1
- 🚨 Watchdog: Algorytm nie działa
- ⚠️ SOC baterii nie zmienia się >6h
- ⚠️ Integracja offline

**Kiedy wysyłane:**
- Sytuacje wymagające uwagi
- Potencjalne problemy
- Nieoptymalne warunki pracy

---

### 🟡 INFO - Informacje standardowe

**Formatowanie:** ℹ️ Normalny tekst

**Przykłady:**
- 🔋 Bateria wybudzona ze Sleep mode
- ✅ Bateria naładowana
- ✅ Temperatura wróciła do normy
- ⚡ Ładowanie w taniej taryfie
- 🏠 Tryb autoconsumption włączony

**Kiedy wysyłane:**
- Standardowe operacje
- Zmiany trybu pracy
- Potwierdzenia akcji

---

### 🟢 DEBUG - Raporty i logi

**Formatowanie:** 📊 Tytuł, `kod` dla treści

**Przykłady:**
- 📊 Podsumowanie dnia - Bateria (23:00)
- 📊 Raport dzienny - Błędy systemu (23:55)
- 📊 Strategia dzienna obliczona (00:00)
- 🔄 Git Pull wykonany

**Kiedy wysyłane:**
- Codzienne raporty
- Statystyki
- Informacje debugowania

---

## 📋 Wszystkie Powiadomienia (32 typy)

### Bateria (14 powiadomień)

| Powiadomienie | Priorytet | Czas/Trigger |
|---------------|-----------|--------------|
| Bateria krytycznie niska | CRITICAL | SOC < 5% |
| Bateria niska w L1 | WARNING | SOC < 20% w L1 |
| Bateria naładowana | INFO | SOC > 78% |
| Bateria wybudzona (22:00) | INFO | 22:00:30 + Sleep mode |
| Bateria wybudzona (13:00) | INFO | 13:00:30 + Sleep mode |
| Temperatura wysoka >40°C | WARNING | Temp > 40°C |
| Temperatura krytyczna >43°C | CRITICAL | Temp > 43°C |
| Temperatura ekstremalna >45°C | CRITICAL | Temp > 45°C |
| Temperatura <0°C (mróz) | CRITICAL | Temp < 0°C |
| Temperatura bezpieczna | INFO | Temp < 38°C przez 15min |
| Watchdog - algorytm nie działa | WARNING | Brak aktualizacji >2h |
| Watchdog - SOC stuck | WARNING | SOC nie zmienia się 6h |
| Podsumowanie dzienne | DEBUG | 23:00 |
| Strategia dzienna obliczona | DEBUG | 00:00 |

### Tryby pracy (9 powiadomień)

| Powiadomienie | Priorytet | Czas/Trigger |
|---------------|-----------|--------------|
| Ładowanie w taniej taryfie | INFO | 22:00 |
| Stop ładowania (90%) | INFO | SOC > 90% |
| Tryb PV Priority | INFO | 06:00 |
| Awaryjne ładowanie | CRITICAL | SOC < 15% |
| Optymalizacja pogody | INFO | 21:00 + chmury |
| Wymuś ładowanie (manual) | INFO | Skrypt |
| Zatrzymaj ładowanie (manual) | INFO | Skrypt |
| Włącz TOU (manual) | INFO | Skrypt |
| Włącz Self Consumption (manual) | INFO | Skrypt |

### Błędy systemu (4 powiadomienia)

| Powiadomienie | Priorytet | Czas/Trigger |
|---------------|-----------|--------------|
| Błąd krytyczny systemu | CRITICAL | binary_sensor |
| Integracja offline | WARNING | 5min offline |
| Raport dzienny błędów | DEBUG | 23:55 |
| Git Pull wykonany | DEBUG | Event trigger |

---

## 🛠️ Użycie w Automatyzacjach

### Wywołanie z YAML

```yaml
action:
  - service: script.send_notification
    data:
      title: "🔋 Bateria"
      message: "SOC: {{ states('sensor.akumulatory_stan_pojemnosci') }}%"
      priority: "INFO"  # DEBUG | INFO | WARNING | CRITICAL
      notification_id: "battery_status"  # opcjonalne
```

### Wywołanie z Python Script

```python
hass.services.call('script', 'send_notification', {
    'title': '📊 Raport',
    'message': f'Target SOC: {target_soc}%',
    'priority': 'DEBUG',
    'notification_id': 'daily_report'
})
```

### Parametry

| Parametr | Typ | Wymagany | Opis |
|----------|-----|----------|------|
| `title` | string | ✅ | Tytuł powiadomienia |
| `message` | string | ✅ | Treść (wspiera markdown) |
| `priority` | string | ❌ | DEBUG/INFO/WARNING/CRITICAL (domyślnie INFO) |
| `notification_id` | string | ❌ | ID dla persistent notification |

---

## 🎨 Formatowanie Telegram

Telegram wspiera **Markdown** formatting:

```yaml
message: |
  **Pogrubiony tekst**
  *Kursywa*
  `Kod inline`

  - Lista
  - Element 2
```

### Przykład z emoji i formatowaniem

```yaml
message: |
  🔥 **TEMPERATURA BATERII: 44°C**

  ⚠️ PRZEKROCZONO BEZPIECZNY PRÓG!

  **WYKONANO:**
  ✅ Zatrzymano ładowanie
  ✅ Tryb bezpieczny włączony

  **CO ZROBIĆ:**
  1. Sprawdź wentylację
  2. NIE wznawiaj ładowania
```

---

## 🔧 Zarządzanie Powiadomieniami

### Włączanie/Wyłączanie Telegram

1. **Przez UI Home Assistant:**
   - Settings → Helpers → `telegram_notifications_enabled`
   - Toggle ON/OFF

2. **Przez automatyzację:**
   ```yaml
   - service: input_boolean.turn_off
     target:
       entity_id: input_boolean.telegram_notifications_enabled
   ```

### Zmiana poziomu priorytetów

1. **Przez UI:**
   - Settings → Helpers → `telegram_notification_level`
   - Wybierz: DEBUG / INFO / WARNING / CRITICAL

2. **Przez automatyzację:**
   ```yaml
   - service: input_select.select_option
     target:
       entity_id: input_select.telegram_notification_level
     data:
       option: "WARNING"  # Tylko WARNING i CRITICAL
   ```

### Przykłady scenariuszy

#### Tryb "Cisza nocna" (tylko CRITICAL)

```yaml
- alias: "Cisza nocna - tylko krytyczne"
  trigger:
    - platform: time
      at: "22:00:00"
  action:
    - service: input_select.select_option
      target:
        entity_id: input_select.telegram_notification_level
      data:
        option: "CRITICAL"
```

#### Powrót do normalnego trybu

```yaml
- alias: "Tryb normalny - INFO+"
  trigger:
    - platform: time
      at: "07:00:00"
  action:
    - service: input_select.select_option
      target:
        entity_id: input_select.telegram_notification_level
      data:
        option: "INFO"
```

---

## 📊 Statystyki

### Liczba powiadomień według priorytetu

| Priorytet | Liczba | % całości |
|-----------|--------|-----------|
| CRITICAL | 7 | 22% |
| WARNING | 6 | 19% |
| INFO | 14 | 44% |
| DEBUG | 5 | 15% |
| **TOTAL** | **32** | **100%** |

### Rozkład czasowy

| Godzina | Powiadomienie | Priorytet |
|---------|---------------|-----------|
| 00:00 | Strategia dzienna | DEBUG |
| 06:00 | Tryb PV Priority | INFO |
| 13:00 | Bateria wybudzona | INFO |
| 21:00 | Optymalizacja pogody | INFO |
| 22:00 | Ładowanie tania taryfa | INFO |
| 23:00 | Podsumowanie dzienne | DEBUG |
| 23:55 | Raport błędów | DEBUG |

---

## 🔍 Troubleshooting

### Powiadomienia nie docierają na Telegram

1. **Sprawdź czy bot token jest poprawny:**
   ```bash
   curl https://api.telegram.org/bot<TOKEN>/getMe
   ```
   Powinno zwrócić informacje o bocie.

2. **Sprawdź czy Chat ID jest poprawny:**
   ```bash
   curl https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
   Znajdź swoje Chat ID w odpowiedzi.

3. **Sprawdź czy Telegram enabled:**
   ```yaml
   input_boolean.telegram_notifications_enabled: 'on'
   ```

4. **Sprawdź poziom priorytetów:**
   - Jeśli ustawiony na CRITICAL, nie dostaniesz INFO/DEBUG

5. **Sprawdź logi Home Assistant:**
   ```
   Settings → System → Logs
   ```
   Szukaj błędów związanych z `telegram` lub `notify`.

### Telegram działa, ale nie widzę w UI HA

Sprawdź:
```yaml
input_boolean.persistent_notifications_enabled: 'on'
```

### Dostaję wszystkie powiadomienia, nawet DEBUG

Sprawdź:
```yaml
input_select.telegram_notification_level: "DEBUG"
```

Zmień na `"INFO"` lub wyżej.

---

## 📝 Changelog

### v1.0.0 (2025-11-20)
- ✅ Integracja Telegram z Home Assistant
- ✅ 4 poziomy priorytetów (CRITICAL/WARNING/INFO/DEBUG)
- ✅ Scentralizowany skrypt `send_notification`
- ✅ 32 powiadomienia zmigrowane na nowy system
- ✅ Konfigurowalny filtr priorytetów
- ✅ Przełączniki włączania/wyłączania kanałów
- ✅ Dokumentacja i instrukcja instalacji

---

## 🤝 Wsparcie

Problemy? Pytania?
- Sprawdź [Troubleshooting](#-troubleshooting)
- Przeczytaj [dokumentację Telegram integration](https://www.home-assistant.io/integrations/telegram/)
- Sprawdź logi Home Assistant

---

**Autor:** Claude Code
**Data:** 2025-11-20
**Wersja:** 1.0.0
