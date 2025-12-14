#!/usr/bin/env python3
"""
Konwertuje dane godzinowe z FusionSolar do formatu ML.

FusionSolar hourly nie ma consumption - obliczamy:
consumption = pv + grid_import + battery_discharge - grid_export - battery_charge
"""

import csv
import os
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FUSIONSOLAR_PATH = os.path.join(SCRIPT_DIR, 'fusionsolar_hourly_with_tariff.csv')
ML_OUTPUT_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'hourly_energy_history_fusionsolar.csv')


def convert_fusionsolar_to_ml():
    """Convert FusionSolar hourly data to ML format."""

    if not os.path.exists(FUSIONSOLAR_PATH):
        print(f"ERROR: File not found: {FUSIONSOLAR_PATH}")
        return

    records = []

    with open(FUSIONSOLAR_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                # Parse values
                pv = float(row.get('pv_kwh', 0) or 0)
                grid_import = float(row.get('grid_import_kwh', 0) or 0)
                grid_export = float(row.get('grid_export_kwh', 0) or 0)
                battery_charge = float(row.get('battery_charge_kwh', 0) or 0)
                battery_discharge = float(row.get('battery_discharge_kwh', 0) or 0)
                tariff = row.get('tariff_zone', '')

                # Calculate consumption (energy balance)
                # Sources: PV + Grid Import + Battery Discharge
                # Uses: Consumption + Grid Export + Battery Charge
                consumption = pv + grid_import + battery_discharge - grid_export - battery_charge
                consumption = max(0, consumption)  # Can't be negative

                # Convert timestamp format: "2025-11-17 00:00" -> "2025-11-17 00:00:00"
                timestamp = row['timestamp']
                if len(timestamp) == 16:  # "YYYY-MM-DD HH:MM"
                    timestamp += ':00'

                records.append({
                    'timestamp': timestamp,
                    'consumption_kwh': round(consumption, 2),
                    'pv_production_kwh': pv,
                    'grid_export_kwh': grid_export,
                    'battery_charge_kwh': battery_charge,
                    'battery_discharge_kwh': battery_discharge,
                    'soc_percent': '',  # Not available in FusionSolar hourly
                    'tariff_zone': tariff,
                    'temperature_c': ''  # Not available
                })

            except (ValueError, KeyError) as e:
                print(f"Skipping row: {e}")
                continue

    # Write ML format
    os.makedirs(os.path.dirname(ML_OUTPUT_PATH), exist_ok=True)

    with open(ML_OUTPUT_PATH, 'w', newline='') as f:
        fieldnames = ['timestamp', 'consumption_kwh', 'pv_production_kwh', 'grid_export_kwh',
                      'battery_charge_kwh', 'battery_discharge_kwh', 'soc_percent',
                      'tariff_zone', 'temperature_c']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Converted {len(records)} records to {ML_OUTPUT_PATH}")

    # Show sample
    print("\nSample (first 5 rows):")
    for r in records[:5]:
        print(f"  {r['timestamp']}: consumption={r['consumption_kwh']} kWh, "
              f"PV={r['pv_production_kwh']}, tariff={r['tariff_zone']}")

    # Stats
    consumptions = [r['consumption_kwh'] for r in records]
    print(f"\nStatistics:")
    print(f"  Total records: {len(records)}")
    print(f"  Total consumption: {sum(consumptions):.1f} kWh")
    print(f"  Avg hourly: {sum(consumptions)/len(consumptions):.2f} kWh")
    print(f"  Min: {min(consumptions):.2f} kWh")
    print(f"  Max: {max(consumptions):.2f} kWh")


if __name__ == '__main__':
    convert_fusionsolar_to_ml()
