# Home Assistant + Huawei Solar - Instalacja i Konfiguracja

## 📋 Spis treści
- [Specyfikacja systemu](#specyfikacja-systemu)
- [Status instalacji](#status-instalacji)
- [Pierwsze uruchomienie](#pierwsze-uruchomienie)
- [Konfiguracja integracji Huawei Solar](#konfiguracja-integracji-huawei-solar)
- [Opis automatyzacji](#opis-automatyzacji)
- [Zarządzanie systemem](#zarządzanie-systemem)
- [Rozwiązywanie problemów](#rozwiązywanie-problemów)

---

## 🔧 Specyfikacja systemu

- **Instalacja PV:** 14.4 kWp (Huawei)
- **Bateria:** Huawei Luna 2000 (15 kWh)
- **Tryb pracy:** PV PRIORITY (priorytet ładowania z fotowoltaiki)
- **Home Assistant:** Najnowsza stabilna wersja (Docker)

---

## ✅ Status instalacji

**Gotowe:**
- ✅ Docker zainstalowany i działa
- ✅ Katalogi utworzone: `~/home-assistant-huawei/`
- ✅ Home Assistant uruchomiony (port 8123)
- ✅ Pliki konfiguracyjne przygotowane
- ✅ Automatyzacje dla trybu PV Priority

**Do wykonania:**
- 🔄 Pierwsze uruchomienie Home Assistant
- 🔄 Instalacja integracji Huawei Solar przez HACS
- 🔄 Dodanie Twojego invertera do systemu
- 🔄 Dostosowanie parametrów automatyzacji

---

## 🚀 Pierwsze uruchomienie

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

---

## 🔌 Konfiguracja integracji Huawei Solar

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
- `sensor.battery_state_of_capacity` - poziom naładowania baterii (%)
- `sensor.active_power` - aktualna moc produkcji PV (W)
- `sensor.grid_active_power` - moc pobierana/oddawana do sieci (W)
- `select.battery_working_mode` - tryb pracy baterii

---

## ⚡ Opis automatyzacji

System zawiera 5 automatyzacji dla trybu **PV PRIORITY**:

### 1. Ładowanie w taniej taryfie (22:00-06:00)
**Plik:** `automations.yaml` - `huawei_cheap_charging_start`

**Działanie:**
- Włącza się o **22:00** (początek taryfy nocnej G12)
- Sprawdza, czy bateria < 80%
- Jeśli tak, włącza ładowanie z sieci

**Dostosowanie:**
```yaml
trigger:
  - platform: time
    at: "22:00:00"  # ← Zmień na Twoją godzinę taryfy nocnej
condition:
  - condition: numeric_state
    entity_id: sensor.battery_state_of_capacity
    below: 80  # ← Zmień próg według potrzeb (50-90%)
```

### 2. Stop ładowania przy 90%
**Plik:** `automations.yaml` - `huawei_stop_charging_high_soc`

Automatycznie zatrzymuje ładowanie, gdy bateria osiągnie 90% w nocy.

### 3. Powrót do trybu PV Priority (06:00)
**Plik:** `automations.yaml` - `huawei_pv_priority_mode`

**Działanie:**
- Włącza się o **06:00** (koniec taryfy nocnej)
- Przełącza na priorytet ładowania z PV
- W ciągu dnia bateria ładowana TYLKO z fotowoltaiki

**Dostosowanie:**
```yaml
trigger:
  - platform: time
    at: "06:00:00"  # ← Zmień na koniec Twojej taryfy nocnej
```

### 4. Awaryjne ładowanie (SOC < 15%)
**Plik:** `automations.yaml` - `huawei_emergency_charging`

Zabezpiecza baterię przed głębokim rozładowaniem.

### 5. Optymalizacja według pogody
**Plik:** `automations.yaml` - `huawei_weather_optimization`

**Wymaga dodatkowej integracji pogody!**
- Sprawdza prognozę na jutro
- Jeśli będzie pochmurno, zwiększa ładowanie nocne

---

## 🛠 Zarządzanie systemem

### Kontrola Docker

```bash
# Status kontenera
cd ~/home-assistant-huawei
docker-compose ps

# Logi Home Assistant
docker-compose logs -f homeassistant

# Restart Home Assistant
docker-compose restart

# Stop
docker-compose down

# Start
docker-compose up -d
```

### Aktualizacja Home Assistant

```bash
cd ~/home-assistant-huawei
docker-compose pull
docker-compose up -d
```

### Backup

```bash
# Backup całego folderu config
cd ~
tar -czf ha-backup-$(date +%Y%m%d).tar.gz home-assistant-huawei/config

# Lub skopiuj tylko config
cp -r ~/home-assistant-huawei/config ~/home-assistant-huawei/backups/config-$(date +%Y%m%d)
```

---

## 🔧 Dostosowanie automatyzacji

### Zmiana godzin taniej taryfy

Edytuj plik `config/automations.yaml`:
```yaml
# Początek taryfy nocnej (domyślnie 22:00)
trigger:
  - platform: time
    at: "22:00:00"

# Koniec taryfy nocnej (domyślnie 06:00)
trigger:
  - platform: time
    at: "06:00:00"
```

### Zmiana progów SOC

```yaml
# Próg rozpoczęcia ładowania (domyślnie 80%)
condition:
  - condition: numeric_state
    entity_id: sensor.battery_state_of_capacity
    below: 80

# Próg zakończenia ładowania (domyślnie 90%)
trigger:
  - platform: numeric_state
    entity_id: sensor.battery_state_of_capacity
    above: 90
```

### Zmiana mocy ładowania

```yaml
# Dla awaryjnego ładowania (domyślnie 5000W - MAX dla Luna 2000)
action:
  - service: huawei_solar.forcible_charge
    data:
      power: 5000  # W (1000-5000)
      duration: 120  # minuty
```

---

## 📊 Dostępne skrypty

W pliku `scripts.yaml` dostępne są ręczne skrypty:

### `force_battery_charge`
Manualnie wymusza ładowanie baterii
```yaml
service: script.force_battery_charge
```

### `stop_battery_charge`
Zatrzymuje ładowanie
```yaml
service: script.stop_battery_charge
```

### `enable_tou_mode`
Przełącza na tryb Time of Use
```yaml
service: script.enable_tou_mode
```

### `enable_self_consumption`
Przełącza na Maksymalną Autoconsumpcję
```yaml
service: script.enable_self_consumption
```

---

## ❓ Rozwiązywanie problemów

### Home Assistant nie startuje

```bash
# Sprawdź logi
cd ~/home-assistant-huawei
docker-compose logs homeassistant

# Sprawdź status
docker-compose ps
```

### Nie widzę invertera w Home Assistant

**Sprawdź:**
1. Czy inverter jest w tej samej sieci co Mac
2. Czy port 502 (Modbus) jest otwarty na inverterze
3. Czy podałeś poprawny IP adres

**Test połączenia:**
```bash
# Ping do invertera
ping <IP_INVERTERA>

# Test portu Modbus
nc -zv <IP_INVERTERA> 502
```

### Automatyzacje nie działają

**Sprawdź:**
1. **Developer Tools** → **States**
   - Czy `sensor.battery_state_of_capacity` istnieje?
   - Czy pokazuje aktualną wartość?

2. **Settings** → **Automations & Scenes**
   - Czy automatyzacje są włączone? (przełącznik)

3. **Logi:**
   - **Settings** → **System** → **Logs**
   - Szukaj błędów związanych z `huawei_solar`

### Błąd "Invalid device_id"

Musisz zamienić w automatyzacjach:
```yaml
device_id: >
  {{ device_id('huawei_solar_inverter') }}
```
na rzeczywiste ID Twojego urządzenia.

**Jak znaleźć device_id:**
1. **Settings** → **Devices & Services** → **Huawei Solar**
2. Kliknij na inverter
3. URL będzie zawierał ID, np.: `/config/devices/device/abc123...`

---

## 📱 Rekomendowane dodatkowe integracje

### Ceny energii (dynamiczna taryfa)
- **Tauron eLicznik** - jeśli masz Tauron
- **Energa** - jeśli masz Energę
- **Nordpool** - dla taryf dynamicznych

### Pogoda
- **OpenWeatherMap** (darmowa)
- **Met.no** (norweska służba pogodowa)

### Monitoring
- **InfluxDB + Grafana** - zaawansowane wykresy
- **Mobile App** - powiadomienia na telefon

---

## 📞 Wsparcie

**Dokumentacja:**
- Home Assistant: https://www.home-assistant.io/docs/
- Huawei Solar: https://github.com/wlcrs/huawei_solar

**Społeczność:**
- Forum HA PL: https://forum.homeassistant.pl/
- Discord: Home Assistant Community

---

## 📝 Checklist pierwszej konfiguracji

- [ ] Uruchom Home Assistant (http://localhost:8123)
- [ ] Utwórz konto administratora
- [ ] Zainstaluj HACS
- [ ] Zainstaluj integrację Huawei Solar przez HACS
- [ ] Dodaj inverter (IP, port 502, slave ID 1)
- [ ] Sprawdź czy encje baterii są widoczne
- [ ] Dostosuj godziny taryfy w `automations.yaml`
- [ ] Dostosuj progi SOC według potrzeb
- [ ] Włącz automatyzacje
- [ ] Przetestuj w Developer Tools
- [ ] (Opcjonalnie) Dodaj integrację pogody
- [ ] (Opcjonalnie) Dodaj integrację cen energii

---

**Powodzenia! 🚀**

*Przy pytaniach sprawdź logi w Home Assistant lub dokumentację integracji Huawei Solar.*
