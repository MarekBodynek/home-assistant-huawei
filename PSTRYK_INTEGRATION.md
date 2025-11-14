# 📊 Integracja Pstryk z Home Assistant

## ✅ Status instalacji

**Integracja:** Pstryk Energy
**GitHub:** https://github.com/balgerion/ha_Pstryk
**Status:** ✅ Zainstalowana, wymaga konfiguracji

---

## 🔑 Uzyskiwanie klucza API

### Krok 1: Zainstaluj aplikację Pstryk

1. **iOS:** App Store → Wyszukaj "Pstryk"
2. **Android:** Google Play → Wyszukaj "Pstryk"

### Krok 2: Zarejestruj się lub zaloguj

1. Otwórz aplikację Pstryk
2. Zarejestruj nowe konto lub zaloguj się

**BONUS:** Użyj kodu rabatowego **E3WOTQ** przy pierwszej fakturze - otrzymasz 50 zł na prąd!

### Krok 3: Wygeneruj klucz API

1. W aplikacji Pstryk: **Ustawienia** (ikona koła zębatego)
2. Przewiń w dół do sekcji **API**
3. Kliknij: **Generuj klucz API**
4. **Skopiuj** wygenerowany klucz (zapisz go w bezpiecznym miejscu!)

---

## 🏠 Konfiguracja w Home Assistant

### Krok 1: Dodaj integrację

1. Otwórz Home Assistant: http://localhost:8123
2. **Settings** → **Devices & Services**
3. Kliknij: **+ ADD INTEGRATION** (prawy dolny róg)
4. Wpisz: **Pstryk Energy**
5. Kliknij: **Pstryk Energy**

### Krok 2: Wprowadź dane

Formularz konfiguracji:

```
┌─────────────────────────────────────────────────┐
│ Pstryk Energy                                   │
├─────────────────────────────────────────────────┤
│                                                 │
│ Klucz API:                                      │
│ [wklej skopiowany klucz z aplikacji Pstryk]    │
│                                                 │
│ Liczba najlepszych cen kupna: 5                 │
│ (ile najtańszych godzin pokazywać)              │
│                                                 │
│ Liczba najlepszych cen sprzedaży: 5             │
│ (ile najdroższych godzin do sprzedaży)          │
│                                                 │
│           [CANCEL]         [SUBMIT]             │
└─────────────────────────────────────────────────┘
```

### Krok 3: Weryfikacja

Po pomyślnym dodaniu, sprawdź **Developer Tools** → **States** i wyszukaj:

```
sensor.pstryk_current_buy_price
sensor.pstryk_current_sell_price
sensor.pstryk_next_hour_buy_price
sensor.pstryk_buy_monthly_average
```

---

## 📊 Dostępne encje (sensory)

### Ceny bieżące

| Encja | Opis | Jednostka |
|-------|------|-----------|
| `sensor.pstryk_current_buy_price` | Aktualna cena kupna energii | PLN/kWh |
| `sensor.pstryk_current_sell_price` | Aktualna cena sprzedaży energii | PLN/kWh |
| `sensor.pstryk_next_hour_buy_price` | Cena w następnej godzinie | PLN/kWh |
| `sensor.pstryk_next_hour_sell_price` | Cena sprzedaży w następnej godzinie | PLN/kWh |

### Średnie ceny

| Encja | Opis | Jednostka |
|-------|------|-----------|
| `sensor.pstryk_buy_monthly_average` | Średnia miesięczna cena kupna | PLN/kWh |
| `sensor.pstryk_buy_yearly_average` | Średnia roczna cena kupna | PLN/kWh |
| `sensor.pstryk_sell_monthly_average` | Średnia miesięczna cena sprzedaży | PLN/kWh |
| `sensor.pstryk_sell_yearly_average` | Średnia roczna cena sprzedaży | PLN/kWh |

### Bilanse finansowe

| Encja | Opis | Jednostka |
|-------|------|-----------|
| `sensor.pstryk_daily_financial_balance` | Dzienny bilans kupna/sprzedaży | PLN |
| `sensor.pstryk_monthly_financial_balance` | Miesięczny bilans kupna/sprzedaży | PLN |
| `sensor.pstryk_yearly_financial_balance` | Roczny bilans kupna/sprzedaży | PLN |

---

## 🎯 Atrybuty sensorów (tabele godzinowe)

### `sensor.pstryk_current_buy_price`

**Atrybuty:**
- `hourly_prices` - Tabela 24h z cenami godzinowymi
- `best_prices` - 5 najtańszych godzin (konfigurowalnych)
- `worst_prices` - 5 najdroższych godzin

**Przykład użycia w template:**

```yaml
{% set prices = state_attr('sensor.pstryk_current_buy_price', 'hourly_prices') %}
{% set best_hours = state_attr('sensor.pstryk_current_buy_price', 'best_prices') %}

Najtańsza godzina dziś:
{{ best_hours[0].start }} - {{ best_hours[0].price }} PLN/kWh
```

---

## 🔄 Jak to działa w Twoim systemie

### 1. Template sensors używają Pstryk

**Plik:** `config/template_sensors.yaml`

```yaml
# Cena zakupu energii
- sensor:
    - name: "Cena zakupu energii"
      state: >
        {{ states('sensor.pstryk_current_buy_price') | float(0.65) }}

# Cena sprzedaży energii
- sensor:
    - name: "Cena sprzedaży energii"
      state: >
        {{ states('sensor.pstryk_current_sell_price') | float(0.55) }}

# Średnia wieczorna (19-22h)
- sensor:
    - name: "RCE średnia wieczorna"
      state: >
        {% set prices = state_attr('sensor.pstryk_current_buy_price', 'hourly_prices') %}
        {% if prices %}
          {% set evening_prices = prices | selectattr('hour', 'in', [19, 20, 21]) | map(attribute='price') | list %}
          {{ (evening_prices | sum / evening_prices | length) | round(3) }}
        {% endif %}
```

### 2. Automatyzacje aktualizują dane

**Plik:** `config/automations_battery.yaml`

```yaml
- id: battery_fetch_rce_prices
  alias: "[Bateria] Pobierz ceny RCE (18:00)"
  trigger:
    - platform: time
      at: "18:00:00"
  action:
    - delay:
        seconds: "{{ range(0, 900) | random }}"
    - service: homeassistant.update_entity
      target:
        entity_id:
          - sensor.pstryk_current_buy_price
          - sensor.pstryk_current_sell_price
```

### 3. Dashboard pokazuje ceny

**Plik:** `config/lovelace_huawei.yaml`

```yaml
- type: entities
  title: Ceny energii
  entities:
    - entity: sensor.pstryk_current_buy_price
      name: Cena RCE (bieżąca kupno)
    - entity: sensor.cena_zakupu_energii
      name: Cena zakupu (z sieci)
    - entity: sensor.cena_sprzedazy_energii
      name: Cena sprzedaży (do sieci)
```

---

## 🚀 Korzyści z Pstryk API

### PRZED (TGE web scraping):
- ❌ Parsowanie plików Excel z TGE (zmiana struktury = błąd)
- ❌ Brak danych historycznych
- ❌ Brak prognoz
- ❌ Trzeba ręcznie dodawać VAT + opłaty dystrybucyjne

### PO (Pstryk API):
- ✅ **Stabilne API** - nie zmienia się jak struktura stron TGE
- ✅ **Wszystkie opłaty zawarte** - VAT + dystrybucja + opłaty
- ✅ **Tabele 24h/48h** - prognozy cen na najbliższe godziny
- ✅ **Najlepsze/najgorsze godziny** - automatyczna identyfikacja
- ✅ **Statystyki** - średnie miesięczne, roczne
- ✅ **Bilanse** - automatyczne obliczanie kosztów/przychodów
- ✅ **MQTT support** - integracja z EVCC i innymi systemami

---

## 🎯 Przykładowe automatyzacje

### Ładuj baterię w 5 najtańszych godzinach

```yaml
alias: "[Bateria] Ładuj w najtańszych godzinach"
trigger:
  - platform: time_pattern
    minutes: "1"
condition:
  - condition: template
    value_template: >
      {% set current_hour = now().replace(minute=0, second=0, microsecond=0).isoformat(timespec='seconds').split('+')[0] %}
      {% set best_hours = state_attr('sensor.pstryk_current_buy_price', 'best_prices') | map(attribute='start') | list %}
      {{ current_hour in best_hours }}
action:
  - service: switch.turn_on
    target:
      entity_id: switch.akumulatory_ladowanie_z_sieci
```

### Rozładuj baterię w 5 najdroższych godzinach

```yaml
alias: "[Bateria] Sprzedaj w najdroższych godzinach"
trigger:
  - platform: time_pattern
    minutes: "1"
condition:
  - condition: template
    value_template: >
      {% set current_hour = now().replace(minute=0, second=0, microsecond=0).isoformat(timespec='seconds').split('+')[0] %}
      {% set worst_hours = state_attr('sensor.pstryk_current_sell_price', 'best_prices') | map(attribute='start') | list %}
      {{ current_hour in worst_hours }}
action:
  - service: select.select_option
    target:
      entity_id: select.akumulatory_tryb_pracy
    data:
      option: "Time Of Use"
```

---

## 📞 Rozwiązywanie problemów

### Problem: "Invalid API key"

**Rozwiązanie:**
1. Sprawdź czy klucz został skopiowany prawidłowo (bez spacji na końcu)
2. Wygeneruj nowy klucz w aplikacji Pstryk
3. Usuń integrację i dodaj ponownie z nowym kluczem

### Problem: Sensory pokazują "unknown"

**Rozwiązanie:**
1. Sprawdź czy integracja jest aktywna: **Settings** → **Devices & Services** → **Pstryk Energy**
2. Zrestartuj Home Assistant:
   ```bash
   docker restart homeassistant
   ```
3. Sprawdź logi:
   ```bash
   docker exec homeassistant grep -i "pstryk" /config/home-assistant.log
   ```

### Problem: Dane nie aktualizują się

**Rozwiązanie:**
1. Integracja aktualizuje dane **co godzinę minutę po pełnej** (np. 14:01, 15:01)
2. Ręczne wymuszenie aktualizacji:
   - **Developer Tools** → **Services**
   - Service: `homeassistant.update_entity`
   - Target: `sensor.pstryk_current_buy_price`

---

## 📝 Linki

- **Dokumentacja:** https://github.com/balgerion/ha_Pstryk
- **Dedykowana karta:** https://github.com/balgerion/ha_Pstryk_card
- **Zgłaszanie błędów:** https://github.com/balgerion/ha_Pstryk/issues

---

**Powodzenia! 🚀⚡**

*Przy pytaniach sprawdź logi lub dokumentację na GitHub*
