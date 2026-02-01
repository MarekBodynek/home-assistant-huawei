# Instrukcja dla Claude - Odczyt temperatur z Home Assistant

## Kluczowe czujniki temperatury

### 1. Temperatura zewnętrzna
```bash
# Entity ID
sensor.temperatura_zewnetrzna

# Przykładowy odczyt: -7.0°C
```

### 2. Temperatura w jadalni
```bash
# Entity ID
sensor.jadalnie_czujnik_temperatury_temperature

# Przykładowy odczyt: 21.84°C
# Uwaga: nazwa ma literówkę "Jadalnie" zamiast "Jadalnia"
```

### 3. Temperatura CWU (ciepła woda użytkowa)
```bash
# Entity ID
sensor.temperatura_cwu

# Przykładowy odczyt: 53.0°C
# Zakres normalny: 55-60°C (zalecany)
# Minimum użytkowe: 45-50°C
```

---

## Jak odczytać temperatury

### Metoda 1: Pojedynczy czujnik (curl + jq)

```bash
# Token z secrets.yaml
HA_TOKEN=$(grep ha_api_token config/secrets.yaml | cut -d'"' -f2)
HA_URL="https://ha.bodino.us.kg"

# Temperatura zewnętrzna
curl -s "${HA_URL}/api/states/sensor.temperatura_zewnetrzna" \
  -H "Authorization: Bearer ${HA_TOKEN}" \
  | jq -r '.state + "°C (zewnętrzna)"'

# Temperatura jadalnia
curl -s "${HA_URL}/api/states/sensor.jadalnie_czujnik_temperatury_temperature" \
  -H "Authorization: Bearer ${HA_TOKEN}" \
  | jq -r '.state + "°C (jadalnia)"'

# Temperatura CWU
curl -s "${HA_URL}/api/states/sensor.temperatura_cwu" \
  -H "Authorization: Bearer ${HA_TOKEN}" \
  | jq -r '.state + "°C (CWU)"'
```

### Metoda 2: Wszystkie trzy naraz (Python)

```bash
HA_TOKEN=$(grep ha_api_token config/secrets.yaml | cut -d'"' -f2)

curl -s "https://ha.bodino.us.kg/api/states" \
  -H "Authorization: Bearer ${HA_TOKEN}" \
  | python3 << 'EOF'
import json, sys

data = json.load(sys.stdin)

sensors = {
    'sensor.temperatura_zewnetrzna': '🌡️ Zewnętrzna',
    'sensor.jadalnie_czujnik_temperatury_temperature': '🏠 Jadalnia',
    'sensor.temperatura_cwu': '💧 CWU'
}

print("📊 Temperatury:")
print("=" * 40)

for entity_id, label in sensors.items():
    sensor = next((s for s in data if s['entity_id'] == entity_id), None)
    if sensor:
        temp = sensor['state']
        print(f"{label:20} {temp:>6}°C")
    else:
        print(f"{label:20} {'ERROR':>6}")

print("=" * 40)
EOF
```

**Przykładowy output:**
```
📊 Temperatury:
========================================
🌡️ Zewnętrzna        -7.0°C
🏠 Jadalnia          21.84°C
💧 CWU               53.0°C
========================================
```

### Metoda 3: Bash helper function

Dodaj do `~/.bashrc` lub `~/.zshrc`:

```bash
# Home Assistant - szybki odczyt temperatur
ha_temps() {
    local HA_TOKEN=$(grep ha_api_token ~/Documents/Kodowanie/home-assistant-huawei/config/secrets.yaml | cut -d'"' -f2)
    local HA_URL="https://ha.bodino.us.kg"

    echo "📊 Temperatury:"
    echo "========================================"

    # Zewnętrzna
    local temp_ext=$(curl -s "${HA_URL}/api/states/sensor.temperatura_zewnetrzna" \
        -H "Authorization: Bearer ${HA_TOKEN}" 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])" 2>/dev/null)
    printf "🌡️  Zewnętrzna:    %6s°C\n" "${temp_ext}"

    # Jadalnia
    local temp_jad=$(curl -s "${HA_URL}/api/states/sensor.jadalnie_czujnik_temperatury_temperature" \
        -H "Authorization: Bearer ${HA_TOKEN}" 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])" 2>/dev/null)
    printf "🏠 Jadalnia:      %6s°C\n" "${temp_jad}"

    # CWU
    local temp_cwu=$(curl -s "${HA_URL}/api/states/sensor.temperatura_cwu" \
        -H "Authorization: Bearer ${HA_TOKEN}" 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])" 2>/dev/null)
    printf "💧 CWU:           %6s°C\n" "${temp_cwu}"

    echo "========================================"
}
```

**Użycie:**
```bash
$ ha_temps
```

### Metoda 4: Python script (dla automatyzacji)

Stwórz plik `scripts/check_temps.py`:

```python
#!/usr/bin/env python3
"""Odczyt kluczowych temperatur z Home Assistant"""

import requests
import json
import sys
from pathlib import Path

# Ścieżka do secrets.yaml
SECRETS_FILE = Path(__file__).parent.parent / "config" / "secrets.yaml"

def get_token():
    """Pobierz token z secrets.yaml"""
    with open(SECRETS_FILE) as f:
        for line in f:
            if 'ha_api_token:' in line:
                return line.split('"')[1]
    raise ValueError("Token not found in secrets.yaml")

def get_temperature(token, entity_id):
    """Pobierz temperaturę z Home Assistant API"""
    url = f"https://ha.bodino.us.kg/api/states/{entity_id}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return float(data['state'])
    except Exception as e:
        print(f"Error getting {entity_id}: {e}", file=sys.stderr)
        return None

def main():
    token = get_token()

    sensors = {
        'sensor.temperatura_zewnetrzna': '🌡️  Zewnętrzna',
        'sensor.jadalnie_czujnik_temperatury_temperature': '🏠 Jadalnia',
        'sensor.temperatura_cwu': '💧 CWU'
    }

    print("📊 Temperatury:")
    print("=" * 40)

    for entity_id, label in sensors.items():
        temp = get_temperature(token, entity_id)
        if temp is not None:
            print(f"{label:20} {temp:>6.1f}°C")
        else:
            print(f"{label:20} {'ERROR':>6}")

    print("=" * 40)

if __name__ == "__main__":
    main()
```

**Użycie:**
```bash
cd ~/Documents/Kodowanie/home-assistant-huawei
python3 scripts/check_temps.py
```

---

## Interpretacja temperatur

### Temperatura zewnętrzna
- **< -10°C** - Mróz ekstremalny
- **-10°C do 0°C** - Mróz normalny (obecnie: -7°C)
- **0°C do 12°C** - Sezon grzewczy
- **> 12°C** - Poza sezonem grzewczym

### Temperatura jadalnia
- **< 18°C** - Za zimno
- **18-22°C** - Komfortowo (obecnie: 21.84°C ✅)
- **22-24°C** - Ciepło
- **> 24°C** - Za gorąco

### Temperatura CWU
- **< 40°C** - 🔴 Za zimna, bakterie!
- **40-50°C** - ⚠️ Minimum użytkowe
- **50-60°C** - ✅ Zalecana (obecnie: 53°C)
- **> 60°C** - ⚠️ Niebezpieczeństwo poparzeń

---

## Przydatne przy analizie

### Różnica temperatur (izolacja budynku)
```python
delta = temp_jadalnia - temp_zewnetrzna
# Obecnie: 21.84 - (-7.0) = 28.84°C

# Typowo:
# - Zima: 25-30°C różnicy
# - Lato: 5-10°C różnicy
```

### Status CWU
```python
if temp_cwu < 45:
    status = "🔴 KRYTYCZNE - podgrzej natychmiast"
elif temp_cwu < 50:
    status = "⚠️ NISKIE - należy podgrzać"
elif temp_cwu < 55:
    status = "✅ OK (można podgrzać do 55-60°C)"
else:
    status = "✅ OPTYMALNE"
```

---

## Integracja z Byte Rover

Możesz dodać te temperatury do kontekstu Byte Rover:

```bash
brv curate "Temperatury HA: ext=$(ha_get temp_ext)°C, jadalnia=$(ha_get temp_jad)°C, CWU=$(ha_get temp_cwu)°C" @docs/CLAUDE_TEMPERATURES.md
```

---

## Troubleshooting

### Problem: "401 Unauthorized"
- Sprawdź czy token w `config/secrets.yaml` jest aktualny
- Token wygasa: 2036-01-20

### Problem: "Extra data" przy parsowaniu JSON
- Użyj `2>/dev/null` żeby usunąć stderr od curl
- Użyj `-s` (silent) w curl

### Problem: Brak połączenia
- Sprawdź czy Home Assistant działa: `curl https://ha.bodino.us.kg/api/`
- Sprawdź Cloudflare Tunnel

---

**Ostatnia aktualizacja:** 2026-02-01
**Testowane wartości:** -7.0°C / 21.84°C / 53.0°C
