# 📚 Home Assistant + Huawei Solar - Kompletna Dokumentacja

**Wersja:** 3.13
**Data aktualizacji:** 2025-12-17
**Autor:** Marek Bodynek + Claude Code (Anthropic AI)

---

## 📋 Spis Treści

### [1. INSTALACJA I KONFIGURACJA](#1-instalacja-i-konfiguracja)
- [1.1 Specyfikacja systemu](#11-specyfikacja-systemu)
- [1.2 Status instalacji](#12-status-instalacji)
- [1.3 Pierwsze uruchomienie](#13-pierwsze-uruchomienie)
- [1.4 Konfiguracja integracji Huawei Solar](#14-konfiguracja-integracji-huawei-solar)
- [1.5 Szybka konfiguracja (5 minut)](#15-szybka-konfiguracja-5-minut)

### [2. ALGORYTM ZARZĄDZANIA BATERIĄ](#2-algorytm-zarządzania-baterią)
- [2.1 Harmonogram uruchamiania](#21-harmonogram-uruchamiania)
- [2.2 Główna funkcja decyzyjna](#22-główna-funkcja-decyzyjna)
- [2.3 Obsługa nadwyżki PV](#23-obsługa-nadwyżki-pv)
- [2.4 Obsługa deficytu mocy](#24-obsługa-deficytu-mocy)
- [2.5 Decyzje ładowania z sieci](#25-decyzje-ładowania-z-sieci)
- [2.6 Arbitraż wieczorny](#26-arbitraż-wieczorny)
- [2.7 Obliczanie Target SOC](#27-obliczanie-target-soc)
- [2.8 Monitoring stanów krytycznych](#28-monitoring-stanów-krytycznych)
- [2.9 Kluczowe parametry](#29-kluczowe-parametry)
- [2.10 Przykładowe scenariusze](#210-przykładowe-scenariusze)

### [3. INTEGRACJE](#3-integracje)
- [3.1 Integracja Pstryk (ceny RCE)](#31-integracja-pstryk-ceny-rce)
- [3.2 Integracja Forecast.Solar (prognoza PV)](#32-integracja-forecastsolar-prognoza-pv)
- [3.3 Integracja Panasonic Aquarea (pompa ciepła)](#33-integracja-panasonic-aquarea-pompa-ciepła)

### [4. AUTOMATYZACJE](#4-automatyzacje)
- [4.1 Automatyzacje baterii](#41-automatyzacje-baterii)
- [4.2 Watchdog algorytmu](#42-watchdog-algorytmu)
- [4.3 Monitoring temperatury baterii](#43-monitoring-temperatury-baterii)
- [4.4 Auto git pull](#44-auto-git-pull)
- [4.5 CWU z nadwyżki PV](#45-cwu-z-nadwyżki-pv)
- [4.6 Watchdog Aquarea](#46-watchdog-aquarea)
- [4.7 CWU harmonogram 13:02](#47-cwu-harmonogram-1302)

### [5. DASHBOARD](#5-dashboard)
- [5.1 Instalacja dashboardu](#51-instalacja-dashboardu)
- [5.2 Struktura dashboardu](#52-struktura-dashboardu)
- [5.3 Kafelek magazynowania baterii](#53-kafelek-magazynowania-baterii)
- [5.4 Reload dashboardu](#54-reload-dashboardu)

### [6. DOSTĘP ZEWNĘTRZNY (CLOUDFLARE TUNNEL)](#6-dostęp-zewnętrzny-cloudflare-tunnel)
- [6.1 Quick Start (5 kroków)](#61-quick-start-5-kroków)
- [6.2 Pełna instrukcja konfiguracji](#62-pełna-instrukcja-konfiguracji)
- [6.3 Darmowa subdomena (.trycloudflare.com)](#63-darmowa-subdomena-trycloudflarecom)
- [6.4 Darmowa domena (.us.kg)](#64-darmowa-domena-uskg)
- [6.5 SSH przez Cloudflare Tunnel (automatyczny deployment)](#65-ssh-przez-cloudflare-tunnel-automatyczny-deployment)

### [7. BEZPIECZEŃSTWO I OPTYMALIZACJA](#7-bezpieczeństwo-i-optymalizacja)
- [7.1 Poprawki bezpieczeństwa](#71-poprawki-bezpieczeństwa)
- [7.2 Optymalizacje kosztowe](#72-optymalizacje-kosztowe)
- [7.3 Rekomendacje dodatkowe](#73-rekomendacje-dodatkowe)

### [8. ROZWIĄZYWANIE PROBLEMÓW](#8-rozwiązywanie-problemów)
- [8.1 Problemy z algorytmem](#81-problemy-z-algorytmem)
- [8.2 Problemy z integracjami](#82-problemy-z-integracjami)
- [8.3 Problemy z dashboardem](#83-problemy-z-dashboardem)
- [8.4 Problemy z Cloudflare Tunnel](#84-problemy-z-cloudflare-tunnel)

### [9. ZARZĄDZANIE SYSTEMEM](#9-zarządzanie-systemem)
- [9.1 Kontrola Docker](#91-kontrola-docker)
- [9.2 Aktualizacja Home Assistant](#92-aktualizacja-home-assistant)
- [9.3 Backup](#93-backup)

### [10. CHECKLISTY](#10-checklisty)
- [10.1 Pierwsza konfiguracja](#101-pierwsza-konfiguracja)
- [10.2 Konfiguracja algorytmu](#102-konfiguracja-algorytmu)
- [10.3 Weryfikacja zmian](#103-weryfikacja-zmian)

### [11. WDROŻENIA I OPTYMALIZACJE](#11-wdrożenia-i-optymalizacje)
- [11.1 FAZA 1: Optymalizacja ładowania baterii](#111-faza-1-optymalizacja-ładowania-baterii-2025-11-17)
- [11.2 Fix: Target SOC Charging](#112-fix-target-soc-charging-2025-11-17)
- [11.3 Fix: Parametry baterii w L1](#113-fix-parametry-baterii-w-l1-2025-11-17)
- [11.4 System logowania błędów + Fix temperatury](#114-system-logowania-błędów--fix-temperatury-2025-11-18)

---

# 1. INSTALACJA I KONFIGURACJA

## 1.1 Specyfikacja systemu

- **Instalacja PV:** 14.4 kWp (Huawei)
- **Bateria:** Huawei Luna 2000 (15 kWh)
- **Tryb pracy:** PV PRIORITY (priorytet ładowania z fotowoltaiki)
- **Home Assistant:** Najnowsza stabilna wersja (Docker)
- **Taryfa:** G12w (dwustrefowa)
- **Pompa ciepła:** Panasonic T-CAP (opcjonalnie)

## 1.2 Status instalacji

**Gotowe:**
- ✅ Docker zainstalowany i działa
- ✅ Katalogi utworzone: `~/home-assistant-huawei/`
- ✅ Home Assistant uruchomiony (port 8123)
- ✅ Pliki konfiguracyjne przygotowane
- ✅ Automatyzacje dla algorytmu baterii
- ✅ Zabezpieczenia termiczne baterii
- ✅ Watchdog algorytmu

**Do wykonania:**
- 🔄 Pierwsze uruchomienie Home Assistant
- 🔄 Instalacja integracji Huawei Solar przez HACS
- 🔄 Dodanie Twojego invertera do systemu
- 🔄 Konfiguracja integracji Pstryk (ceny RCE)
- 🔄 Konfiguracja integracji Forecast.Solar (prognoza PV)

## 1.3 Pierwsze uruchomienie

### 1. Otwórz Home Assistant
```bash
# Home Assistant dostępny pod adresem:
open http://localhost:8123
```

**Pierwsze logowanie:**
- Utwórz konto administratora
- Podaj nazwę domu i lokalizację
- Wybierz strefę czasową: **Europe/Warsaw**

### 2. Zainstaluj HACS (Home Assistant Community Store)

HACS jest wymagany do instalacji integracji Huawei Solar.

**Instalacja HACS:**
```bash
# Pobierz HACS
cd ~/home-assistant-huawei/config
wget -O - https://get.hacs.xyz | bash -
```

**W Home Assistant:**
1. Przejdź do **Settings** → **Devices & Services**
2. Kliknij **+ ADD INTEGRATION**
3. Wyszukaj **HACS** i zainstaluj
4. Autoryzuj z kontem GitHub

### 3. Zainstaluj integrację Huawei Solar

**Przez HACS:**
1. Otwórz **HACS** → **Integrations**
2. Kliknij **+ EXPLORE & DOWNLOAD REPOSITORIES**
3. Wyszukaj **Huawei Solar**
4. Kliknij **DOWNLOAD**
5. Zrestartuj Home Assistant

**Po restarcie:**
1. **Settings** → **Devices & Services** → **+ ADD INTEGRATION**
2. Wyszukaj **Huawei Solar**
3. Podaj:
   - **IP adres invertera** (znajdź w aplikacji FusionSolar)
   - **Port:** 502 (domyślny Modbus)
   - **Slave ID:** 1 (domyślny)

## 1.4 Konfiguracja integracji Huawei Solar

### Znalezienie IP invertera

**Metoda 1: Aplikacja FusionSolar**
- Otwórz aplikację FusionSolar
- Zakładka **Ustawienia** → **Informacje o urządzeniu**
- Sprawdź adres IP invertera

**Metoda 2: Router**
- Zaloguj się do routera
- Sprawdź listę podłączonych urządzeń
- Szukaj urządzenia Huawei (nazwa może zawierać "SUN")

### Konfiguracja połączenia

Po dodaniu integracji, Home Assistant wykryje:
- **Inverter** (SUN2000)
- **Baterię** (LUNA2000)
- **Miernik energii** (Power Meter)

**Ważne encje:**
- `sensor.akumulatory_stan_pojemnosci` - poziom naładowania baterii (%)
- `sensor.inwerter_moc_czynna` - aktualna moc produkcji PV (W)
- `sensor.pomiar_mocy_moc_czynna` - moc pobierana/oddawana do sieci (W)
- `select.akumulatory_tryb_pracy` - tryb pracy baterii

## 1.5 Szybka konfiguracja (5 minut)

### Krok 1: Dodaj integrację Pstryk (ceny RCE)

**Jak uzyskać klucz API Pstryk:**
1. Zainstaluj aplikację **Pstryk** na telefonie (iOS/Android)
2. Zarejestruj się lub zaloguj
3. W aplikacji: **Ustawienia** → **API** → **Generuj klucz**
4. Skopiuj klucz API

**BONUS:** Użyj kodu rabatowego **E3WOTQ** przy pierwszej fakturze - otrzymasz 50 zł na prąd!

**Dodaj integrację w Home Assistant:**
1. Otwórz: http://localhost:8123
2. **Settings** → **Devices & Services** → **+ ADD INTEGRATION**
3. Wpisz: **Pstryk Energy**
4. Wprowadź dane:
   - **Klucz API**: [wklej skopiowany klucz]
   - **Liczba najlepszych cen kupna**: 5
   - **Liczba najlepszych cen sprzedaży**: 5
5. Kliknij: **SUBMIT**

### Krok 2: Dodaj integrację Forecast.Solar (prognoza PV)

1. **Settings** → **Devices & Services** → **+ ADD INTEGRATION**
2. Wpisz: **Forecast.Solar**
3. Wypełnij formularz:

```
✅ Latitude: 54.163651
✅ Longitude: 16.106855
✅ Declination (nachylenie paneli): 35
✅ Azimuth (azymut - kierunek): 180
   (0=północ, 90=wschód, 180=południe, 270=zachód)
✅ Modules Power (moc paneli): 14400
   (14.4 kWp = 14400 Wp)
✅ Damping: 0
```

4. Kliknij: **SUBMIT**

### Krok 3: Sprawdź czy działa

1. **Developer Tools** → **States**
2. Wyszukaj:
   - `sensor.pstryk_current_sell_price` - powinna być wartość np. 0.450
   - `sensor.energy_production_tomorrow` - powinna być wartość np. 12.5
   - `sensor.strefa_taryfowa` - powinna być **L1** lub **L2**
   - `binary_sensor.sezon_grzewczy` - powinna być **on** (temp < 12°C)

### Krok 4: Test algorytmu ręcznie

1. **Developer Tools** → **Services**
2. Service: `python_script.calculate_daily_strategy`
3. Kliknij: **CALL SERVICE**
4. Sprawdź notyfikację - powinna pojawić się: "📊 Strategia dzienna obliczona"

### Krok 5: Test głównego algorytmu

1. **Developer Tools** → **Services**
2. Service: `python_script.battery_algorithm`
3. Kliknij: **CALL SERVICE**
4. Sprawdź logi: **Settings** → **System** → **Logs**
   - Szukaj: "Applying strategy" lub "DECISION"

---

# 2. ALGORYTM ZARZĄDZANIA BATERIĄ

## 2.1 Harmonogram uruchamiania

```
03:55  → fetch_forecast_pv()
04:30  → execute_strategy() [początek okna CWU]
06:00  → execute_strategy() [zmiana L2→L1]
12:00  → fetch_forecast_pv()
13:00  → execute_strategy() [zmiana L1→L2]
15:00  → execute_strategy() [zmiana L2→L1]
18:00  → fetch_rce_prices() [random 0-15min delay]
19:00  → execute_strategy() [SZCZYT + arbitraż]
20:00  → fetch_forecast_pv()
21:05  → calculate_daily_strategy() [Target SOC na dobę 22:00-21:59]
22:00  → execute_strategy() [zmiana L1→L2 + ładowanie]

CO 1h (XX:00) → execute_strategy() [główna pętla]
```

## 2.2 Główna funkcja decyzyjna

Algorytm wykonywany co godzinę podejmuje decyzje na podstawie:

**Dane wejściowe:**
- Czas (godzina, dzień tygodnia, święta)
- Taryfa (L1 lub L2)
- Ceny RCE (aktualne, przyszłe, średnie wieczorne)
- Stan baterii (SOC, moc, temperatura)
- PV i zużycie (moc PV, obciążenie domu, moc sieci)
- Prognozy (PV dziś, jutro, 6h)
- Temperatura i PC (temperatura zewnętrzna, sezon grzewczy, okna CWU)
- Strategia (Target SOC, okno ładowania)

**Decyzje wyjściowe:**
- `charge_from_pv` - Ładowanie tylko z PV
- `charge_from_grid` - Ładowanie z sieci (L2)
- `discharge_to_home` - Rozładowanie do domu
- `discharge_to_grid` - Rozładowanie do sieci (arbitraż)
- `idle` - Bateria nieaktywna

## 2.3 Obsługa nadwyżki PV

Gdy mamy nadwyżkę energii z PV, algorytm decyduje czy:

### MAGAZYNOWAĆ w baterii gdy:
- ✅ RCE ujemne lub bardzo niskie (< 0.20 zł/kWh)
- ✅ Jutro pochmurno (prognoza < 12 kWh)
- ✅ Wkrótce drogi wieczór (RCE wieczór > 0.55 zł/kWh)
- ✅ Zima (listopad-luty)
- ✅ Słaba prognoza na 6h (< 5 kWh)

### SPRZEDAĆ do sieci gdy:
- ✅ Warunki OK, sprzedaj po aktualnym RCE × 1.23

## 2.4 Obsługa deficytu mocy

Gdy brakuje energii z PV, algorytm decyduje czy:

### W SEZONIE GRZEWCZYM:
**Strefa L1 (droga):**
- Używaj baterii jeśli SOC > 25% (oszczędzaj drogą L1!)
- Ładuj z sieci jeśli SOC < 25%

**Strefa L2 (tania):**
- Okno CWU: PC może z sieci, oszczędzaj baterię na L1
- Poza CWU: Ładuj baterię do Target SOC

### POZA SEZONEM:
**Strefa L1 (droga):**
- Używaj baterii jeśli SOC > 20%

**Strefa L2 (tania):**
- Okno CWU: PC może z sieci
- Poza CWU: Ładuj baterię jeśli < Target SOC

## 2.5 Decyzje ładowania z sieci

### CASE 1: RCE UJEMNE (rzadkie!)
Płacą Ci za pobór energii - ładuj do 95%!

### CASE 2: RCE BARDZO NISKIE w południe
RCE < 0.15 zł/kWh + pochmurno jutro → ładuj do 75%

### CASE 3: NOC L2 - GŁÓWNE ŁADOWANIE
**Godziny:** 22:00-06:00
**Cel:** Target SOC obliczony o 21:05

**Priorytety:**
- Pochmurno jutro (< 15 kWh) → CRITICAL
- Średnio jutro (< 25 kWh) → HIGH
- Słonecznie jutro (> 25 kWh) → MEDIUM

**W sezonie grzewczym:** +1 poziom priorytetu

### CASE 4: RANO przed końcem L2 (04:00-06:00)
Ostatnia szansa! Jeśli pochmurno jutro + SOC < 85% → ładuj do 90%

### CASE 5: SOC KRYTYCZNIE NISKI
SOC < 15% → ładuj do 30% (bezpieczeństwo baterii)

## 2.6 Arbitraż wieczorny

**Godziny:** 19:00-22:00
**Warunek:** Sprzedaj energię z baterii gdy opłacalne

### Wymagania:
1. **RCE wysokie:**
   - Sezon grzewczy: > 0.65 zł/kWh
   - Poza sezonem: > 0.55 zł/kWh

2. **SOC odpowiednie:**
   - Sezon grzewczy: > 60-70% (rezerwa na PC)
   - Poza sezonem: > 55%

3. **Jutro prognoza OK:**
   - Sezon grzewczy: > 25 kWh
   - Poza sezonem: > 20 kWh

### Ile sprzedać:
**Sezon grzewczy:**
- Lato (V-VIII): min SOC = 40%
- Przejściówka (III-IV, IX-X): min SOC = 45%
- Zima (XI-II): min SOC = 50%

**Poza sezonem:**
- Lato (V-VIII): min SOC = 30%
- Przejściówka: min SOC = 35%

**Potencjalny zysk:**
(SOC_teraz - SOC_min) × 15 kWh × RCE × 1.23 × 90%

**Przykład:**
(75% - 30%) × 15 kWh × 0.68 zł/kWh × 1.23 × 90% = **~5.64 zł**

## 2.7 Obliczanie Target SOC

Wykonywane codziennie o 21:05 (przed dobą energetyczną 22:00-21:59)

### SEZON GRZEWCZY:

**Bazowe zużycie CO (zależy od temperatury):**
- Temp < -10°C: 60 kWh (Mróz)
- Temp < 0°C: 50 kWh (Zima)
- Temp < 5°C: 40 kWh (Chłodno)
- Temp 5-12°C: 30 kWh (Umiarkowanie)

**Zużycie domu:** 26 kWh
**Suma L1:** CO + Dom

**Obliczenia:**
```
Pokrycie_PV = min(prognoza_jutro × 0.7, suma_L1 × 0.3)
Z_baterii = min(suma_L1 - pokrycie_PV, 15)
Target_SOC = (z_baterii / 15) × 100
Target_SOC = max(60%, min(80%, target_SOC))
```

**W mrozy (< -5°C):** Target SOC minimum 85%

### POZA SEZONEM:

**Zużycie domu:** 28 kWh (tylko dom)

**Obliczenia:**
```
Pokrycie_PV = min(prognoza_jutro × 0.8, dom_L1 × 0.6)
Z_baterii = min(dom_L1 - pokrycie_PV, 15)
Target_SOC = (z_baterii / 15) × 100
Target_SOC = max(20%, min(80%, target_SOC))
```

**Latem:**
- Prognoza > 30 kWh → Target = 20%
- Prognoza > 20 kWh → Target = 20%
- Prognoza < 20 kWh → Target = 50%

## 2.8 Monitoring stanów krytycznych

**Uruchamiany co 1 minutę**

### SOC KRYTYCZNIE NISKIE (≤ 10%)
- 🚨 Alert krytyczny
- Wymuszenie ładowania do 20%
- Powiadomienie: "🚨 Bateria krytycznie niska!"

### SOC BARDZO NISKIE w L1 (≤ 20%)
- ⚠️ Ostrzeżenie
- Powiadomienie: "⚠️ Bateria niska w L1"

### SOC ZA WYSOKIE (≥ 95%)
- Stop ładowania
- Info: "SOC max osiągnięty"

### TEMPERATURA BATERII:

**> 45°C - ALARM POŻAROWY:**
- ⚫ NATYCHMIASTOWY STOP wszystkich operacji
- Instrukcje ewakuacji
- Wezwanie serwisu
- NIE GASIĆ WODĄ! (gaśnica proszkowa lub CO₂)

**> 43°C - STOP ŁADOWANIA:**
- 🔴 Wyłączenie ładowania z sieci
- Tryb bezpieczny (Maximise Self Consumption)
- Monitoring co 5 min

**> 40°C - OSTRZEŻENIE:**
- 🟠 Alert o podwyższonej temperaturze
- Monitoring przez 30 min

**< 0°C - ZAMARZANIE:**
- ❄️ Blokada ładowania
- Instrukcje ogrzania pomieszczenia

**< 38°C przez 15 min - POWRÓT DO NORMY:**
- ✅ Potwierdzenie bezpieczeństwa
- Usunięcie alertów

### BRAK DANYCH RCE:
Jeśli dane starsze niż 24h:
- ⚠️ Alert: "Brak świeżych cen RCE"
- Powiadomienie: "Sprawdź połączenie z API"

## 2.9 Kluczowe parametry

### Progi cenowe RCE:
```python
RCE_NEGATIVE = 0.00
RCE_VERY_LOW = 0.20
RCE_LOW = 0.35
RCE_MEDIUM = 0.45
RCE_HIGH = 0.55
RCE_VERY_HIGH = 0.65
RCE_EXTREME = 0.75
```

### Progi prognozy PV:
```python
FORECAST_EXCELLENT = 30  # kWh
FORECAST_VERY_GOOD = 25
FORECAST_GOOD = 20
FORECAST_MEDIUM = 15
FORECAST_POOR = 12
FORECAST_BAD = 8
FORECAST_VERY_BAD = 5
```

### Progi baterii:
```python
BATTERY_CRITICAL = 5   # % - SOC krytyczne, natychmiastowe ładowanie 24/7
BATTERY_LOW = 20       # % - SOC niskie, pilne ładowanie w L2
BATTERY_RESERVE = 30   # % - Rezerwa weekendowa (stała, niezależna od sezonu)
BATTERY_GOOD = 65      # % - SOC dobre
BATTERY_HIGH = 70      # % - SOC wysokie
BATTERY_MAX = 80       # % - Limit Huawei (nie przekraczać!)
```

### Temperatura i PC:
```python
TEMP_HEATING_THRESHOLD = 12  # °C - poniżej włącza się CO
TEMP_FROST = -10
TEMP_WINTER = 0
TEMP_COLD = 5
```

### Taryfa G12w:
```python
L2_NIGHT_START = 22  # Godzina
L2_NIGHT_END = 6
L2_AFTERNOON_START = 13
L2_AFTERNOON_END = 15
```

### Okna CWU:
```python
CWU_MORNING_START = 4.5  # 04:30
CWU_MORNING_END = 6
CWU_AFTERNOON_START = 13
CWU_AFTERNOON_END = 15
```

### Bezpieczne zakresy temperatury baterii:
- 🟢 **Optymalna:** 15-25°C
- 🟡 **Dopuszczalna:** 5-40°C
- 🟠 **Ostrzeżenie:** >40°C (degradacja)
- 🔴 **STOP ładowania:** >43°C
- ⚫ **ALARM POŻAROWY:** >45°C
- ❄️ **Mróz:** <0°C (uszkodzenie)

## 2.10 Przykładowe scenariusze

### Scenariusz 1: Zimowy dzień (mróz -10°C, pochmurno)

```
21:05 → calculate_daily_strategy()
  Prognoza jutro: 5 kWh
  Temp: -10°C (CO aktywne)
  TARGET_SOC = 80% (PC będzie ciężko pracować!)

22:00 → execute_strategy()
  Zmiana L1→L2, SOC 42% < 80%
  DECYZJA: Ładuj z sieci L2

06:00 → execute_strategy()
  Zmiana L2→L1, PC CO pracuje 6 kW!
  SOC 85%, deficyt
  DECYZJA: BATERIA→DOM (oszczędzaj L1!)

19:00 → execute_strategy()
  L1, PC 5 kW, SOC 35%
  RCE = 0.72 (wysokie!)
  Ale: mróz + pochmurno jutro
  DECYZJA: BATERIA→DOM (nie sprzedawaj, PC potrzebuje!)

22:00 → execute_strategy()
  Zmiana L1→L2, SOC 28%
  DECYZJA: Ładuj do 85% (jutro będzie ciężko)
```

### Scenariusz 2: Letni dzień (20°C, słonecznie)

```
21:05 → calculate_daily_strategy()
  Prognoza jutro: 35 kWh
  Temp: 20°C (CO wyłączone!)
  TARGET_SOC = 35% (PV wystarczy)

13:00 → execute_strategy()
  L2, PC CWU 3 kW, PV 8 kW
  Nadwyżka 5 kW, SOC 45%
  DECYZJA: PV→BATERIA (magazynuj na wieczór L1!)

19:00 → execute_strategy()
  L1, SOC 75%, RCE = 0.68
  Prognoza jutro: 38 kWh ✅
  Brak CO = więcej miejsca!
  DECYZJA: BATERIA→SIEĆ (sprzedaj do 30%!)
  Zysk: 6.75 kWh × 0.836 zł = ~5.64 zł
```

---

# 3. INTEGRACJE

## 3.1 Integracja Pstryk (ceny RCE)

**Status:** ✅ Zainstalowana (v1.8.0)
**GitHub:** https://github.com/balgerion/ha_Pstryk

### Dostępne encje:

**Ceny bieżące:**
- `sensor.pstryk_current_buy_price` - Aktualna cena kupna (zł/kWh)
- `sensor.pstryk_current_sell_price` - Aktualna cena sprzedaży (zł/kWh)
- `sensor.pstryk_next_hour_buy_price` - Cena w następnej godzinie
- `sensor.pstryk_next_hour_sell_price` - Cena sprzedaży w następnej godzinie

**Średnie ceny:**
- `sensor.pstryk_buy_monthly_average` - Średnia miesięczna cena kupna
- `sensor.pstryk_buy_yearly_average` - Średnia roczna cena kupna
- `sensor.pstryk_sell_monthly_average` - Średnia miesięczna cena sprzedaży
- `sensor.pstryk_sell_yearly_average` - Średnia roczna cena sprzedaży

**Bilanse finansowe:**
- `sensor.pstryk_daily_financial_balance` - Dzienny bilans kupna/sprzedaży (PLN)
- `sensor.pstryk_monthly_financial_balance` - Miesięczny bilans (PLN)
- `sensor.pstryk_yearly_financial_balance` - Roczny bilans (PLN)

### Atrybuty sensorów:

`sensor.pstryk_current_buy_price` zawiera:
- `hourly_prices` - Tabela 24h z cenami godzinowymi
- `best_prices` - 5 najtańszych godzin
- `worst_prices` - 5 najdroższych godzin
- `all_prices` - Wszystkie ceny (używane przez battery_algorithm.py)

### Korzyści z Pstryk API:
- ✅ Stabilne API (nie zmienia się jak TGE)
- ✅ Wszystkie opłaty zawarte (VAT + dystrybucja)
- ✅ Tabele 24h/48h z prognozami
- ✅ Najlepsze/najgorsze godziny automatycznie
- ✅ Statystyki miesięczne i roczne
- ✅ Bilanse finansowe
- ✅ MQTT support

## 3.2 Integracja Forecast.Solar (prognoza PV)

**Encje utworzone:**
- `sensor.energy_production_today` - Produkcja dziś (całkowita)
- `sensor.energy_production_today_remaining` - Pozostało dziś
- `sensor.energy_production_tomorrow` - Prognoza jutro
- `sensor.energy_current_hour` - Bieżąca godzina

**Konto:**
- **Darmowe:** 12 zapytań/dzień, prognoza 1 dzień
- **Płatne (Personal):** 6 EUR/rok, 60 zapytań/godzinę, prognoza 3 dni

**Optymalizacja:**
- `scan_interval: 7200s` (2h) = 36 zapytań/dobę (zmiana z 72)
- Redukcja zapytań: -50%
- Ręczne update o 03:55, 12:00, 20:00 (kluczowe momenty)

## 3.3 Integracja Panasonic Aquarea (pompa ciepła)

**Status:** ✅ Zainstalowana i działająca
**GitHub:** https://github.com/cjaliaga/home-assistant-aquarea
**Integracja:** Aquarea Smart Cloud (HACS)

### Wymagania:
- Moduł WiFi CZ-TAW1 w pompie ciepła
- Konto Panasonic Aquarea Smart Cloud (aquarea-smart.panasonic.com)

### Konfiguracja:
1. **HACS** → **Integrations** → Wyszukaj: **Aquarea Smart Cloud**
2. Zainstaluj i restart HA
3. **Settings** → **Devices & Services** → **+ ADD INTEGRATION**
4. Wyszukaj: **Aquarea Smart Cloud**
5. Podaj dane logowania z aquarea-smart.panasonic.com

### Główne encje:
- `climate.bodynek_nb_zone_1` - Sterowanie ogrzewaniem (CO)
  - Stany: `heat`, `off`
  - Atrybut: `current_temperature` - temperatura zasilania
- `water_heater.bodynek_nb_tank` - Sterowanie CWU
  - Stany: `heating`, `off`
  - Atrybut: `current_temperature` - temperatura wody w zbiorniku
  - Atrybut: `temperature` - temperatura docelowa
- `switch.bodynek_nb_wymus_c_w_u` - Wymuszenie grzania CWU

### Sensory pomocnicze (template):
```yaml
# config/template_sensors.yaml
- binary_sensor:
    - name: "PC CO aktywne"
      state: "{{ states('climate.bodynek_nb_zone_1') == 'heat' }}"

    - name: "CWU aktywne"
      state: "{{ states('water_heater.bodynek_nb_tank') == 'heating' }}"
```

### Korzyści:
- ✅ Rzeczywisty status CO i CWU (z API pompy)
- ✅ Sterowanie pompą z Home Assistant
- ✅ Wymuszanie grzania CWU z nadwyżki PV
- ✅ Integracja z algorytmem zarządzania baterią

---

# 4. AUTOMATYZACJE

## 4.1 Automatyzacje baterii

**Plik:** `config/automations_battery.yaml`

### Lista automatyzacji:

1. **[Bateria] Oblicz strategię dzienną 21:05**
   - Trigger: time 21:05:00
   - Wywołuje: `python_script.calculate_daily_strategy`
   - Oblicza Target SOC na dzień

2. **[Bateria] Wykonaj strategię (co 1h)**
   - Trigger: time_pattern (XX:00:00)
   - Wywołuje: `python_script.battery_algorithm`
   - Główna pętla decyzyjna

3. **[Bateria] Wykonaj strategię przy zmianie strefy taryfowej**
   - Trigger: zmiana `sensor.strefa_taryfowa`
   - Natychmiastowa reakcja na L1↔L2

4. **[Bateria] Pobierz prognozę PV (03:55)**
   - Aktualizacja prognozy przed obliczeniem strategii

5. **[Bateria] Pobierz prognozę PV (12:00)**
   - Aktualizacja w południe

6. **[Bateria] Pobierz prognozę PV (20:00)**
   - Aktualizacja przed nocą

7. **[Bateria] Pobierz ceny RCE (18:00)**
   - Random delay 0-15 min
   - Aktualizacja `sensor.pstryk_current_sell_price`

8. **[Bateria] Monitor SOC krytyczne**
   - Trigger: time_pattern (co 1 min)
   - Condition: SOC ≤ 10%
   - Action: Wymuszenie ładowania + notyfikacja

9. **[Bateria] Monitor SOC niskie w L1**
   - Condition: SOC ≤ 20% AND L1
   - Action: Notyfikacja ostrzegawcza

10. **[Bateria] Podsumowanie dnia (23:00)**
    - Raport dziennych oszczędności

## 4.2 Watchdog algorytmu

### Watchdog 1: Zdrowie algorytmu
**Plik:** `config/automations_battery.yaml:367-399`

**Trigger:** co 30 min
**Condition:** Ostatnia aktualizacja `input_text.battery_decision_reason` > 2h
**Action:**
- Notyfikacja: "⚠️ Algorytm nie aktualizuje decyzji"
- Ustawienie trybu awaryjnego: Maximise Self Consumption
- Próba restartu algorytmu

### Watchdog 2: Zablokowany SOC
**Plik:** `config/automations_battery.yaml:401-431`

**Trigger:** co 1h
**Condition:** SOC nie zmienił się przez 6h
**Action:**
- Notyfikacja: "⚠️ SOC zablokowane - możliwa awaria"
- Sprawdzenie komunikacji z baterią
- Instrukcje diagnostyczne

## 4.3 Monitoring temperatury baterii

**KRYTYCZNE zabezpieczenie dodane 2025-11-16**

### 5 automatyzacji termicznych:

**1. Ostrzeżenie (>40°C)**
- Alert o podwyższonej temperaturze
- Monitoring przez 30 min

**2. STOP ŁADOWANIA (>43°C)**
- Natychmiastowe wyłączenie ładowania z sieci
- Tryb bezpieczny (Maximise Self Consumption)
- Instrukcje postępowania

**3. ALARM POŻAROWY (>45°C)**
- Alarm krytyczny
- Instrukcje ewakuacji
- Wezwanie serwisu
- Informacja: NIE GASIĆ WODĄ!

**4. Zamarzanie (<0°C)**
- Blokada ładowania przy mrozie
- Instrukcje ogrzania pomieszczenia

**5. Powrót do normy (<38°C przez 15 min)**
- Potwierdzenie bezpieczeństwa
- Usunięcie alertów
- Przywrócenie normalnej pracy

## 4.4 Auto git pull

### Opcja 1: Jednorazowy manual (NAJSZYBSZA)
```bash
ssh marekbodynek@192.168.0.106
cd /Users/marekbodynek/home-assistant-huawei
git pull
```

### Opcja 2: Webhook do git pull

**Automatyzacja:**
```yaml
alias: "[System] Git Pull via Webhook"
trigger:
  - platform: webhook
    webhook_id: git_pull_webhook_secret_12345
action:
  - service: shell_command.git_pull
  - service: persistent_notification.create
    data:
      title: "🔄 Git Pull"
      message: "Wykonano git pull o {{ now().strftime('%H:%M:%S') }}"
```

**Configuration.yaml:**
```yaml
shell_command:
  git_pull: 'cd /config && git pull'
```

**Test:**
```bash
curl -X POST http://192.168.0.106:8123/api/webhook/git_pull_webhook_secret_12345
```

### Opcja 3: Auto git pull co godzinę

**Automatyzacja:**
```yaml
- id: auto_git_pull_hourly
  alias: "[System] Auto Git Pull co godzinę"
  trigger:
    - platform: time_pattern
      hours: "*"
  action:
    - service: shell_command.git_pull
    - delay:
        seconds: 5
    - service: homeassistant.reload_core_config
```

## 4.5 CWU z nadwyżki PV

**Plik:** `config/automations_battery.yaml`

### Opis funkcjonalności:
Automatyczne grzanie ciepłej wody użytkowej (CWU) gdy:
- Jest nadwyżka produkcji PV
- Cena energii jest w zielonej strefie (< p33)

### Automatyzacja 1: Włączenie CWU
**ID:** `cwu_pv_surplus_enable`

**Trigger:**
- Nadwyżka PV > 2 kW

**Warunki (wszystkie muszą być spełnione):**
1. CWU nie grzeje aktualnie (`water_heater.bodynek_nb_tank` = off)
2. Wymuszenie CWU wyłączone (`switch.bodynek_nb_wymus_c_w_u` = off)
3. Cena energii < p33 (dynamiczny próg zielonej strefy z `sensor.rce_progi_cenowe`)
4. Temperatura wody < 55°C

**Akcja:**
- Włącz `switch.bodynek_nb_wymus_c_w_u`
- Wyślij powiadomienie

### Automatyzacja 2: Wyłączenie CWU
**ID:** `cwu_pv_surplus_disable`

**Trigger (dowolny):**
- Nadwyżka PV < 0.5 kW
- Temperatura wody > 55°C

**Warunek:**
- Flaga `input_boolean.cwu_pv_surplus_active` = ON (włączone przez automatyzację PV, nie ręcznie!)

**Akcja:**
- Wyłącz `switch.bodynek_nb_wymus_c_w_u`
- Wyłącz flagę `input_boolean.cwu_pv_surplus_active`
- Wyślij powiadomienie z powodem

### Automatyzacja 3: Ręczne wymuszenie CWU - auto-off po 30 min
**ID:** `cwu_manual_force_auto_off`

**Trigger:**
- `switch.bodynek_nb_wymus_c_w_u` = ON przez 30 minut

**Akcja:**
- Wyłącz `switch.bodynek_nb_wymus_c_w_u`
- Wyślij powiadomienie o automatycznym wyłączeniu

### Flaga automatyzacji PV
**Encja:** `input_boolean.cwu_pv_surplus_active`

Flaga rozróżnia czy CWU zostało włączone:
- **Przez automatyzację PV** → wyłączy się automatycznie gdy spadnie nadwyżka
- **Ręcznie przez użytkownika** → wyłączy się po 30 minutach (safety timeout)

### Parametry:
| Parametr | Wartość | Opis |
|----------|---------|------|
| Próg włączenia PV | > 2 kW | Minimalna nadwyżka do startu |
| Próg wyłączenia PV | < 0.5 kW | Histereza wyłączenia |
| Próg temp. wyłączenia | > 55°C | Max temperatura wody |
| Próg cenowy | < p33 | Dynamiczny (zielona strefa) |

### Diagram działania:
```
┌─────────────────────────────────────────────────────────────┐
│  WŁĄCZENIE gdy:                                              │
│  ✓ Nadwyżka PV > 2 kW                                       │
│  ✓ Cena energii < p33 (zielona strefa - DYNAMICZNY próg!)   │
│  ✓ CWU nie grzeje (stan "off")                              │
│  ✓ Temp wody < 55°C                                         │
├─────────────────────────────────────────────────────────────┤
│  WYŁĄCZENIE gdy:                                             │
│  ✓ Nadwyżka PV < 0.5 kW  LUB  Temp wody > 55°C              │
│  ✓ Wymuszenie CWU jest włączone                             │
└─────────────────────────────────────────────────────────────┘
```

### Korzyści:
- ✅ Wykorzystanie darmowej energii z PV do grzania wody
- ✅ Redukcja eksportu do sieci (niskie ceny sprzedaży)
- ✅ Grzanie tylko w najtańszych godzinach (ochrona przed drogą energią)
- ✅ Automatyczna ochrona przed przegrzaniem (max 55°C)

---

## 4.6 Watchdog Aquarea

**Plik:** `config/automations_battery.yaml`
**ID:** `aquarea_watchdog_token`

### Opis funkcjonalności:
Automatyczne monitorowanie i naprawianie połączenia z integracją Aquarea Smart Cloud.

**Problem:** Integracja Aquarea traci połączenie z chmurą Panasonic (TOKEN_EXPIRED, Failed communication with adaptor).

**Rozwiązanie:** Watchdog co godzinę sprawdza stan i automatycznie przeładowuje integrację.

### Trigger:
- Co godzinę o :47 (`time_pattern: minutes: "47"`)

### Warunek:
- `water_heater.bodynek_nb_tank` = `unavailable`

### Akcje:
1. Powiadomienie o wykryciu problemu
2. Przeładowanie integracji Aquarea (`homeassistant.reload_config_entry`)
3. Czekanie 30 sekund
4. Sprawdzenie czy naprawione
5. Powiadomienie o wyniku (sukces/porażka)

### Parametry:
| Parametr | Wartość |
|----------|---------|
| Entry ID Aquarea | `01KCFK1ETFE13JR1S6C97PT0QY` |
| Częstotliwość | Co godzinę o :47 |
| Timeout naprawy | 30 sekund |

---

## 4.7 CWU harmonogram 13:02

**Plik:** `config/automations_battery.yaml`
**ID:** `cwu_scheduled_1300`

### Opis funkcjonalności:
Backup harmonogramu CWU z Aquarea Smart Cloud. Uruchamia grzanie CWU o 13:02 jeśli chmura Panasonic nie zadziałała.

**Problem:** Harmonogram CWU w Aquarea Cloud może nie zadziałać gdy:
- Serwery Panasonic mają problemy
- Token sesji wygasł
- Brak komunikacji z adapterem WiFi pompy

**Rozwiązanie:** HA uruchamia wymuszenie CWU o 13:02 (2 min po harmonogramie chmury) jako backup.

### Trigger:
- Godzina 13:02 (`time: "13:02:00"`)

### Warunki (wszystkie muszą być spełnione):
1. Integracja dostępna (`water_heater.bodynek_nb_tank` ≠ `unavailable`)
2. CWU nie grzeje aktualnie (`water_heater.bodynek_nb_tank` ≠ `heating`)
3. Temperatura wody < cel (dynamicznie z atrybutu `temperature`)

### Akcje:
1. Powiadomienie o uruchomieniu
2. Włączenie wymuszenia CWU (`switch.bodynek_nb_wymus_c_w_u`)
3. Czekanie aż temperatura osiągnie cel (timeout 2h)
4. Wyłączenie wymuszenia CWU
5. Powiadomienie o zakończeniu

### Logika działania:
```
13:00 → Harmonogram Panasonic Cloud (jeśli działa)
13:02 → Backup HA sprawdza:
        ├─ CWU już grzeje? → nie rób nic (chmura zadziałała)
        └─ CWU nie grzeje i temp < cel? → włącz wymuszenie
```

### Parametry:
| Parametr | Wartość |
|----------|---------|
| Godzina uruchomienia | 13:02 |
| Timeout grzania | 2 godziny |
| Warunek temperatury | < cel (dynamiczny) |

### Obliczenia czasu grzania:
- Zbiornik: 385 litrów
- Pompa: 9 kW (Panasonic T-CAP)
- ΔT: 20°C (35→55°C)
- Energia: 8.96 kWh
- Czas teoretyczny: ~1h (pełna moc) do ~2h (50% mocy CWU)

---

# 5. DASHBOARD

## 5.1 Instalacja dashboardu

**Plik:** `config/lovelace_huawei.yaml`

### Metoda 1: Przez interfejs (zalecana)
1. Otwórz Home Assistant
2. Przejdź do **Settings** → **Dashboards**
3. Kliknij **+ ADD DASHBOARD**
4. Wybierz **New dashboard from scratch**
5. Nazwa: "Huawei Solar PV"
6. Kliknij trzy kropki (⋮) → **Edit Dashboard**
7. Trzy kropki → **Raw configuration editor**
8. Skopiuj zawartość pliku `lovelace_huawei.yaml` i wklej
9. Zapisz (Save)

### Metoda 2: Tryb YAML (dla zaawansowanych)

Edytuj `configuration.yaml`:
```yaml
lovelace:
  mode: yaml
  dashboards:
    lovelace-huawei:
      mode: yaml
      title: Huawei Solar PV
      icon: mdi:solar-power
      show_in_sidebar: true
      filename: lovelace_huawei.yaml
```

## 5.2 Struktura dashboardu

**Sections view z 3 kolumnami** - ujednolicony układ: tytuł → gauge'y → encje

### SEKCJA 1 (lewa kolumna):

#### Zarządzanie baterią
- **Gauge'y:** Stan baterii (SOC %), Moc baterii (W)
- **Encje:** Decyzja, Target SOC, Ładowanie z sieci, Status, Temperatura, Tryb pracy

#### Pompa ciepła
- **Gauge'y:**
  - Temp. zasilania (°C) - zakres 15-65°C, kolory: niebieski (15-20), zielony (20-35), pomarańczowy (35-50), czerwony (50-65)
  - Temp. CWU (°C) - zakres 30-60°C + wyświetlanie temperatury docelowej pod gauge
- **Status:** Sezon grzewczy • CO • CWU (emoji indicators)
- **Encje:** Wymuś CWU (switch)

### SEKCJA 2 (środkowa kolumna):

#### Ceny RCE
- **Tabela:** Ceny godzinowe DZIŚ i JUTRO (06:00-21:00)
- **Encje:** Strefa taryfowa G12w, Cena obecna RCE, RCE najtańsze godziny

### SEKCJA 3 (prawa kolumna):

#### Pogoda i prognoza PV
- **Kafelek pogody:** weather.forecast_dom (hourly forecast)
- **Encje:** Prognoza PV dziś, Prognoza PV jutro

#### Produkcja energii
- **Gauge'y:** Produkcja PV (W), Nadwyżka PV (W)
- **Encje:** Produkcja PV w tej godzinie, Dzienna produkcja PV
- **Wykres:** Historia mocy 24h (zużycie domu, moc wyjściowa, bateria, sieć)

### Widok STATYSTYKI:
- Bateria - ostatni tydzień (średnia, min, max)
- Produkcja dzienna (suma, 30 dni)

## 5.3 Kafelek magazynowania baterii

### Opcja 1: Karta Entities (prosta)

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

### Opcja 2: Karta Markdown (ładniejsza)

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

### Przykładowe wyświetlanie:

**Gdy MAGAZYNUJ:**
```
🎯 Decyzja
TANIA godzina (8h: 0.25 zł) - top 3 najtańszych - MAGAZYNUJ

📊 Analiza
Potrzeba: 3h | Najtańsze: [6, 7, 8] | Teraz: 8h

💵 Najtańsze godziny
[6, 7, 8]
```

**Gdy SPRZEDAJ:**
```
🎯 Decyzja
DROGA godzina (14h: 0.55 zł vs najtańsza 0.25 zł) - SPRZEDAJ

📊 Analiza
Potrzeba: 3h | Najtańsze: [6, 7, 8] | Teraz: 14h

💵 Najtańsze godziny
[6, 7, 8]
```

## 5.4 Reload dashboardu

### Problem znaleziony:
Dashboard używał nieprawidłowej składni `layout: { type: grid, columns: 3 }` która NIE jest wspierana natywnie.

### Rozwiązanie:
Przepisano dashboard używając natywnych **grid cards** i **sections view**.

### Jak przeładować:

**Opcja 1: Przez UI (ZALECANE)**
1. Otwórz dashboard
2. Kliknij trzy kropki (⋮) w prawym górnym rogu
3. Wybierz **Odśwież** lub **Reload**
4. Wyczyść cache: CTRL+SHIFT+R

**Opcja 2: Przez SSH**
```bash
ssh marekbodynek@192.168.0.106
cd /Users/marekbodynek/home-assistant-huawei
git pull
```

**Opcja 3: Restart HA**
1. **Settings** → **System** → **Restart**
2. Poczekaj aż system się zrestartuje

---

# 6. DOSTĘP ZEWNĘTRZNY (CLOUDFLARE TUNNEL)

## 6.1 Quick Start (5 kroków)

### Krok 1: Utwórz tunnel w Cloudflare

1. Idź na: https://one.dash.cloudflare.com/
2. Menu: **Networks → Tunnels**
3. Kliknij **Create a tunnel**
4. Nazwa: `home-assistant-tunnel`
5. **SKOPIUJ TOKEN** (długi ciąg znaków po `--token`)

### Krok 2: Dodaj Public Hostname

1. W tunelu kliknij **Public Hostname** → **Add a public hostname**
2. Subdomain: `ha`
3. Domain: twoja domena (musi być już w Cloudflare)
4. Type: `HTTP`
5. URL: `homeassistant:8123`
6. Save

### Krok 3: Edytuj docker-compose.yml

```yaml
  cloudflared:
    container_name: cloudflared
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    command: tunnel --no-autoupdate run --token TWOJ_TOKEN_TUTAJ
    depends_on:
      - homeassistant
```

### Krok 4: Uruchom

```bash
ssh marekbodynek@192.168.0.106
cd ~/home-assistant-huawei
git pull
docker-compose down
docker-compose up -d
docker logs cloudflared
```

Poczekaj na: `INF Connection registered` (4 razy)

### Krok 5: Testuj

Otwórz: `https://ha.twojadomena.pl`

## 6.2 Pełna instrukcja konfiguracji

### Etap 1: Przygotowanie domeny

1. Zaloguj się do Cloudflare: https://dash.cloudflare.com/
2. Dodaj domenę:
   - Kliknij "Add a Site"
   - Wpisz nazwę domeny
   - Wybierz plan Free
   - Skopiuj nameservery
   - Zmień nameservery u rejestratora
   - Poczekaj na propagację (1-24h)

### Etap 2: Utwórz tunnel

1. Zero Trust Dashboard: https://one.dash.cloudflare.com/
2. Jeśli to pierwsze użycie:
   - "Get started" → nazwa zespołu (np. "Home")
   - Plan Free
3. Networks → Tunnels → Create a tunnel
4. Typ: Cloudflared
5. Nazwa: `home-assistant-tunnel`
6. **SKOPIUJ TOKEN**

### Etap 3: Public Hostname

1. Zakładka "Public Hostname"
2. "Add a public hostname"
3. Wypełnij:
   - Subdomain: `ha`
   - Domain: wybierz z listy
   - Type: `HTTP`
   - URL: `homeassistant:8123`
4. Save

URL: `https://ha.twojadomena.pl`

### Etap 4: docker-compose.yml

```yaml
services:
  homeassistant:
    container_name: homeassistant
    image: "ghcr.io/home-assistant/home-assistant:stable"
    volumes:
      - ./config:/config
      - /etc/localtime:/etc/localtime:ro
    restart: unless-stopped
    privileged: true
    ports:
      - "8123:8123"
    environment:
      - TZ=Europe/Warsaw

  cloudflared:
    container_name: cloudflared
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    command: tunnel --no-autoupdate run --token TU_WSTAW_TOKEN
    depends_on:
      - homeassistant
```

### Etap 5: Uruchomienie

```bash
cd ~/home-assistant-huawei
docker-compose down
docker-compose up -d
docker logs cloudflared
```

Sprawdź logi:
```
INF Connection registered connIndex=0
INF Connection registered connIndex=1
INF Connection registered connIndex=2
INF Connection registered connIndex=3
```

### Etap 6: Konfiguracja HA

1. Lokalnie: http://192.168.0.106:8123
2. Settings → System → Network
3. Home Assistant URL:
   - Internet: `https://ha.twojadomena.pl`
   - Local Network: `http://192.168.0.106:8123`

## 6.3 Darmowa subdomena (.trycloudflare.com)

### Zalety:
✅ Całkowicie darmowe
✅ Gotowe w 2 minuty
✅ Automatyczny HTTPS
✅ Nie wymaga konta Cloudflare

### Minusy:
⚠️ URL zmienia się po restarcie
⚠️ URL losowy (np. `https://abc-def-123.trycloudflare.com`)

### Instalacja:

**Krok 1: Uruchom**
```bash
cd ~/home-assistant-huawei
git pull
docker-compose down
docker-compose up -d
```

**Krok 2: Sprawdź URL**
```bash
docker logs cloudflared | grep trycloudflare.com
```

Szukaj:
```
INF |  https://abc-def-123.trycloudflare.com  |
```

**Krok 3: Konfiguruj HA**
1. Settings → System → Network
2. Internet: wklej URL z logów
3. Local: `http://192.168.0.106:8123`

## 6.4 Darmowa domena (.us.kg)

**100% darmowa domena na zawsze**

### Zalety:
✅ Darmowa na zawsze
✅ Odnawiana automatycznie
✅ Działa z Cloudflare
✅ Max 3 domeny na konto
✅ Akceptacja kilka minut-24h

### Etap 1: Rejestracja

1. Wejdź: https://nic.us.kg/
2. "Register a new domain"
3. Podaj email (Gmail, Outlook, Yahoo, iCloud, Hotmail, Zoho, Yandex)
4. Sprawdź email - kliknij link
5. Uzupełnij KYC (NIE MUSISZ uploadować dokumentów!)
6. Wybierz nazwę (np. `mojeha.us.kg`)
7. Poczekaj na akceptację

### Etap 2: Cloudflare

1. Zaloguj do Cloudflare: https://dash.cloudflare.com/
2. "Add a Site" → wpisz `mojeha.us.kg`
3. Plan Free
4. Skopiuj nameservery

### Etap 3: Nameservery

1. Zaloguj do nic.us.kg
2. Moje domeny → wybierz domenę
3. Nameservers → Custom
4. Wklej nameservery z Cloudflare
5. Poczekaj 5-30 min

### Etap 4: Tunnel

1. https://one.dash.cloudflare.com/
2. Networks → Tunnels → Create
3. Nazwa: `home-assistant-tunnel`
4. Skopiuj TOKEN

### Etap 5: Public Hostname

1. Zakładka "Public Hostname"
2. "Add a public hostname"
3. Subdomain: `ha` (lub puste)
4. Domain: wybierz `mojeha.us.kg`
5. Type: `HTTP`
6. URL: `homeassistant:8123`

URL: `https://ha.mojeha.us.kg`

### Etap 6: docker-compose.yml

Zamień token w:
```yaml
command: tunnel --no-autoupdate run --token TUTAJ_TOKEN
```

### Etap 7: Uruchom

```bash
docker-compose down
docker-compose up -d
docker logs cloudflared
```

### ✅ GOTOWE!

Otwórz `https://ha.mojeha.us.kg` z dowolnego miejsca!

### Alternatywa: EU.ORG

**Darmowa domena `.eu.org`**

1. https://nic.eu.org/
2. Create Account
3. Wypełnij formularz
4. Poczekaj 1-7 dni (wolniej niż us.kg)
5. Dalej identycznie jak us.kg

**Koszt:** 0 zł/rok (us.kg lub eu.org) + 0 zł Cloudflare = **0 zł łącznie**

## 6.5 SSH przez Cloudflare Tunnel (automatyczny deployment)

**Cel:** Automatyczny dostęp SSH do serwera przez Cloudflare Tunnel, umożliwiający Claude Code wykonywanie `git pull` i wdrażanie zmian bez ręcznej interwencji.

### Po co to?

✅ Claude Code może automatycznie wdrażać zmiany na serwerze
✅ Nie trzeba ręcznie logować się przez TeamViewer
✅ Działa z dowolnego miejsca na świecie
✅ Zabezpieczone przez Cloudflare Access (opcjonalnie)

### Konfiguracja (jednorazowa)

#### Etap 1: Włącz Remote Login na serwerze

Na serwerze (Mac mini):
1. **System Preferences** → **Sharing**
2. Włącz **Remote Login**
3. Dodaj użytkownika `marekbodynek` do listy

#### Etap 2: Dodaj SSH jako Published Application Route

1. Idź na: https://one.dash.cloudflare.com/
2. **Networks** → **Tunnels**
3. Wybierz swój tunnel (np. `n8n-tunnel`)
4. Kliknij **Configure**
5. Zakładka **Public Hostname**
6. Kliknij **+ Add a public hostname**
7. Wypełnij:
   - **Subdomain**: `ssh`
   - **Domain**: `bodino.us.kg` (twoja domena)
   - **Type**: `SSH`
   - **URL**: `localhost:22`
8. Kliknij **Save**

#### Etap 3: Zrestartuj cloudflared na serwerze

Przez TeamViewer lub lokalnie na serwerze:
```bash
sudo launchctl stop com.cloudflare.cloudflared
sudo launchctl start com.cloudflare.cloudflared
```

#### Etap 4: Skonfiguruj SSH config lokalnie (na Macu z którym pracujesz)

Edytuj `~/.ssh/config`:
```bash
nano ~/.ssh/config
```

Dodaj:
```
Host ssh.bodino.us.kg
  ProxyCommand /opt/homebrew/bin/cloudflared access ssh --hostname %h
  User marekbodynek
  StrictHostKeyChecking no
```

**Uwaga:** Ścieżka do `cloudflared` może być inna, sprawdź przez:
```bash
which cloudflared
```

#### Etap 5: Testuj SSH

```bash
ssh ssh.bodino.us.kg "echo '✅ SSH działa!' && hostname && whoami"
```

Powinno zwrócić:
```
✅ SSH działa!
Mac-mini-Marek.local
marekbodynek
```

### Jak używać

#### Automatyczny deployment przez Claude Code

Claude Code teraz może automatycznie:
1. Połączyć się przez SSH
2. Wykonać `git pull` w katalogu `~/home-assistant-huawei`
3. Zrestartować Home Assistant

Przykład komendy:
```bash
ssh ssh.bodino.us.kg "cd ~/home-assistant-huawei && git pull"
```

#### Ręczny deployment

```bash
# Połącz się z serwerem
ssh ssh.bodino.us.kg

# Wejdź do katalogu
cd ~/home-assistant-huawei

# Pobierz najnowsze zmiany
git pull

# Sprawdź status
git status

# Wyjdź
exit
```

### Troubleshooting

#### Problem: "websocket: bad handshake"

**Rozwiązanie:**
1. Sprawdź czy Remote Login jest włączony na serwerze
2. Zrestartuj cloudflared na serwerze
3. Sprawdź czy ssh.bodino.us.kg istnieje w Published Application Routes

#### Problem: "Connection refused"

**Rozwiązanie:**
1. Sprawdź czy cloudflared działa na serwerze:
   ```bash
   ps aux | grep cloudflared
   ```
2. Sprawdź logi cloudflared:
   ```bash
   tail -f /var/log/cloudflared.log
   ```

#### Problem: "No such file or directory: cloudflared"

**Rozwiązanie:**
Zainstaluj cloudflared lokalnie:
```bash
brew install cloudflare/cloudflare/cloudflared
```

#### Problem: DNS error "An A, AAAA, or CNAME record with that host already exists"

**Rozwiązanie:**
1. Idź do Cloudflare DNS: https://dash.cloudflare.com/
2. Znajdź rekord `ssh.bodino.us.kg` (typ CNAME)
3. Usuń go
4. Spróbuj ponownie dodać SSH jako Published Application Route

### Bezpieczeństwo (opcjonalnie)

#### Cloudflare Access Policy

Możesz dodatkowo zabezpieczyć SSH przez Cloudflare Access:

1. **Access** → **Applications** → **Add an application**
2. Application type: **Self-hosted**
3. Application name: `SSH Server`
4. Subdomain: `ssh`, Domain: `bodino.us.kg`
5. **Next**
6. **Add a policy**:
   - Policy name: `Allow my email`
   - Action: `Allow`
   - Include: `Emails` → `marek.bodynek@gmail.com`
7. **Next** → **Add application**

Teraz każde połączenie SSH będzie wymagało autoryzacji przez email.

---

# 7. BEZPIECZEŃSTWO I OPTYMALIZACJA

**Raport z 2025-11-16**

## 7.1 Poprawki bezpieczeństwa

### ✅ 1. KRYTYCZNE: Limit SOC baterii (80%)
**Problem:** Max SOC = 95% (przekracza limit Huawei 80%)
**Ryzyko:** Uszkodzenie baterii, utrata gwarancji
**Rozwiązanie:** Zmieniono na 80%
**Plik:** `config/input_numbers.yaml:6`

```yaml
# PRZED
max: 95  # ❌ NIEBEZPIECZNE!

# PO
max: 80  # ✅ Zgodne z Huawei Luna (20-80%)
```

### ✅ 2. KRYTYCZNE: Błąd zmiennej `month`
**Problem:** Brak zmiennej `month` w funkcji
**Ryzyko:** Crash algorytmu
**Rozwiązanie:** `month` → `data['month']`
**Plik:** `battery_algorithm.py:578`

### ✅ 3. WYSOKIE: Dynamiczny device_id
**Problem:** Hardcoded device_id
**Ryzyko:** Kod przestanie działać przy wymianie
**Rozwiązanie:** Pobieranie z atrybutów encji + fallback
**Plik:** `battery_algorithm.py:789-797`

### ✅ 4. ŚREDNIE: Watchdog algorytmu
**Problem:** Brak fail-safe
**Ryzyko:** Bateria może się rozładować w L1 (drogo!)
**Rozwiązanie:** 2 watchdogi:
- Zdrowie algorytmu (co 30 min)
- Zablokowany SOC (co 1h)

### ✅ 5. KRYTYCZNE: Monitoring temperatury 🔥
**Problem:** BRAK zabezpieczeń termicznych!
**Ryzyko:** POŻAR/WYBUCH baterii litowo-jonowej

**Rozwiązanie:** 5 automatyzacji:

**Ostrzeżenie (>40°C):**
- Alert podwyższonej temperatury
- Monitoring 30 min

**STOP ŁADOWANIA (>43°C):**
- Wyłączenie ładowania z sieci
- Tryb bezpieczny
- Instrukcje

**ALARM POŻAROWY (>45°C):**
- Alarm krytyczny
- Ewakuacja
- Serwis
- NIE GASIĆ WODĄ!

**Zamarzanie (<0°C):**
- Blokada ładowania
- Ogrzać pomieszczenie

**Powrót do normy (<38°C przez 15 min):**
- Potwierdzenie
- Usunięcie alertów

**Bezpieczne zakresy:**
- 🟢 Optymalna: 15-25°C
- 🟡 Dopuszczalna: 5-40°C
- 🟠 Ostrzeżenie: >40°C
- 🔴 STOP: >43°C
- ⚫ ALARM: >45°C
- ❄️ Mróz: <0°C

## 7.2 Optymalizacje kosztowe

### ✅ 6. Dynamiczny próg arbitrażu

**Przed:** 0.90 zł/kWh (stały)
**Po:**
- Sezon grzewczy: 0.90 zł/kWh
- Poza sezonem: 0.88 zł/kWh

**Korzyści:**
- +2-4 okazje/miesiąc (IV-X)
- Szacunkowy zysk: **+15-30 zł/mc**

### ✅ 7. Optymalizacja Forecast Solar API

**Przed:** scan_interval 3600s = 72 zapytania/dobę
**Po:** scan_interval 7200s = 36 zapytań/dobę

**Korzyści:**
- Redukcja -50%
- Ochrona przed rate limiting
- Dane nadal świeże (+ ręczne update)

## 7.3 Rekomendacje dodatkowe

### Średni priorytet:

**1. Backup bazy danych**
- Auto backup `home-assistant_v2.db` (co tydzień)
- Google Drive Backup addon

**2. Monitoring degradacji baterii**
- Licznik cykli baterii
- Aktualizacja kosztu cyklu (obecnie 0.33 zł/kWh)

**3. Predykcja cen RCE**
- Sensor średniej RCE (7 dni)
- Optymalizacja arbitrażu na podstawie trendu

### Niski priorytet:

**4. Optymalizacja trusted_proxies**
- Zawężenie IP Cloudflare
- Dodatkowa autentykacja (2FA)

**5. Dynamiczny próg sezonu**
- Zamiast stałego 12°C
- Dostosowanie na podstawie zużycia

---

# 8. ROZWIĄZYWANIE PROBLEMÓW

## 8.1 Problemy z algorytmem

### Problem: Sensory `unknown` / `unavailable`

**Przyczyna:** Brak danych z integracji

**Rozwiązanie:**
1. Sprawdź: Settings → Devices & Services
2. Logi: Settings → System → Logs
3. Refresh: Developer Tools → States → refresh
4. Restart: Settings → System → Restart

### Problem: Automatyzacje nie wykonują się

**Przyczyna:** Błąd w Python script

**Rozwiązanie:**
```bash
docker exec homeassistant tail -100 /config/home-assistant.log | grep python_script
ls -la /Users/marekbodynek/home-assistant-huawei/config/python_scripts/
```

### Problem: Bateria nie ładuje w nocy

**Przyczyna:** SOC > Target SOC

**Rozwiązanie:**
1. Sprawdź `input_number.battery_target_soc`
2. Sprawdź prognozę jutro (>30 kWh = Target 20%)
3. Ręcznie: `python_script.calculate_daily_strategy`

### Problem: RCE zawsze 0.45 (default)

**Przyczyna:** Integracja Pstryk nie pobiera cen

**Rozwiązanie:**
1. Sprawdź integrację Pstryk
2. Update: `homeassistant.update_entity` → `sensor.pstryk_current_sell_price`
3. Sprawdź API: https://github.com/balgerion/ha_Pstryk/issues

### Problem: Pstryk rate limited

**Komunikat w logach:**
```
Endpoint 'pricing' is rate limited. Will retry after 3600 seconds
```

**Przyczyna:** Przekroczony limit zapytań API Pstryk

**Rozwiązanie:**
- Poczekaj 1h
- API automatycznie się odblokuje
- Algorytm używa ostatnich pobranych cen

## 8.2 Problemy z integracjami

### Problem: Panasonic nie działa

**Przyczyna:** Bug w integracji aioaquarea 0.7.2

**Rozwiązanie (tymczasowe):**
- Temperatura z Met.no (wystarczy!)
- Gdy naprawią - automatycznie przełączy na PC

### Problem: Forecast.Solar brak danych

**Rozwiązanie:**
```bash
# Sprawdź konfigurację
Developer Tools → Services
Service: forecast_solar.update
Target: all

# Sprawdź logi
Settings → System → Logs → filtruj "forecast"
```

## 8.3 Problemy z dashboardem

### Problem: Stary układ (masonry zamiast grid)

**Rozwiązanie:**
1. CTRL+SHIFT+R (wyczyść cache)
2. Dashboard → ⋮ → Odśwież
3. Sprawdź git: `git log` (commit "Przepisano dashboard")
4. Restart HA

### Problem: Karty nie wyświetlają się

**Rozwiązanie:**
1. Sprawdź: Developer Tools → States
2. Czy encje istnieją?
3. Czy mają wartości (nie `unknown`)?
4. Edit Dashboard → Raw config → sprawdź błędy YAML

## 8.4 Problemy z Cloudflare Tunnel

### Problem: Tunnel nie działa

```bash
# Sprawdź logi
docker logs cloudflared -f

# Błąd autoryzacji = zły token
# Wygeneruj nowy w Cloudflare Dashboard
```

### Problem: 502 Bad Gateway

```bash
# Sprawdź HA
docker logs homeassistant -f

# Sprawdź sieć
docker network inspect home-assistant-huawei_default
```

### Problem: Nie mogę się połączyć z zewnątrz

1. Status "Healthy" w Cloudflare Dashboard?
2. Public Hostname prawidłowo skonfigurowany?
3. Domena poprawnie w Cloudflare?
4. DNS: `nslookup ha.twojadomena.pl`

### Problem: Nameservery nie propagują się

```bash
# Sprawdź DNS
nslookup mojeha.us.kg

# Cloudflare IP = działa!
# Nie = poczekaj 30 min
```

---

# 9. ZARZĄDZANIE SYSTEMEM

## 9.1 Kontrola Docker

```bash
# Status kontenera
cd ~/home-assistant-huawei
docker-compose ps

# Logi Home Assistant
docker-compose logs -f homeassistant

# Logi Cloudflared
docker logs cloudflared -f

# Restart Home Assistant
docker-compose restart homeassistant

# Restart wszystkich
docker-compose restart

# Stop
docker-compose down

# Start
docker-compose up -d
```

## 9.2 Aktualizacja Home Assistant

```bash
cd ~/home-assistant-huawei
docker-compose pull
docker-compose up -d
```

## 9.3 Backup

### Backup config

```bash
# Backup całego folderu
cd ~
tar -czf ha-backup-$(date +%Y%m%d).tar.gz home-assistant-huawei/config

# Lub kopiuj
cp -r ~/home-assistant-huawei/config ~/backups/config-$(date +%Y%m%d)
```

### Git backup

```bash
cd /Users/marekbodynek/home-assistant-huawei
git add -A
git commit -m "Backup $(date +%Y-%m-%d)"
git push origin main
```

### Backup z HA

**Settings → System → Backups → CREATE BACKUP**

---

# 10. CHECKLISTY

## 10.1 Pierwsza konfiguracja

- [ ] Uruchom Home Assistant (http://localhost:8123)
- [ ] Utwórz konto administratora
- [ ] Zainstaluj HACS
- [ ] Zainstaluj integrację Huawei Solar przez HACS
- [ ] Dodaj inverter (IP, port 502, slave ID 1)
- [ ] Sprawdź czy encje baterii są widoczne
- [ ] Zainstaluj integrację Pstryk (klucz API)
- [ ] Zainstaluj integrację Forecast.Solar
- [ ] Sprawdź czy sensory mają wartości (nie `unknown`)
- [ ] (Opcjonalnie) Zainstaluj integrację Panasonic

## 10.2 Konfiguracja algorytmu

- [ ] Template sensors mają wartości
- [ ] Python scripts załadowane
- [ ] Automatyzacje włączone (Settings → Automations)
- [ ] Ręcznie wywołaj `calculate_daily_strategy`
- [ ] Ręcznie wywołaj `battery_algorithm`
- [ ] Dashboard pokazuje karty z cenami i prognozami
- [ ] Logbook pokazuje decyzje algorytmu
- [ ] Watchdog działa (sprawdź za 2h)
- [ ] Monitoring temperatury działa

## 10.3 Weryfikacja zmian

**Przed uruchomieniem:**

1. **Backup:**
```bash
cd /Users/marekbodynek/home-assistant-huawei
git add -A
git commit -m "Backup before updates"
git push
```

2. **Check config:**
- Configuration → Server Controls → Check Configuration

3. **Restart:**
- Configuration → Server Controls → Restart

4. **Monitor:**
```bash
tail -f /Users/marekbodynek/home-assistant-huawei/config/home-assistant.log
```

---


---

# 11. WDROŻENIA I OPTYMALIZACJE

## 11.1 FAZA 1: Optymalizacja ładowania baterii (2025-11-17)

**Szacowane oszczędności:** 120-240 zł/mc (1,440-2,880 zł/rok)
**Czas wdrożenia:** ~5 minut
**Status:** ✅ Wdrożone

### Podsumowanie zmian

#### 1. Nocne ładowanie: 70% → 80% (+100-200 zł/mc)
- **Przed:** Ładowanie baterii do 70% w nocy (taryfa L2)
- **Po:** Ładowanie baterii do 80% w nocy (maksymalny limit Huawei)
- **Korzyść:** Więcej energii taniej (0.72 zł/kWh) zamiast droższej L1 (1.11 zł/kWh)
- **Implementacja:**
  - Zmieniono domyślny `target_soc` z 70% → 80% w `battery_algorithm.py:169`
  - Ustawiono `input_number.battery_target_soc` na 80%

#### 2. Popołudniowe ładowanie: Zawsze → Tylko <5 kWh (+20-40 zł/mc)
- **Przed:** Ładowanie w oknie L2 13-15h gdy prognoza < 20-35 kWh (za liberalne)
- **Po:** Ładowanie TYLKO gdy prognoza PV < 5 kWh (bardzo pochmurno)
- **Korzyść:** Oszczędność energii z sieci w dni z wystarczającą produkcją PV
- **Implementacja:** Uproszczona logika w `battery_algorithm.py:706-717`

#### 3. Próg arbitrażu: Już dynamiczny ✅
- **Status:** Już zoptymalizowane (0.90 zł w sezonie grzewczym, 0.88 zł poza)
- **Brak zmian:** Algorytm już używa dynamicznego progu od poprzednich wersji

### Monitorowanie efektów

**Kluczowe metryki do obserwacji:**
1. **Średni SOC rano (06:00):** Powinien wzrosnąć z ~70% do ~80%
2. **Zakupy energii w L1:** Powinny spaść o ~30-50%
3. **Liczba ładowań popołudniowych:** Spadek z ~15/mc do ~3/mc
4. **Roczne oszczędności:** Docelowo 1,440-2,880 zł/rok

### Bezpieczeństwo baterii
- ✅ Limit 80% SOC przestrzegany (maksymalny dozwolony przez Huawei)
- ✅ Zabezpieczenia termiczne bez zmian (5-40°C)
- ✅ Cykle ładowania bez zmian (~250 cykli/rok)

### Cofnięcie zmian
Jeśli chcesz wrócić do poprzedniej wersji:
```bash
# Ustaw Target SOC z powrotem na 70%
curl -X POST http://localhost:8123/api/services/input_number/set_value \
  -d '{"entity_id": "input_number.battery_target_soc", "value": 70}'
```

### Następne kroki: FAZA 2 (Grudzień 2024)

Po zebraniu 4 tygodni danych (do 10 grudnia 2024):
- **Model ML predykcji zużycia:** +150-300 zł/mc
- **Optymalizacja godzin ładowania:** +80-120 zł/mc
- **Prognozowanie cen RCE:** +100-200 zł/mc

**Łączne oszczędności wszystkie fazy:** 450-860 zł/mc (~5,400-10,300 zł/rok)

---

## 11.2 Fix: Target SOC Charging (2025-11-17)

**Problem:** System nie zatrzymywał ładowania przy osiągnięciu Target SOC + bug blokował ładowanie w dni powszednie

### Rozwiązane problemy

#### Problem 1: Brak zatrzymania przy Target SOC
- **Przyczyna:** Algorytm ustawiał `charge_soc_limit`, ale polegał na inwenterze Huawei
- **Rozwiązanie:** Dodano explicite zatrzymanie ładowania gdy SOC >= Target SOC
- **Efekt:**
  - ✅ `switch.akumulatory_ladowanie_z_sieci` wyłącza się przy Target SOC
  - ✅ `number.akumulatory_maksymalna_moc_ladowania` ustawia się na 0W
  - ✅ Dashboard pokazuje: "✅ Target SOC osiągnięty"

#### Problem 2: Bug warunku L2 blokował ładowanie
- **Przyczyna:** Warunek `tariff == 'L2' and soc >= 40` działał też w dni powszednie 22:00-05:59
- **Rozwiązanie:** Dodano sprawdzenie `binary_sensor.dzien_roboczy`
- **Efekt:**
  - ✅ Ładowanie w dni powszednie działa poprawnie
  - ✅ Weekend/święta - strategia oszczędzania baterii zachowana

### Weryfikacja
```bash
# Sprawdź status decyzji
curl -s -H "Authorization: Bearer TOKEN" \
  http://localhost:8123/api/states/input_text.battery_decision_reason

# Sprawdź sensor dzień roboczy
curl -s -H "Authorization: Bearer TOKEN" \
  http://localhost:8123/api/states/binary_sensor.dzien_roboczy
```

---

## 11.3 Fix: Parametry baterii w L1 (2025-11-17)

**Problem:** Po zmianie strefy L2→L1 status zmieniał się poprawnie, ale parametry baterii nie były aktualizowane

### Rozwiązanie
- Dodano obsługę `max_charge_power` w funkcji `set_huawei_mode()`
- Poprawiono tryb dla `discharge_to_grid`

### Oczekiwane wartości (po 15:00, SOC ≥ 80%, nadwyżka PV)

| Parametr | Wartość |
|----------|---------|
| Status decyzji | "SOC 80%, nadwyżka PV - sprzedaj" |
| Tryb pracy | `maximise_self_consumption` |
| Max moc ładowania | `0` W |
| Max moc rozładowania | `5000` W |
| Ładowanie z sieci | `off` |

### Weryfikacja
```bash
# Sprawdź parametry baterii
curl -s -H "Authorization: Bearer TOKEN" \
  http://localhost:8123/api/states/number.akumulatory_maksymalna_moc_ladowania

curl -s -H "Authorization: Bearer TOKEN" \
  http://localhost:8123/api/states/number.akumulatory_maksymalna_moc_rozladowania
```

---

## 11.4 System logowania błędów + Fix temperatury (2025-11-18)

**Status:** ✅ Wdrożone (commit `404569e`, `d3824dd`)
**Czas wdrożenia:** ~15 minut

### Podsumowanie zmian

#### 1. System logowania błędów (📊 Monitoring w czasie rzeczywistym)

**Problem:** Brak scentralizowanego systemu śledzenia błędów i ostrzeżeń

**Rozwiązanie:** Utworzono kompleksowy system logowania i monitoringu:

##### Nowe pliki:

**A. config/logger.yaml** - Scentralizowane logowanie
```yaml
default: warning

logs:
  # Algorytm baterii
  homeassistant.components.python_script: info
  homeassistant.helpers.template: warning

  # Integracje
  custom_components.huawei_solar: warning
  custom_components.pstryk: warning
  homeassistant.components.forecast_solar: warning
  custom_components.panasonic_cc: warning

  # Automations i sensory
  homeassistant.components.automation: info
  homeassistant.components.template: warning
```

**B. config/automations_errors.yaml** - Automatyczne powiadomienia
- **[BŁĄD] Krytyczny błąd systemu** - Natychmiastowe powiadomienie gdy algorytm zgłasza błąd
- **[BŁĄD] Integracja offline** - Alert gdy Huawei Solar, Pstryk lub Forecast.Solar nie działa
- **[INFO] Temperatura baterii - fałszywy alarm** - Logowanie gdy JV* sensory (PV optimizers) pokazują nierealne temperatury
- **[RAPORT] Dzienny raport błędów (22:00)** - Podsumowanie błędów z całego dnia

##### Nowe sensory błędów (config/template_sensors.yaml):

**sensor.bledy_algorytmu_licznik**
- Licznik błędów algorytmu (resetowany codziennie)
- Automatycznie zwiększa się gdy `input_text.battery_decision_reason` zawiera "BŁĄD"

**sensor.system_ostatni_blad**
- Pokazuje ostatni błąd systemu
- Agreguje błędy z algorytmu, Huawei Solar, Pstryk
- Atrybuty: `all_errors` (lista wszystkich aktywnych błędów)

**binary_sensor.system_blad_krytyczny**
- Stan: ON gdy jest krytyczny błąd
- Sprawdza słowa kluczowe: "BŁĄD", "🚨", "ZATRZYMANO"
- device_class: problem (integracja z Alexa/Google Home)

**binary_sensor.integracje_status**
- Stan: ON gdy wszystkie integracje działają
- Monitoruje: Huawei Solar, Pstryk RCE, Forecast.Solar
- Atrybuty pokazują status każdej integracji oddzielnie
- device_class: connectivity

##### Korzyści:
- ✅ Natychmiastowe powiadomienia o błędach krytycznych
- ✅ Dzienny raport błędów (monitoring trendów)
- ✅ Monitoring statusu integracji w czasie rzeczywistym
- ✅ Historia błędów (długość 30 dni w recorder)
- ✅ Lepsza diagnostyka problemów

#### 2. Fix sensora temperatury baterii (🌡️ Fallback logic)

**Problem:**
- `binary_sensor.bateria_bezpieczna_temperatura` pokazywał OFF (niebezpieczna temperatura)
- Powód: sensor używa temp. z optymalizatorów PV (JV*) na dachu, NIE baterii
- JV* sensory pokazują 3-5°C (temperatura dachu), podczas gdy bateria w garażu ma ~31.6°C (FusionSolar)
- Zakres bezpieczny: 5-40°C
- Rezultat: algorytm blokował ładowanie baterii z powodu fałszywego alarmu

**Rozwiązanie:**
Dodano logikę fallback w `config/template_sensors.yaml:269-313`:

```yaml
- binary_sensor:
    - name: "Bateria - bezpieczna temperatura"
      unique_id: battery_temperature_safe
      # Fallback: jeśli JV* pokazuje <5°C (nierealne dla baterii w garażu 15°C)
      # użyj bezpiecznej wartości 25°C
      state: >
        {% set measured_temp = states('sensor.bateria_temperatura_maksymalna') | float(-999) %}
        {% if measured_temp < 5 %}
          {% set temp = 25 %}
        {% else %}
          {% set temp = measured_temp %}
        {% endif %}
        {{ temp >= 5 and temp <= 40 }}

      attributes:
        measured_temp: "{{ states('sensor.bateria_temperatura_maksymalna') }}°C"
        effective_temp: >
          {% set measured = states('sensor.bateria_temperatura_maksymalna') | float(-999) %}
          {% if measured < 5 %}
            25°C (fallback - JV* pokazuje {{ measured }}°C)
          {% else %}
            {{ measured }}°C (JV*)
          {% endif %}
        safe_range: "5-40°C"
        note: "TYMCZASOWE: Gdy JV* (PV optimizers) <5°C, użyj 25°C. Wieczorem: FusionSolar API."
```

##### Nowe atrybuty:
- **measured_temp:** Rzeczywisty odczyt z JV* (np. 3.5°C)
- **effective_temp:** Temperatura używana do sprawdzenia zakresu (25°C fallback lub JV*)
- **note:** Wyjaśnienie tymczasowego rozwiązania

##### Rezultat:
- ✅ Sensor: **ON** (temperatura bezpieczna)
- ✅ Ładowanie baterii: **ODBLOKOWANE**
- ✅ Gdy JV* <5°C → fallback 25°C (bezpieczna wartość dla baterii w garażu 15°C)
- ✅ Gdy JV* ≥5°C → używa wartości z JV*
- ✅ Zachowany zakres 5-40°C (zgodnie z wymaganiami użytkownika)

##### TODO (wieczorem):
Integracja FusionSolar Cloud API dla prawdziwej temperatury baterii (31.6°C):
- RESTful sensor pobierający "Internal temperature" z Huawei FusionSolar Cloud
- Wymaga API key + konfiguracja (~30 min)
- Po wdrożeniu: usunięcie fallback logic, użycie prawdziwej temp.

### Weryfikacja wdrożenia

#### Sprawdzenie sensora temperatury:
```bash
curl -s -H "Authorization: Bearer TOKEN" \
  https://ha.bodino.us.kg/api/states/binary_sensor.bateria_bezpieczna_temperatura \
  | python3 -m json.tool
```

**Oczekiwany wynik (gdy JV* <5°C - sensor OFF):**
```json
{
  "state": "off",
  "attributes": {
    "current_temp": "3.5°C (JV* - optymalizatory PV)",
    "safe_range": "5-40°C",
    "note": "Sensor OFF - JV* pokazuje temp. dachu (<5°C). Wieczorem: FusionSolar Cloud API",
    "status": "NIEBEZPIECZNE (<5°C)"
  }
}
```

#### Sprawdzenie statusu integracji:
```bash
curl -s -H "Authorization: Bearer TOKEN" \
  https://ha.bodino.us.kg/api/states/binary_sensor.integracje_status \
  | python3 -c "import sys, json; data=json.load(sys.stdin); \
    print(f\"Status: {data['state']}\"); \
    print(f\"Huawei: {data['attributes']['huawei_solar']}\"); \
    print(f\"Pstryk: {data['attributes']['pstryk_rce']}\"); \
    print(f\"Forecast: {data['attributes']['forecast_solar']}\")"
```

**Oczekiwany wynik:**
```
Status: on
Huawei: OK
Pstryk: OK
Forecast: OK
```

### Pliki zmodyfikowane

| Plik | Zmiany |
|------|--------|
| `config/configuration.yaml` | Dodano `logger: !include logger.yaml`<br/>Dodano `automation errors: !include automations_errors.yaml` |
| `config/logger.yaml` | **NOWY** - Scentralizowane logowanie |
| `config/automations_errors.yaml` | **NOWY** - Automatyzacje błędów i powiadomień |
| `config/template_sensors.yaml` | Dodano sensory błędów (linie 372-442)<br/>Zmieniono sensor temperatury baterii (linie 269-313) |

### Commits

**Commit 1: `404569e`** - System logowania błędów
```
📊 System logowania błędów + fix temperatury baterii

Zmiany:
- Utworzono config/logger.yaml (scentralizowane logowanie)
- Utworzono config/automations_errors.yaml (automatyczne powiadomienia)
- Dodano sensory błędów do template_sensors.yaml
- Zaktualizowano binary_sensor.bateria_bezpieczna_temperatura
- Zaktualizowano configuration.yaml
```

**Commit 2: `d3824dd`** - ~~Fix sensora temperatury~~ (ZREZYGNOWANO)
```
UWAGA: Ten commit zawierał fallback logic (gdy JV* <5°C → użyj 25°C)
Użytkownik odrzucił to rozwiązanie: "nie uzywaj fallbcku"
Fallback został usunięty w następnym commicie.
```

### Bezpieczeństwo

- ✅ Monitoring błędów nie wpływa na wydajność systemu
- ⚠️ Sensor temperatury OFF - JV* (PV optimizers) pokazują temp. dachu <5°C
- ⚠️ Ładowanie baterii ZABLOKOWANE do czasu integracji FusionSolar Cloud API
- ✅ Zachowany zakres 5-40°C (zgodnie z specyfikacją Huawei)
- ✅ Automatyzacje błędów nie blokują normalnej pracy algorytmu
- ✅ Historia błędów przechowywana przez 30 dni (recorder)

### Następne kroki

**Wieczorem (2025-11-18) - WYMAGANE:**
- ✅ Usunięto fallback logic (zgodnie z instrukcją użytkownika)
- 🔴 **KRYTYCZNE**: Integracja FusionSolar Cloud API
  - Sensor temperatury OFF (JV* <5°C)
  - Ładowanie baterii zablokowane
  - Wymagane: RESTful sensor do FusionSolar Cloud
  - Prawdziwa temp. baterii: 31.6°C (z FusionSolar)
- Test z prawdziwymi danymi przez 24h

**Opcjonalnie (przyszłość):**
- Dashboard z wykresami błędów
- Export błędów do Google Sheets (analiza trendów)
- Integracja z Telegram/Pushover (powiadomienia push)

---

## 11.5 Event Log System + Telegram Fix (2025-11-23)

**Status:** ✅ Wdrożone
**Czas wdrożenia:** ~30 minut

### Podsumowanie zmian

#### 1. Event Log System (📋 Historia zdarzeń)

**Problem:** Brak historii zdarzeń algorytmu baterii

**Rozwiązanie:** Wdrożono system Event Log z 5 slotami:

##### Nowe encje:
- `input_text.event_log_1` do `input_text.event_log_5` - Sloty na zdarzenia (JSON)
- `sensor.event_log_ostatnie_zdarzenie` - Parsowane ostatnie zdarzenie
- `sensor.event_log_historia` - Statystyki historii (liczba zdarzeń, błędów, ostrzeżeń)

##### Format zdarzenia (JSON):
```json
{
  "ts": "2025-11-23T18:30:00",
  "lvl": "INFO|WARNING|ERROR",
  "cat": "BATTERY|ALGORITHM|SYSTEM",
  "msg": "Opis zdarzenia"
}
```

##### Automatyzacje Event Log:
- `[EVENT LOG] Telegram alert - błąd` - Wysyła Telegram przy ERROR
- `[EVENT LOG] Telegram alert - ostrzeżenie` - Wysyła Telegram przy WARNING
- `[EVENT LOG] System log - ważne zdarzenia` - Loguje ERROR/WARNING do system_log
- `[EVENT LOG] Reset dzienny` - Reset slotów o północy

#### 2. Telegram dla błędów krytycznych (📱 Powiadomienia)

**Problem:** Automatyzacja `[BŁĄD] Krytyczny błąd systemu` używała tylko `persistent_notification` - nie wysyłała na Telegram

**Rozwiązanie:** Dodano `notify.telegram` do automatyzacji:

##### Zmodyfikowane automatyzacje:
- `[BŁĄD] Krytyczny błąd systemu` - Teraz wysyła Telegram + persistent_notification
- `[OSTRZEŻENIE] Integracja offline` - Teraz wysyła Telegram + persistent_notification

##### Przykład powiadomienia Telegram:
```
🚨 BŁĄD KRYTYCZNY SYSTEMU

**Wykryto błąd krytyczny!**

L2 ładowanie - SOC 48% < 80%

**Czas:** 2025-11-23 19:30:00
**SOC:** 48%
**Temp:** 13.7°C
```

#### 3. Fix algorytmu baterii (🔧 Python scripts)

**Problem:** Algorytm crashował z błędami:
- "Not allowed to import json"
- "'NoneType' object is not callable" (datetime, range, isinstance)

**Rozwiązanie:** Dostosowano kod do ograniczeń `python_scripts` w HA:
- Usunięto `import json` - tworzenie JSON ręcznie przez konkatenację stringów
- Usunięto `datetime.datetime.now()` - użycie `sensor.time` i `sensor.date`
- Usunięto `range()` - hardcoded odczyt slotów
- Usunięto `isinstance()` - użycie try/except

### Pliki zmodyfikowane

| Plik | Zmiany |
|------|--------|
| `config/automations_errors.yaml` | Dodano Telegram do błędów krytycznych i integracji offline |
| `config/python_scripts/battery_algorithm.py` | Fix dla python_scripts limitations + Event Log integration |
| `config/template_sensors.yaml` | Dodano sensory Event Log |
| `config/input_text.yaml` | Dodano sloty event_log_1 do event_log_5 |
| `config/lovelace_huawei.yaml` | Dodano kartę Event Log na dashboard |

### Weryfikacja

```bash
# Sprawdź Event Log
curl -s -H "Authorization: Bearer TOKEN" \
  https://ha.bodino.us.kg/api/states/sensor.event_log_ostatnie_zdarzenie

# Sprawdź automatyzację błędów
curl -s -H "Authorization: Bearer TOKEN" \
  https://ha.bodino.us.kg/api/states/automation.blad_krytyczny_blad_systemu

# Test Telegram
curl -s -X POST https://ha.bodino.us.kg/api/services/notify/telegram \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Test OK"}'
```

### Bezpieczeństwo

- ✅ Telegram wysyłany przy błędach krytycznych
- ✅ Event Log przechowuje 5 ostatnich zdarzeń
- ✅ Reset dzienny zapobiega przepełnieniu
- ✅ Algorytm baterii działa poprawnie z Event Log

---

## 11.6 Konfiguracja narzędzi deweloperskich (2025-11-23)

### Whisper Assistant (VSCode)

**Rozszerzenie:** `martinopensky.whisper-assistant`

**Konfiguracja (VSCode settings.json):**
```json
{
  "whisper-assistant.apiProvider": "openai",
  "whisper-assistant.apiKey": "sk-proj-...",
  "whisper-assistant.language": "pl"
}
```

**Uwaga:** Język hardcoded w rozszerzeniu - zmieniono z `'en'` na `'pl'` w pliku:
`~/.vscode/extensions/martinopensky.whisper-assistant-1.2.4/out/speech-transcription.js`

### Klucze API

Klucze przechowywane w `.claude/settings.local.json`:

| Klucz | Użycie |
|-------|--------|
| `HA_TOKEN` | Home Assistant Long-Lived Access Token |
| `TELEGRAM_BOT_TOKEN` | Bot Telegram (@huawei_battery_bot) |
| `OPENAI_API_KEY` | OpenAI API (Whisper, GPT) |

---

## 11.7 Dashboard redesign + CWU improvements (2025-12-15)

**Status:** ✅ Wdrożone
**Wersja:** 3.11

### Podsumowanie zmian

#### 1. Redesign dashboardu Lovelace

**Problem:** Niespójny układ kart - różne style, brak grupowania

**Rozwiązanie:** Ujednolicony układ wszystkich sekcji:
- Każda grupa: **tytuł → gauge'y → encje (bez tytułu)**
- Użycie `vertical-stack` z tytułem jako kontener
- `horizontal-stack` dla par gauge'ów
- `entities` bez tytułu pod gauge'ami

##### Zmiany w sekcjach:

| Sekcja | Przed | Po |
|--------|-------|-----|
| Zarządzanie baterią | Luźne karty | vertical-stack z tytułem + gauge'y + entities |
| Pompa ciepła | Bez gauge'ów | Gauge'y temp. CO/CWU + status markdown |
| Ceny RCE | Tabela + entities | vertical-stack z tytułem + tabela + entities |
| Pogoda | Osobna karta | Połączona z prognozą PV w jednej grupie |
| Produkcja energii | Luźne karty | vertical-stack + gauge'y + entities + history-graph |

#### 2. CWU z nadwyżki PV - ulepszenia

**Nowe encje:**
- `input_boolean.cwu_pv_surplus_active` - flaga czy CWU włączone przez automatyzację PV

**Nowe automatyzacje:**
- `cwu_manual_force_auto_off` - automatyczne wyłączenie wymuszenia CWU po 30 minutach

**Logika:**
- CWU włączone przez PV → wyłączy się gdy spadnie nadwyżka lub temp > 55°C
- CWU włączone ręcznie → wyłączy się po 30 min (safety timeout)

### Pliki zmodyfikowane

| Plik | Zmiany |
|------|--------|
| `config/lovelace_huawei.yaml` | Kompletny redesign - ujednolicony układ sekcji |
| `config/automations_battery.yaml` | Dodano automatyzację auto-off CWU po 30 min |
| `config/input_boolean.yaml` | Dodano `cwu_pv_surplus_active` |

### Korzyści

- ✅ Spójny, czytelny interfejs użytkownika
- ✅ Lepsze grupowanie informacji tematycznie
- ✅ Bezpieczne ręczne wymuszanie CWU (auto-off)
- ✅ Rozróżnienie między automatycznym a ręcznym CWU

---

## 11.8 Dashboard improvements + Claude Code settings (2025-12-17)

**Status:** ✅ Wdrożone
**Wersja:** 3.12

### Podsumowanie zmian

#### 1. Dashboard - zmiany w gauge'ach

**Gauge Temp. CO → Temp. zasilania:**
- Zmiana nazwy z "Temp. CO" na "Temp. zasilania"
- Rozszerzenie zakresu: 35°C → 65°C
- Nowe segmenty kolorów:
  - 15-20°C: niebieski (zimno)
  - 20-35°C: zielony (norma)
  - 35-50°C: pomarańczowy (ciepło)
  - 50-65°C: czerwony (gorąco)

**Gauge Temp. CWU:**
- Dodanie wyświetlania temperatury docelowej pod gauge
- Format: `<center>Cel: XX°C</center>`

#### 2. Dashboard - tabela cen RCE

- Konwersja z markdown table na HTML table
- Nagłówki "Dziś" i "Jutro" z colspan dla lepszego wyrównania
- Separator 40px między sekcjami Dziś/Jutro

#### 3. Claude Code - poprawka uprawnień Bash

**Problem:** Nieprawidłowa składnia `"Bash(*)"` w permissions

**Rozwiązanie:** Prawidłowa składnia to `"Bash"` (bez nawiasów)

```json
// ❌ Nieprawidłowo
"permissions": { "allow": ["Bash(*)"] }

// ✅ Prawidłowo
"permissions": { "allow": ["Bash"] }
```

**Pliki zaktualizowane:**
- `~/.claude/settings.json` - globalne ustawienia
- `.claude/settings.local.json` - ustawienia projektu

#### 4. Znane ograniczenia integracji Aquarea Smart Cloud

**Problem:** `climate.bodynek_nb_zone_1.current_temperature` zwraca temperaturę zbiornika CWU (55°C) zamiast temperatury zasilania strefy (33°C)

**Status:** Bug w integracji Aquarea Smart Cloud - nie do naprawienia po stronie HA

**Workaround:** Brak - czekać na fix integracji lub użyć lokalnego odczytu z pompy

#### 5. Aquarea Smart Cloud - niedostępne dane

Integracja NIE udostępnia:
- Harmonogramu CWU (tylko w aplikacji Panasonic)
- Histerezy CWU (ustawienie lokalne na pompie, domyślnie ~5°C)
- Temperatury wyjściowej strefy (zwraca temp zbiornika)

### Pliki zmodyfikowane

| Plik | Zmiany |
|------|--------|
| `config/lovelace_huawei.yaml` | Gauge'y, tabela HTML, temp docelowa CWU |
| `~/.claude/settings.json` | Dodano `"Bash"` w permissions |
| `.claude/settings.local.json` | Poprawiono `"Bash(*)"` → `"Bash"` |

---

## v3.13 (2025-12-17) - Watchdog Aquarea + CWU backup

### Nowe automatyzacje

#### 1. Watchdog Aquarea (ID: `aquarea_watchdog_token`)

**Problem:** Integracja Aquarea Smart Cloud traci połączenie (TOKEN_EXPIRED, Failed communication with adaptor)

**Rozwiązanie:**
- Automatyzacja uruchamia się co godzinę o :47
- Sprawdza czy `water_heater.bodynek_nb_tank` jest `unavailable`
- Jeśli tak → automatycznie przeładowuje integrację
- Powiadomienia o wykryciu problemu i wyniku naprawy

#### 2. CWU harmonogram 13:02 (ID: `cwu_scheduled_1300`)

**Problem:** Harmonogram CWU w Aquarea Cloud nie zadziałał z powodu awarii komunikacji

**Rozwiązanie:**
- Backup harmonogramu chmury uruchamiany przez HA
- O 13:02 (2 min po harmonogramie Panasonic) sprawdza:
  - Czy CWU już grzeje (chmura zadziałała) → nie rób nic
  - Czy temp < cel i CWU nie grzeje → włącz wymuszenie
- Timeout 2h (obliczony dla zbiornika 385l i pompy 9kW)
- Automatyczne wyłączenie po osiągnięciu temperatury celu

### Analiza czasu grzania CWU

| Parametr | Wartość |
|----------|---------|
| Zbiornik | 385 litrów |
| Pompa | 9 kW (Panasonic T-CAP) |
| ΔT | 20°C (35→55°C) |
| Energia | 8.96 kWh |
| Czas (pełna moc) | ~1h |
| Czas (50% mocy CWU) | ~2h |

### Pliki zmodyfikowane

| Plik | Zmiany |
|------|--------|
| `config/automations_battery.yaml` | Watchdog Aquarea, CWU harmonogram 13:02 |

---

# WSPARCIE

**Dokumentacja:**
- Home Assistant: https://www.home-assistant.io/docs/
- Huawei Solar: https://github.com/wlcrs/huawei_solar
- Pstryk: https://github.com/balgerion/ha_Pstryk

**Społeczność:**
- Forum HA PL: https://forum.homeassistant.pl/
- Discord: Home Assistant Community

**GitHub:**
- Issues: https://github.com/anthropics/claude-code/issues

---

**Autor:** Marek Bodynek + Claude Code (Anthropic AI)
**Licencja:** MIT
**Ostatnia aktualizacja:** 2025-12-17

**Powodzenia! 🚀⚡**