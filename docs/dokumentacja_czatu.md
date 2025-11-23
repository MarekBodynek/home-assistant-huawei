# Dokumentacja Czatu - Sesja 2025-11-23

## 1. Główne Zadania

1. **Konfiguracja FusionSolar Northbound API** - do pobierania danych historycznych dla ML
2. **Wdrożenie systemu zbierania danych o zużyciu nocnym** - utility_meter + automatyzacje
3. **Przygotowanie planowania nocnego ładowania** - obliczanie ile energii potrzeba przed 22:00

## 2. Kluczowe Koncepty Techniczne

- **FusionSolar Northbound API** - konto Bodino, hasło Keram098, region eu5
- **Utility Meter** - integracja HA do pomiaru zużycia z resetem czasowym
- **EMA (Exponential Moving Average)** - wygładzanie danych zużycia nocnego (alpha=0.3)
- **PV Start Hour** - pierwsza godzina z produkcją >500W
- **Taryfa G12w** - L2 22:00-06:00 (tania), L1 reszta (droga)
- **SCP deployment** - kopiowanie plików przez SSH zamiast git pull

## 3. Utworzone/Zmodyfikowane Pliki

### config/utility_meter.yaml (NOWY)
Mierniki zużycia energii z różnymi cyklami resetu:
```yaml
# Zuzycie nocne (22:00-06:00) - resetuje sie codziennie o 22:00
night_consumption:
  name: "Zuzycie nocne (od 22:00)"
  source: sensor.pomiar_mocy_zuzycie
  cycle: daily
  offset:
    hours: 22  # Reset o 22:00

# Zuzycie dzienne - standardowy reset o polnocy
daily_consumption:
  name: "Zuzycie dzienne"
  source: sensor.pomiar_mocy_zuzycie
  cycle: daily

# Zuzycie tygodniowe
weekly_consumption:
  name: "Zuzycie tygodniowe"
  source: sensor.pomiar_mocy_zuzycie
  cycle: weekly

# Zuzycie miesieczne
monthly_consumption:
  name: "Zuzycie miesieczne"
  source: sensor.pomiar_mocy_zuzycie
  cycle: monthly
```

### config/input_numbers.yaml (ZMODYFIKOWANY)
Dodane zmienne do przechowywania danych nocnych:
```yaml
# === ZUZYCIE NOCNE - dane do planowania ===

night_consumption_avg:
  name: "Srednie zuzycie nocne (EMA)"
  min: 0
  max: 50
  step: 0.1
  initial: 16  # Domyslna wartosc z pierwszej analizy
  unit_of_measurement: "kWh"
  icon: mdi:moon-waning-crescent

night_consumption_last:
  name: "Ostatnie zuzycie nocne"
  min: 0
  max: 50
  step: 0.1
  initial: 0
  unit_of_measurement: "kWh"
  icon: mdi:weather-night

pv_start_hour:
  name: "Godzina startu PV"
  min: 5
  max: 12
  step: 1
  initial: 8
  unit_of_measurement: "h"
  icon: mdi:weather-sunny
```

### config/automations_battery.yaml (ZMODYFIKOWANY)
Dodane automatyzacje zbierania danych:
```yaml
# O 06:00 - koniec nocy, zapisz zuzycie i zaktualizuj EMA
- id: night_consumption_capture
  alias: "[Dane] Zapisz zuzycie nocne o 06:00"
  trigger:
    - platform: time
      at: "06:00:00"
  action:
    - service: input_number.set_value
      target:
        entity_id: input_number.night_consumption_last
      data:
        value: "{{ states('sensor.zuzycie_nocne_od_22_00') | float(0) | round(1) }}"
    - service: input_number.set_value
      target:
        entity_id: input_number.night_consumption_avg
      data:
        value: >
          {% set alpha = 0.3 %}
          {% set new_val = states('sensor.zuzycie_nocne_od_22_00') | float(0) %}
          {% set old_avg = states('input_number.night_consumption_avg') | float(16) %}
          {{ (alpha * new_val + (1 - alpha) * old_avg) | round(1) }}
  mode: single

# O 21:00 - oblicz PV start hour na jutro
- id: pv_start_hour_calculate
  alias: "[Dane] Oblicz PV start hour o 21:00"
  trigger:
    - platform: time
      at: "21:00:00"
  action:
    - service: input_number.set_value
      target:
        entity_id: input_number.pv_start_hour
      data:
        value: >
          {% set tomorrow = (now().date() + timedelta(days=1)) | string %}
          {% set watts_e = state_attr('sensor.pv_wschod_prognoza_dzis', 'watts') or {} %}
          {% set watts_s = state_attr('sensor.pv_poludnie_prognoza_dzis', 'watts') or {} %}
          {% set watts_w = state_attr('sensor.pv_zachod_prognoza_dzis', 'watts') or {} %}
          {% set ns = namespace(start_hour=8) %}
          {% for hour in range(5, 12) %}
            {% set ts = tomorrow ~ ' ' ~ '%02d' % hour ~ ':00:00' %}
            {% set total = (watts_e.get(ts, 0) | float) + (watts_s.get(ts, 0) | float) + (watts_w.get(ts, 0) | float) %}
            {% if total > 500 and ns.start_hour == 8 %}
              {% set ns.start_hour = hour %}
            {% endif %}
          {% endfor %}
          {{ ns.start_hour }}
  mode: single
```

### config/configuration.yaml (ZMODYFIKOWANY)
Dodany include:
```yaml
# Utility meters - pomiary zuzycia energii
utility_meter: !include utility_meter.yaml
```

## 4. Napotkane Błędy i Rozwiązania

### FusionSolar API - brak stacji "Marek Bodynek"
- **Problem**: API zwracało tylko 3 stacje, nie stację użytkownika
- **Próba naprawy**: Użytkownik autoryzował konto Bodino jako owner (luxury.md)
- **Status**: Nie rozwiązane - użytkownik powiedział "spróbujesz później"

### Git pull w kontenerze Docker
- **Problem**: `fatal: not a git repository` - /config w Docker to nie root git repo
- **Fix**: Użycie SCP do kopiowania plików bezpośrednio na Mac Mini:
```bash
scp config/*.yaml ssh.bodino.us.kg:/Users/marekbodynek/home-assistant-huawei/config/
```

### Nazwa sensora utility_meter
- **Problem**: Automatyzacja używała `sensor.night_consumption`, ale HA utworzył `sensor.zuzycie_nocne_od_22_00`
- **Przyczyna**: Entity_id generowany z atrybutu `name`
- **Fix**: Zmiana w automations_battery.yaml na poprawną nazwę

## 5. Wdrożone Encje w HA

- `sensor.zuzycie_nocne_od_22_00` - stan "unknown", next_reset 2025-11-24 22:00
- `sensor.zuzycie_dzienne`
- `sensor.zuzycie_tygodniowe`
- `sensor.zuzycie_miesieczne`
- `input_number.night_consumption_avg` = 16.0 kWh
- `input_number.night_consumption_last` = 0
- `input_number.pv_start_hour` = 8

## 6. Commity

1. `9c4854e` - 📊 Utility Meter: Zbieranie danych o zuzyciu nocnym
2. `14dd21f` - 🔧 FIX: Poprawna nazwa sensora utility_meter

## 7. Zadania Do Wykonania

### Nierozwiązane:
1. **FusionSolar API** - ponowić próbę gdy autoryzacja się propaguje
2. **OpenAI API** - klucz utracony przy podsumowaniu poprzedniej sesji, trzeba podać ponownie
3. **Planowanie nocnego ładowania** - logika do implementacji po zebraniu danych
4. **Weryfikacja** - sprawdzić czy zużycie nocne się zbiera po 22:00

## 8. Credentials

- **FusionSolar Northbound**: username=Bodino, systemCode=Keram098, region=eu5
- **SSH**: `ssh ssh.bodino.us.kg` (user: marekbodynek)
- **HA config on Mac Mini**: `/Users/marekbodynek/home-assistant-huawei/config`
- **HA Token**: znajduje się w `.claude/settings.local.json`

## 9. Koncepcja Planowania Nocnego Ładowania

### Jak ma działać:

| Godzina | Co się dzieje |
|---------|---------------|
| 21:00 | Oblicz: ile energii potrzeba na noc + rano? |
| 21:30 | Ustaw target_soc na podstawie obliczeń |
| 22:00 | Rozpocznij ładowanie (L2 - tania taryfa) |
| 06:00 | Zapisz rzeczywiste zużycie nocne, zaktualizuj EMA |

### Wzór na Target SOC:
```
energia_potrzebna = zużycie_nocne_avg + zużycie_rano_do_PV
target_soc = current_soc + (energia_potrzebna / pojemność_baterii * 100)
```

### Przykład:
- SOC o 21:00: 25%
- Średnie zużycie nocne (EMA): 16 kWh
- Godzina startu PV: 08:00
- Zużycie rano (06:00-08:00): 4 kWh
- **Razem potrzeba**: 20 kWh
- Pojemność baterii: 15 kWh użyteczne
- **Target SOC**: 25% + (20/15 * 100) = 25% + 133% = **80%** (max)
