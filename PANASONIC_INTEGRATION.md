# 🔌 Integracja Panasonic T-CAP z Home Assistant

## ✅ Status instalacji

**Integracja:** Panasonic Comfort Cloud
**GitHub:** https://github.com/sockless-coding/panasonic_cc
**Status:** ✅ Zainstalowana, wymaga konfiguracji

---

## 📝 Konfiguracja

### Krok 1: Dodaj integrację

1. Otwórz Home Assistant: http://localhost:8123
2. **Settings → Devices & Services → + ADD INTEGRATION**
3. Wyszukaj: **"Panasonic Comfort Cloud"**
4. Podaj dane logowania (z aplikacji mobilnej):
   - **Email:** twoj@email.pl
   - **Password:** ••••••••

### Krok 2: Sprawdź encje

Po konfiguracji, przejdź do **Developer Tools → States** i wyszukaj:

```
climate.pompa_ciepla
sensor.pompa_ciepla_outside_temperature
binary_sensor.pompa_ciepla_heating
binary_sensor.pompa_ciepla_hot_water
```

---

## 🔧 Aktualizacja template sensors

Po dodaniu integracji Panasonic, zaktualizuj `config/template_sensors.yaml`:

### PRZED (obliczane):

```yaml
# Linia 322
- sensor:
    - name: "Temperatura zewnętrzna"
      state: >
        {{ state_attr('weather.forecast_dom', 'temperature') | float(10) }}

# Linia 32
- binary_sensor:
    - name: "Sezon grzewczy"
      state: >
        {{ states('sensor.outdoor_temperature') | float(20) < 12 }}

# Linia 47
- binary_sensor:
    - name: "PC CO aktywne"
      state: >
        {{ states('sensor.outdoor_temperature') | float(20) < 12 }}

# Linia 62
- binary_sensor:
    - name: "Okno CWU"
      state: >
        {% set h = now().hour %}
        {% set m = now().minute %}
        {% set time_decimal = h + (m / 60.0) %}
        {{ (time_decimal >= 4.5 and time_decimal < 6) or
           (time_decimal >= 13 and time_decimal < 15) }}
```

### PO (rzeczywiste dane z PC):

```yaml
# Linia 322 - Temperatura zewnętrzna z czujnika PC
- sensor:
    - name: "Temperatura zewnętrzna"
      state: >
        {{ states('sensor.pompa_ciepla_outside_temperature') | float(10) }}

# Linia 32 - Sezon grzewczy = czy PC grzeje
- binary_sensor:
    - name: "Sezon grzewczy"
      state: >
        {{ is_state('binary_sensor.pompa_ciepla_heating', 'on') }}

# Linia 47 - PC CO aktywne = tryb grzania
- binary_sensor:
    - name: "PC CO aktywne"
      state: >
        {{ is_state('binary_sensor.pompa_ciepla_heating', 'on') }}

# Linia 62 - Okno CWU = czy PC podgrzewa wodę
- binary_sensor:
    - name: "Okno CWU"
      state: >
        {{ is_state('binary_sensor.pompa_ciepla_hot_water', 'on') }}
```

---

## 📊 Dodatkowe sensory (opcjonalnie)

Możesz dodać więcej sensorów z PC do dashboardu:

```yaml
# W lovelace_huawei.yaml
- entity: sensor.pompa_ciepla_inside_temperature
  name: Temperatura wewnętrzna
  icon: mdi:thermometer

- entity: sensor.pompa_ciepla_tank_temperature
  name: Temperatura zasobnika CWU
  icon: mdi:water-thermometer

- entity: sensor.pompa_ciepla_compressor_frequency
  name: Częstotliwość sprężarki
  icon: mdi:speedometer

- entity: switch.pompa_ciepla_quiet_mode
  name: Tryb cichy PC
  icon: mdi:volume-off
```

---

## 🎯 Korzyści z integracji

### PRZED (bez integracji PC):
- ❌ Obliczanie "sezon grzewczy" na podstawie temp < 12°C
- ❌ Okna CWU hardcoded (04:30-06:00, 13:00-15:00)
- ❌ Temperatura z prognozy pogody (niezbyt dokładna)
- ❌ Brak informacji o rzeczywistej pracy PC

### PO (z integracją PC):
- ✅ **Rzeczywisty status:** Czy PC aktualnie grzeje
- ✅ **Dokładna temperatura:** Z czujnika PC (dokładniejsza niż prognoza)
- ✅ **Rzeczywisty CWU:** Algorytm wie kiedy PC podgrzewa wodę
- ✅ **Optymalizacja:** Algorytm może unikać ładowania baterii gdy PC pobiera dużo mocy
- ✅ **Monitoring:** Zobacz ile energii zużywa PC w czasie rzeczywistym

---

## 🚀 Algorytm będzie działał lepiej!

### Przykład:

**Scenariusz: Zima, 6°C, PC grzeje dom**

**PRZED:**
```
Algorytm: "Temperatura 6°C < 12°C → Sezon grzewczy ON"
Problem: Nie wie czy PC RZECZYWIŚCIE pracuje
```

**PO:**
```
Algorytm: "binary_sensor.pompa_ciepla_heating = ON"
Algorytm: "PC pobiera 4.2 kW → Nie ładuj baterii teraz, poczekaj"
Algorytm: "Za 30 min PC wyłączy CO → Wtedy załaduj baterię"
```

---

## ⚠️ Ważne!

### Czy masz moduł WiFi CZ-TAW1?

**TAK** → Możesz użyć Comfort Cloud (cloud API)
**NIE** → Potrzebujesz:
- **Opcja 1:** Kupić CZ-TAW1 (~500 zł)
- **Opcja 2:** Użyć Modbus (jeśli PC ma port Modbus)
- **Opcja 3:** Zostać przy obliczanych wartościach

---

## 📞 Pytania?

Jeśli masz pytania lub problemy z konfiguracją, sprawdź:
- **GitHub Issues:** https://github.com/sockless-coding/panasonic_cc/issues
- **Dokumentacja HA:** https://www.home-assistant.io/integrations/panasonic_comfort_cloud/

---

**Powodzenia! 🎉**
