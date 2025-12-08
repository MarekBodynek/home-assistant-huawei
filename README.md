# Home Assistant - Huawei Solar Battery Management System

[![GitHub](https://img.shields.io/badge/GitHub-Public-green)](https://github.com/MarekBodynek/home-assistant-huawei)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.x-blue)](https://www.home-assistant.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Inteligentny system zarządzania baterią Huawei LUNA 2000 z optymalizacją kosztów energii na podstawie cen RCE PSE i prognoz produkcji PV.

> **📚 Pełna instrukcja instalacji:** [docs/INSTRUKCJA_NOWA_INSTALACJA.md](docs/INSTRUKCJA_NOWA_INSTALACJA.md)

## Quick Start

```bash
# 1. Sklonuj repozytorium
git clone https://github.com/MarekBodynek/home-assistant-huawei.git
cd home-assistant-huawei

# 2. Skopiuj pliki do Home Assistant
cp -r config/* /path/to/homeassistant/config/

# 3. Zainstaluj wymagane integracje HACS:
#    - Huawei Solar (wlcrs/huawei_solar)
#    - Pstryk lub RCE PSE

# 4. Dostosuj parametry w plikach (lokalizacja, moc PV, pojemność baterii)

# 5. Restart Home Assistant
```

## Funkcje

- **Optymalizacja kosztów** - automatyczne ładowanie baterii w najtańszych godzinach (L2)
- **Arbitraż cenowy** - sprzedaż energii w szczycie, zakup w dolinie
- **Prognozowanie** - wykorzystanie prognoz PV (Forecast Solar) do planowania
- **Bezpieczeństwo** - monitoring temperatury baterii, ochrona przed przegrzaniem/zamarzaniem
- **Taryfa G12w** - pełna obsługa stref taryfowych (L1/L2), weekendów i świąt polskich
- **Sezon grzewczy** - uwzględnienie zużycia pompy ciepła
- **Dashboard** - wizualizacja cen RCE, prognoz PV, statusu baterii

## Wymagania sprzętowe

### Instalacja PV z magazynem energii
- **Inwerter**: Huawei SUN2000 (4-10kW) z możliwością komunikacji Modbus
- **Bateria**: Huawei LUNA 2000 (5-15kWh)
- **Smart Meter**: Huawei DTSU666-H (pomiar energii sieciowej)
- **Dongle WiFi**: Huawei Smart Dongle-WLAN-FE lub SDongleA-05

### Serwer Home Assistant
- Raspberry Pi 4 (min. 4GB RAM) lub Mac Mini / PC
- Docker lub Home Assistant OS
- Stałe połączenie internetowe

### Panele PV (opcjonalnie multi-płaszczyzna)
System obsługuje do 3 płaszczyzn z różnymi azymutami (wschód/południe/zachód).

## Wymagane integracje

### HACS (Home Assistant Community Store)
1. **Huawei Solar** - komunikacja z inwerterem/baterią
   - Repozytorium: `wlcrs/huawei_solar`
   - Protokół: Modbus TCP/IP

2. **RCE PSE** (opcjonalnie Pstryk) - ceny energii z rynku hurtowego
   - Repozytorium: Własna integracja lub Pstryk

### Wbudowane integracje HA
- **Workday** - wykrywanie dni roboczych i świąt polskich
- **Sun** - czas wschodu/zachodu słońca
- **Forecast Solar** - prognoza produkcji PV (REST API)
- **Telegram** (opcjonalnie) - powiadomienia

## Struktura plików

```
config/
├── configuration.yaml          # Główna konfiguracja HA
├── template_sensors.yaml       # Sensory obliczeniowe
├── automations_battery.yaml    # Automatyzacje zarządzania baterią
├── automations_errors.yaml     # Automatyzacje obsługi błędów
├── utility_meter.yaml          # Mierniki energii (dzienne, godzinowe)
├── input_numbers.yaml          # Zmienne numeryczne (target SOC, EMA)
├── input_text.yaml             # Zmienne tekstowe (status, decyzje)
├── input_boolean.yaml          # Przełączniki (powiadomienia)
├── input_select.yaml           # Listy wyboru (poziom logowania)
├── lovelace_huawei.yaml        # Dashboard Huawei Solar
├── secrets.yaml                # Dane wrażliwe (API keys, hasła)
├── python_scripts/
│   ├── battery_algorithm.py    # Główny algorytm zarządzania baterią
│   └── calculate_daily_strategy.py  # Obliczanie strategii dziennej
└── custom_components/
    ├── huawei_solar/           # Integracja Huawei Solar
    └── pstryk/                 # Integracja Pstryk (RCE)
```

## Kluczowe sensory

### Sensory Huawei Solar (z integracji)
| Entity ID | Opis |
|-----------|------|
| `sensor.akumulatory_stan_pojemnosci` | SOC baterii (%) |
| `sensor.akumulatory_status` | Status baterii (Running/Sleep/Standby) |
| `sensor.akumulatory_moc_ladowania_rozladowania` | Moc ładowania/rozładowania (W) |
| `sensor.inwerter_moc_wejsciowa` | Aktualna produkcja PV (W) |
| `sensor.inwerter_total_dc_input_energy` | Skumulowana produkcja DC (kWh) |
| `sensor.pomiar_mocy_moc_czynna` | Moc pobierana/oddawana do sieci (W) |
| `sensor.akumulator_1_temperatura` | Temperatura baterii (°C) |
| `switch.akumulatory_ladowanie_z_sieci` | Włącznik ładowania z sieci |
| `select.akumulatory_tryb_pracy` | Tryb pracy baterii |

### Sensory szablonowe (template_sensors.yaml)
| Entity ID | Opis |
|-----------|------|
| `sensor.strefa_taryfowa` | Aktualna strefa (L1/L2) |
| `sensor.cena_zakupu_energii` | Cena RCE (PLN/kWh) |
| `sensor.rce_progi_cenowe` | Progi percentylowe (p33/p66) |
| `sensor.rce_ceny_godzinowe` | Ceny godzinowe z kolorami |
| `sensor.prognoza_pv_dzisiaj` | Pozostała prognoza PV dziś (kWh) |
| `binary_sensor.dzien_roboczy` | Czy dzień roboczy |
| `binary_sensor.sezon_grzewczy` | Czy sezon grzewczy |
| `binary_sensor.bateria_bezpieczna_temperatura` | Czy temperatura OK |

### Zmienne wejściowe
| Entity ID | Opis |
|-----------|------|
| `input_number.battery_target_soc` | Docelowy SOC (obliczany o 00:00) |
| `input_number.night_consumption_avg` | Średnie zużycie nocne (EMA) |
| `input_text.battery_decision_reason` | Powód ostatniej decyzji |
| `input_text.battery_cheapest_hours` | Najtańsze godziny słoneczne |

## Logika algorytmu

### Taryfa G12w - Strefy czasowe
```
DNI ROBOCZE:
├── 06:00-13:00  → L1 (droga)
├── 13:00-15:00  → L2 (tania) ← okno ładowania południe
├── 15:00-22:00  → L1 (droga)
└── 22:00-06:00  → L2 (tania) ← okno ładowania noc

WEEKENDY + ŚWIĘTA:
└── 00:00-24:00  → L2 (tania) ← cały dzień
```

### Priorytety decyzji (od najwyższego)
1. **BEZPIECZEŃSTWO** - temperatura baterii (0-45°C)
2. **KRYTYCZNE** - SOC < 5% → ładuj natychmiast
3. **PILNE** - SOC < 20% w L1 → czekaj na L2
4. **OKNO L2** - SOC < Target → ładuj z sieci
5. **AUTOCONSUMPTION** - nadwyżka PV → magazynuj, deficyt → rozładuj
6. **ARBITRAŻ** - droga godzina → sprzedaj, tania → kupuj

### Kolorowanie cen RCE
```
🟢🟢 < 0.20 PLN/kWh    (super tanie - bezwzględny próg)
🟢   < p33             (najtańsze 33% dnia)
🟡   p33-p66           (średnie)
🔴   ≥ p66             (najdroższe 33% dnia)
```

## Instalacja

### 1. Instalacja Home Assistant
```bash
# Docker Compose
docker run -d \
  --name homeassistant \
  --privileged \
  --restart=unless-stopped \
  -v /path/to/config:/config \
  -p 8123:8123 \
  ghcr.io/home-assistant/home-assistant:stable
```

### 2. Instalacja HACS
1. Pobierz HACS: https://hacs.xyz/docs/setup/download
2. Restart HA
3. Skonfiguruj HACS w UI

### 3. Instalacja integracji Huawei Solar
1. HACS → Integracje → Szukaj "Huawei Solar"
2. Instaluj → Restart HA
3. Ustawienia → Integracje → Dodaj "Huawei Solar"
4. Podaj IP inwertera i port Modbus (502)

### 4. Instalacja integracji RCE PSE
Opcja A: Pstryk (HACS)
- HACS → Integracje → Szukaj "Pstryk"

Opcja B: Własna integracja REST
```yaml
# configuration.yaml
rest:
  - resource: https://api.rce.pse.pl/api/rce/...
    sensor:
      - name: "RCE PSE Cena"
        value_template: "{{ value_json.price }}"
```

### 5. Kopiowanie plików konfiguracji
```bash
# Sklonuj repozytorium
git clone https://github.com/MarekBodynek/home-assistant-huawei.git

# Skopiuj pliki do katalogu config HA
cp -r config/* /path/to/homeassistant/config/
```

### 6. Konfiguracja secrets.yaml
```yaml
# secrets.yaml (NIE commituj do Git!)
telegram_bot_token: "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
telegram_chat_id: "-1001234567890"
```

### 7. Dostosowanie configuration.yaml
Zmień następujące wartości:
```yaml
homeassistant:
  latitude: TWOJA_SZEROKOSC   # np. 52.2297
  longitude: TWOJA_DLUGOSC    # np. 21.0122
  elevation: WYSOKOSC_NPM     # np. 100

# Forecast Solar - dostosuj do swoich paneli
rest:
  - resource: https://api.forecast.solar/estimate/LAT/LON/TILT/AZIMUTH/KWP
```

### 8. Restart i weryfikacja
```bash
# Sprawdź konfigurację
docker exec homeassistant python -c "
from homeassistant.config import check_ha_config_file
check_ha_config_file('/config/configuration.yaml')
"

# Restart
docker restart homeassistant
```

## Konfiguracja parametrów

### Dostosowanie do instalacji

1. **device_id baterii** (automations_battery.yaml)
   - Znajdź w: Ustawienia → Urządzenia → Akumulatory → ID urządzenia
   - Zmień w automatyzacjach `huawei_solar.forcible_charge`

2. **Progi temperatury** (automations_battery.yaml)
   - Domyślne: ostrzeżenie >40°C, krytyczne >43°C, ekstremalne >45°C
   - Dostosuj do specyfikacji baterii

3. **Okna czasowe CWU** (template_sensors.yaml)
   - Domyślne: 04:30-06:00, 13:00-15:00, 20:00-24:00
   - Dostosuj do harmonogramu pompy ciepła

4. **Target SOC** (input_numbers.yaml)
   - Zakres: 20-80% (limit Huawei LUNA 2000)
   - Algorytm oblicza optymalny cel o 00:00

## Dashboard

### Struktura (3 kolumny)
```
┌─────────────┬─────────────┬─────────────┐
│   Pogoda    │  Ceny RCE   │Historia mocy│
├─────────────┼─────────────┼─────────────┤
│  Bateria    │Ceny godzin. │ Produkcja   │
│ (zarządz.)  │ DZIŚ | JUTRO│   energii   │
├─────────────┼─────────────┼─────────────┤
│             │Prognoza PV  │ Sezon       │
│             │ bilans mocy │ grzewczy    │
├─────────────┼─────────────┼─────────────┤
│             │             │Powiadomienia│
│             │             │ Event Log   │
└─────────────┴─────────────┴─────────────┘
```

### Import dashboardu
1. Ustawienia → Dashboardy → Dodaj dashboard
2. Nazwa: "Huawei Solar PV"
3. Tryb: YAML
4. Plik: `lovelace_huawei.yaml`

## Harmonogram automatyzacji

| Czas | Automatyzacja | Opis |
|------|---------------|------|
| 03:55 | update_forecast | Pobierz prognozę PV |
| 04:30 | execute_strategy | Start okna CWU rano |
| 06:00 | execute_strategy, capture_night | Koniec L2 noc, zapisz zużycie nocne |
| co 1h | execute_strategy | Główna pętla algorytmu |
| 12:00 | update_forecast | Aktualizacja prognozy PV |
| 12:40 | wake_from_sleep | Wybudź baterię przed L2 południe (5x retry) |
| 12:41 | diagnostyka wake | Status po próbie wybudzenia (południe) |
| 13:00 | execute_strategy | Start L2 południe (dni robocze) |
| 15:00 | execute_strategy | Koniec L2 południe |
| 18:00 | fetch_rce | Pobierz ceny RCE na jutro |
| 19:00 | execute_strategy | Szczyt wieczorny |
| 20:00 | update_forecast | Aktualizacja prognozy PV |
| 21:00 | calculate_pv_start | Oblicz godzinę startu PV jutro |
| 21:05 | calculate_daily_strategy | Oblicz Target SOC (okres 22:00-21:59) |
| 21:40 | wake_from_sleep | Wybudź baterię przed L2 noc (5x retry) |
| 21:41 | diagnostyka wake | Status po próbie wybudzenia (noc) |
| 22:00 | execute_strategy | Start L2 noc (początek doby energetycznej) |
| 00:01 | daily_summary | Podsumowanie doby (22:00-21:59) |
| co 30min | watchdog | Monitoring zdrowia algorytmu |
| co 1h (:59) | ml_data_collection | Zbieranie danych dla Machine Learning |

## Rozwiązywanie problemów

### Bateria nie ładuje się w L2
1. Sprawdź `sensor.strefa_taryfowa` → czy pokazuje L2?
2. Sprawdź `binary_sensor.dzien_roboczy` → czy prawidłowo wykrywa weekend/święto?
3. Sprawdź `sensor.akumulatory_status` → czy nie jest "Sleep mode"?
4. Sprawdź logi: Narzędzia → Logi → szukaj "battery_algorithm"

### Temperatura baterii pokazuje złą wartość
1. Sprawdź `sensor.akumulator_1_temperatura` → to prawdziwa temperatura BMS
2. NIE używaj sensorów od optymalizatorów PV (są na dachu!)

### Ceny RCE nie są pobierane
1. Sprawdź `sensor.rce_pse_cena` → czy ma atrybut `prices`?
2. Sprawdź połączenie z API PSE
3. Ceny na jutro dostępne są dopiero po ~14:00

### Kolory cen nie są spójne
Problem z precyzją float rozwiązany przez:
1. Zaokrąglenie średniej do 2 miejsc (`round(x, 2)`)
2. Porównanie w groszach (`int(price * 100)`)

### Algorytm nie działa
1. Sprawdź czy `python_script` jest włączony w configuration.yaml
2. Sprawdź logi: `grep python_script home-assistant.log`
3. Uruchom ręcznie: Narzędzia → Usługi → `python_script.battery_algorithm`

## Bezpieczeństwo

### Limity Huawei LUNA 2000
- **SOC**: 5-100% (algorytm używa 20-80%)
- **Temperatura**: 0-45°C (optymalnie 15-25°C)
- **Moc ładowania**: max 5kW (LUNA 2000-5)

### Progi bezpieczeństwa algorytmu
```python
CRITICAL_SOC = 5       # Krytycznie niski → ładuj 24/7
LOW_SOC = 20           # Niski → priorytet ładowania w L2
TEMP_WARNING = 40      # Ostrzeżenie
TEMP_CRITICAL = 43     # Stop ładowania
TEMP_EXTREME = 45      # Alarm ekstremalny
TEMP_FREEZING = 0      # Stop ładowania (mróz)
```

## Licencja

MIT License - możesz używać, modyfikować i dystrybuować.

## Autor

Projekt rozwijany przy wsparciu Claude Code (Anthropic).

## Changelog

### v3.10 (2025-12-08)
- **Fix**: Po zachodzie słońca kafelek RCE pokazuje dane na JUTRO (nie stare z wczoraj)
- Dodano label `[Jutro]` gdy wyświetlane dane na następny dzień
- Komunikat "Brak cen RCE na jutro" gdy dane niedostępne

### v3.9 (2025-12-08)
- **Zmiana**: Weekend energetyczny używa self-consumption zamiast TOU protection
- PV produkuje → bateria ładuje, PV nie produkuje → bateria rozładowuje na dom
- Sieć NIE ładuje baterii w weekend (piątek 22:00 → niedziela 22:00)

### v3.8 (2025-12-08)
- **Fix**: Kompletna logika weekendu energetycznego (piątek 22:00 → niedziela 22:00)
- Dodano `is_friday_evening` - piątek 22:00+ = START weekendu
- Dodano `is_sunday_evening` - niedziela 22:00+ = KONIEC weekendu

### v3.7 (2025-12-08)
- **Fix**: Niedziela 22:00 - bateria zaczyna ładować (koniec weekendu energetycznego)
- **Fix**: Spójność kolorów RCE - zaokrąglanie cen przed porównaniem z progami

### v3.6 (2025-12-04)
- **Fix**: Korekta mocy PV w Forecast.Solar (E=6.0, S=4.8, W=3.6 kWp)
- **Nowa funkcja**: Współczynnik korekcji sezonowej dla prognoz PV (0.50 zima → 0.90 lato)
- **Dashboard**: Usunięty "Max moc rozładowania", przeniesiony kafelek "Powiadomienia"
- **Dokumentacja**: Kompletna instrukcja instalacji z pełnym kodem wszystkich plików
- Repozytorium publiczne: https://github.com/MarekBodynek/home-assistant-huawei

### v3.5 (2025-12-01)
- **Fix**: Kolory godzin RCE używają percentyli (p33/p66) zamiast sztywnych progów
- **Fix**: Wybudzanie baterii wcześniej (21:20 zamiast 21:40) - bateria potrzebuje do 45 min na wake-up
- Dodano: Instrukcja dla nowej instalacji (`docs/INSTRUKCJA_NOWA_INSTALACJA.md`)

### v3.4 (2025-11-29)
- **Nowa funkcja**: Kolorowe kropki dla godzin słonecznych (🟢 < p33 | 🟡 p33-p66 | 🔴 > p66)
- **Nowa funkcja**: Wyświetlanie najtańszych godzin chronologicznie `[7, 8, 9, 10, 11, 12, 13]`
- **Fix**: RCE PSE zwraca dane co 15 min - agregacja do godzin (avg)
- **Fix**: Parsowanie pola `period` zamiast `dtime` (koniec vs początek okresu)
- **Zmiana**: Weekend bez ładowania! Tylko od niedzieli 22:00
  - Sobota: brak ładowania (cały dzień)
  - Niedziela 00:00-22:00: brak ładowania
  - Niedziela 22:00+: ładowanie włączone
- Dodano: Sezonowe wschody/zachody słońca (zamiast UTC z sun.sun)
- Dodano: ML training scripts (train_consumption_model.py)

### v3.3 (2025-11-26)
- Fix: Spójne kolorowanie cen RCE (float precision)
- Fix: Prawidłowa temperatura baterii (sensor BMS)
- Dodano: Wybudzanie baterii ze Sleep mode przed L2
- Dodano: Zbieranie danych godzinowych dla ML

### v3.2 (2025-11-23)
- Dodano: System Event Log (5 slotów)
- Dodano: Utility meters (nocne, godzinowe)
- Dodano: EMA dla średniego zużycia nocnego

### v3.1 (2025-11-20)
- Dodano: Progi cenowe RCE (percentyle)
- Dodano: Diagnostyka wybudzania baterii
- Fix: Konwersja UTC→CET dla wschodu/zachodu słońca
