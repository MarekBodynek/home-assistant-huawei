# Instrukcja konfiguracji Home Assistant - Huawei Solar Battery Management

## Dla Claude Code - Kompletna instrukcja instalacji

Ta instrukcja pozwala skonfigurować pełny system zarządzania baterią Huawei LUNA 2000 z optymalizacją kosztów energii RCE PSE.

---

## PARAMETRY INSTALACJI (DOSTOSUJ!)

```yaml
# ========================================
# PARAMETRY SPECYFICZNE DLA TEJ INSTALACJI
# ========================================

BATERIA:
  model: "Huawei LUNA 2000"
  pojemnosc_kwh: 10          # Zmień na rzeczywistą pojemność
  min_soc: 20                # Minimalny SOC (%)
  max_soc: 80                # Maksymalny SOC (%)
  moc_ladowania_kw: 5        # Max moc ładowania

PANELE_PV:
  laczna_moc_kwp: 6.0        # Łączna moc instalacji

  plaszczyzna_1:
    nazwa: "Południowy-wschód"
    moc_kwp: 3.6             # 9 paneli × 400W = 3.6 kWp
    azymut: 135              # SE = 135° (S=180, E=90)
    nachylenie: 30           # Kąt nachylenia

  plaszczyzna_2:
    nazwa: "Południowy-zachód"
    moc_kwp: 2.8             # 7 paneli × 400W = 2.8 kWp
    azymut: 225              # SW = 225° (S=180, W=270)
    nachylenie: 30           # Kąt nachylenia

LOKALIZACJA:
  latitude: 52.2297          # Szerokość geograficzna
  longitude: 21.0122         # Długość geograficzna
  elevation: 100             # Wysokość n.p.m.
  timezone: "Europe/Warsaw"

TARYFA:
  typ: "G12w"                # Taryfa dwustrefowa weekendowa
  # L1 (droga): 06:00-13:00, 15:00-22:00 dni robocze
  # L2 (tania): 13:00-15:00, 22:00-06:00 dni robocze + całe weekendy

POWIADOMIENIA:
  telegram_enabled: true
  telegram_bot_token: "UZUPELNIJ"
  telegram_chat_id: "UZUPELNIJ"
  mobile_app_enabled: true   # iOS/Android
```

---

## KROK 1: Wymagane integracje HACS

### 1.1 Instalacja HACS
```bash
# W kontenerze HA lub SSH
wget -O - https://get.hacs.xyz | bash -
# Restart HA, potem skonfiguruj HACS w UI
```

### 1.2 Integracje do zainstalowania przez HACS
1. **Huawei Solar** - `wlcrs/huawei_solar`
   - Komunikacja Modbus z inwerterem
   - Sterowanie baterią (TOU, ładowanie z sieci)

2. **Pstryk** lub **RCE PSE** - ceny energii z rynku hurtowego
   - Sensor: `sensor.rce_pse_cena` z atrybutem `prices`

### 1.3 Wbudowane integracje HA
- **Workday** - święta polskie (country: PL)
- **Sun** - wschód/zachód słońca
- **Telegram** - powiadomienia

---

## KROK 2: Struktura plików do utworzenia

```
config/
├── configuration.yaml      # Główna konfiguracja
├── secrets.yaml            # Dane wrażliwe (NIE COMMITUJ!)
├── template_sensors.yaml   # Sensory obliczeniowe
├── automations_battery.yaml # Automatyzacje baterii
├── automations_errors.yaml  # Automatyzacje błędów
├── input_numbers.yaml      # Zmienne numeryczne
├── input_text.yaml         # Zmienne tekstowe
├── input_boolean.yaml      # Przełączniki
├── input_select.yaml       # Listy wyboru
├── utility_meter.yaml      # Mierniki energii
├── lovelace_huawei.yaml    # Dashboard
└── python_scripts/
    ├── battery_algorithm.py        # Główny algorytm
    └── calculate_daily_strategy.py # Strategia dzienna
```

---

## KROK 3: configuration.yaml

```yaml
homeassistant:
  name: "Home"
  latitude: !secret latitude
  longitude: !secret longitude
  elevation: !secret elevation
  unit_system: metric
  time_zone: Europe/Warsaw
  country: PL

# Włącz python_scripts
python_script:

# Importy konfiguracji
template: !include template_sensors.yaml
automation: !include_merge_list
  - automations_battery.yaml
  - automations_errors.yaml
input_number: !include input_numbers.yaml
input_text: !include input_text.yaml
input_boolean: !include input_boolean.yaml
input_select: !include input_select.yaml
utility_meter: !include utility_meter.yaml

# Telegram
telegram_bot:
  - platform: polling
    api_key: !secret telegram_bot_token
    allowed_chat_ids:
      - !secret telegram_chat_id

notify:
  - platform: telegram
    name: telegram
    chat_id: !secret telegram_chat_id

# Workday - święta polskie
binary_sensor:
  - platform: workday
    name: workday_poland
    country: PL

# Forecast Solar - DOSTOSUJ DO SWOJEJ INSTALACJI!
rest:
  # Płaszczyzna 1: SE (azymut 135°)
  - resource: https://api.forecast.solar/estimate/{{latitude}}/{{longitude}}/30/135/3.6
    scan_interval: 3600
    sensor:
      - name: "Prognoza PV SE"
        value_template: "{{ value_json.result.watt_hours_day | default(0) / 1000 }}"
        unit_of_measurement: "kWh"

  # Płaszczyzna 2: SW (azymut 225°)
  - resource: https://api.forecast.solar/estimate/{{latitude}}/{{longitude}}/30/225/2.8
    scan_interval: 3600
    sensor:
      - name: "Prognoza PV SW"
        value_template: "{{ value_json.result.watt_hours_day | default(0) / 1000 }}"
        unit_of_measurement: "kWh"

# Recorder - historia
recorder:
  purge_keep_days: 30
  commit_interval: 5
```

---

## KROK 4: secrets.yaml

```yaml
# UZUPEŁNIJ RZECZYWISTYMI WARTOŚCIAMI!

# Lokalizacja
latitude: "52.2297"
longitude: "21.0122"
elevation: "100"

# Telegram
telegram_bot_token: "123456789:ABCdefGHI..."
telegram_chat_id: "-1001234567890"

# Huawei Solar (jeśli potrzebne)
huawei_inverter_ip: "192.168.1.100"
huawei_modbus_port: "502"
```

---

## KROK 5: input_numbers.yaml

```yaml
battery_target_soc:
  name: "Docelowy SOC baterii"
  min: 20
  max: 80
  step: 5
  unit_of_measurement: "%"
  icon: mdi:battery-charging-high
  initial: 60

battery_capacity_kwh:
  name: "Pojemność baterii"
  min: 5
  max: 30
  step: 0.1
  unit_of_measurement: "kWh"
  icon: mdi:battery
  initial: 10  # DOSTOSUJ! 10 kWh

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
  max: 50
  step: 0.1
  unit_of_measurement: "kWh"
  icon: mdi:home-lightning-bolt
  initial: 15
```

---

## KROK 6: input_text.yaml

```yaml
battery_decision_reason:
  name: "Powód decyzji baterii"
  max: 255
  icon: mdi:head-cog

battery_storage_status:
  name: "Status magazynowania baterii"
  max: 255
  icon: mdi:battery-charging

battery_cheapest_hours:
  name: "Najtańsze godziny do magazynowania"
  max: 100
  icon: mdi:clock-outline

battery_event_log_1:
  name: "Event Log 1"
  max: 255
  icon: mdi:history

battery_event_log_2:
  name: "Event Log 2"
  max: 255
  icon: mdi:history

battery_event_log_3:
  name: "Event Log 3"
  max: 255
  icon: mdi:history

battery_event_log_4:
  name: "Event Log 4"
  max: 255
  icon: mdi:history

battery_event_log_5:
  name: "Event Log 5"
  max: 255
  icon: mdi:history
```

---

## KROK 7: input_boolean.yaml

```yaml
battery_notifications_enabled:
  name: "Powiadomienia baterii"
  icon: mdi:bell

battery_algorithm_enabled:
  name: "Algorytm baterii włączony"
  icon: mdi:robot
  initial: true

heating_season:
  name: "Sezon grzewczy"
  icon: mdi:radiator
  initial: true  # Ustaw na true w okresie grzewczym (X-IV)
```

---

## KROK 8: input_select.yaml

```yaml
battery_log_level:
  name: "Poziom logowania baterii"
  options:
    - "debug"
    - "info"
    - "warning"
    - "error"
  initial: "info"
  icon: mdi:bug
```

---

## KROK 9: template_sensors.yaml (KLUCZOWE!)

```yaml
- sensor:
    # ========================================
    # STREFA TARYFOWA G12w
    # ========================================
    - name: "Strefa taryfowa"
      unique_id: strefa_taryfowa
      state: >
        {% set hour = now().hour %}
        {% set weekday = now().weekday() %}
        {% set is_holiday = is_state('binary_sensor.workday_poland', 'off') and weekday < 5 %}
        {% set is_weekend = weekday >= 5 %}

        {% if is_weekend or is_holiday %}
          L2
        {% elif (hour >= 6 and hour < 13) or (hour >= 15 and hour < 22) %}
          L1
        {% else %}
          L2
        {% endif %}
      icon: >
        {% if is_state('sensor.strefa_taryfowa', 'L1') %}
          mdi:currency-usd
        {% else %}
          mdi:currency-usd-off
        {% endif %}

    # ========================================
    # CENA ENERGII RCE
    # ========================================
    - name: "Cena zakupu energii"
      unique_id: cena_zakupu_energii
      unit_of_measurement: "PLN/kWh"
      state: >
        {% set rce = states('sensor.rce_pse_cena') | float(0) %}
        {% if rce > 10 %}
          {{ (rce / 1000) | round(4) }}
        {% else %}
          {{ rce | round(4) }}
        {% endif %}
      icon: mdi:cash

    # ========================================
    # PROGNOZA PV - SUMA OBU PŁASZCZYZN
    # ========================================
    - name: "Prognoza PV dzisiaj"
      unique_id: prognoza_pv_dzisiaj
      unit_of_measurement: "kWh"
      state: >
        {% set pv_se = states('sensor.prognoza_pv_se') | float(0) %}
        {% set pv_sw = states('sensor.prognoza_pv_sw') | float(0) %}
        {{ (pv_se + pv_sw) | round(1) }}
      icon: mdi:solar-power

    # ========================================
    # PROGI CENOWE RCE (PERCENTYLE)
    # ========================================
    - name: "RCE Progi cenowe"
      unique_id: rce_progi_cenowe
      state: "OK"
      attributes:
        p33: >
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') %}
          {% if prices %}
            {% set values = prices | map(attribute='rce_pln') | list | sort %}
            {% set idx = (values | length * 0.33) | int %}
            {{ (values[idx] / 1000) | round(2) if values[idx] > 10 else values[idx] | round(2) }}
          {% else %}
            0.5
          {% endif %}
        p66: >
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') %}
          {% if prices %}
            {% set values = prices | map(attribute='rce_pln') | list | sort %}
            {% set idx = (values | length * 0.66) | int %}
            {{ (values[idx] / 1000) | round(2) if values[idx] > 10 else values[idx] | round(2) }}
          {% else %}
            0.7
          {% endif %}

    # ========================================
    # RCE CENY GODZINOWE Z KOLORAMI
    # ========================================
    - name: "RCE Ceny godzinowe"
      unique_id: rce_ceny_godzinowe
      state: "OK"
      attributes:
        hours: >
          {% set prices = state_attr('sensor.rce_pse_cena', 'prices') %}
          {% set p33 = state_attr('sensor.rce_progi_cenowe', 'p33') | float(0.5) %}
          {% set p66 = state_attr('sensor.rce_progi_cenowe', 'p66') | float(0.7) %}
          {% set result = [] %}
          {% if prices %}
            {% for p in prices %}
              {% set hour = p.dtime.split(' ')[1].split(':')[0] | int %}
              {% set price = (p.rce_pln / 1000) if p.rce_pln > 10 else p.rce_pln %}
              {% if price < 0.20 %}
                {% set color = 'super_green' %}
              {% elif price < p33 %}
                {% set color = 'green' %}
              {% elif price < p66 %}
                {% set color = 'yellow' %}
              {% else %}
                {% set color = 'red' %}
              {% endif %}
              {% set result = result + [{'hour': hour, 'price': price | round(2), 'color': color}] %}
            {% endfor %}
          {% endif %}
          {{ result }}

- binary_sensor:
    # ========================================
    # DZIEŃ ROBOCZY
    # ========================================
    - name: "Dzień roboczy"
      unique_id: dzien_roboczy
      state: >
        {{ is_state('binary_sensor.workday_poland', 'on') }}
      icon: >
        {% if is_state('binary_sensor.dzien_roboczy', 'on') %}
          mdi:briefcase
        {% else %}
          mdi:party-popper
        {% endif %}

    # ========================================
    # SEZON GRZEWCZY
    # ========================================
    - name: "Sezon grzewczy"
      unique_id: sezon_grzewczy
      state: >
        {% set month = now().month %}
        {{ month >= 10 or month <= 4 }}
      icon: mdi:radiator

    # ========================================
    # BEZPIECZNA TEMPERATURA BATERII
    # ========================================
    - name: "Bateria bezpieczna temperatura"
      unique_id: bateria_bezpieczna_temperatura
      state: >
        {% set temp = states('sensor.akumulator_1_temperatura') | float(20) %}
        {{ temp >= 5 and temp <= 40 }}
      icon: mdi:thermometer-check

    # ========================================
    # AWARIA SIECI
    # ========================================
    - name: "Awaria sieci"
      unique_id: awaria_sieci
      state: >
        {% set grid_sensor = states('sensor.pomiar_mocy_moc_czynna') %}
        {% set inverter_state = states('sensor.inwerter_stan') | lower %}
        {% set grid_unavailable = grid_sensor in ['unavailable', 'unknown'] %}
        {% set inverter_backup = inverter_state in ['off-grid', 'backup', 'fault'] %}
        {{ grid_unavailable or inverter_backup }}
      icon: >
        {% if is_state('binary_sensor.awaria_sieci', 'on') %}
          mdi:transmission-tower-off
        {% else %}
          mdi:transmission-tower
        {% endif %}
```

---

## KROK 10: utility_meter.yaml

```yaml
# Zużycie nocne (22:00-06:00)
zuzycie_nocne:
  source: sensor.pomiar_mocy_zuzycie
  cycle: daily
  tariffs:
    - noc
    - dzien

# Zużycie godzinowe
zuzycie_godzinowe:
  source: sensor.pomiar_mocy_zuzycie
  cycle: hourly

# Produkcja PV dzienna
produkcja_pv_dzienna:
  source: sensor.inwerter_total_dc_input_energy
  cycle: daily

# Eksport dzienny
eksport_dzienny:
  source: sensor.pomiar_mocy_eksport
  cycle: daily
```

---

## KROK 11: python_scripts/battery_algorithm.py

**WAŻNE PARAMETRY DO DOSTOSOWANIA W ALGORYTMIE:**

```python
# ========================================
# PARAMETRY INSTALACJI - DOSTOSUJ!
# ========================================

BATTERY_CAPACITY_KWH = 10  # Pojemność baterii (kWh)
BATTERY_MAX_CHARGE_KW = 5  # Max moc ładowania (kW)
BATTERY_MIN_SOC = 20       # Minimalny SOC (%)
BATTERY_MAX_SOC = 80       # Maksymalny SOC (%)

# Progi bezpieczeństwa
CRITICAL_SOC = 5           # Krytycznie niski - ładuj 24/7
LOW_SOC = 20               # Niski - priorytet ładowania w L2
TEMP_WARNING = 40          # Ostrzeżenie temperatura
TEMP_CRITICAL = 43         # Stop ładowania
TEMP_FREEZING = 0          # Stop ładowania (mróz)

# TOU periods - Weekend bez ładowania (tylko od Ndz 22:00)
TOU_PERIODS_NORMAL = (
    "22:00-23:59/123457/+\n"   # Pon-Pt + Ndz wieczór
    "00:00-05:59/12345/+\n"    # Tylko dni robocze
    "13:00-14:59/12345/+\n"    # Tylko dni robocze
    "06:00-12:59/67/+\n"       # Weekend: ochrona
    "15:00-21:59/67/+"         # Weekend: ochrona
)

TOU_PERIODS_URGENT = "00:00-23:59/1234567/+"  # Ładuj 24/7

# Sezonowe wschody/zachody słońca (Polska)
SUNRISE_SUNSET = {
    'winter': {'sunrise': 7, 'sunset': 16},    # XI-II
    'spring': {'sunrise': 6, 'sunset': 18},    # III-IV
    'summer': {'sunrise': 5, 'sunset': 20},    # V-VIII
    'autumn': {'sunrise': 6, 'sunset': 17},    # IX-X
}
```

**Skopiuj pełny algorytm z repozytorium źródłowego:**
- Plik: `config/python_scripts/battery_algorithm.py`
- Zmień tylko parametry instalacji na górze pliku

---

## KROK 12: automations_battery.yaml

```yaml
# ========================================
# GŁÓWNA PĘTLA ALGORYTMU
# ========================================
- alias: "[BATERIA] Główna pętla algorytmu"
  id: battery_main_loop
  trigger:
    # Co godzinę
    - platform: time_pattern
      minutes: 0
    # Zmiana strefy taryfowej
    - platform: state
      entity_id: sensor.strefa_taryfowa
    # Start L2 południe
    - platform: time
      at: "13:00:00"
    # Start L2 noc
    - platform: time
      at: "22:00:00"
  condition:
    - condition: state
      entity_id: input_boolean.battery_algorithm_enabled
      state: "on"
  action:
    - service: python_script.battery_algorithm

# ========================================
# OBLICZANIE TARGET SOC (21:05)
# ========================================
- alias: "[BATERIA] Oblicz Target SOC"
  id: battery_calculate_target_soc
  trigger:
    - platform: time
      at: "21:05:00"
  action:
    - service: python_script.calculate_daily_strategy

# ========================================
# WYBUDZANIE BATERII PRZED L2
# ========================================
- alias: "[BATERIA] Wybudź przed L2 noc"
  id: battery_wake_before_l2_night
  trigger:
    - platform: time
      at: "21:40:00"
  condition:
    - condition: state
      entity_id: sensor.akumulatory_status
      state: "Sleep mode"
  action:
    - repeat:
        count: 5
        sequence:
          - service: huawei_solar.forcible_charge
            data:
              device_id: !secret huawei_battery_device_id
              power: 2500
              duration: 1
          - delay:
              seconds: 30
          - condition: not
            conditions:
              - condition: state
                entity_id: sensor.akumulatory_status
                state: "Sleep mode"

- alias: "[BATERIA] Wybudź przed L2 południe"
  id: battery_wake_before_l2_noon
  trigger:
    - platform: time
      at: "12:40:00"
  condition:
    - condition: state
      entity_id: binary_sensor.dzien_roboczy
      state: "on"
    - condition: state
      entity_id: sensor.akumulatory_status
      state: "Sleep mode"
  action:
    - repeat:
        count: 5
        sequence:
          - service: huawei_solar.forcible_charge
            data:
              device_id: !secret huawei_battery_device_id
              power: 2500
              duration: 1
          - delay:
              seconds: 30
          - condition: not
            conditions:
              - condition: state
                entity_id: sensor.akumulatory_status
                state: "Sleep mode"

# ========================================
# ZBIERANIE DANYCH ML (CO GODZINĘ)
# ========================================
- alias: "[ML] Zbieranie danych godzinowych"
  id: ml_hourly_data_collection
  trigger:
    - platform: time_pattern
      minutes: 59
  action:
    - service: python_script.battery_algorithm
      data:
        collect_ml_data: true
```

---

## KROK 13: automations_errors.yaml

```yaml
# ========================================
# AWARIA SIECI - TELEGRAM
# ========================================
- alias: "[KRYTYCZNE] Awaria sieci - backup mode"
  id: grid_outage_notification
  trigger:
    - platform: state
      entity_id: binary_sensor.awaria_sieci
      to: "on"
  action:
    - service: python_script.battery_algorithm
    - service: notify.telegram
      data:
        title: "🚨 AWARIA SIECI!"
        message: |
          **Brak napięcia w sieci!**

          Bateria przejęła zasilanie domu.

          **SOC:** {{ states('sensor.akumulatory_stan_pojemnosci') }}%
          **Czas:** {{ now().strftime('%H:%M:%S') }}

          Bateria 10kWh przy zużyciu 2kW wystarczy na ~5h.

- alias: "[INFO] Sieć przywrócona"
  id: grid_restored_notification
  trigger:
    - platform: state
      entity_id: binary_sensor.awaria_sieci
      from: "on"
      to: "off"
  action:
    - service: notify.telegram
      data:
        title: "✅ Sieć przywrócona"
        message: |
          **Napięcie w sieci wróciło!**

          **SOC po awarii:** {{ states('sensor.akumulatory_stan_pojemnosci') }}%
    - delay:
        seconds: 10
    - service: python_script.battery_algorithm

# ========================================
# TEMPERATURA BATERII
# ========================================
- alias: "[OSTRZEŻENIE] Wysoka temperatura baterii"
  id: battery_temp_warning
  trigger:
    - platform: numeric_state
      entity_id: sensor.akumulator_1_temperatura
      above: 40
  action:
    - service: notify.telegram
      data:
        title: "🌡️ Wysoka temperatura baterii"
        message: |
          Temperatura: {{ states('sensor.akumulator_1_temperatura') }}°C
          Limit: 40°C

          Ładowanie może zostać ograniczone.

- alias: "[KRYTYCZNE] Temperatura krytyczna baterii"
  id: battery_temp_critical
  trigger:
    - platform: numeric_state
      entity_id: sensor.akumulator_1_temperatura
      above: 43
  action:
    - service: notify.telegram
      data:
        title: "🔥 TEMPERATURA KRYTYCZNA!"
        message: |
          Temperatura: {{ states('sensor.akumulator_1_temperatura') }}°C

          Ładowanie ZATRZYMANE!

# ========================================
# NISKI SOC
# ========================================
- alias: "[OSTRZEŻENIE] Niski SOC baterii"
  id: battery_low_soc
  trigger:
    - platform: numeric_state
      entity_id: sensor.akumulatory_stan_pojemnosci
      below: 20
  condition:
    - condition: state
      entity_id: sensor.strefa_taryfowa
      state: "L1"
  action:
    - service: notify.telegram
      data:
        title: "🔋 Niski poziom baterii"
        message: |
          SOC: {{ states('sensor.akumulatory_stan_pojemnosci') }}%
          Strefa: L1 (droga)

          Bateria będzie naładowana w L2.
```

---

## KROK 14: Konfiguracja integracji Huawei Solar

### 14.1 Dodanie integracji
1. Settings → Devices & Services → Add Integration
2. Szukaj "Huawei Solar"
3. Podaj:
   - Host: IP inwertera (np. 192.168.1.100)
   - Port: 502 (Modbus)
   - Slave IDs: 1 (inwerter), 200 (bateria)

### 14.2 Znajdź device_id baterii
1. Settings → Devices & Services → Huawei Solar
2. Kliknij urządzenie "Akumulatory" lub "Battery"
3. Skopiuj ID z URL (format: `abc123...`)
4. Dodaj do `secrets.yaml`:
```yaml
huawei_battery_device_id: "abc123def456..."
```

### 14.3 Włącz sensory temperatury
1. Settings → Devices & Services → Huawei Solar
2. Akumulator 1 → Entities
3. Enable: "BMS temperature" (sensor.akumulator_1_temperatura)

---

## KROK 15: Weryfikacja po instalacji

### 15.1 Sprawdź sensory
```yaml
# Te sensory muszą działać:
sensor.strefa_taryfowa: "L1" lub "L2"
sensor.akumulatory_stan_pojemnosci: 0-100 (%)
sensor.akumulator_1_temperatura: 15-35 (°C)
sensor.rce_pse_cena: > 0 (PLN/MWh)
sensor.prognoza_pv_se: > 0 (kWh)
sensor.prognoza_pv_sw: > 0 (kWh)
binary_sensor.dzien_roboczy: on/off
binary_sensor.awaria_sieci: off
```

### 15.2 Test algorytmu
```yaml
# Uruchom ręcznie:
# Developer Tools → Services → python_script.battery_algorithm

# Sprawdź wyniki:
input_text.battery_decision_reason: "powinien zawierać opis decyzji"
input_text.battery_cheapest_hours: "7🟢 8🟡 9🟢..." (w dzień)
```

### 15.3 Test powiadomień Telegram
```yaml
# Developer Tools → Services
service: notify.telegram
data:
  message: "Test powiadomienia z Home Assistant"
```

---

## KROK 16: Dashboard (lovelace_huawei.yaml)

Skopiuj plik `lovelace_huawei.yaml` z repozytorium źródłowego.

Dostosuj entity_id jeśli różnią się nazwy sensorów.

---

## PODSUMOWANIE KROKÓW

1. ✅ Zainstaluj HACS
2. ✅ Zainstaluj integracje: Huawei Solar, RCE PSE/Pstryk, Workday
3. ✅ Utwórz pliki konfiguracji (configuration.yaml, secrets.yaml, etc.)
4. ✅ Skopiuj template_sensors.yaml
5. ✅ Skopiuj battery_algorithm.py (DOSTOSUJ PARAMETRY!)
6. ✅ Skopiuj automations
7. ✅ Skonfiguruj integrację Huawei Solar (device_id!)
8. ✅ Włącz sensor temperatury baterii
9. ✅ Skonfiguruj Telegram
10. ✅ Restart HA
11. ✅ Weryfikacja sensorów
12. ✅ Test algorytmu
13. ✅ Test powiadomień

---

## RÓŻNICE OD INSTALACJI ŹRÓDŁOWEJ

| Parametr | Źródło | Ta instalacja |
|----------|--------|---------------|
| Bateria | 15 kWh | 10 kWh |
| PV łącznie | 10 kWp | 6 kWp |
| Płaszczyzna 1 | S | SE (135°) |
| Płaszczyzna 2 | - | SW (225°) |
| Moc PV 1 | 10 kWp | 3.6 kWp |
| Moc PV 2 | - | 2.8 kWp |
| Backup time | ~7h | ~5h |

---

## KONTAKT / WSPARCIE

Repozytorium źródłowe: https://github.com/MarekBodynek/home-assistant-huawei

W razie problemów sprawdź logi:
- Settings → System → Logs
- Szukaj: "battery_algorithm", "huawei_solar", "telegram"
