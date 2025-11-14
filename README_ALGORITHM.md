# 🤖 Algorytm Zarządzania Baterią - Instrukcja Implementacji

## ✅ Co zostało zaimplementowane

Kompletny system zarządzania baterią Huawei Luna 15kWh zgodny z [ALGORITHM.md](ALGORITHM.md).

### 📁 Pliki utworzone

1. **Template Sensors** ([config/template_sensors.yaml](config/template_sensors.yaml))
   - Strefy taryfowe G12w (L1/L2)
   - Sezon grzewczy i okna CWU
   - Ceny energii (zakup i sprzedaż)
   - Prognozy PV i bilansy mocy
   - 15 sensorów pomocniczych

2. **Python Scripts** ([config/python_scripts/](config/python_scripts/))
   - `battery_algorithm.py` - Główny algorytm decyzyjny
   - `calculate_daily_strategy.py` - Obliczanie celu ładowania (Target SOC)

3. **Automatyzacje** ([config/automations_battery.yaml](config/automations_battery.yaml))
   - Harmonogram wykonywania algorytmu (co 1h, kluczowe momenty)
   - Monitorowanie stanów krytycznych
   - Pobieranie prognoz i cen RCE
   - 13 automatyzacji

4. **Input Numbers** ([config/input_numbers.yaml](config/input_numbers.yaml))
   - `battery_target_soc` - Docelowy poziom naładowania

5. **Dashboard** ([config/lovelace_huawei.yaml](config/lovelace_huawei.yaml))
   - Karty z cenami RCE
   - Prognozy PV
   - Bilanse mocy
   - Sezon grzewczy

---

## 🚀 Kroki konfiguracji

### 1. Skonfiguruj integrację TGE (ceny RCE)

✅ **Status:** Zainstalowana, wymaga konfiguracji przez UI

**Jak skonfigurować:**
1. Otwórz Home Assistant w przeglądarce: http://localhost:8123
2. Przejdź do **Settings → Devices & Services**
3. Kliknij **+ ADD INTEGRATION**
4. Wyszukaj **"TGE"**
5. Kliknij **Submit** (nie wymaga klucza API)

**Encje utworzone:**
- `sensor.tge_rce_current` - Aktualna cena RCE (zł/kWh)
- `sensor.tge_rce_hourly` - Ceny godzinowe (atrybuty)

---

### 2. Skonfiguruj integrację Forecast.Solar (prognoza PV)

**Jak skonfigurować:**
1. **Settings → Devices & Services → + ADD INTEGRATION**
2. Wyszukaj **"Forecast.Solar"**
3. Podaj parametry instalacji PV:
   - **Latitude**: 52.2297 (Warszawa)
   - **Longitude**: 21.0122
   - **Declination (nachylenie)**: np. 35°
   - **Azimuth (azymut)**: 180° (południe)
   - **Modules Power**: 14.4 kWp (14400 Wp)
   - **Damping**: 0 (brak)

**Encje utworzone:**
- `sensor.energy_production_today` - Produkcja dziś
- `sensor.energy_production_tomorrow` - Prognoza jutro
- `sensor.energy_production_today_remaining` - Pozostało dziś
- `sensor.energy_current_hour` - Bieżąca godzina

**Konto darmowe vs. płatne:**
- **Darmowe:** 12 zapytań/dzień, prognoza 1 dzień
- **Płatne (Personal):** 6 EUR/rok, 60 zapytań/godzinę, prognoza 3 dni

---

### 3. Sprawdź czy sensory działają

Po skonfigurowaniu TGE i Forecast.Solar, sprawdź czy sensory mają wartości:

```bash
# Otwórz Developer Tools → States
# Wyszukaj:
sensor.strefa_taryfowa         # L1 lub L2
sensor.tge_rce_current          # np. 0.450 (zł/kWh)
sensor.cena_zakupu_energii      # np. 0.773 (zł/kWh)
sensor.prognoza_pv_jutro        # np. 12.5 (kWh)
binary_sensor.sezon_grzewczy    # on lub off
```

---

### 4. Sprawdź ID urządzeń Huawei

Skrypty Pythona używają nazw encji. Upewnij się że nazwy są poprawne:

**Developer Tools → States → Filtruj:**
```
akumulatory_
inwerter_
pomiar_mocy_
```

**Jeśli nazwy się różnią**, edytuj [config/python_scripts/battery_algorithm.py](config/python_scripts/battery_algorithm.py):

```python
# Linia ~86-106
'soc': float(get_state('sensor.akumulatory_stan_pojemnosci') or 50),
'battery_power': float(get_state('sensor.akumulatory_moc_ladowania_rozladowania') or 0) / 1000,
# ... itd
```

---

### 5. Włącz automatyzacje

**Settings → Automations & Scenes**

Sprawdź czy automatyzacje zostały załadowane:
- `[Bateria] Oblicz strategię dzienną 04:00`
- `[Bateria] Wykonaj strategię (co 1h)`
- `[Bateria] Monitor SOC krytyczne`
- ... itd. (13 automatyzacji)

Wszystkie powinny być **włączone** (toggle ON).

---

### 6. Testuj algorytm ręcznie

**Opcja 1: Przez Developer Tools**

1. **Developer Tools → Services**
2. Service: `python_script.battery_algorithm`
3. Kliknij **CALL SERVICE**
4. Sprawdź logi: **Settings → System → Logs**

**Opcja 2: Przez Dashboard**

Przejdź do **Huawei Solar PV** dashboard i zobacz czy karty pokazują dane:
- Ceny energii
- Prognoza PV
- Sezon grzewczy

**Opcja 3: Sprawdź logbook**

**Settings → Logbook** → Filtruj `battery_algorithm`

---

### 7. Dostosuj parametry (opcjonalnie)

#### Taryfa G12w - godziny L2 (tanie)

Edytuj [config/template_sensors.yaml](config/template_sensors.yaml), linie 14-23:

```yaml
- sensor:
    - name: "Strefa taryfowa"
      state: >
        {% set h = now().hour %}
        {% if (h >= 22) or (h < 6) %}    # ← NOC 22:00-06:00
          L2
        {% elif (h >= 13) and (h < 15) %}  # ← POŁUDNIE 13:00-15:00
          L2
        {% else %}
          L1
        {% endif %}
```

#### Progi temperaturowe (sezon grzewczy)

Domyślnie: **12°C**

Zmień w [config/template_sensors.yaml](config/template_sensors.yaml), linia 30:

```yaml
state: >
  {{ states('sensor.outdoor_temperature') | float(20) < 12 }}  # ← Zmień 12 na np. 10
```

#### Ceny energii - dystrybucja

Edytuj [config/template_sensors.yaml](config/template_sensors.yaml), linie 59-68:

```yaml
# Cena zakupu w L1:
{{ ((rce * 1.23) + 0.4933) | round(4) }}  # ← 0.4933 zł/kWh dystrybucja L1

# Cena zakupu w L2:
{{ ((rce * 1.23) + 0.2813) | round(4) }}  # ← 0.2813 zł/kWh dystrybucja L2
```

**Jak obliczyć swoje ceny:**
1. Sprawdź fakturę za energię
2. Znajdź: `Dystrybucja + Opłata mocowa + Opłata handlowa + VAT`
3. Podziel przez zużycie (kWh)

---

## 📊 Jak działa algorytm

### Harmonogram wykonywania

```
04:00  → Oblicz strategię dzienną (Target SOC)
CO 1h  → Wykonaj strategię (główna pętla)
06:00  → Zmiana L2→L1 (koniec taniej taryfy)
13:00  → Zmiana L1→L2 (południe tanie)
15:00  → Zmiana L2→L1
19:00  → SZCZYT wieczorny + arbitraż
22:00  → Zmiana L1→L2 (noc) + ładowanie
```

### Główne decyzje

**W L2 (tanie):**
- Ładuj baterię do Target SOC
- PC CWU może brać z sieci

**W L1 (drogi):**
- Używaj baterii maksymalnie
- Oszczędzaj drogą energię
- Arbitraż wieczorny (jeśli RCE > 0.50 zł/kWh)

**Nadwyżka PV:**
- Magazynuj jeśli: jutro pochmurno, zima, RCE niskie
- Sprzedaj jeśli: warunki OK

---

## 🔧 Rozwiązywanie problemów

### Problem: Sensory pokazują `unknown` lub `unavailable`

**Przyczyna:** Brak danych z integracji TGE lub Forecast.Solar

**Rozwiązanie:**
1. Sprawdź czy integracje są skonfigurowane: **Settings → Devices & Services**
2. Zobacz logi: **Settings → System → Logs**
3. Zaktualizuj encje: **Developer Tools → States → Kliknij refresh**

---

### Problem: Automatyzacje nie wykonują się

**Przyczyna:** Błąd w Python script

**Rozwiązanie:**
1. Sprawdź logi: `docker exec homeassistant tail -100 /config/home-assistant.log | grep python_script`
2. Sprawdź czy plik istnieje: `ls -la /config/python_scripts/`
3. Sprawdź syntax: Otwórz plik w edytorze i poszukaj błędów Python

---

### Problem: Bateria nie ładuje się w nocy

**Przyczyna:** Algorytm sprawdza Target SOC

**Rozwiązanie:**
1. Sprawdź `input_number.battery_target_soc` - jeśli SOC > Target, nie ładuje
2. Sprawdź prognozę jutro - jeśli > 30 kWh (lato), Target SOC = 30%
3. Ręcznie wywołaj: **Developer Tools → Services → `python_script.calculate_daily_strategy`**

---

### Problem: RCE zawsze 0.45 (wartość domyślna)

**Przyczyna:** Integracja TGE nie pobiera cen

**Rozwiązanie:**
1. Sprawdź czy integracja TGE jest skonfigurowana
2. Ręcznie zaktualizuj: **Developer Tools → Services → `homeassistant.update_entity`**
   - Entity: `sensor.tge_rce_current`
3. Sprawdź czy API PSE działa: https://api.raporty.pse.pl/api/rce-pln

---

## 📈 Monitoring i metryki

### Logbook - Historia decyzji

**Settings → Logbook** → Filtruj: `battery_algorithm`

Zobacz wszystkie decyzje algorytmu z uzasadnieniem.

### Powiadomienia

Algorytm wysyła powiadomienia:
- 🚨 **SOC krytyczne** (< 10%)
- ⚠️ **SOC niskie w L1** (< 20%)
- ✅ **Bateria naładowana** (95%)
- 📊 **Strategia dzienna obliczona** (04:00)
- 📊 **Podsumowanie dnia** (23:00)

**Gdzie zobaczyć:** **Settings → Notifications**

---

## 🎯 Następne kroki (opcjonalnie)

1. **Grafana + InfluxDB** - Zaawansowane wykresy i metryki
2. **Notyfikacje na telefon** - Home Assistant Mobile App
3. **Optymalizacja parametrów** - Na podstawie 30 dni danych
4. **Webhook do Slack/Telegram** - Powiadomienia o arbitrażu

---

## 📝 Checkl lista pierwszej konfiguracji

- [ ] Home Assistant działa (http://localhost:8123)
- [ ] Integracja TGE skonfigurowana
- [ ] Integracja Forecast.Solar skonfigurowana
- [ ] Template sensors mają wartości (nie `unknown`)
- [ ] Python scripts załadowane (`python_script` w logach)
- [ ] Automatyzacje włączone (Settings → Automations)
- [ ] Ręcznie wywołano `calculate_daily_strategy`
- [ ] Ręcznie wywołano `battery_algorithm`
- [ ] Dashboard pokazuje karty z cenami i prognozami
- [ ] Logbook pokazuje decyzje algorytmu

---

**Powodzenia z optymalizacją! 🚀⚡**

*Przy pytaniach sprawdź [ALGORITHM.md](ALGORITHM.md) lub logi Home Assistant.*
