# 🚀 Instrukcja wdrożenia - Poprawka wyboru najtańszych godzin

## 📋 Podsumowanie zmian

**Commit:** `156af63` - 🐛 Napraw wybór najtańszych godzin słonecznych

**Problem:**
- Dashboard pokazywał nieprawidłowe godziny w kafelkach "Ceny Energii" i "Prognoza PV"
- Po 18:00 wyświetlał godziny 5, 6, 7, 10 (dzisiejsze, już minione)
- Zamiast 10, 11, 12, 13 (jutrzejsze, faktycznie najtańsze według Pstryka)

**Przyczyna:**
- Algorytm używał `next_rising/next_setting` (jutrzejsze czasy słońca) do filtrowania dzisiejszych cen
- Po zachodzie słońca nadal analizował dzisiejsze godziny zamiast jutrzejszych
- Brak logiki wyboru "dziś vs jutro"

## 🔧 Co zostało zmienione

### Plik: `config/python_scripts/battery_algorithm.py`

#### 1. Pobieranie czasów wschodu/zachodu słońca (linie 321-377)

**Przed:**
```python
# Używał TYLKO next_rising/next_setting (jutrzejsze czasy)
next_rising_str = sun_state.attributes.get('next_rising', '')
next_setting_str = sun_state.attributes.get('next_setting', '')
sunrise_hour = int(next_rising_str.split('T')[1].split(':')[0])
sunset_hour = int(next_setting_str.split('T')[1].split(':')[0])
```

**Po:**
```python
# Pobiera DZISIEJSZE i JUTRZEJSZE czasy
today_rising_str = sun_state.attributes.get('last_rising', '')
today_setting_str = sun_state.attributes.get('last_setting', '')
tomorrow_rising_str = sun_state.attributes.get('next_rising', '')
tomorrow_setting_str = sun_state.attributes.get('next_setting', '')

# Inteligentny wybór: dziś lub jutro?
if hour >= today_sunset_hour or hour < today_sunrise_hour:
    analyze_tomorrow = True  # Po zachodzie lub w nocy
    sunrise_hour = tomorrow_sunrise_hour
    sunset_hour = tomorrow_sunset_hour
else:
    analyze_tomorrow = False  # W ciągu dnia
    sunrise_hour = today_sunrise_hour
    sunset_hour = today_sunset_hour
```

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

3. Sprawdź czy `sun.sun` istnieje i ma atrybuty `last_rising/last_setting`

## 📊 Różnice przed/po

### Przed (błąd):
```
Teraz: 18:30 (po zachodzie)
Analiza: dziś: [5, 6, 7, 10]  ❌ (minione godziny)
Algorytm używa: next_rising (jutro 7:30) do filtrowania dzisiejszych cen
```

### Po (poprawka):
```
Teraz: 18:30 (po zachodzie)
Analiza: jutro: [10, 11, 12, 13]  ✅ (najtańsze jutrzejsze godziny)
Algorytm używa: next_rising (jutro 7:30) do filtrowania jutrzejszych cen
```

## 📞 Kontakt

W razie problemów:
- GitHub Issues: https://github.com/MarekBodynek/home-assistant-huawei/issues
- Sprawdź logi: `/config/home-assistant.log`

---

**Data wdrożenia:** 2025-11-17
**Wersja:** 1.0
**Autor:** Claude Code
