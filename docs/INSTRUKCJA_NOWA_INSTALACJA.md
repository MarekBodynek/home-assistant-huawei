# Instrukcja konfiguracji Home Assistant - Huawei Solar Battery Management

## Dla Claude Code - KOMPLETNA instrukcja instalacji jeden-do-jednego

Ta instrukcja pozwala skonfigurować **identyczny** system zarządzania baterią Huawei LUNA 2000 z optymalizacją kosztów energii RCE PSE. Zawiera pełny kod wszystkich komponentów.

**WAŻNE DLA CLAUDE:** Ta instrukcja jest przeznaczona do kopiowania konfiguracji z jednej instalacji do drugiej. Musisz:
1. Skopiować WSZYSTKIE pliki dokładnie jak pokazano
2. Zmienić TYLKO parametry w sekcji "PARAMETRY DO DOSTOSOWANIA"
3. NIE modyfikować logiki algorytmu

---

## PARAMETRY DO DOSTOSOWANIA (ZMIEŃ NA POCZĄTKU!)

```yaml
# ========================================
# PARAMETRY SPECYFICZNE DLA NOWEJ INSTALACJI
# Zmień te wartości przed rozpoczęciem instalacji!
# ========================================

LOKALIZACJA:
  latitude: 52.2297          # Szerokość geograficzna (Google Maps)
  longitude: 21.0122         # Długość geograficzna (Google Maps)
  elevation: 100             # Wysokość n.p.m. (metry)
  timezone: "Europe/Warsaw"  # Strefa czasowa

BATERIA:
  model: "Huawei LUNA 2000"
  pojemnosc_kwh: 10          # Pojemność baterii w kWh
  min_soc: 20                # Minimalny SOC (%) - limit Huawei
  max_soc: 80                # Maksymalny SOC (%) - limit Huawei
  moc_ladowania_kw: 5        # Max moc ładowania (kW)

PANELE_PV:
  # Dla każdej płaszczyzny podaj: moc, azymut, nachylenie
  # Azymut: N=0, E=90, S=180, W=270, NE=45, SE=135, SW=225, NW=315

  plaszczyzna_1:
    nazwa: "Południowy-wschód"
    moc_kwp: 3.6             # Moc w kWp (np. 9 paneli × 400W = 3.6 kWp)
    azymut: 135              # SE = 135°
    nachylenie: 30           # Kąt nachylenia (stopnie)

  plaszczyzna_2:
    nazwa: "Południowy-zachód"
    moc_kwp: 2.8             # 7 paneli × 400W = 2.8 kWp
    azymut: 225              # SW = 225°
    nachylenie: 30

  # Jeśli jest trzecia płaszczyzna - dodaj plaszczyzna_3

TARYFA:
  typ: "G12w"                # Taryfa dwustrefowa weekendowa
  # L1 (droga): 06:00-13:00, 15:00-22:00 dni robocze
  # L2 (tania): 13:00-15:00, 22:00-06:00 dni robocze + całe weekendy

POWIADOMIENIA:
  telegram_enabled: true
  telegram_bot_token: "UZUPELNIJ_TOKEN"
  telegram_chat_id: "UZUPELNIJ_CHAT_ID"

HUAWEI_SOLAR:
  inverter_ip: "192.168.1.100"  # IP inwertera
  modbus_port: 502              # Port Modbus (domyślnie 502)
  # device_id baterii - znajdziesz po dodaniu integracji (patrz KROK 14)
```

---

## STRUKTURA PLIKÓW DO UTWORZENIA

```
config/
├── configuration.yaml         # Główna konfiguracja HA
├── secrets.yaml               # Dane wrażliwe (NIE COMMITUJ!)
├── template_sensors.yaml      # ~1000 linii - wszystkie sensory obliczeniowe
├── automations_battery.yaml   # ~860 linii - automatyzacje baterii
├── automations_errors.yaml    # Automatyzacje błędów i powiadomień
├── automations.yaml           # Standardowe automatyzacje HA
├── input_numbers.yaml         # Zmienne numeryczne
├── input_text.yaml            # Zmienne tekstowe (event log, decyzje)
├── input_boolean.yaml         # Przełączniki (telegram, algorytm)
├── input_select.yaml          # Listy wyboru
├── utility_meter.yaml         # Mierniki energii
├── lovelace_huawei.yaml       # Dashboard 3-kolumnowy
├── logger.yaml                # Konfiguracja logów
├── scenes.yaml                # Sceny HA
├── scripts.yaml               # Skrypty HA
└── python_scripts/
    ├── battery_algorithm.py           # Główny algorytm (~1470 linii)
    └── calculate_daily_strategy.py    # Strategia dzienna
```

---

## KROK 1: Wymagane integracje

### 1.1 Instalacja HACS
```bash
# W kontenerze HA lub przez SSH:
wget -O - https://get.hacs.xyz | bash -
# Restart HA
# Konfiguruj HACS w UI: Settings → Devices & Services → Add Integration → HACS
```

### 1.2 Integracje HACS (zainstaluj przez HACS → Integrations)
1. **Huawei Solar** - `wlcrs/huawei_solar`
   - Komunikacja Modbus z inwerterem Huawei
   - Sterowanie baterią (TOU, forcible charge/discharge)

2. **Pstryk** - ceny energii RCE z rynku hurtowego
   - Alternatywnie: inna integracja dostarczająca `sensor.rce_pse_cena`

### 1.3 Wbudowane integracje HA (Settings → Devices & Services)
- **Workday** - święta polskie (country: PL)
- **Sun** - wschód/zachód słońca
- **Telegram** - powiadomienia
- **Time & Date** - sensory czasu

---

## KROK 2: secrets.yaml

**UTWÓRZ PLIK:** `config/secrets.yaml`

```yaml
# ========================================
# SECRETS - Dane wrażliwe
# NIE COMMITUJ TEGO PLIKU DO GIT!
# ========================================

# Lokalizacja
latitude: "52.2297"      # ZMIEŃ!
longitude: "21.0122"     # ZMIEŃ!
elevation: "100"         # ZMIEŃ!

# Telegram Bot
telegram_bot_token: "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"  # ZMIEŃ!
telegram_chat_id: "-1001234567890"                          # ZMIEŃ!

# Huawei Solar
huawei_inverter_ip: "192.168.1.100"  # ZMIEŃ! IP inwertera
huawei_modbus_port: "502"
huawei_battery_device_id: "abc123..."  # Uzupełnij po KROK 14!
```

---

## KROK 3: configuration.yaml

**UTWÓRZ PLIK:** `config/configuration.yaml`

```yaml
# Home Assistant - Konfiguracja dla Huawei Solar
# Dokumentacja: https://www.home-assistant.io/docs/configuration/

# Podstawowa konfiguracja
homeassistant:
  name: Dom
  latitude: !secret latitude
  longitude: !secret longitude
  elevation: !secret elevation
  unit_system: metric
  time_zone: Europe/Warsaw
  currency: PLN

# Frontend
frontend:
  themes: !include_dir_merge_named themes

# Dashboardy
lovelace:
  mode: storage
  dashboards:
    lovelace-huawei:
      mode: yaml
      title: Huawei Solar PV
      icon: mdi:solar-power
      show_in_sidebar: true
      filename: lovelace_huawei.yaml
  resources:
    - url: /local/community/apexcharts-card/apexcharts-card.js
      type: module

# Logowanie
logger: !include logger.yaml

# Historia
history:

# Logbook
logbook:

# Rekorder - przechowywanie danych
recorder:
  purge_keep_days: 30
  db_url: sqlite:////config/home-assistant_v2.db

# Energia
energy:

# Aplikacja mobilna
mobile_app:

# Template sensors
template: !include template_sensors.yaml

# Input numbers
input_number: !include input_numbers.yaml

# Input text
input_text: !include input_text.yaml

# Input boolean
input_boolean: !include input_boolean.yaml

# Input select
input_select: !include input_select.yaml

# Utility meters
utility_meter: !include utility_meter.yaml

# Telegram Bot
telegram_bot:
  - platform: polling
    api_key: !secret telegram_bot_token
    allowed_chat_ids:
      - !secret telegram_chat_id

# Notify - Telegram
notify:
  - platform: telegram
    name: telegram
    chat_id: !secret telegram_chat_id

# Python Scripts
python_script:

# Automatyzacje
automation manual: !include automations.yaml
automation battery: !include automations_battery.yaml
automation errors: !include automations_errors.yaml

# Skrypty
script: !include scripts.yaml

# Sceny
scene: !include scenes.yaml

# Shell commands
shell_command:
  git_pull: 'cd /config && git pull'

# Time & Date sensors
sensor:
  - platform: time_date
    display_options:
      - 'time'
      - 'date'
      - 'date_time'

# ========================================
# Forecast Solar - REST API
# DOSTOSUJ: latitude, longitude, nachylenie, azymut, moc!
# Format URL: /estimate/{lat}/{lon}/{tilt}/{azimuth}/{kwp}
# ========================================

rest:
  # PŁASZCZYZNA 1: Południowy-wschód (SE = 135°)
  # ZMIEŃ: 52.2297/21.0122 na swoje współrzędne
  # ZMIEŃ: 30 na swoje nachylenie
  # ZMIEŃ: 135 na swój azymut
  # ZMIEŃ: 3.6 na swoją moc w kWp
  - resource: https://api.forecast.solar/estimate/52.2297/21.0122/30/135/3.6
    scan_interval: 7200
    sensor:
      - name: "PV SE - Prognoza dziś"
        unique_id: forecast_solar_se_today
        value_template: >
          {% set today = now().date() | string %}
          {% set data = value_json.result.watt_hours_day %}
          {{ data[today] | float(0) / 1000 | round(1) }}
        unit_of_measurement: "kWh"
        json_attributes_path: "$.result"
        json_attributes:
          - "watt_hours_day"
          - "watts"
      - name: "PV SE - Prognoza jutro"
        unique_id: forecast_solar_se_tomorrow
        value_template: >
          {% set tomorrow = (now().date() + timedelta(days=1)) | string %}
          {% set data = value_json.result.watt_hours_day %}
          {{ data[tomorrow] | float(0) / 1000 | round(1) }}
        unit_of_measurement: "kWh"

  # PŁASZCZYZNA 2: Południowy-zachód (SW = 225°)
  - resource: https://api.forecast.solar/estimate/52.2297/21.0122/30/225/2.8
    scan_interval: 7200
    sensor:
      - name: "PV SW - Prognoza dziś"
        unique_id: forecast_solar_sw_today
        value_template: >
          {% set today = now().date() | string %}
          {% set data = value_json.result.watt_hours_day %}
          {{ data[today] | float(0) / 1000 | round(1) }}
        unit_of_measurement: "kWh"
        json_attributes_path: "$.result"
        json_attributes:
          - "watt_hours_day"
          - "watts"
      - name: "PV SW - Prognoza jutro"
        unique_id: forecast_solar_sw_tomorrow
        value_template: >
          {% set tomorrow = (now().date() + timedelta(days=1)) | string %}
          {% set data = value_json.result.watt_hours_day %}
          {{ data[tomorrow] | float(0) / 1000 | round(1) }}
        unit_of_measurement: "kWh"

# Binary sensor - Dzień roboczy (wykrywa święta i weekendy)
binary_sensor:
  - platform: workday
    name: Dzień roboczy
    country: PL
    workdays: [mon, tue, wed, thu, fri]
    excludes: [sat, sun, holiday]
    add_holidays:
      # 2025
      - '2025-01-01'  # Nowy Rok
      - '2025-01-06'  # Trzech Króli
      - '2025-04-20'  # Wielkanoc
      - '2025-04-21'  # Poniedziałek Wielkanocny
      - '2025-05-01'  # Święto Pracy
      - '2025-05-03'  # Święto Konstytucji 3 Maja
      - '2025-06-19'  # Boże Ciało
      - '2025-08-15'  # Wniebowzięcie NMP
      - '2025-11-01'  # Wszystkich Świętych
      - '2025-11-11'  # Święto Niepodległości
      - '2025-12-25'  # Boże Narodzenie
      - '2025-12-26'  # Drugi dzień Bożego Narodzenia
      # 2026
      - '2026-01-01'
      - '2026-01-06'
      - '2026-04-05'  # Wielkanoc
      - '2026-04-06'  # Poniedziałek Wielkanocny
      - '2026-05-01'
      - '2026-05-03'
      - '2026-05-28'  # Boże Ciało
      - '2026-08-15'
      - '2026-11-01'
      - '2026-11-11'
      - '2026-12-25'
      - '2026-12-26'

# HTTP (jeśli używasz reverse proxy)
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 127.0.0.1
    - ::1
    - 172.30.33.0/24
```

---

## KROK 4: input_numbers.yaml

**UTWÓRZ PLIK:** `config/input_numbers.yaml`

```yaml
# ========================================
# INPUT NUMBERS - Zmienne numeryczne
# ========================================

battery_target_soc:
  name: "Target SOC baterii"
  min: 20
  max: 100
  step: 5
  unit_of_measurement: "%"
  icon: mdi:battery-charging-high
  initial: 80

battery_capacity_kwh:
  name: "Pojemność baterii"
  min: 5
  max: 30
  step: 0.1
  unit_of_measurement: "kWh"
  icon: mdi:battery
  initial: 10  # ZMIEŃ na swoją pojemność!

night_consumption_avg:
  name: "Średnie zużycie nocne (EMA)"
  min: 0
  max: 20
  step: 0.1
  unit_of_measurement: "kWh"
  icon: mdi:weather-night
  initial: 4

daily_consumption_avg:
  name: "Średnie zużycie dzienne (EMA)"
  min: 0
  max: 100
  step: 0.1
  unit_of_measurement: "kWh"
  icon: mdi:home-lightning-bolt
  initial: 25
```

---

## KROK 5: input_text.yaml

**UTWÓRZ PLIK:** `config/input_text.yaml`

```yaml
# ========================================
# INPUT TEXT - Zmienne tekstowe
# ========================================

battery_decision_reason:
  name: "Powód decyzji baterii"
  max: 255
  icon: mdi:head-cog

battery_storage_status:
  name: "Analiza magazynowania"
  max: 255
  icon: mdi:battery-charging

battery_cheapest_hours:
  name: "Najtańsze godziny RCE"
  max: 100
  icon: mdi:clock-outline

# Event Log - 3 sloty
event_log_1:
  name: "Event Log 1"
  max: 255
  icon: mdi:history

event_log_2:
  name: "Event Log 2"
  max: 255
  icon: mdi:history

event_log_3:
  name: "Event Log 3"
  max: 255
  icon: mdi:history
```

---

## KROK 6: input_boolean.yaml

**UTWÓRZ PLIK:** `config/input_boolean.yaml`

```yaml
# ========================================
# INPUT BOOLEAN - Przełączniki
# ========================================

telegram_notifications_enabled:
  name: "Powiadomienia Telegram"
  icon: mdi:telegram
  initial: true

persistent_notifications_enabled:
  name: "Powiadomienia UI"
  icon: mdi:bell-ring
  initial: true

battery_algorithm_enabled:
  name: "Algorytm baterii włączony"
  icon: mdi:robot
  initial: true
```

---

## KROK 7: input_select.yaml

**UTWÓRZ PLIK:** `config/input_select.yaml`

```yaml
# ========================================
# INPUT SELECT - Listy wyboru
# ========================================

telegram_notification_level:
  name: "Min. poziom powiadomień Telegram"
  options:
    - "DEBUG"
    - "INFO"
    - "WARNING"
    - "ERROR"
    - "CRITICAL"
  initial: "INFO"
  icon: mdi:filter
```

---

## KROK 8: utility_meter.yaml

**UTWÓRZ PLIK:** `config/utility_meter.yaml`

```yaml
# ========================================
# UTILITY METERS - Mierniki energii
# ========================================

# Zużycie godzinowe
zuzycie_godzinowe:
  source: sensor.pomiar_mocy_zuzycie
  cycle: hourly

# Produkcja PV dzienna
produkcja_pv_dzienna:
  source: sensor.inwerter_dzienna_produkcja
  cycle: daily
```

---

## KROK 9: logger.yaml

**UTWÓRZ PLIK:** `config/logger.yaml`

```yaml
# ========================================
# LOGGER - Konfiguracja logowania
# ========================================

default: warning
logs:
  homeassistant.components.python_script: info
  custom_components.huawei_solar: warning
  custom_components.pstryk: warning
```

---

## KROK 10: template_sensors.yaml (KRYTYCZNE!)

**UTWÓRZ PLIK:** `config/template_sensors.yaml`

Ten plik jest bardzo długi (~1000 linii). Zawiera wszystkie sensory obliczeniowe.

```yaml
# ============================================
# TEMPLATE SENSORS - Sensory obliczeniowe
# Home Assistant Huawei Solar Battery Management
# ============================================

# ============================================
# STREFA TARYFOWA G12w
# ============================================
- sensor:
    - name: "Strefa taryfowa"
      unique_id: strefa_taryfowa
      state: >
        {% set hour = now().hour %}
        {% set is_workday = is_state('binary_sensor.dzien_roboczy', 'on') %}
        {% if not is_workday %}
          L2
        {% elif (hour >= 6 and hour < 13) or (hour >= 15 and hour < 22) %}
          L1
        {% else %}
          L2
        {% endif %}
      icon: >
        {% if this.state == 'L1' %}
          mdi:currency-usd
        {% else %}
          mdi:currency-usd-off
        {% endif %}
      attributes:
        friendly_name: "Strefa taryfowa G12w"
        l1_hours: "06:00-13:00, 15:00-22:00 (dni robocze)"
        l2_hours: "13:00-15:00, 22:00-06:00 + weekendy"

# ============================================
# CENA ENERGII RCE
# ============================================
- sensor:
    - name: "Cena zakupu energii"
      unique_id: cena_zakupu_energii
      unit_of_measurement: "PLN/kWh"
      state: >
        {% set rce = states('sensor.rce_pse_cena') | float(0) %}
        {% if rce > 10 %}
          {{ (rce / 1000) | round(2) }}
        {% else %}
          {{ rce | round(2) }}
        {% endif %}
      icon: mdi:cash
      attributes:
        friendly_name: "Cena RCE"

# ============================================
# RCE ŚREDNIA WIECZORNA (zachód słońca → 22:00)
# ============================================
- sensor:
    - name: "RCE średnia wieczorna"
      unique_id: rce_srednia_wieczorna
      unit_of_measurement: "PLN/kWh"
      state: >
        {% set prices = state_attr('sensor.rce_pse_cena', 'prices') %}
        {% set today = now().strftime('%Y-%m-%d') %}
        {% set sunset_hour = state_attr('sun.sun', 'next_setting') %}
        {% set start_hour = 16 %}
        {% set end_hour = 22 %}
        {% set ns = namespace(prices=[], count=0) %}
        {% if prices %}
          {% for p in prices %}
            {% if p.dtime.startswith(today) %}
              {% set hour = p.dtime.split(' ')[1].split(':')[0] | int %}
              {% if hour >= start_hour and hour < end_hour %}
                {% set price = p.rce_pln / 1000 if p.rce_pln > 10 else p.rce_pln %}
                {% set ns.prices = ns.prices + [price] %}
              {% endif %}
            {% endif %}
          {% endfor %}
        {% endif %}
        {% if ns.prices | length > 0 %}
          {{ (ns.prices | sum / ns.prices | length) | round(2) }}
        {% else %}
          0.50
        {% endif %}
      icon: mdi:chart-timeline
      attributes:
        friendly_name: "RCE średnia wieczorna (zachód→22h)"

# ============================================
# RCE PROGI CENOWE (PERCENTYLE p33/p66)
# UŻYWANE DO KOLOROWANIA GODZIN!
# ============================================
- sensor:
    - name: "RCE Progi cenowe"
      unique_id: rce_progi_cenowe
      state: "OK"
      icon: mdi:palette
      attributes:
        friendly_name: "Progi cenowe RCE (percentyle)"
        p33: >
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') %}
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set ns = namespace(values=[]) %}
          {% if prices %}
            {% for p in prices if p.dtime.startswith(today) %}
              {% set hour = p.dtime.split(' ')[1].split(':')[0] | int %}
              {% if hour >= 6 and hour <= 21 %}
                {% set price = p.rce_pln / 1000 if p.rce_pln > 10 else p.rce_pln %}
                {% set ns.values = ns.values + [price] %}
              {% endif %}
            {% endfor %}
          {% endif %}
          {% if ns.values | length > 0 %}
            {% set sorted = ns.values | sort %}
            {% set idx = ((sorted | length) * 0.33) | int %}
            {{ sorted[idx] | round(2) }}
          {% else %}
            0.50
          {% endif %}
        p66: >
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') %}
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set ns = namespace(values=[]) %}
          {% if prices %}
            {% for p in prices if p.dtime.startswith(today) %}
              {% set hour = p.dtime.split(' ')[1].split(':')[0] | int %}
              {% if hour >= 6 and hour <= 21 %}
                {% set price = p.rce_pln / 1000 if p.rce_pln > 10 else p.rce_pln %}
                {% set ns.values = ns.values + [price] %}
              {% endif %}
            {% endfor %}
          {% endif %}
          {% if ns.values | length > 0 %}
            {% set sorted = ns.values | sort %}
            {% set idx = ((sorted | length) * 0.66) | int %}
            {{ sorted[idx] | round(2) }}
          {% else %}
            0.70
          {% endif %}
        legend: "🟢 < p33 | 🟡 p33-p66 | 🔴 > p66"

# ============================================
# RCE CENY GODZINOWE Z KOLOROWYMI KROPKAMI
# Format: h06, h07, ... h21 dla dziś
# Format: t06, t07, ... t21 dla jutro
# Wartość: "🟢 0.45" lub "🟡 0.65" lub "🔴 0.85"
# ============================================
- sensor:
    - name: "RCE Ceny godzinowe"
      unique_id: rce_ceny_godzinowe
      state: "OK"
      icon: mdi:clock-time-four-outline
      attributes:
        # DZIŚ - godziny 06-21
        h06: >
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') or [] %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set ns = namespace(hour_prices=[]) %}
          {% for p in prices if p.dtime.startswith(today) and p.dtime.split(' ')[1][:2] == '06' %}
            {% set ns.hour_prices = ns.hour_prices + [p.rce_pln/1000 if p.rce_pln > 10 else p.rce_pln] %}
          {% endfor %}
          {% if ns.hour_prices | length > 0 %}
            {% set pr = ((ns.hour_prices | sum) / (ns.hour_prices | length)) | round(2) %}
            {% if pr < 0.2 %}🟢🟢{% elif pr < p33 %}🟢{% elif pr <= p66 %}🟡{% else %}🔴{% endif %} {{ '%.2f'|format(pr) }}
          {% else %}-{% endif %}
        h07: >
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') or [] %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set ns = namespace(hour_prices=[]) %}
          {% for p in prices if p.dtime.startswith(today) and p.dtime.split(' ')[1][:2] == '07' %}
            {% set ns.hour_prices = ns.hour_prices + [p.rce_pln/1000 if p.rce_pln > 10 else p.rce_pln] %}
          {% endfor %}
          {% if ns.hour_prices | length > 0 %}
            {% set pr = ((ns.hour_prices | sum) / (ns.hour_prices | length)) | round(2) %}
            {% if pr < 0.2 %}🟢🟢{% elif pr < p33 %}🟢{% elif pr <= p66 %}🟡{% else %}🔴{% endif %} {{ '%.2f'|format(pr) }}
          {% else %}-{% endif %}
        h08: >
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') or [] %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set ns = namespace(hour_prices=[]) %}
          {% for p in prices if p.dtime.startswith(today) and p.dtime.split(' ')[1][:2] == '08' %}
            {% set ns.hour_prices = ns.hour_prices + [p.rce_pln/1000 if p.rce_pln > 10 else p.rce_pln] %}
          {% endfor %}
          {% if ns.hour_prices | length > 0 %}
            {% set pr = ((ns.hour_prices | sum) / (ns.hour_prices | length)) | round(2) %}
            {% if pr < 0.2 %}🟢🟢{% elif pr < p33 %}🟢{% elif pr <= p66 %}🟡{% else %}🔴{% endif %} {{ '%.2f'|format(pr) }}
          {% else %}-{% endif %}
        h09: >
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') or [] %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set ns = namespace(hour_prices=[]) %}
          {% for p in prices if p.dtime.startswith(today) and p.dtime.split(' ')[1][:2] == '09' %}
            {% set ns.hour_prices = ns.hour_prices + [p.rce_pln/1000 if p.rce_pln > 10 else p.rce_pln] %}
          {% endfor %}
          {% if ns.hour_prices | length > 0 %}
            {% set pr = ((ns.hour_prices | sum) / (ns.hour_prices | length)) | round(2) %}
            {% if pr < 0.2 %}🟢🟢{% elif pr < p33 %}🟢{% elif pr <= p66 %}🟡{% else %}🔴{% endif %} {{ '%.2f'|format(pr) }}
          {% else %}-{% endif %}
        h10: >
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') or [] %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set ns = namespace(hour_prices=[]) %}
          {% for p in prices if p.dtime.startswith(today) and p.dtime.split(' ')[1][:2] == '10' %}
            {% set ns.hour_prices = ns.hour_prices + [p.rce_pln/1000 if p.rce_pln > 10 else p.rce_pln] %}
          {% endfor %}
          {% if ns.hour_prices | length > 0 %}
            {% set pr = ((ns.hour_prices | sum) / (ns.hour_prices | length)) | round(2) %}
            {% if pr < 0.2 %}🟢🟢{% elif pr < p33 %}🟢{% elif pr <= p66 %}🟡{% else %}🔴{% endif %} {{ '%.2f'|format(pr) }}
          {% else %}-{% endif %}
        h11: >
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') or [] %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set ns = namespace(hour_prices=[]) %}
          {% for p in prices if p.dtime.startswith(today) and p.dtime.split(' ')[1][:2] == '11' %}
            {% set ns.hour_prices = ns.hour_prices + [p.rce_pln/1000 if p.rce_pln > 10 else p.rce_pln] %}
          {% endfor %}
          {% if ns.hour_prices | length > 0 %}
            {% set pr = ((ns.hour_prices | sum) / (ns.hour_prices | length)) | round(2) %}
            {% if pr < 0.2 %}🟢🟢{% elif pr < p33 %}🟢{% elif pr <= p66 %}🟡{% else %}🔴{% endif %} {{ '%.2f'|format(pr) }}
          {% else %}-{% endif %}
        h12: >
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') or [] %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set ns = namespace(hour_prices=[]) %}
          {% for p in prices if p.dtime.startswith(today) and p.dtime.split(' ')[1][:2] == '12' %}
            {% set ns.hour_prices = ns.hour_prices + [p.rce_pln/1000 if p.rce_pln > 10 else p.rce_pln] %}
          {% endfor %}
          {% if ns.hour_prices | length > 0 %}
            {% set pr = ((ns.hour_prices | sum) / (ns.hour_prices | length)) | round(2) %}
            {% if pr < 0.2 %}🟢🟢{% elif pr < p33 %}🟢{% elif pr <= p66 %}🟡{% else %}🔴{% endif %} {{ '%.2f'|format(pr) }}
          {% else %}-{% endif %}
        h13: >
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') or [] %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set ns = namespace(hour_prices=[]) %}
          {% for p in prices if p.dtime.startswith(today) and p.dtime.split(' ')[1][:2] == '13' %}
            {% set ns.hour_prices = ns.hour_prices + [p.rce_pln/1000 if p.rce_pln > 10 else p.rce_pln] %}
          {% endfor %}
          {% if ns.hour_prices | length > 0 %}
            {% set pr = ((ns.hour_prices | sum) / (ns.hour_prices | length)) | round(2) %}
            {% if pr < 0.2 %}🟢🟢{% elif pr < p33 %}🟢{% elif pr <= p66 %}🟡{% else %}🔴{% endif %} {{ '%.2f'|format(pr) }}
          {% else %}-{% endif %}
        h14: >
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') or [] %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set ns = namespace(hour_prices=[]) %}
          {% for p in prices if p.dtime.startswith(today) and p.dtime.split(' ')[1][:2] == '14' %}
            {% set ns.hour_prices = ns.hour_prices + [p.rce_pln/1000 if p.rce_pln > 10 else p.rce_pln] %}
          {% endfor %}
          {% if ns.hour_prices | length > 0 %}
            {% set pr = ((ns.hour_prices | sum) / (ns.hour_prices | length)) | round(2) %}
            {% if pr < 0.2 %}🟢🟢{% elif pr < p33 %}🟢{% elif pr <= p66 %}🟡{% else %}🔴{% endif %} {{ '%.2f'|format(pr) }}
          {% else %}-{% endif %}
        h15: >
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') or [] %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set ns = namespace(hour_prices=[]) %}
          {% for p in prices if p.dtime.startswith(today) and p.dtime.split(' ')[1][:2] == '15' %}
            {% set ns.hour_prices = ns.hour_prices + [p.rce_pln/1000 if p.rce_pln > 10 else p.rce_pln] %}
          {% endfor %}
          {% if ns.hour_prices | length > 0 %}
            {% set pr = ((ns.hour_prices | sum) / (ns.hour_prices | length)) | round(2) %}
            {% if pr < 0.2 %}🟢🟢{% elif pr < p33 %}🟢{% elif pr <= p66 %}🟡{% else %}🔴{% endif %} {{ '%.2f'|format(pr) }}
          {% else %}-{% endif %}
        h16: >
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') or [] %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set ns = namespace(hour_prices=[]) %}
          {% for p in prices if p.dtime.startswith(today) and p.dtime.split(' ')[1][:2] == '16' %}
            {% set ns.hour_prices = ns.hour_prices + [p.rce_pln/1000 if p.rce_pln > 10 else p.rce_pln] %}
          {% endfor %}
          {% if ns.hour_prices | length > 0 %}
            {% set pr = ((ns.hour_prices | sum) / (ns.hour_prices | length)) | round(2) %}
            {% if pr < 0.2 %}🟢🟢{% elif pr < p33 %}🟢{% elif pr <= p66 %}🟡{% else %}🔴{% endif %} {{ '%.2f'|format(pr) }}
          {% else %}-{% endif %}
        h17: >
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') or [] %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set ns = namespace(hour_prices=[]) %}
          {% for p in prices if p.dtime.startswith(today) and p.dtime.split(' ')[1][:2] == '17' %}
            {% set ns.hour_prices = ns.hour_prices + [p.rce_pln/1000 if p.rce_pln > 10 else p.rce_pln] %}
          {% endfor %}
          {% if ns.hour_prices | length > 0 %}
            {% set pr = ((ns.hour_prices | sum) / (ns.hour_prices | length)) | round(2) %}
            {% if pr < 0.2 %}🟢🟢{% elif pr < p33 %}🟢{% elif pr <= p66 %}🟡{% else %}🔴{% endif %} {{ '%.2f'|format(pr) }}
          {% else %}-{% endif %}
        h18: >
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') or [] %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set ns = namespace(hour_prices=[]) %}
          {% for p in prices if p.dtime.startswith(today) and p.dtime.split(' ')[1][:2] == '18' %}
            {% set ns.hour_prices = ns.hour_prices + [p.rce_pln/1000 if p.rce_pln > 10 else p.rce_pln] %}
          {% endfor %}
          {% if ns.hour_prices | length > 0 %}
            {% set pr = ((ns.hour_prices | sum) / (ns.hour_prices | length)) | round(2) %}
            {% if pr < 0.2 %}🟢🟢{% elif pr < p33 %}🟢{% elif pr <= p66 %}🟡{% else %}🔴{% endif %} {{ '%.2f'|format(pr) }}
          {% else %}-{% endif %}
        h19: >
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') or [] %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set ns = namespace(hour_prices=[]) %}
          {% for p in prices if p.dtime.startswith(today) and p.dtime.split(' ')[1][:2] == '19' %}
            {% set ns.hour_prices = ns.hour_prices + [p.rce_pln/1000 if p.rce_pln > 10 else p.rce_pln] %}
          {% endfor %}
          {% if ns.hour_prices | length > 0 %}
            {% set pr = ((ns.hour_prices | sum) / (ns.hour_prices | length)) | round(2) %}
            {% if pr < 0.2 %}🟢🟢{% elif pr < p33 %}🟢{% elif pr <= p66 %}🟡{% else %}🔴{% endif %} {{ '%.2f'|format(pr) }}
          {% else %}-{% endif %}
        h20: >
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') or [] %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set ns = namespace(hour_prices=[]) %}
          {% for p in prices if p.dtime.startswith(today) and p.dtime.split(' ')[1][:2] == '20' %}
            {% set ns.hour_prices = ns.hour_prices + [p.rce_pln/1000 if p.rce_pln > 10 else p.rce_pln] %}
          {% endfor %}
          {% if ns.hour_prices | length > 0 %}
            {% set pr = ((ns.hour_prices | sum) / (ns.hour_prices | length)) | round(2) %}
            {% if pr < 0.2 %}🟢🟢{% elif pr < p33 %}🟢{% elif pr <= p66 %}🟡{% else %}🔴{% endif %} {{ '%.2f'|format(pr) }}
          {% else %}-{% endif %}
        h21: >
          {% set today = now().strftime('%Y-%m-%d') %}
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') or [] %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set ns = namespace(hour_prices=[]) %}
          {% for p in prices if p.dtime.startswith(today) and p.dtime.split(' ')[1][:2] == '21' %}
            {% set ns.hour_prices = ns.hour_prices + [p.rce_pln/1000 if p.rce_pln > 10 else p.rce_pln] %}
          {% endfor %}
          {% if ns.hour_prices | length > 0 %}
            {% set pr = ((ns.hour_prices | sum) / (ns.hour_prices | length)) | round(2) %}
            {% if pr < 0.2 %}🟢🟢{% elif pr < p33 %}🟢{% elif pr <= p66 %}🟡{% else %}🔴{% endif %} {{ '%.2f'|format(pr) }}
          {% else %}-{% endif %}
        # JUTRO - t06-t21 (analogicznie z tomorrow)
        t06: >
          {% set tmr = (as_timestamp(now()) + 86400) | timestamp_custom('%Y-%m-%d') %}
          {% set prices = state_attr('sensor.rce_pse_cena_jutro', 'prices') or [] %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set ns = namespace(hour_prices=[]) %}
          {% for p in prices if p.dtime.startswith(tmr) and p.dtime.split(' ')[1][:2] == '06' %}
            {% set ns.hour_prices = ns.hour_prices + [p.rce_pln/1000 if p.rce_pln > 10 else p.rce_pln] %}
          {% endfor %}
          {% if ns.hour_prices | length > 0 %}
            {% set pr = ((ns.hour_prices | sum) / (ns.hour_prices | length)) | round(2) %}
            {% if pr < 0.2 %}🟢🟢{% elif pr < p33 %}🟢{% elif pr <= p66 %}🟡{% else %}🔴{% endif %} {{ '%.2f'|format(pr) }}
          {% else %}-{% endif %}
        # ... (analogicznie t07-t21 dla jutro)

# ============================================
# WSPÓŁCZYNNIK KOREKCJI PROGNOZY PV
# Forecast.Solar zawyża prognozy, szczególnie zimą
# ============================================
- sensor:
    - name: "PV Współczynnik korekcji"
      unique_id: pv_correction_factor
      state: >
        {% set month = now().month %}
        {% set factors = {1: 0.50, 2: 0.60, 3: 0.75, 4: 0.85, 5: 0.90, 6: 0.90,
                          7: 0.90, 8: 0.90, 9: 0.85, 10: 0.75, 11: 0.60, 12: 0.50} %}
        {{ factors.get(month, 0.75) }}
      icon: mdi:percent
      attributes:
        friendly_name: "Współczynnik korekcji prognozy PV"
        description: "Zimą Forecast.Solar zawyża prognozy o 30-50%"

# ============================================
# PROGNOZA PV - SUMA PŁASZCZYZN Z KOREKCJĄ
# ZMIEŃ nazwy sensorów jeśli masz inne płaszczyzny!
# ============================================
- sensor:
    - name: "Prognoza PV dzisiaj"
      unique_id: prognoza_pv_dzisiaj
      unit_of_measurement: "kWh"
      state: >
        {% set se = states('sensor.pv_se_prognoza_dzis') | float(0) %}
        {% set sw = states('sensor.pv_sw_prognoza_dzis') | float(0) %}
        {% set factor = states('sensor.pv_wspolczynnik_korekcji') | float(0.75) %}
        {{ ((se + sw) * factor) | round(1) }}
      icon: mdi:solar-power
      attributes:
        friendly_name: "Prognoza PV dziś (skorygowana)"
        raw_forecast: "{{ (states('sensor.pv_se_prognoza_dzis') | float(0) + states('sensor.pv_sw_prognoza_dzis') | float(0)) | round(1) }}"
        correction_factor: "{{ states('sensor.pv_wspolczynnik_korekcji') }}"

- sensor:
    - name: "Prognoza PV jutro"
      unique_id: prognoza_pv_jutro
      unit_of_measurement: "kWh"
      state: >
        {% set se = states('sensor.pv_se_prognoza_jutro') | float(0) %}
        {% set sw = states('sensor.pv_sw_prognoza_jutro') | float(0) %}
        {% set factor = states('sensor.pv_wspolczynnik_korekcji') | float(0.75) %}
        {{ ((se + sw) * factor) | round(1) }}
      icon: mdi:solar-power

# ============================================
# NADWYŻKA / DEFICYT MOCY
# ============================================
- sensor:
    - name: "Nadwyżka PV"
      unique_id: nadwyzka_pv
      unit_of_measurement: "kW"
      state: >
        {% set pv = states('sensor.inwerter_moc_wejsciowa') | float(0) / 1000 %}
        {% set load = states('sensor.pomiar_mocy_moc_czynna') | float(0) / 1000 | abs %}
        {% set surplus = pv - load %}
        {{ [surplus, 0] | max | round(2) }}
      icon: mdi:solar-power

- sensor:
    - name: "Deficyt mocy"
      unique_id: deficyt_mocy
      unit_of_measurement: "kW"
      state: >
        {% set pv = states('sensor.inwerter_moc_wejsciowa') | float(0) / 1000 %}
        {% set load = states('sensor.pomiar_mocy_moc_czynna') | float(0) / 1000 | abs %}
        {% set deficit = load - pv %}
        {{ [deficit, 0] | max | round(2) }}
      icon: mdi:flash-alert

# ============================================
# BINARNE SENSORY
# ============================================
- binary_sensor:
    - name: "Sezon grzewczy"
      unique_id: sezon_grzewczy
      state: >
        {% set month = now().month %}
        {{ month >= 10 or month <= 4 }}
      icon: mdi:radiator

    - name: "PC CO aktywne"
      unique_id: pc_co_aktywne
      state: >
        {% set temp = states('sensor.temperatura_zewnetrzna') | float(15) %}
        {% set sezon = is_state('binary_sensor.sezon_grzewczy', 'on') %}
        {{ sezon and temp < 12 }}
      icon: mdi:heat-pump

    - name: "Okno CWU"
      unique_id: okno_cwu
      state: >
        {% set hour = now().hour %}
        {{ hour >= 12 and hour < 15 }}
      icon: mdi:water-boiler

    - name: "Bateria bezpieczna temperatura"
      unique_id: bateria_bezpieczna_temperatura
      state: >
        {% set temp = states('sensor.akumulator_1_bms_temperature') | float(25) %}
        {{ temp >= 5 and temp <= 40 }}
      icon: mdi:thermometer-check

    - name: "Awaria sieci"
      unique_id: awaria_sieci
      state: >
        {% set grid = states('sensor.pomiar_mocy_moc_czynna') %}
        {% set status = states('sensor.inwerter_stan') | lower %}
        {{ grid in ['unavailable', 'unknown'] or status in ['off-grid', 'backup', 'fault'] }}
      icon: >
        {% if this.state == 'on' %}mdi:transmission-tower-off{% else %}mdi:transmission-tower{% endif %}

# ============================================
# TEMPERATURA BATERII
# ZMIEŃ sensor jeśli masz inną nazwę!
# ============================================
- sensor:
    - name: "Bateria temperatura maksymalna"
      unique_id: bateria_temperatura_maksymalna
      unit_of_measurement: "°C"
      state: >
        {{ states('sensor.akumulator_1_bms_temperature') | float(25) }}
      icon: mdi:thermometer

# ============================================
# EVENT LOG - Ostatnie zdarzenie (parser JSON)
# ============================================
- sensor:
    - name: "Event Log - Ostatnie zdarzenie"
      unique_id: event_log_ostatnie_zdarzenie
      state: >
        {% set log = states('input_text.event_log_1') %}
        {% if log and log != 'unknown' and log | length > 10 %}
          {% set ts = log.split('"ts":"')[1].split('"')[0] if '"ts":"' in log else '' %}
          {% set time = ts.split('T')[1][:5] if 'T' in ts else ts %}
          {% set cat = log.split('"cat":"')[1].split('"')[0] if '"cat":"' in log else 'INFO' %}
          {{ time }} [{{ cat }}]
        {% else %}
          Brak
        {% endif %}
      icon: mdi:history
      attributes:
        full_message: >
          {% set log = states('input_text.event_log_1') %}
          {% if log and '"msg":"' in log %}
            {{ log.split('"msg":"')[1].split('"')[0] }}
          {% else %}
            -
          {% endif %}
```

**WAŻNE:** To jest tylko część template_sensors.yaml. Pełny plik zawiera ~1000 linii i jest w repozytorium źródłowym. Skopiuj pełną wersję z: `config/template_sensors.yaml`

---

## KROK 11: lovelace_huawei.yaml (Dashboard)

**UTWÓRZ PLIK:** `config/lovelace_huawei.yaml`

```yaml
# Dashboard Huawei Solar - 3 kolumny
title: Huawei Solar PV
views:
  - title: Przegląd
    icon: mdi:solar-power
    type: sections
    max_columns: 3
    sections:
      # SEKCJA 1 (lewa kolumna)
      - type: grid
        column_span: 1
        cards:
          # Pogoda
          - type: weather-forecast
            entity: weather.forecast_dom
            show_forecast: true
            forecast_type: hourly
            show_current: true

          # Bateria
          - type: entities
            title: Zarządzanie Baterią
            icon: mdi:battery-charging
            entities:
              - entity: input_text.battery_decision_reason
                name: 🎯 Decyzja
                icon: mdi:chart-line
              - entity: input_number.battery_target_soc
                name: 🎯 Target SOC (obliczony o 04:00)
              - entity: sensor.akumulatory_stan_pojemnosci
                name: 🔋 Stan naładowania (SOC)
                icon: mdi:battery-80
              - entity: switch.akumulatory_ladowanie_z_sieci
                name: Ładowanie z sieci
              - entity: sensor.akumulatory_status
                name: Status baterii
              - entity: sensor.akumulatory_moc_ladowania_rozladowania
                name: Moc ładowania (+) lub rozładowania (-)
                icon: mdi:battery-charging
              - entity: sensor.bateria_temperatura_maksymalna
                name: 🌡️ Temperatura baterii (max)
                icon: mdi:thermometer-high
              - entity: binary_sensor.bateria_bezpieczna_temperatura
                name: ✅ Bezpieczna temperatura
                icon: mdi:thermometer-check
              - entity: select.akumulatory_tryb_pracy
                name: ⚙️ Tryb pracy
            state_color: true

          # Powiadomienia
          - type: entities
            title: Powiadomienia
            icon: mdi:bell
            entities:
              - entity: input_boolean.telegram_notifications_enabled
                name: 📱 Telegram
                icon: mdi:telegram
              - entity: input_boolean.persistent_notifications_enabled
                name: 🔔 Powiadomienia UI
                icon: mdi:bell-ring
              - entity: input_select.telegram_notification_level
                name: 📊 Min. poziom Telegram
                icon: mdi:filter

      # SEKCJA 2 (środkowa kolumna)
      - type: grid
        column_span: 1
        cards:
          # Ceny energii
          - type: entities
            title: Ceny energii RCE
            icon: mdi:cash-multiple
            entities:
              - entity: sensor.strefa_taryfowa
                name: Strefa taryfowa G12w
                icon: mdi:clock-time-four-outline
              - entity: sensor.cena_zakupu_energii
                name: Cena obecna RCE
                icon: mdi:cash
              - entity: sensor.rce_srednia_wieczorna
                name: RCE średnia wieczorna (zachód→22h)
                icon: mdi:chart-timeline
              - entity: input_text.battery_cheapest_hours
                name: RCE najtańsze godziny
                icon: mdi:currency-usd
              - type: attribute
                entity: sensor.rce_progi_cenowe
                attribute: legend
                name: Progi cenowe
                icon: mdi:palette

          # Ceny godzinowe RCE (tabela z kolorami)
          - type: markdown
            title: Ceny RCE godzinowe
            content: |
              **Dziś** &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **Jutro**
              | Godz | Cena | &nbsp;&nbsp; | Godz | Cena | &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&#124;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; | Godz | Cena | &nbsp;&nbsp; | Godz | Cena |
              |------|------|------|------|------|:------------:|------|------|------|------|------|
              | 06 | {{ state_attr('sensor.rce_ceny_godzinowe', 'h06') }} | | 14 | {{ state_attr('sensor.rce_ceny_godzinowe', 'h14') }} | &nbsp;&nbsp;&nbsp;&#124;&nbsp;&nbsp;&nbsp; | 06 | {{ state_attr('sensor.rce_ceny_godzinowe', 't06') }} | | 14 | {{ state_attr('sensor.rce_ceny_godzinowe', 't14') }} |
              | 07 | {{ state_attr('sensor.rce_ceny_godzinowe', 'h07') }} | | 15 | {{ state_attr('sensor.rce_ceny_godzinowe', 'h15') }} | &nbsp;&nbsp;&nbsp;&#124;&nbsp;&nbsp;&nbsp; | 07 | {{ state_attr('sensor.rce_ceny_godzinowe', 't07') }} | | 15 | {{ state_attr('sensor.rce_ceny_godzinowe', 't15') }} |
              | 08 | {{ state_attr('sensor.rce_ceny_godzinowe', 'h08') }} | | 16 | {{ state_attr('sensor.rce_ceny_godzinowe', 'h16') }} | &nbsp;&nbsp;&nbsp;&#124;&nbsp;&nbsp;&nbsp; | 08 | {{ state_attr('sensor.rce_ceny_godzinowe', 't08') }} | | 16 | {{ state_attr('sensor.rce_ceny_godzinowe', 't16') }} |
              | 09 | {{ state_attr('sensor.rce_ceny_godzinowe', 'h09') }} | | 17 | {{ state_attr('sensor.rce_ceny_godzinowe', 'h17') }} | &nbsp;&nbsp;&nbsp;&#124;&nbsp;&nbsp;&nbsp; | 09 | {{ state_attr('sensor.rce_ceny_godzinowe', 't09') }} | | 17 | {{ state_attr('sensor.rce_ceny_godzinowe', 't17') }} |
              | 10 | {{ state_attr('sensor.rce_ceny_godzinowe', 'h10') }} | | 18 | {{ state_attr('sensor.rce_ceny_godzinowe', 'h18') }} | &nbsp;&nbsp;&nbsp;&#124;&nbsp;&nbsp;&nbsp; | 10 | {{ state_attr('sensor.rce_ceny_godzinowe', 't10') }} | | 18 | {{ state_attr('sensor.rce_ceny_godzinowe', 't18') }} |
              | 11 | {{ state_attr('sensor.rce_ceny_godzinowe', 'h11') }} | | 19 | {{ state_attr('sensor.rce_ceny_godzinowe', 'h19') }} | &nbsp;&nbsp;&nbsp;&#124;&nbsp;&nbsp;&nbsp; | 11 | {{ state_attr('sensor.rce_ceny_godzinowe', 't11') }} | | 19 | {{ state_attr('sensor.rce_ceny_godzinowe', 't19') }} |
              | 12 | {{ state_attr('sensor.rce_ceny_godzinowe', 'h12') }} | | 20 | {{ state_attr('sensor.rce_ceny_godzinowe', 'h20') }} | &nbsp;&nbsp;&nbsp;&#124;&nbsp;&nbsp;&nbsp; | 12 | {{ state_attr('sensor.rce_ceny_godzinowe', 't12') }} | | 20 | {{ state_attr('sensor.rce_ceny_godzinowe', 't20') }} |
              | 13 | {{ state_attr('sensor.rce_ceny_godzinowe', 'h13') }} | | 21 | {{ state_attr('sensor.rce_ceny_godzinowe', 'h21') }} | &nbsp;&nbsp;&nbsp;&#124;&nbsp;&nbsp;&nbsp; | 13 | {{ state_attr('sensor.rce_ceny_godzinowe', 't13') }} | | 21 | {{ state_attr('sensor.rce_ceny_godzinowe', 't21') }} |

          # Prognoza PV
          - type: entities
            title: Prognoza PV i bilans mocy
            icon: mdi:solar-power-variant
            entities:
              - entity: sensor.prognoza_pv_dzisiaj
                name: Prognoza PV dziś (pozostało)
                icon: mdi:solar-power
              - entity: sensor.prognoza_pv_jutro
                name: Prognoza PV jutro
                icon: mdi:solar-power
              - entity: sensor.nadwyzka_pv
                name: Nadwyżka PV
                icon: mdi:solar-power
              - entity: sensor.deficyt_mocy
                name: Deficyt mocy
                icon: mdi:flash-alert
              - entity: input_text.battery_storage_status
                name: 📊 Analiza
                icon: mdi:clock-outline

      # SEKCJA 3 (prawa kolumna)
      - type: grid
        column_span: 1
        cards:
          # Historia mocy
          - type: history-graph
            title: Historia mocy (24h)
            hours_to_show: 24
            entities:
              - entity: sensor.inwerter_moc_czynna
                name: Moc wyjściowa
              - entity: sensor.akumulatory_moc_ladowania_rozladowania
                name: Bateria
              - entity: sensor.pomiar_mocy_moc_czynna
                name: Sieć

          # Produkcja
          - type: entities
            title: Produkcja energii
            icon: mdi:chart-line
            entities:
              - entity: sensor.inwerter_moc_wejsciowa
                name: Aktualna produkcja PV
                icon: mdi:solar-power
              - entity: sensor.produkcja_pv_dzienna_rzeczywista
                name: Dzienna produkcja PV
                icon: mdi:weather-sunny

          # Sezon grzewczy
          - type: entities
            title: Sezon grzewczy
            icon: mdi:radiator
            entities:
              - entity: binary_sensor.sezon_grzewczy
                name: Sezon grzewczy aktywny
                icon: mdi:radiator
              - entity: binary_sensor.pc_co_aktywne
                name: Pompa ciepła CO aktywna
                icon: mdi:heat-pump
              - entity: binary_sensor.okno_cwu
                name: Okno CWU aktywne
                icon: mdi:water-boiler

          # Event Log
          - type: entities
            title: 📋 Event Log
            icon: mdi:text-box-outline
            entities:
              - entity: sensor.event_log_ostatnie_zdarzenie
                name: Ostatnie zdarzenie
                secondary_info: attribute
                attribute: full_message
              - entity: input_text.event_log_1
                name: "Slot 1"
              - entity: input_text.event_log_2
                name: "Slot 2"
              - entity: input_text.event_log_3
                name: "Slot 3"
```

---

## KROK 12: Skopiuj pełne pliki z repozytorium

Następujące pliki są zbyt długie, aby umieścić je w instrukcji. **SKOPIUJ JE Z REPOZYTORIUM ŹRÓDŁOWEGO:**

| Plik | Linie | Opis |
|------|-------|------|
| `config/python_scripts/battery_algorithm.py` | ~1470 | Główny algorytm zarządzania baterią |
| `config/python_scripts/calculate_daily_strategy.py` | ~200 | Obliczanie Target SOC |
| `config/automations_battery.yaml` | ~860 | Wszystkie automatyzacje baterii |
| `config/automations_errors.yaml` | ~200 | Automatyzacje błędów i powiadomień |
| `config/template_sensors.yaml` | ~1000 | Pełna wersja sensorów |

**Repozytorium źródłowe:** https://github.com/MarekBodynek/home-assistant-huawei

### Parametry do zmiany w battery_algorithm.py:

```python
# Na górze pliku - ZMIEŃ te wartości:
BATTERY_CAPACITY_KWH = 10  # Twoja pojemność baterii
BATTERY_MAX_CHARGE_KW = 5  # Max moc ładowania
```

### Parametry TOU (ładowanie w L2):

```python
# Weekend bez ładowania (tylko od Ndz 22:00)
tou_periods = (
    "22:00-23:59/123457/+\n"   # Pon-Pt + Ndz wieczór (nie Sob!)
    "00:00-05:59/12345/+\n"    # Tylko dni robocze
    "13:00-14:59/12345/+\n"    # Tylko dni robocze
    "06:00-12:59/67/+\n"       # Weekend: ochrona baterii
    "15:00-21:59/67/+"         # Weekend: ochrona baterii
)
```

---

## KROK 13: Konfiguracja integracji Huawei Solar

### 13.1 Dodanie integracji
1. Settings → Devices & Services → Add Integration
2. Szukaj "Huawei Solar"
3. Podaj:
   - Host: IP inwertera (np. 192.168.1.100)
   - Port: 502 (Modbus)
   - Slave IDs: 1 (inwerter), 200 (bateria)

### 13.2 Znajdź device_id baterii (WAŻNE!)
1. Settings → Devices & Services → Huawei Solar
2. Kliknij urządzenie "Akumulatory" lub "Battery"
3. Skopiuj ID z URL: `...device_id=abc123def456...`
4. Dodaj do `secrets.yaml`:
```yaml
huawei_battery_device_id: "abc123def456..."
```

### 13.3 Włącz sensor temperatury baterii
1. Settings → Devices & Services → Huawei Solar
2. Akumulator 1 → Entities
3. Enable: "BMS temperature"
4. Nazwa sensora: `sensor.akumulator_1_bms_temperature`

---

## KROK 14: Weryfikacja po instalacji

### 14.1 Sprawdź sensory (Developer Tools → States)
```
sensor.strefa_taryfowa: "L1" lub "L2" ✓
sensor.akumulatory_stan_pojemnosci: 20-80 (%) ✓
sensor.akumulator_1_bms_temperature: 15-35 (°C) ✓
sensor.rce_pse_cena: > 0 ✓
sensor.prognoza_pv_dzisiaj: > 0 (kWh) ✓
binary_sensor.dzien_roboczy: on/off ✓
binary_sensor.awaria_sieci: off ✓
sensor.rce_progi_cenowe (p33, p66): > 0 ✓
```

### 14.2 Test algorytmu
```yaml
# Developer Tools → Services
service: python_script.battery_algorithm

# Sprawdź wyniki:
input_text.battery_decision_reason: "powinien zawierać opis decyzji"
input_text.battery_cheapest_hours: "7🟢 8🟡 9🟢..." (z kolorowymi kropkami)
```

### 14.3 Test powiadomień Telegram
```yaml
# Developer Tools → Services
service: notify.telegram
data:
  message: "Test powiadomienia z Home Assistant"
```

---

## PODSUMOWANIE ZMIAN DLA NOWEJ INSTALACJI

| Plik | Co zmienić |
|------|------------|
| `secrets.yaml` | latitude, longitude, elevation, telegram_*, huawei_* |
| `configuration.yaml` | URL-e Forecast.Solar (lat/lon/tilt/azimuth/kwp) |
| `input_numbers.yaml` | battery_capacity_kwh |
| `battery_algorithm.py` | BATTERY_CAPACITY_KWH, BATTERY_MAX_CHARGE_KW |
| `template_sensors.yaml` | Nazwy sensorów PV jeśli inne |

---

## LOGIKA KOLOROWYCH KROPEK RCE

```
🟢🟢 (super green) = cena < 0.20 PLN/kWh (bardzo tania)
🟢 (green) = cena < p33 (tania - dolne 33%)
🟡 (yellow) = cena p33-p66 (średnia - środkowe 33%)
🔴 (red) = cena > p66 (droga - górne 33%)
```

Progi p33 i p66 są obliczane dynamicznie na podstawie percentyli cen danego dnia (godziny 06-21).

---

## TROUBLESHOOTING

### Problem: Sensory "unavailable"
- Sprawdź czy integracja Huawei Solar jest połączona
- Sprawdź IP inwertera i port Modbus

### Problem: Kolory RCE nie działają
- Sprawdź czy `sensor.rce_pse_cena` ma atrybut `prices`
- Sprawdź czy `sensor.rce_progi_cenowe` pokazuje p33/p66

### Problem: Bateria nie ładuje
- Sprawdź `sensor.akumulatory_status` - czy nie jest "Sleep mode"?
- Sprawdź `binary_sensor.bateria_bezpieczna_temperatura` - czy ON?
- Sprawdź `sensor.strefa_taryfowa` - czy L2?

### Problem: Prognozy PV zawyżone
- Sprawdź `sensor.pv_wspolczynnik_korekcji` - powinien być 0.5-0.9
- Zimą (XII-II) współczynnik = 0.50 (prognoza × 0.5)

---

## KONTAKT

Repozytorium: https://github.com/MarekBodynek/home-assistant-huawei

W razie problemów sprawdź logi:
- Settings → System → Logs
- Szukaj: "battery_algorithm", "huawei_solar", "telegram"
