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

    temps = {}
    for entity_id, label in sensors.items():
        temp = get_temperature(token, entity_id)
        temps[entity_id] = temp
        if temp is not None:
            print(f"{label:20} {temp:>6.1f}°C")
        else:
            print(f"{label:20} {'ERROR':>6}")

    print("=" * 40)

    # Dodatkowe analizy
    if all(temps.values()):
        temp_ext = temps['sensor.temperatura_zewnetrzna']
        temp_jad = temps['sensor.jadalnie_czujnik_temperatury_temperature']
        temp_cwu = temps['sensor.temperatura_cwu']

        delta = temp_jad - temp_ext
        print(f"\n🔍 Analiza:")
        print(f"   Różnica temp (jadalnia - zewn.): {delta:.1f}°C")

        # Status CWU
        if temp_cwu < 45:
            cwu_status = "🔴 KRYTYCZNE - podgrzej natychmiast"
        elif temp_cwu < 50:
            cwu_status = "⚠️  NISKIE - należy podgrzać"
        elif temp_cwu < 55:
            cwu_status = "✅ OK (można podgrzać do 55-60°C)"
        else:
            cwu_status = "✅ OPTYMALNE"

        print(f"   Status CWU: {cwu_status}")

if __name__ == "__main__":
    main()
