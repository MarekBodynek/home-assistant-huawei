# ⚡ Szybka konfiguracja - 5 minut!

## Krok 1: Dodaj integrację Pstryk (ceny RCE)

**WAŻNE:** Potrzebujesz klucza API z platformy Pstryk!

### Jak uzyskać klucz API Pstryk:
1. Zainstaluj aplikację **Pstryk** na telefonie (iOS/Android)
2. Zarejestruj się lub zaloguj
3. W aplikacji: **Ustawienia** → **API** → **Generuj klucz**
4. Skopiuj klucz API

### Dodaj integrację w Home Assistant:
1. Otwórz: http://localhost:8123
2. **Settings** → **Devices & Services** → **+ ADD INTEGRATION** (prawy dolny róg)
3. Wpisz: **Pstryk Energy**
4. Kliknij: **Pstryk Energy**
5. Wprowadź dane:
   - **Klucz API**: [wklej skopiowany klucz]
   - **Liczba najlepszych cen kupna**: 5
   - **Liczba najlepszych cen sprzedaży**: 5
6. Kliknij: **SUBMIT**

**Encje które się pojawią:**
- `sensor.pstryk_current_buy_price` - Aktualna cena kupna (zł/kWh) + tabela 24h
- `sensor.pstryk_current_sell_price` - Aktualna cena sprzedaży (zł/kWh)
- `sensor.pstryk_next_hour_buy_price` - Cena w następnej godzinie
- `sensor.pstryk_buy_monthly_average` - Średnia miesięczna
- Inne sensory (bilans, średnie)

---

## Krok 2: Dodaj integrację Forecast.Solar (prognoza PV)

1. **Settings** → **Devices & Services** → **+ ADD INTEGRATION**
2. Wpisz: **Forecast.Solar**
3. Wypełnij formularz:

```
✅ Latitude: 52.2297
✅ Longitude: 21.0122
✅ Declination (nachylenie paneli): 35
✅ Azimuth (azymut - kierunek): 180
   (0=północ, 90=wschód, 180=południe, 270=zachód)
✅ Modules Power (moc paneli): 14400
   (14.4 kWp = 14400 Wp)
✅ Damping: 0
   (tłumienie - zostaw 0)
```

4. Kliknij: **SUBMIT**

**Encje które się pojawią:**
- `sensor.energy_production_today` - Produkcja dziś (całkowita)
- `sensor.energy_production_today_remaining` - Pozostało dziś
- `sensor.energy_production_tomorrow` - Prognoza jutro
- `sensor.energy_current_hour` - Bieżąca godzina

---

## Krok 3: Sprawdź czy działa

1. **Developer Tools** → **States**
2. Wyszukaj:
   - `sensor.tge_rce_current` - powinna być wartość np. 0.450
   - `sensor.energy_production_tomorrow` - powinna być wartość np. 12.5
   - `sensor.strefa_taryfowa` - powinna być **L1** lub **L2**
   - `binary_sensor.sezon_grzewczy` - powinna być **on** (temp < 12°C)

---

## Krok 4: Test algorytmu ręcznie

1. **Developer Tools** → **Services**
2. Service: `python_script.calculate_daily_strategy`
3. Kliknij: **CALL SERVICE**
4. Sprawdź notyfikację - powinna pojawić się: "📊 Strategia dzienna obliczona"

---

## Krok 5: Test głównego algorytmu

1. **Developer Tools** → **Services**
2. Service: `python_script.battery_algorithm`
3. Kliknij: **CALL SERVICE**
4. Sprawdź logi: **Settings** → **System** → **Logs**
   - Szukaj: "Applying strategy" lub "DECISION"

---

## ✅ Gotowe!

Algorytm teraz działa:
- **Co 1h** wykonuje strategię
- **O 04:00** oblicza Target SOC
- **O 22:00** ładuje baterię w L2
- **Wieczorem (19-22h)** sprawdza czy opłaca się arbitraż

---

## 🎯 Co dalej?

### Dostosuj parametry (opcjonalnie):

#### 1. Godziny taryfy G12w

Jeśli masz inne godziny L2, edytuj:
`config/template_sensors.yaml` linie 12-19

```yaml
{% if (h >= 22) or (h < 6) %}   # NOC: 22:00-06:00
  L2
{% elif (h >= 13) and (h < 15) %}  # POŁUDNIE: 13:00-15:00
  L2
{% else %}
  L1
{% endif %}
```

#### 2. Próg temperatury sezon grzewczy

Domyślnie: **12°C**

Edytuj: `config/template_sensors.yaml` linia 33
```yaml
{{ states('sensor.temperatura_zewnetrzna') | float(20) < 12 }}
#                                                           ^^ zmień na np. 10
```

#### 3. Ceny dystrybucji

Edytuj: `config/template_sensors.yaml` linie 86-93

```yaml
{% if zone == 'L2' %}
  {{ ((rce * 1.23) + 0.2813) | round(4) }}  # ← Twoja cena dystrybucji L2
{% else %}
  {{ ((rce * 1.23) + 0.4933) | round(4) }}  # ← Twoja cena dystrybucji L1
{% endif %}
```

**Jak obliczyć swoje ceny:**
- Sprawdź fakturę za energię
- Znajdź: `Dystrybucja za kWh` + `Opłata handlowa` + `Opłata mocowa`
- Dodaj wszystko i podziel przez zużycie kWh

---

## 📊 Monitoring

### Logbook
**Settings** → **Logbook** → Filtruj: `battery`

Zobacz wszystkie decyzje algorytmu z uzasadnieniem.

### Powiadomienia
**Settings** → **Notifications**

Algorytm wysyła:
- 🚨 SOC krytyczne (< 10%)
- ⚠️ SOC niskie w L1 (< 20%)
- ✅ Bateria naładowana (95%)
- 📊 Strategia dzienna (04:00)
- 📊 Podsumowanie dnia (23:00)

---

## 🐛 Rozwiązywanie problemów

### Problem: Sensory pokazują "unknown"

**Rozwiązanie:**
1. Sprawdź czy dodałeś TGE i Forecast.Solar
2. Zrestartuj Home Assistant:
   ```bash
   docker restart homeassistant
   ```

### Problem: Algorytm nie wykonuje się

**Sprawdź logi:**
```bash
docker exec homeassistant tail -50 /config/home-assistant.log | grep -i "battery_algorithm\|error"
```

### Problem: Panasonic nie działa

To normaln - jest **bug w integracji** (aioaquarea 0.7.2).
Tymczasowo używamy temperaturę z Met.no - wystarczy!

Gdy Panasonic zostanie naprawiony, automatycznie przełączymy na dane z pompy ciepła.

---

## 📝 Pliki konfiguracyjne

- **Algorytm:** [config/python_scripts/battery_algorithm.py](config/python_scripts/battery_algorithm.py)
- **Obliczanie Target SOC:** [config/python_scripts/calculate_daily_strategy.py](config/python_scripts/calculate_daily_strategy.py)
- **Template sensors:** [config/template_sensors.yaml](config/template_sensors.yaml)
- **Automatyzacje:** [config/automations_battery.yaml](config/automations_battery.yaml)
- **Dashboard:** [config/lovelace_huawei.yaml](config/lovelace_huawei.yaml)
- **Dokumentacja algorytmu:** [ALGORITHM.md](ALGORITHM.md)
- **Instrukcja Panasonic:** [PANASONIC_INTEGRATION.md](PANASONIC_INTEGRATION.md)

---

**Powodzenia! 🚀⚡**

*Przy pytaniach sprawdź logi lub [README_ALGORITHM.md](README_ALGORITHM.md)*
