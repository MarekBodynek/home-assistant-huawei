#!/usr/bin/env python3
"""
Export historical hourly energy data from Home Assistant for ML training.

Usage:
    python3 export_hourly_data.py --days 30 --output hourly_energy_history.csv

This script connects to HA API and exports hourly aggregated data for:
- Power consumption (sensor.pomiar_mocy_zuzycie)
- PV production (sensor.inwerter_calkowita_produkcja_energii)
- Grid export (sensor.pomiar_mocy_eksport)
- Battery charge/discharge
- SOC, tariff zone, temperature
"""

import argparse
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from collections import defaultdict
import csv
import os

# Configuration
HA_URL = os.environ.get('HA_URL', 'https://ha.bodino.us.kg')
HA_TOKEN = os.environ.get('HA_TOKEN', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJkNjRkYzVmY2FjYWY0MWQ0OGI5M2EyYjNiZTU4ZGRmMyIsImlhdCI6MTc2MzUwMDcyOCwiZXhwIjoyMDc4ODYwNzI4fQ.4GyI_6NVc477NLWVWjKEDb16faG5bTVyo3FgcN9Aspc')

# Sensors to export
SENSORS = {
    'consumption': 'sensor.pomiar_mocy_zuzycie',
    'pv_production': 'sensor.inwerter_calkowita_produkcja_energii',
    'grid_export': 'sensor.pomiar_mocy_eksport',
    'battery_charge': 'sensor.akumulatory_ladowania_dzienne',
    'battery_discharge': 'sensor.akumulatory_rozladowanie_dzienne',
    'soc': 'sensor.akumulatory_stan_pojemnosci',
    'tariff': 'sensor.strefa_taryfowa',
    'temperature': 'sensor.bateria_temperatura_maksymalna',
}


def fetch_history(entity_id: str, start_time: str, end_time: str) -> list:
    """Fetch history data from HA API."""
    url = f"{HA_URL}/api/history/period/{start_time}?filter_entity_id={entity_id}&end_time={end_time}"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode())
            if data and len(data) > 0:
                return data[0]
    except Exception as e:
        print(f"Error fetching {entity_id}: {e}")
    return []


def calculate_hourly_change(records: list) -> dict:
    """Calculate hourly change from total_increasing sensor."""
    hourly = defaultdict(lambda: {'first': None, 'last': None})

    for r in records:
        ts = r.get('last_changed', '')[:13]  # YYYY-MM-DDTHH
        try:
            val = float(r.get('state', 0))
            if hourly[ts]['first'] is None:
                hourly[ts]['first'] = val
            hourly[ts]['last'] = val
        except (ValueError, TypeError):
            pass

    # Calculate change for each hour
    result = {}
    for hour, vals in hourly.items():
        if vals['first'] is not None and vals['last'] is not None:
            result[hour] = vals['last'] - vals['first']

    return result


def get_hourly_state(records: list) -> dict:
    """Get the last state for each hour (for non-cumulative sensors like SOC, tariff)."""
    hourly = {}

    for r in records:
        ts = r.get('last_changed', '')[:13]  # YYYY-MM-DDTHH
        state = r.get('state')
        if state not in ['unavailable', 'unknown', None]:
            hourly[ts] = state

    return hourly


def export_data(days: int, output_file: str):
    """Export historical data to CSV."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)

    start_str = start_time.strftime('%Y-%m-%dT00:00:00Z')
    end_str = end_time.strftime('%Y-%m-%dT23:59:59Z')

    print(f"Fetching data from {start_str} to {end_str}...")

    # Fetch all sensor data
    data = {}
    for name, entity_id in SENSORS.items():
        print(f"  Fetching {name} ({entity_id})...")
        records = fetch_history(entity_id, start_str, end_str)

        if name in ['consumption', 'pv_production', 'grid_export', 'battery_charge', 'battery_discharge']:
            # Cumulative sensors - calculate hourly change
            data[name] = calculate_hourly_change(records)
        else:
            # State sensors - get last value per hour
            data[name] = get_hourly_state(records)

        print(f"    Found {len(data[name])} hourly records")

    # Get all unique hours
    all_hours = set()
    for sensor_data in data.values():
        all_hours.update(sensor_data.keys())

    all_hours = sorted(all_hours)
    print(f"\nTotal hours with data: {len(all_hours)}")

    # Write CSV
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'timestamp',
            'consumption_kwh',
            'pv_production_kwh',
            'grid_export_kwh',
            'battery_charge_kwh',
            'battery_discharge_kwh',
            'soc_percent',
            'tariff_zone',
            'temperature_c'
        ])

        for hour in all_hours:
            # Convert hour format: 2025-11-22T14 -> 2025-11-22 14:00:00
            ts = hour.replace('T', ' ') + ':00:00'

            row = [
                ts,
                round(data['consumption'].get(hour, 0), 3),
                round(data['pv_production'].get(hour, 0), 3),
                round(data['grid_export'].get(hour, 0), 3),
                round(data['battery_charge'].get(hour, 0), 3),
                round(data['battery_discharge'].get(hour, 0), 3),
                data['soc'].get(hour, ''),
                data['tariff'].get(hour, ''),
                data['temperature'].get(hour, ''),
            ]
            writer.writerow(row)

    print(f"\nExported {len(all_hours)} records to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Export hourly energy data from Home Assistant')
    parser.add_argument('--days', type=int, default=30, help='Number of days to export (default: 30)')
    parser.add_argument('--output', type=str, default='hourly_energy_history.csv', help='Output CSV file')

    args = parser.parse_args()
    export_data(args.days, args.output)


if __name__ == '__main__':
    main()
