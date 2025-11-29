#!/usr/bin/env python3
"""
Generuje dane treningowe ML na podstawie:
1. Profilu godzinowego z utility_meter (192h)
2. Danych dziennych z FusionSolar (rok historii)

Rozbija dzienne zużycie na godzinowe według profilu sezonu grzewczego.

WAŻNE: Korekta przesunięcia czasowego +1h
Dane z utility_meter mają przesunięcie o 1 godzinę wstecz:
- Zapis o 21:00 to w rzeczywistości dane z 22:00 (kiedy L2 się zaczyna)
- Zapis o 12:00 to w rzeczywistości dane z 13:00 (kiedy L2 południe się zaczyna)
Skrypt koryguje to dodając +1h do timestampów z HA.
"""

import csv
import os
from datetime import datetime, timedelta
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HA_HOURLY_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'hourly_energy_history.csv')
FUSIONSOLAR_DAILY_PATH = os.path.join(SCRIPT_DIR, 'fusionsolar_history_full.csv')
OUTPUT_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'ml_training_data.csv')

# Polskie święta 2024-2025
POLISH_HOLIDAYS = {
    '2024-01-01', '2024-01-06', '2024-04-01', '2024-05-01', '2024-05-03',
    '2024-05-30', '2024-08-15', '2024-11-01', '2024-11-11', '2024-12-25', '2024-12-26',
    '2025-01-01', '2025-01-06', '2025-04-20', '2025-04-21', '2025-05-01',
    '2025-05-03', '2025-06-19', '2025-08-15', '2025-11-01', '2025-11-11',
    '2025-12-25', '2025-12-26',
}


def is_weekend_or_holiday(date):
    """Check if date is weekend or holiday."""
    return date.weekday() >= 5 or date.strftime('%Y-%m-%d') in POLISH_HOLIDAYS


def get_tariff_zone(hour, is_weekend):
    """Get G12w tariff zone for given hour."""
    if is_weekend:
        return 'L2'
    if hour in [22, 23, 0, 1, 2, 3, 4, 5, 13, 14]:
        return 'L2'
    return 'L1'


def calculate_real_consumption(row):
    """
    Oblicza RZECZYWISTE zużycie domu z danych HA.

    PROBLEM: sensor.zuzycie_godzinowe = grid_import (zawiera ładowanie baterii!)

    ROZWIĄZANIE:
    real_consumption = grid_import - battery_charge + battery_discharge

    Gdzie:
    - grid_import = consumption_kwh (błędnie nazwane w danych)
    - battery_charge = energia użyta na ładowanie baterii
    - battery_discharge = energia oddana przez baterię do domu
    """
    grid_import = float(row.get('consumption_kwh', 0) or 0)
    battery_charge = float(row.get('battery_charge_kwh', 0) or 0)
    battery_discharge = float(row.get('battery_discharge_kwh', 0) or 0)

    # Rzeczywiste zużycie = import - ładowanie + rozładowanie
    real_consumption = grid_import - battery_charge + battery_discharge

    return max(0, real_consumption)  # Nie może być ujemne


def calculate_hourly_profile(ha_data):
    """
    Calculate hourly consumption profile from HA utility_meter data.
    Returns dict: {hour: percentage_of_daily} where sum = 1.0

    UWAGA: Używa RZECZYWISTEGO zużycia domu (po korekcie o baterię)

    KOREKTA CZASOWA: Dodaje +1h do timestampów z utility_meter.
    Dane z HA są przesunięte o 1 godzinę wstecz - zapis o 21:00 to 22:00 itp.
    """
    hourly_sums = defaultdict(float)
    hourly_counts = defaultdict(int)

    for row in ha_data:
        try:
            # POPRAWKA: Oblicz rzeczywiste zużycie (nie grid_import)
            consumption = calculate_real_consumption(row)
            if consumption <= 0:
                continue

            ts = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')

            # KOREKTA: Dodaj +1 godzinę do timestampu (dane są przesunięte wstecz)
            ts_corrected = ts + timedelta(hours=1)
            hour = ts_corrected.hour

            hourly_sums[hour] += consumption
            hourly_counts[hour] += 1
        except (ValueError, KeyError):
            continue

    # Calculate average for each hour
    hourly_avg = {}
    for hour in range(24):
        if hourly_counts[hour] > 0:
            hourly_avg[hour] = hourly_sums[hour] / hourly_counts[hour]
        else:
            hourly_avg[hour] = 0

    # Convert to percentage (sum = 1.0)
    total = sum(hourly_avg.values())
    if total > 0:
        profile = {h: v / total for h, v in hourly_avg.items()}
    else:
        # Default profile if no data
        profile = {h: 1/24 for h in range(24)}

    return profile, hourly_avg


def load_ha_hourly_data():
    """Load HA utility_meter hourly data."""
    data = []
    if not os.path.exists(HA_HOURLY_PATH):
        print(f"Warning: HA hourly data not found: {HA_HOURLY_PATH}")
        return data

    with open(HA_HOURLY_PATH, 'r') as f:
        reader = csv.DictReader(f)
        data = list(reader)

    print(f"Loaded {len(data)} rows from HA hourly data")
    return data


def load_fusionsolar_daily():
    """Load FusionSolar daily data."""
    data = []
    if not os.path.exists(FUSIONSOLAR_DAILY_PATH):
        print(f"Warning: FusionSolar daily data not found: {FUSIONSOLAR_DAILY_PATH}")
        return data

    with open(FUSIONSOLAR_DAILY_PATH, 'r') as f:
        reader = csv.DictReader(f)
        data = list(reader)

    print(f"Loaded {len(data)} days from FusionSolar")
    return data


def generate_hourly_from_daily(daily_data, hourly_profile):
    """
    Generate synthetic hourly data from daily FusionSolar data.
    Uses the hourly profile to distribute daily consumption.

    UWAGA: Profil z utility_meter to sezon grzewczy (XI 2025).
    Stosujemy go tylko do miesięcy grzewczych: X, XI, XII, I, II, III
    Miesiące letnie (IV-IX) pomijamy - inny profil zużycia.
    """
    hourly_records = []

    # Miesiące sezonu grzewczego
    HEATING_MONTHS = {10, 11, 12, 1, 2, 3}  # X-III

    for day in daily_data:
        try:
            date_str = day['date']
            date = datetime.strptime(date_str, '%Y-%m-%d')

            # Zastosuj profil tylko do sezonu grzewczego
            if date.month not in HEATING_MONTHS:
                continue  # Pomiń miesiące letnie

            daily_consumption = float(day.get('consumption_kwh', 0) or 0)
            daily_pv = float(day.get('pv_production_kwh', 0) or 0)
            daily_battery_charge = float(day.get('battery_charge_kwh', 0) or 0)
            daily_battery_discharge = float(day.get('battery_discharge_kwh', 0) or 0)
            daily_grid_export = float(day.get('grid_export_kwh', 0) or 0)

            if daily_consumption <= 0:
                continue

            is_weekend = is_weekend_or_holiday(date)

            # Generate 24 hourly records
            for hour in range(24):
                ts = date.replace(hour=hour)

                # Distribute based on profile
                pct = hourly_profile.get(hour, 1/24)

                # Consumption follows profile
                consumption = round(daily_consumption * pct, 2)

                # PV - distribute to daylight hours (7-17)
                if 7 <= hour <= 17:
                    pv_hours = 11
                    pv = round(daily_pv / pv_hours, 2)
                else:
                    pv = 0

                # Battery charge - mainly L2 hours (22-06, 13-15)
                tariff = get_tariff_zone(hour, is_weekend)
                if tariff == 'L2' and daily_battery_charge > 0:
                    # Count L2 hours
                    l2_hours = 10 if not is_weekend else 24
                    battery_charge = round(daily_battery_charge / l2_hours, 2)
                else:
                    battery_charge = 0

                # Battery discharge - mainly L1 hours
                if tariff == 'L1' and daily_battery_discharge > 0:
                    l1_hours = 14 if not is_weekend else 0
                    if l1_hours > 0:
                        battery_discharge = round(daily_battery_discharge / l1_hours, 2)
                    else:
                        battery_discharge = 0
                else:
                    battery_discharge = 0

                # Grid export - during PV hours
                if 9 <= hour <= 15 and daily_grid_export > 0:
                    grid_export = round(daily_grid_export / 7, 2)
                else:
                    grid_export = 0

                hourly_records.append({
                    'timestamp': ts.strftime('%Y-%m-%d %H:%M:%S'),
                    'consumption_kwh': consumption,
                    'pv_production_kwh': pv,
                    'grid_export_kwh': grid_export,
                    'battery_charge_kwh': battery_charge,
                    'battery_discharge_kwh': battery_discharge,
                    'soc_percent': '',
                    'tariff_zone': tariff,
                    'temperature_c': '',
                    'source': 'fusionsolar_synthetic'
                })

        except (ValueError, KeyError) as e:
            print(f"Skipping day {day}: {e}")
            continue

    return hourly_records


def main():
    print("=" * 60)
    print("Generowanie danych treningowych ML")
    print("=" * 60)

    # 1. Load HA hourly data and calculate profile
    ha_data = load_ha_hourly_data()

    if ha_data:
        profile, hourly_avg = calculate_hourly_profile(ha_data)

        print("\nProfil godzinowy (% dziennego zużycia):")
        print("-" * 40)
        for hour in range(24):
            bar = "█" * int(profile[hour] * 100)
            print(f"  {hour:02d}:00  {profile[hour]*100:5.2f}%  {hourly_avg[hour]:5.2f} kWh  {bar}")
        print(f"\n  SUMA: {sum(profile.values())*100:.1f}%")
        print(f"  Średnie dzienne: {sum(hourly_avg.values()):.1f} kWh")
    else:
        print("No HA data - using default profile")
        profile = {h: 1/24 for h in range(24)}

    # 2. Load FusionSolar daily data
    fs_daily = load_fusionsolar_daily()

    # 3. Generate synthetic hourly data
    if fs_daily:
        synthetic_hourly = generate_hourly_from_daily(fs_daily, profile)
        print(f"\nWygenerowano {len(synthetic_hourly)} syntetycznych rekordów godzinowych")
    else:
        synthetic_hourly = []

    # 4. Combine: HA real data + FusionSolar synthetic
    all_records = []

    # Add HA data with source marker and CORRECTED consumption + timestamp
    for row in ha_data:
        try:
            # POPRAWKA: Zamień grid_import na rzeczywiste zużycie domu
            real_cons = calculate_real_consumption(row)
            row['consumption_kwh'] = round(real_cons, 2)

            # KOREKTA CZASOWA: Dodaj +1h do timestampu
            ts = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
            ts_corrected = ts + timedelta(hours=1)
            row['timestamp'] = ts_corrected.strftime('%Y-%m-%d %H:%M:%S')

            row['source'] = 'ha_utility_meter_corrected_+1h'
            all_records.append(row)
        except (ValueError, KeyError):
            continue

    # Add synthetic data (only for dates not in HA data)
    # Użyj skorygowanych timestampów z all_records
    ha_dates = set()
    for row in all_records:
        try:
            ha_dates.add(row['timestamp'][:10])
        except:
            pass

    for row in synthetic_hourly:
        ts = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
        if ts.strftime('%Y-%m-%d') not in ha_dates:
            all_records.append(row)

    # Sort by timestamp
    all_records.sort(key=lambda x: x['timestamp'])

    # 5. Save combined data
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    fieldnames = ['timestamp', 'consumption_kwh', 'pv_production_kwh', 'grid_export_kwh',
                  'battery_charge_kwh', 'battery_discharge_kwh', 'soc_percent',
                  'tariff_zone', 'temperature_c', 'source']

    with open(OUTPUT_PATH, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_records)

    print(f"\n{'=' * 60}")
    print(f"ZAPISANO: {OUTPUT_PATH}")
    print(f"{'=' * 60}")
    print(f"  Rekordy z HA (real):        {len(ha_data)}")
    print(f"  Rekordy syntetyczne:        {len([r for r in all_records if r.get('source') == 'fusionsolar_synthetic'])}")
    print(f"  RAZEM:                      {len(all_records)}")

    # Stats
    consumptions = [float(r['consumption_kwh']) for r in all_records if r.get('consumption_kwh')]
    if consumptions:
        print(f"\nStatystyki zużycia:")
        print(f"  Suma:     {sum(consumptions):.1f} kWh")
        print(f"  Średnia:  {sum(consumptions)/len(consumptions):.2f} kWh/h")
        print(f"  Min:      {min(consumptions):.2f} kWh")
        print(f"  Max:      {max(consumptions):.2f} kWh")

    # Date range
    if all_records:
        dates = [r['timestamp'][:10] for r in all_records]
        print(f"\nZakres dat: {min(dates)} do {max(dates)}")
        print(f"Liczba dni: {len(set(dates))}")


if __name__ == '__main__':
    main()
