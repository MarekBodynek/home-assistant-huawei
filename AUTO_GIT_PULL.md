# Automatyczne Git Pull - Instrukcja Setup

## Problem
Dashboard z GitHub nie może zostać automatycznie załadowany bez jednorazowej ręcznej akcji.

## Rozwiązanie (wybierz JEDNĄ opcję)

### OPCJA 1: Jednorazowy manual git pull (NAJSZYBSZA)

Zaloguj się przez SSH i wykonaj:
```bash
ssh root@192.168.0.106
# (lub inny użytkownik który działa)
cd /config
git pull
exit
```

Potem restart HA i gotowe!

### OPCJA 2: Webhook do git pull (jedna linijka w HA!)

1. **Zaloguj się do Home Assistant** (http://192.168.0.106:8123)
2. **Settings** → **Automations & Scenes** → **+ CREATE AUTOMATION**
3. Kliknij **⋮** (trzy kropki) → **Edit in YAML**
4. Wklej:

```yaml
alias: "[System] Git Pull via Webhook"
description: "Automatyczne git pull przy wywołaniu webhooka"
trigger:
  - platform: webhook
    webhook_id: git_pull_webhook_secret_12345
    allowed_methods:
      - POST
      - GET
    local_only: false
action:
  - service: shell_command.git_pull
  - service: persistent_notification.create
    data:
      title: "🔄 Git Pull"
      message: "Wykonano git pull o {{ now().strftime('%H:%M:%S') }}"
mode: single
```

5. **Zapisz**
6. Następnie dodaj do `configuration.yaml` (przez File Editor lub SSH):

```yaml
shell_command:
  git_pull: 'cd /config && git pull'
```

7. **Restart Home Assistant**

8. **Testuj webhook** (z mojego poziomu mogę to zrobić!):
```bash
curl -X POST http://192.168.0.106:8123/api/webhook/git_pull_webhook_secret_12345
```

### OPCJA 3: Automatyczny git pull co godzinę

Dodaj do `automations.yaml`:
```yaml
- id: auto_git_pull_hourly
  alias: "[System] Auto Git Pull co godzinę"
  description: "Automatyczne git pull co godzinę"
  trigger:
    - platform: time_pattern
      hours: "*"  # co godzinę
  action:
    - service: shell_command.git_pull
    - delay:
        seconds: 5
    - service: homeassistant.reload_core_config
  mode: single
```

Dodaj do `configuration.yaml`:
```yaml
shell_command:
  git_pull: 'cd /config && git pull'
```

Restart HA i automatyka zadziała!

## Czego potrzebuję od Ciebie

**Wybierz JEDNĄ opcję i powiedz mi którą:**
- "opcja 1" - zrobię manual git pull przez SSH (podaj mi działającego usera+hasło)
- "opcja 2" - stwórz webhook (skopiuj automatyzację do HA przez UI)
- "opcja 3" - chcę automatyczny git pull co godzinę (skopiuj do automations.yaml)

Po wyborze opcji 2 lub 3, wystarczy że powiesz "gotowe" jak dodasz config, a ja zrobię resztę!
