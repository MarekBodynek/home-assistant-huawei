# 🔧 Instrukcja Wdrożenia - Integracja Telegram z Home Assistant

## Wymagania wstępne

- Home Assistant Core 2023.1+
- Dostęp do plików konfiguracyjnych HA
- Konto Telegram
- Bot Telegram (utworzony przez @BotFather)

---

## KROK 1: Utworzenie bota Telegram

### 1.1 Utwórz bota przez BotFather

```
1. Otwórz Telegram
2. Wyszukaj: @BotFather
3. Wyślij: /newbot
4. Podaj nazwę wyświetlaną: "Home Assistant Battery"
5. Podaj username: "ha_battery_XXXXX_bot" (musi kończyć się na "_bot")
6. ZAPISZ TOKEN API (format: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)
```

### 1.2 Uzyskaj Chat ID

```bash
# Najpierw wyślij wiadomość do swojego bota w Telegram (np. "test")
# Następnie otwórz w przeglądarce:
https://api.telegram.org/bot<TWÓJ_TOKEN>/getUpdates

# Znajdź w odpowiedzi JSON:
"chat": {"id": 123456789, ...}

# Skopiuj numer ID
```

### 1.3 Test połączenia z botem

```bash
# Wyślij testową wiadomość przez API:
curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
  -d "chat_id=<CHAT_ID>" \
  -d "text=Test z curl"

# Oczekiwana odpowiedź: {"ok":true,"result":{...}}
```

---

## KROK 2: Konfiguracja Home Assistant

### 2.1 Struktura plików

```
config/
├── configuration.yaml      # Główna konfiguracja
├── secrets.yaml           # Tokeny (w .gitignore!)
├── input_boolean.yaml     # Przełączniki
├── input_select.yaml      # Wybór poziomu
├── scripts.yaml           # Skrypt send_notification
├── automations.yaml       # Automatyzacje
├── automations_battery.yaml
└── automations_errors.yaml
```

### 2.2 Plik secrets.yaml

**Lokalizacja:** `config/secrets.yaml`

```yaml
# TELEGRAM BOT
telegram_bot_token: "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
telegram_chat_id: "123456789"
```

**WAŻNE:**
- Plik musi być w `.gitignore`
- Chat ID musi być STRING (w cudzysłowach)
- Token nie może zawierać spacji ani znaków specjalnych

### 2.3 Plik configuration.yaml

**Dodaj sekcje:**

```yaml
# Input boolean
input_boolean: !include input_boolean.yaml

# Input select
input_select: !include input_select.yaml

# Telegram Bot - POLLING mode
telegram_bot:
  - platform: polling
    api_key: !secret telegram_bot_token
    allowed_chat_ids:
      - !secret telegram_chat_id

# Telegram Notifications
notify:
  - platform: telegram
    name: telegram
    chat_id: !secret telegram_chat_id
```

**UWAGA:** Sekcja `notify:` musi być na głównym poziomie YAML (bez wcięcia).

### 2.4 Plik input_boolean.yaml

```yaml
# Globalne włączanie/wyłączanie powiadomień Telegram
telegram_notifications_enabled:
  name: "Telegram - Powiadomienia włączone"
  initial: true
  icon: mdi:telegram

# Włączanie/wyłączanie persistent notifications
persistent_notifications_enabled:
  name: "Persistent Notifications włączone"
  initial: true
  icon: mdi:bell
```

### 2.5 Plik input_select.yaml

```yaml
# Minimalny poziom powiadomień wysyłanych na Telegram
telegram_notification_level:
  name: "Telegram - Minimalny poziom powiadomień"
  options:
    - "DEBUG"
    - "INFO"
    - "WARNING"
    - "CRITICAL"
  initial: "INFO"
  icon: mdi:telegram
```

### 2.6 Plik scripts.yaml - Skrypt send_notification

```yaml
send_notification:
  alias: "Wyślij powiadomienie (Telegram + HA)"
  description: "Scentralizowany system wysyłania powiadomień z obsługą priorytetów"
  fields:
    title:
      description: "Tytuł powiadomienia"
      example: "🔋 Bateria"
    message:
      description: "Treść powiadomienia"
      example: "Ładowanie rozpoczęte"
    priority:
      description: "Priorytet: DEBUG, INFO, WARNING, CRITICAL"
      example: "INFO"
      default: "INFO"
    notification_id:
      description: "ID dla persistent notification (opcjonalne)"
      example: "battery_charging"
  sequence:
    # Krok 1: Przygotowanie priorytetów numerycznych
    - variables:
        priority_value: >
          {% set priorities = {'DEBUG': 0, 'INFO': 1, 'WARNING': 2, 'CRITICAL': 3} %}
          {{ priorities.get(priority, 1) }}
        min_priority_value: >
          {% set priorities = {'DEBUG': 0, 'INFO': 1, 'WARNING': 2, 'CRITICAL': 3} %}
          {% set min_level = states('input_select.telegram_notification_level') %}
          {{ priorities.get(min_level, 1) }}

    # Krok 2: Formatowanie wiadomości
    - variables:
        formatted_message: >
          {% if priority == 'CRITICAL' %}
          🚨 *{{ title }}*

          *{{ message }}*
          {% elif priority == 'WARNING' %}
          ⚠️ *{{ title }}*

          {{ message }}
          {% elif priority == 'DEBUG' %}
          📊 {{ title }}

          {{ message }}
          {% else %}
          ℹ️ {{ title }}

          {{ message }}
          {% endif %}

    # Krok 3: Wysłanie do Telegram
    - choose:
        - conditions:
            - condition: state
              entity_id: input_boolean.telegram_notifications_enabled
              state: 'on'
            - condition: template
              value_template: "{{ priority_value|int >= min_priority_value|int }}"
          sequence:
            - service: notify.telegram
              data:
                message: "{{ formatted_message }}"

    # Krok 4: Wysłanie do Persistent Notification
    - choose:
        - conditions:
            - condition: state
              entity_id: input_boolean.persistent_notifications_enabled
              state: 'on'
          sequence:
            - service: persistent_notification.create
              data:
                title: "{{ title }}"
                message: "{{ message }}"
                notification_id: "{{ notification_id if notification_id is defined else '' }}"
```

---

## KROK 3: Weryfikacja konfiguracji

### 3.1 Sprawdź składnię YAML

```bash
# W kontenerze HA lub przez SSH:
ha core check

# Lub przez UI:
# Developer Tools → YAML → Check Configuration
```

### 3.2 Restart Home Assistant

```bash
# Przez CLI:
ha core restart

# Lub przez UI:
# Settings → System → Restart
```

### 3.3 Sprawdź logi po restarcie

```bash
# Przez CLI:
ha core logs | grep -i telegram

# Lub przez UI:
# Settings → System → Logs
# Szukaj: "telegram", "notify", "error"
```

**Oczekiwane wpisy (poprawne):**
```
Setting up telegram_bot
Setting up notify.telegram
```

**Błędne wpisy (problem):**
```
Error setting up telegram_bot
Unable to connect to Telegram API
Invalid token
```

---

## KROK 4: Diagnostyka problemów

### 4.1 Test bezpośredni notify.telegram

```yaml
# Developer Tools → Services
service: notify.telegram
data:
  message: "Test bezpośredni z HA"
```

**Jeśli błąd:**
- Sprawdź czy `notify.telegram` istnieje w `Developer Tools → States`
- Sprawdź logi

### 4.2 Test skryptu send_notification

```yaml
# Developer Tools → Services
service: script.send_notification
data:
  title: "🧪 Test"
  message: "Integracja działa!"
  priority: "INFO"
```

### 4.3 Sprawdź czy input helpers istnieją

```yaml
# Developer Tools → States
# Szukaj:
input_boolean.telegram_notifications_enabled  # Powinien być 'on'
input_boolean.persistent_notifications_enabled # Powinien być 'on'
input_select.telegram_notification_level       # Powinien być 'INFO'
```

**Jeśli nie istnieją:**
- Sprawdź czy `input_boolean: !include input_boolean.yaml` jest w configuration.yaml
- Sprawdź czy pliki input_boolean.yaml i input_select.yaml istnieją

### 4.4 Weryfikacja secrets.yaml

```yaml
# Developer Tools → Services
service: persistent_notification.create
data:
  title: "Test Secrets"
  message: "Jeśli to widzisz, secrets działają"
```

---

## KROK 5: Najczęstsze błędy i rozwiązania

### ❌ Błąd: "notify.telegram not found"

**Przyczyna:** Integracja Telegram nie załadowała się

**Rozwiązanie:**
1. Sprawdź składnię w configuration.yaml
2. Upewnij się że `notify:` jest na głównym poziomie (bez wcięcia)
3. Sprawdź czy secrets.yaml ma poprawny format
4. Restart HA

### ❌ Błąd: "Unauthorized" lub "Invalid token"

**Przyczyna:** Niepoprawny token bota

**Rozwiązanie:**
1. Zresetuj token przez @BotFather (/mybots → API Token → Revoke)
2. Skopiuj nowy token do secrets.yaml
3. Upewnij się że token jest w cudzysłowach
4. Restart HA

### ❌ Błąd: "Chat not found" lub "Bad Request"

**Przyczyna:** Niepoprawny Chat ID

**Rozwiązanie:**
1. Wyślij wiadomość do bota w Telegram
2. Pobierz Chat ID ponownie przez getUpdates
3. Upewnij się że Chat ID jest liczbą (bez cudzysłowów lub jako string)
4. Restart HA

### ❌ Błąd: "input_boolean.telegram_notifications_enabled not found"

**Przyczyna:** Input helpers nie załadowane

**Rozwiązanie:**
1. Sprawdź czy plik input_boolean.yaml istnieje
2. Sprawdź czy jest include w configuration.yaml:
   ```yaml
   input_boolean: !include input_boolean.yaml
   ```
3. Sprawdź składnię YAML w pliku
4. Restart HA

### ❌ Błąd: Powiadomienia nie docierają na Telegram

**Przyczyna:** Filtr priorytetów blokuje

**Rozwiązanie:**
1. Sprawdź stan `input_boolean.telegram_notifications_enabled` (musi być 'on')
2. Sprawdź `input_select.telegram_notification_level` (ustaw na 'DEBUG' do testów)
3. Przetestuj bezpośrednio `notify.telegram` (bez skryptu)

### ❌ Błąd: YAML syntax error

**Przyczyna:** Błąd formatowania YAML

**Rozwiązanie:**
1. Użyj walidatora YAML online
2. Sprawdź wcięcia (zawsze 2 spacje, nie taby)
3. Sprawdź cudzysłowy przy stringach ze znakami specjalnymi
4. Uruchom `ha core check`

---

## KROK 6: Testy end-to-end

### 6.1 Test minimalny

```yaml
# Developer Tools → Services
service: notify.telegram
data:
  message: "Test 1 - bezpośredni"
```

### 6.2 Test przez skrypt

```yaml
service: script.send_notification
data:
  title: "Test 2"
  message: "Przez skrypt"
  priority: "INFO"
```

### 6.3 Test wszystkich priorytetów

```yaml
# DEBUG
service: script.send_notification
data:
  title: "Test DEBUG"
  message: "Priorytet DEBUG"
  priority: "DEBUG"

# INFO
service: script.send_notification
data:
  title: "Test INFO"
  message: "Priorytet INFO"
  priority: "INFO"

# WARNING
service: script.send_notification
data:
  title: "Test WARNING"
  message: "Priorytet WARNING"
  priority: "WARNING"

# CRITICAL
service: script.send_notification
data:
  title: "Test CRITICAL"
  message: "Priorytet CRITICAL"
  priority: "CRITICAL"
```

### 6.4 Test automatyzacji

```yaml
# Wywołaj skrypt manualny:
service: script.force_battery_charge

# Oczekiwany wynik:
# - Telegram: ℹ️ 🔋 Huawei Solar - Uruchomiono ręczne ładowanie baterii
# - HA UI: Persistent notification
```

---

## KROK 7: Monitoring i logi

### 7.1 Włącz debug logging dla Telegram

Dodaj do `configuration.yaml`:

```yaml
logger:
  default: warning
  logs:
    homeassistant.components.telegram_bot: debug
    homeassistant.components.notify: debug
```

### 7.2 Sprawdź logi

```bash
# Filtruj logi:
ha core logs | grep -E "(telegram|notify|error)"
```

### 7.3 Monitorowanie w czasie rzeczywistym

```bash
# W terminalu HA:
tail -f /config/home-assistant.log | grep -i telegram
```

---

## Checklist wdrożenia

- [ ] Bot utworzony przez @BotFather
- [ ] Token API zapisany
- [ ] Chat ID uzyskany
- [ ] Wiadomość testowa wysłana do bota
- [ ] Test curl działa
- [ ] secrets.yaml utworzony z tokenem i chat_id
- [ ] secrets.yaml w .gitignore
- [ ] configuration.yaml zawiera sekcje telegram_bot i notify
- [ ] input_boolean.yaml utworzony
- [ ] input_select.yaml utworzony
- [ ] scripts.yaml zawiera send_notification
- [ ] ha core check - brak błędów
- [ ] Home Assistant zrestartowany
- [ ] Logi nie zawierają błędów Telegram
- [ ] notify.telegram widoczny w Developer Tools
- [ ] Test bezpośredni notify.telegram działa
- [ ] Test script.send_notification działa
- [ ] Powiadomienia docierają na Telegram

---

## Kontakt i wsparcie

- Dokumentacja HA: https://www.home-assistant.io/integrations/telegram/
- Telegram Bot API: https://core.telegram.org/bots/api

---

**Wersja:** 1.0.0
**Data:** 2025-11-21
**Autor:** Claude Code
