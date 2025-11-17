# 🚀 Instrukcja wdrożenia - Poprawka najtańszych godzin słonecznych

## 📦 Branch i commity

**Branch:** `claude/fix-energy-price-tiles-01J1tRyS4VB8xJUMyTgbcoAV`

**Kluczowe commity:**
- `710626a` - 🐛 Napraw wybór najtańszych godzin (używa next_rising/next_setting)
- `d9602a3` - ⚡ Optymalizacja (obliczaj 1x dziennie zamiast 24x)

## ⚡ Szybkie wdrożenie (SSH)

```bash
# 1. Połącz się z Home Assistant
ssh user@192.168.0.106

# 2. Przejdź do /config
cd /config

# 3. Pobierz zmiany
git fetch origin
git checkout claude/fix-energy-price-tiles-01J1tRyS4VB8xJUMyTgbcoAV
git pull origin claude/fix-energy-price-tiles-01J1tRyS4VB8xJUMyTgbcoAV

# 4. Weryfikuj plik
grep "analyze_tomorrow" python_scripts/battery_algorithm.py
# Powinien zwrócić kilka linii zawierających "analyze_tomorrow"

grep "if hour == 23:" python_scripts/battery_algorithm.py
# Powinien zwrócić: if hour == 23:

# 5. Przeładuj Python Scripts w HA
# Developer Tools > YAML > Python Scripts Reload
# LUB restart Home Assistant
```

## 🔍 Weryfikacja działania

### 1. Sprawdź logi (brak błędów = OK)
```bash
tail -100 /config/home-assistant.log | grep -i "battery\|error"
```

### 2. Sprawdź dashboard

**O 23:00** (obliczanie):
- Kafelek "Prognoza PV i bilans mocy"
- 📊 Analiza: `Potrzeba: 5h | jutro: [7, 10, 11, 12, 13] | Teraz: 23h`

**Następnego dnia o 10:00** (wykorzystanie):
- 📊 Analiza: `Potrzeba: 5h | jutro: [7, 10, 11, 12, 13] | Teraz: 10h`
- *(Te same godziny co o 23:00 - nie są przeliczane!)*

### 3. Sprawdź input_text

```bash
# Developer Tools > States > input_text.battery_cheapest_hours
# Powinno pokazywać: "[7, 10, 11, 12, 13]" lub podobną listę
```

### 4. Sprawdź sun.sun

```bash
# Developer Tools > States > sun.sun
# Atrybuty:
# - next_rising: "2025-11-18T07:29:00+01:00" ✅
# - next_setting: "2025-11-18T16:02:00+01:00" ✅
# NIE POWINNO BYĆ: last_rising, last_setting
```

## ✅ Test akceptacyjny

| Godzina | Wschód słońca | Oczekiwane godziny | Status |
|---------|---------------|-------------------|--------|
| 23:00 | jutro 7:29 | [7, 10, 11, 12, 13] | ✅ Obliczone |
| 05:00 | dziś 7:29 | [7, 10, 11, 12, 13] | ✅ Te same (nie przeliczone) |
| 10:00 | dziś 7:29 | [7, 10, 11, 12, 13] | ✅ Te same (nie przeliczone) |

**Kluczowy test:**
- Godzina **5** i **6** NIE MOGĄ być w wynikach (przed wschodem słońca 7:29) ✅
- Lista jest **stała przez cały dzień** (zmienia się tylko o 23:00) ✅

## 🐛 Troubleshooting

### Problem: Dashboard pokazuje stare godziny (np. [5, 6, 7, 10])

**Sprawdź:**
```bash
grep "next_rising_str" /config/python_scripts/battery_algorithm.py
# Musi być: next_rising_str = sun_state.attributes.get('next_rising', '')

grep "if hour == 23:" /config/python_scripts/battery_algorithm.py  
# Musi być obecne
```

**Rozwiązanie:**
1. Przeładuj Python Scripts
2. Poczekaj do 23:00 na przeliczenie
3. Lub ręcznie wywołaj skrypt

### Problem: Brak godzin na dashboardzie

**Sprawdź:**
```bash
# Developer Tools > States > sensor.pstryk_current_sell_price
# Atrybut "All prices" musi mieć listę cen na dziś i jutro
```

### Problem: Błąd w logach

```bash
tail -100 /config/home-assistant.log | grep -A5 -B5 "battery_algorithm"
```

## 📊 Co zostało zmienione?

### Plik: `config/python_scripts/battery_algorithm.py`

**Linia 321-397:** Parsowanie `next_rising/next_setting` (zamiast nieistniejących `last_rising/last_setting`)

**Linia 96-109:** Obliczanie tylko o 23:00
```python
if hour == 23:
    calculate_cheapest_hours_to_store(data)
```

**Linia 607-630:** Wczytywanie zapisanej wartości
```python
cheapest_hours_str = get_state('input_text.battery_cheapest_hours')
cheapest_hours = eval(cheapest_hours_str)
is_cheap_hour = hour in cheapest_hours
```

## 📞 Wsparcie

- GitHub: https://github.com/MarekBodynek/home-assistant-huawei
- Branch: `claude/fix-energy-price-tiles-01J1tRyS4VB8xJUMyTgbcoAV`
- Issues: https://github.com/MarekBodynek/home-assistant-huawei/issues

---

**Wersja:** 1.0  
**Data:** 2025-11-17  
**Autor:** Claude Code
