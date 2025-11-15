# Kafelek: Status Magazynowania Baterii

## 📊 Informacje wyświetlane:

1. **Status magazynowania** - ile godzin potrzeba, najtańsze godziny, aktualna godzina
2. **Powód decyzji** - dlaczego MAGAZYNUJ lub SPRZEDAJ
3. **Najtańsze godziny** - lista godzin do magazynowania

---

## 🎨 Opcja 1: Karta Entities (prosta)

Dodaj tę kartę do swojego dashboardu (Settings → Dashboards → Edit):

```yaml
type: entities
title: 💰 Magazynowanie Baterii
icon: mdi:battery-charging
entities:
  - entity: input_text.battery_decision_reason
    name: 🎯 Decyzja
    icon: mdi:chart-line
  - entity: input_text.battery_storage_status
    name: 📊 Analiza
    icon: mdi:clock-outline
  - entity: input_text.battery_cheapest_hours
    name: 💵 Najtańsze godziny
    icon: mdi:currency-usd
  - type: divider
  - entity: sensor.akumulatory_stan_pojemnosci
    name: 🔋 SOC
  - entity: input_number.battery_target_soc
    name: 🎯 Target SOC
state_color: true
```

---

## 🎨 Opcja 2: Karta Markdown (ładniejsza)

```yaml
type: markdown
title: 💰 Magazynowanie Baterii
content: |
  ## 🎯 Decyzja Algorytmu
  **{{ states('input_text.battery_decision_reason') }}**

  ---

  ## 📊 Analiza
  {{ states('input_text.battery_storage_status') }}

  ## 💵 Najtańsze godziny
  {{ states('input_text.battery_cheapest_hours') }}

  ---

  ### 🔋 Stan baterii
  - **SOC:** {{ states('sensor.akumulatory_stan_pojemnosci') }}%
  - **Target:** {{ states('input_number.battery_target_soc') }}%
  - **Tryb:** {{ states('select.akumulatory_tryb_pracy') }}
```

---

## 🎨 Opcja 3: Karta Custom (najładniejsza, wymaga HACS)

Jeśli masz zainstalowany **ApexCharts Card** lub **Mushroom Cards** z HACS:

### Z Mushroom Cards:

```yaml
type: vertical-stack
cards:
  - type: custom:mushroom-title-card
    title: Magazynowanie Baterii
    subtitle: Inteligentna optymalizacja PV

  - type: custom:mushroom-entity-card
    entity: input_text.battery_decision_reason
    name: Decyzja
    icon: mdi:chart-line
    icon_color: >
      {% if 'MAGAZYNUJ' in states('input_text.battery_decision_reason') %}
        green
      {% elif 'SPRZEDAJ' in states('input_text.battery_decision_reason') %}
        blue
      {% else %}
        grey
      {% endif %}

  - type: custom:mushroom-entity-card
    entity: input_text.battery_storage_status
    name: Analiza
    icon: mdi:clock-outline
    icon_color: orange

  - type: custom:mushroom-entity-card
    entity: input_text.battery_cheapest_hours
    name: Najtańsze godziny
    icon: mdi:currency-usd
    icon_color: green
```

---

## 📱 Opcja 4: Tile Card (nowoczesna)

```yaml
type: tile
entity: input_text.battery_decision_reason
name: Magazynowanie Baterii
icon: mdi:battery-charging
color: >
  {% if 'MAGAZYNUJ' in states('input_text.battery_decision_reason') %}
    green
  {% elif 'SPRZEDAJ' in states('input_text.battery_decision_reason') %}
    blue
  {% else %}
    grey
  {% endif %}
features:
  - type: target-temperature
    entity: input_number.battery_target_soc
vertical: true
```

---

## 🚀 Jak dodać kartę?

1. **Otwórz pulpit**: Ustawienia → Pulpity → Twój pulpit
2. **Kliknij**: Edytuj pulpit (✏️ w prawym górnym rogu)
3. **Kliknij**: + Dodaj kartę
4. **Wybierz**: Ręcznie (na dole)
5. **Wklej**: jeden z kodów YAML powyżej
6. **Kliknij**: Zapisz

---

## 🔍 Przykładowe wyświetlanie:

### Gdy MAGAZYNUJ:
```
🎯 Decyzja
TANIA godzina (8h: 0.25 zł) - top 3 najtańszych - MAGAZYNUJ

📊 Analiza
Potrzeba: 3h | Najtańsze: [6, 7, 8] | Teraz: 8h

💵 Najtańsze godziny
[6, 7, 8]
```

### Gdy SPRZEDAJ:
```
🎯 Decyzja
DROGA godzina (14h: 0.55 zł vs najtańsza 0.25 zł) - SPRZEDAJ

📊 Analiza
Potrzeba: 3h | Najtańsze: [6, 7, 8] | Teraz: 14h

💵 Najtańsze godziny
[6, 7, 8]
```

---

## ✅ Gotowe!

Po wdrożeniu zobaczysz status w czasie rzeczywistym (aktualizacja co godzinę o :00).
