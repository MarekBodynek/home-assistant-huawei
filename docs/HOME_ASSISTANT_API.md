# Home Assistant API - Instrukcja dla Claude Code

## Dostęp do API

**Token API zapisany w:** `config/secrets.yaml` → `ha_api_token`

**Endpointy:**
- **Zewnętrzny:** https://ha.bodino.us.kg/api/
- **Lokalny:** http://192.168.0.106:8123/api/

## Podstawowe użycie

### 1. Sprawdzenie dostępności API

```bash
curl -X GET "https://ha.bodino.us.kg/api/" \
  -H "Authorization: Bearer $(cat config/secrets.yaml | grep ha_api_token | cut -d'"' -f2)"
```

**Odpowiedź:** `{"message":"API running."}`

### 2. Pobranie wszystkich stanów encji

```bash
curl -s -X GET "https://ha.bodino.us.kg/api/states" \
  -H "Authorization: Bearer <TOKEN>" \
  | jq '.[0:5]'  # pierwsze 5 encji
```

### 3. Pobranie stanu konkretnej encji

```bash
# Stan baterii (SOC)
curl -s -X GET "https://ha.bodino.us.kg/api/states/sensor.akumulatory_stan_pojemnosci" \
  -H "Authorization: Bearer <TOKEN>" \
  | jq '.state'

# Strefa taryfowa
curl -s -X GET "https://ha.bodino.us.kg/api/states/sensor.strefa_taryfowa" \
  -H "Authorization: Bearer <TOKEN>" \
  | jq '.state'

# Temperatura baterii
curl -s -X GET "https://ha.bodino.us.kg/api/states/sensor.akumulator_1_temperatura" \
  -H "Authorization: Bearer <TOKEN>" \
  | jq '.state'
```

### 4. Wywołanie usługi (service call)

```bash
# Uruchomienie algorytmu baterii
curl -X POST "https://ha.bodino.us.kg/api/services/python_script/battery_algorithm" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json"

# Obliczenie strategii dziennej
curl -X POST "https://ha.bodino.us.kg/api/services/python_script/calculate_daily_strategy" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json"

# Włączenie ładowania baterii
curl -X POST "https://ha.bodino.us.kg/api/services/switch/turn_on" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "switch.akumulatory_ladowanie_z_sieci"}'

# Wyłączenie ładowania baterii
curl -X POST "https://ha.bodino.us.kg/api/services/switch/turn_off" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "switch.akumulatory_ladowanie_z_sieci"}'
```

### 5. Ustawienie wartości input_number

```bash
# Ustawienie Target SOC na 75%
curl -X POST "https://ha.bodino.us.kg/api/services/input_number/set_value" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "entity_id": "input_number.battery_target_soc",
    "value": 75
  }'
```

## Kluczowe encje do monitoringu

### Bateria
| Entity ID | Opis |
|-----------|------|
| `sensor.akumulatory_stan_pojemnosci` | SOC baterii (%) |
| `sensor.akumulatory_moc_ladowania_rozladowania` | Moc ładowania/rozładowania (W) |
| `sensor.akumulator_1_temperatura` | Temperatura baterii (°C) |
| `switch.akumulatory_ladowanie_z_sieci` | Włącznik ładowania z sieci |
| `select.akumulatory_tryb_pracy` | Tryb pracy baterii |

### Energia
| Entity ID | Opis |
|-----------|------|
| `sensor.inwerter_moc_wejsciowa` | Produkcja PV (W) |
| `sensor.pomiar_mocy_moc_czynna` | Moc sieci (W, +pobór/-oddawanie) |
| `sensor.prognoza_pv_dzisiaj` | Prognoza PV dziś (kWh) |
| `sensor.prognoza_pv_jutro` | Prognoza PV jutro (kWh) |

### Taryfa i ceny
| Entity ID | Opis |
|-----------|------|
| `sensor.strefa_taryfowa` | Aktualna strefa (L1/L2) |
| `sensor.rce_pse_cena` | Cena RCE (PLN/MWh) |
| `binary_sensor.dzien_roboczy` | Czy dzień roboczy |
| `binary_sensor.sezon_grzewczy` | Czy sezon grzewczy |

### Strategia
| Entity ID | Opis |
|-----------|------|
| `input_number.battery_target_soc` | Docelowy SOC (%) |
| `input_text.battery_decision_reason` | Powód ostatniej decyzji |
| `input_text.battery_status` | Status algorytmu |

## Przykłady dla Claude Code

### Sprawdzenie stanu baterii
```python
import requests
import json

TOKEN = "..."  # z secrets.yaml
API_URL = "https://ha.bodino.us.kg/api"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Pobierz SOC
response = requests.get(
    f"{API_URL}/states/sensor.akumulatory_stan_pojemnosci",
    headers=headers
)
soc = float(response.json()['state'])
print(f"SOC baterii: {soc}%")
```

### Uruchomienie algorytmu
```python
response = requests.post(
    f"{API_URL}/services/python_script/battery_algorithm",
    headers=headers
)
print(f"Algorytm uruchomiony: {response.status_code}")
```

### Monitorowanie w czasie rzeczywistym
```python
# Pobierz kluczowe dane
entities = [
    "sensor.akumulatory_stan_pojemnosci",
    "sensor.strefa_taryfowa",
    "sensor.akumulator_1_temperatura",
    "sensor.inwerter_moc_wejsciowa",
]

for entity_id in entities:
    response = requests.get(
        f"{API_URL}/states/{entity_id}",
        headers=headers
    )
    data = response.json()
    print(f"{entity_id}: {data['state']} {data.get('attributes', {}).get('unit_of_measurement', '')}")
```

## Bash helper functions

Dodaj do `~/.bashrc` lub `~/.zshrc`:

```bash
# Home Assistant API
export HA_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
export HA_URL="https://ha.bodino.us.kg"

# Pobierz stan encji
ha_get() {
    curl -s -X GET "${HA_URL}/api/states/$1" \
        -H "Authorization: Bearer ${HA_TOKEN}" \
        | jq -r '.state'
}

# Wywołaj usługę
ha_service() {
    local domain=$1
    local service=$2
    local entity=$3

    curl -s -X POST "${HA_URL}/api/services/${domain}/${service}" \
        -H "Authorization: Bearer ${HA_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "{\"entity_id\": \"${entity}\"}"
}

# Przykłady użycia:
# ha_get sensor.akumulatory_stan_pojemnosci
# ha_service python_script battery_algorithm
```

## Bezpieczeństwo

⚠️ **WAŻNE:**
- Token ma dostęp do WSZYSTKICH funkcji Home Assistant
- NIE udostępniaj tokenu publicznie
- Token jest ważny do: 2036-01-20 (exp: 2085310999)
- Jeśli token wycieknie, usuń go w HA → Profil → Tokeny

## Debugging

### Sprawdzenie czy API działa
```bash
curl -v https://ha.bodino.us.kg/api/
```

### Sprawdzenie autoryzacji
```bash
curl -X GET "https://ha.bodino.us.kg/api/config" \
  -H "Authorization: Bearer ${HA_TOKEN}" \
  | jq '.location_name'
```

Jeśli zwróci "Dom" - autoryzacja działa!

## Linki
- [Home Assistant REST API Docs](https://developers.home-assistant.io/docs/api/rest/)
- [Service Calls](https://www.home-assistant.io/docs/scripts/service-calls/)
