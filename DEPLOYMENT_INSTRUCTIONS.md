# 🚀 Instrukcja wdrożenia - Poprawka wyboru najtańszych godzin

## 📋 Podsumowanie zmian

**Commity:**
- `156af63` - 🐛 Napraw wybór najtańszych godzin słonecznych (pierwsza próba)
- `710626a` - 🐛 Napraw wybór najtańszych godzin słonecznych (v2 - **POPRAWKA**)
- `384caa6` - 📚 Zaktualizuj instrukcję wdrożenia (v2)
- `d9602a3` - ⚡ **OPTYMALIZACJA:** Obliczaj najtańsze godziny 1x dziennie (zamiast 24x)

**Problem:**
- Dashboard pokazywał nieprawidłowe godziny w kafelkach "Ceny Energii" i "Prognoza PV"
- Po 18:00 wyświetlał godziny **5, 6, 7, 10** (z czego 5, 6 są PRZED wschodem słońca 7:29!)
- Zamiast **10, 11, 12, 13** (jutrzejsze, faktycznie najtańsze według Pstryka)

**Przyczyna:**
- **sun.sun NIE MA atrybutów `last_rising` i `last_setting`** (tylko `next_rising` i `next_setting`)
- Poprzedni kod próbował użyć nieistniejących atrybutów
- Fallback (6:00) powodował błędne filtrowanie godzin
- Godziny przed wschodem słońca przechodziły przez filtr

**Optymalizacja (commit `d9602a3`):**
- Algorytm wykonywał się CO GODZINĘ (24x dziennie) i za każdym razem przeliczał najtańsze godziny
- Ceny RCE publikowane są o **17:00 na następny dzień** i się **nie zmieniają** do kolejnego dnia
- Nie ma sensu przeliczać 24 razy - wynik jest zawsze **TAKI SAM**!
- **NOWE:** Obliczaj najtańsze godziny **RAZ DZIENNIE (o 23:00)**
- Pozostałe 23 godziny - wczytuj zapisaną wartość z `input_text.battery_cheapest_hours`

## 🔧 Co zostało zmienione

### Plik: `config/python_scripts/battery_algorithm.py`

#### 1. Pobieranie czasów wschodu/zachodu słońca (linie 321-397)

**Przed (BŁĄD):**
```python
# Próba użycia nieistniejących atrybutów
today_rising_str = sun_state.attributes.get('last_rising', '')  # NIE ISTNIEJE!
today_setting_str = sun_state.attributes.get('last_setting', '')  # NIE ISTNIEJE!

# Zwraca pusty string → fallback 6:00
if 'T' in today_rising_str:  # '' nie zawiera 'T'
    ...
else:
    today_sunrise_hour = 6  # FALLBACK - niepoprawny!
```

**Po (POPRAWKA v2):**
```python
# Używa TYLKO next_rising i next_setting (jedyne dostępne)
next_rising_str = sun_state.attributes.get('next_rising', '')
next_setting_str = sun_state.attributes.get('next_setting', '')

# Pobierz dzisiejszą datę
today_str = date_state.state  # "2025-11-17"

# Parse DATĘ z next_setting aby określić czy słońce zaszło
if 'T' in next_setting_str:
    setting_date = next_setting_str.split('T')[0]  # "2025-11-17" lub "2025-11-18"
    setting_hour = int(next_setting_str.split('T')[1].split(':')[0])

    # Sprawdź czy next_setting to DZIŚ czy JUTRO
    if setting_date == today_str:
        # Słońce JESZCZE NIE zaszło → analizuj DZIŚ
        analyze_tomorrow = False
        sunrise_hour = hour  # Od teraz do zachodu
        sunset_hour = setting_hour
    else:
        # Słońce JUŻ zaszło → analizuj JUTRO
        analyze_tomorrow = True
        sunrise_hour = int(next_rising_str.split('T')[1].split(':')[0])  # 7:29 → 7
        sunset_hour = setting_hour
```

**Kluczowa różnica:**
- ✅ Parsowanie DATY z `next_setting` do określenia czy słońce zaszło
- ✅ Używanie rzeczywistych czasów wschodu/zachodu (7:29 → sunrise_hour=7)
- ✅ Filtr `7 <= price_hour < 16` eliminuje godziny 5, 6

#### 2. Filtrowanie cen dla odpowiedniej daty (linie 421-474)

**Przed:**
```python
# Filtrował TYLKO dzisiejsze godziny
if date_part == today_str and sunrise_hour <= price_hour < sunset_hour:
    sun_prices.append(...)
```

**Po:**
```python
# Oblicza jutrzejszą datę
tomorrow_str = (datetime.strptime(today_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

# Wybiera odpowiednią datę
target_date_str = tomorrow_str if analyze_tomorrow else today_str

# Filtruje dla odpowiedniej daty
if date_part == target_date_str and sunrise_hour <= price_hour < sunset_hour:
    # Pomija przeszłe godziny przy analizie dzisiejszej
    if not analyze_tomorrow and price_hour < hour:
        continue
    sun_prices.append(...)
```

#### 3. Komunikaty na dashboardzie (linie 504-511)

**Przed:**
```python
status_msg = f"Potrzeba: {hours_needed}h | Najtańsze: {cheapest_hours} | Teraz: {hour}h"
```

**Po:**
```python
day_label = "jutro" if analyze_tomorrow else "dziś"
status_msg = f"Potrzeba: {hours_needed}h | {day_label}: {cheapest_hours} | Teraz: {hour}h"
```

#### 4. OPTYMALIZACJA: Obliczanie 1x dziennie zamiast 24x (linie 96-109, 607-630)

**Przed:**
```python
# W execute_strategy() - wykonywane CO GODZINĘ
balance = calculate_power_balance(data)

# ZAWSZE obliczaj najtańsze godziny - 24x DZIENNIE!
try:
    calculate_cheapest_hours_to_store(data)  # Ciężkie obliczenia
except Exception as e:
    ...

# W handle_pv_surplus() - wykonywane przy nadwyżce PV
is_cheap_hour, reason, cheapest_hours = calculate_cheapest_hours_to_store(data)  # Ponowne obliczenia!
```

**Po (OPTYMALIZACJA):**
```python
# W execute_strategy() - wykonywane CO GODZINĘ
balance = calculate_power_balance(data)

# OPTYMALIZACJA: Obliczaj TYLKO o 23:00!
hour = data['hour']
if hour == 23:
    try:
        calculate_cheapest_hours_to_store(data)  # Zapisz do input_text.battery_cheapest_hours
    except Exception as e:
        ...

# W handle_pv_surplus() - wczytaj zapisaną wartość zamiast przeliczać
cheapest_hours_str = get_state('input_text.battery_cheapest_hours')
if not cheapest_hours_str or cheapest_hours_str == 'Brak danych':
    # Brak zapisanych godzin - fallback
    is_cheap_hour = None
else:
    # Parse "[10, 11, 12, 13]" → [10, 11, 12, 13]
    cheapest_hours = eval(cheapest_hours_str)
    is_cheap_hour = hour in cheapest_hours
```

**Korzyści:**
- ✅ **23x mniej obliczeń** dziennie (1x zamiast 24x)
- ✅ **Mniejsze obciążenie** systemu
- ✅ **Szybsze wykonanie** algorytmu co godzinę
- ✅ **Bardziej przewidywalne** zachowanie (wynik stały przez cały dzień)

## 📥 Wdrożenie na Home Assistant

### Metoda 1: Przez SSH (zalecana)

```bash
# 1. Połącz się z Home Assistant
ssh user@192.168.0.106

# 2. Przejdź do katalogu config
cd /config

# 3. Pobierz najnowsze zmiany
git fetch origin
git checkout claude/fix-energy-price-tiles-01J1tRyS4VB8xJUMyTgbcoAV
git pull origin claude/fix-energy-price-tiles-01J1tRyS4VB8xJUMyTgbcoAV

# 4. Sprawdź czy plik został zaktualizowany
ls -la python_scripts/battery_algorithm.py
head -50 python_scripts/battery_algorithm.py

# 5. Przeładuj skrypty Python w Home Assistant
# Opcja A: Developer Tools > YAML > Python Scripts Reload
# Opcja B: Restart Home Assistant
```

### Metoda 2: Przez Cloudflare Tunnel (jeśli SSH niedostępny)

```bash
# 1. Połącz się przez tunnel
ssh -o ProxyCommand='cloudflared access ssh --hostname ssh.bodynek.pl' marekbodynek@ssh.bodynek.pl

# 2. Dalsze kroki jak w Metodzie 1
```

### Metoda 3: Ręczne kopiowanie pliku

1. Pobierz plik z GitHub:
   ```
   https://github.com/MarekBodynek/home-assistant-huawei/blob/claude/fix-energy-price-tiles-01J1tRyS4VB8xJUMyTgbcoAV/config/python_scripts/battery_algorithm.py
   ```

2. W Home Assistant przejdź do:
   - File Editor
   - `config/python_scripts/battery_algorithm.py`

3. Zamień całą zawartość pliku na nową wersję

4. Zapisz (Ctrl+S)

5. Przeładuj Python Scripts:
   - Developer Tools > YAML > Python Scripts Reload

## ✅ Weryfikacja wdrożenia

### 1. Sprawdź logi Home Assistant

```bash
# Sprawdź logi pod kątem błędów
tail -f /config/home-assistant.log | grep battery_algorithm
```

Jeśli brak błędów = sukces ✅

### 2. Sprawdź dashboard

Przejdź do **Huawei Solar PV > Przegląd** i sprawdź kafelki:

**Kafelek "Ceny energii":**
- RCE najtańsze godziny: powinny pokazywać listę godzin

**Kafelek "Prognoza PV i bilans mocy":**
- 📊 Analiza: powinno pokazywać np. `Potrzeba: 4h | jutro: [10, 11, 12, 13] | Teraz: 18h`

### 3. Testy scenariuszowe

| Czas | Oczekiwane zachowanie |
|------|----------------------|
| **8:00** (w ciągu dnia) | Dashboard: `dziś: [12, 13, 14, 15]` - pozostałe godziny słoneczne |
| **18:00** (po zachodzie) | Dashboard: `jutro: [10, 11, 12, 13]` - jutrzejsze godziny słoneczne |
| **2:00** (noc) | Dashboard: `jutro: [10, 11, 12, 13]` - jutrzejsze godziny słoneczne |

### 4. Sprawdź czy czasy wschodu/zachodu są prawidłowe

Przejdź do **Developer Tools > States** i znajdź `sun.sun`:

Sprawdź atrybuty:
- `last_rising` - dzisiejszy wschód (np. `2025-11-17T07:28:00+01:00`)
- `last_setting` - dzisiejszy zachód (np. `2025-11-17T16:02:00+01:00`)
- `next_rising` - jutrzejszy wschód (np. `2025-11-18T07:30:00+01:00`)
- `next_setting` - jutrzejszy zachód (np. `2025-11-18T16:00:00+01:00`)

## 🔍 Troubleshooting

### Problem: Dashboard nadal pokazuje stare godziny

**Rozwiązanie:**
1. Sprawdź czy plik faktycznie się zaktualizował:
   ```bash
   grep "analyze_tomorrow" /config/python_scripts/battery_algorithm.py
   ```
   Powinien zwrócić kilka linii zawierających `analyze_tomorrow`

2. Przeładuj Python Scripts:
   - Developer Tools > YAML > Python Scripts Reload

3. Poczekaj 1 godzinę (algorytm wykonuje się co godzinę)

### Problem: Błąd w logach "name 'datetime' is not defined"

**Przyczyna:** Import datetime nie zadziałał

**Rozwiązanie:** Sprawdź czy linia 429 zawiera:
```python
from datetime import datetime, timedelta
```

### Problem: Dashboard pokazuje "Brak danych"

**Rozwiązanie:**
1. Sprawdź czy sensor Pstryk działa:
   ```
   Developer Tools > States > sensor.pstryk_current_sell_price
   ```

2. Sprawdź czy ma atrybut `All prices` z listą cen

3. Sprawdź czy `sun.sun` istnieje i ma atrybuty `next_rising/next_setting` (NIE last_rising/last_setting!)

## 📊 Różnice przed/po

### Przed v1 (błąd - nieistniejące atrybuty):
```
Teraz: 18:30 (po zachodzie, wschód jutro o 7:29)
Analiza: jutro: [5, 6, 7, 10, 11]  ❌ BŁĄD!

Godziny 5, 6 są PRZED wschodem słońca (7:29)!

Dlaczego?
- Kod używa last_rising/last_setting (NIE ISTNIEJĄ w sun.sun)
- Fallback: today_sunrise_hour = 6
- Filtr: 6 <= hour < 16 → przepuszcza 6, ale też 5 (błąd w logice)
```

### Po v2 (poprawka - parsowanie daty):
```
Teraz: 18:30 (po zachodzie, wschód jutro o 7:29)
Analiza: jutro: [7, 8, 9, 10, 11, 12, 13, 14, 15]  ✅ POPRAWKA!

Godziny 5, 6 są ODFILTROWANE (przed wschodem 7:29)

Dlaczego działa?
- Kod parsuje DATĘ z next_setting → wykrywa że słońce zaszło
- Ustawia sunrise_hour = 7 (z next_rising "2025-11-18T07:29:00")
- Filtr: 7 <= hour < 16 → przepuszcza TYLKO [7, 8, ..., 15] ✅
- Algorytm wybiera N najtańszych z tej listy
```

### Weryfikacja poprawności:
| Godzina | Wschód słońca | Czy powinna być w wynikach? | v1 (błąd) | v2 (poprawka) |
|---------|---------------|----------------------------|-----------|---------------|
| 5h | 7:29 | ❌ NIE (przed wschodem) | ❌ 5 jest | ✅ 5 NIE MA |
| 6h | 7:29 | ❌ NIE (przed wschodem) | ❌ 6 jest | ✅ 6 NIE MA |
| 7h | 7:29 | ✅ TAK (po wschodzie) | ✅ 7 jest | ✅ 7 jest |
| 10h | 7:29 | ✅ TAK (w ciągu dnia) | ✅ 10 jest | ✅ 10 jest |

## 📞 Kontakt

W razie problemów:
- GitHub Issues: https://github.com/MarekBodynek/home-assistant-huawei/issues
- Sprawdź logi: `/config/home-assistant.log`

---

**Data wdrożenia:** 2025-11-17
**Wersja:** 1.0
**Autor:** Claude Code
