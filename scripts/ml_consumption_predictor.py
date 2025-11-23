#!/usr/bin/env python3
"""
ML Consumption Predictor - Predykcja zużycia energii na 24h

Model przewiduje zużycie energii dla każdej godziny na podstawie:
- Godziny dnia (0-23)
- Dnia tygodnia (0-6, 0=poniedziałek)
- Czy weekend/święto
- Miesiąca (sezonu)
- Historycznego zużycia z poprzednich dni

Używa XGBoost lub prostej średniej ważonej gdy brak danych.
"""

import json
import os
import pickle
from datetime import datetime, timedelta
from collections import defaultdict
import urllib.request
import csv

# Configuration
HA_URL = os.environ.get('HA_URL', 'https://ha.bodino.us.kg')
HA_TOKEN = os.environ.get('HA_TOKEN', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJkNjRkYzVmY2FjYWY0MWQ0OGI5M2EyYjNiZTU4ZGRmMyIsImlhdCI6MTc2MzUwMDcyOCwiZXhwIjoyMDc4ODYwNzI4fQ.4GyI_6NVc477NLWVWjKEDb16faG5bTVyo3FgcN9Aspc')
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'consumption_model.pkl')
HISTORY_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'hourly_energy_history.csv')

# Polskie święta 2024-2027
POLISH_HOLIDAYS = {
    # 2025
    '2025-01-01', '2025-01-06', '2025-04-20', '2025-04-21', '2025-05-01',
    '2025-05-03', '2025-06-19', '2025-08-15', '2025-11-01', '2025-11-11',
    '2025-12-25', '2025-12-26',
    # 2026
    '2026-01-01', '2026-01-06', '2026-04-05', '2026-04-06', '2026-05-01',
    '2026-05-03', '2026-05-28', '2026-08-15', '2026-11-01', '2026-11-11',
    '2026-12-25', '2026-12-26',
}


class ConsumptionPredictor:
    """Predictor for hourly energy consumption."""

    def __init__(self):
        self.model = None
        self.hourly_averages = defaultdict(lambda: defaultdict(list))  # [weekday][hour] -> [values]
        self.global_hourly_avg = defaultdict(list)  # [hour] -> [values]

    def load_history(self, csv_path: str = HISTORY_PATH):
        """Load historical data from CSV."""
        if not os.path.exists(csv_path):
            print(f"History file not found: {csv_path}")
            return False

        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        ts = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
                        consumption = float(row['consumption_kwh'])

                        if consumption > 0:  # Skip zero/invalid values
                            hour = ts.hour
                            weekday = ts.weekday()

                            self.hourly_averages[weekday][hour].append(consumption)
                            self.global_hourly_avg[hour].append(consumption)
                    except (ValueError, KeyError):
                        continue

            print(f"Loaded {sum(len(v) for h in self.hourly_averages.values() for v in h.values())} records")
            return True
        except Exception as e:
            print(f"Error loading history: {e}")
            return False

    def is_holiday(self, date: datetime) -> bool:
        """Check if date is a Polish holiday."""
        return date.strftime('%Y-%m-%d') in POLISH_HOLIDAYS

    def is_weekend_or_holiday(self, date: datetime) -> bool:
        """Check if date is weekend or holiday."""
        return date.weekday() >= 5 or self.is_holiday(date)

    def predict_hour(self, target_dt: datetime) -> float:
        """Predict consumption for a specific hour."""
        hour = target_dt.hour
        weekday = target_dt.weekday()
        is_weekend = self.is_weekend_or_holiday(target_dt)

        # Try specific weekday+hour average first
        if weekday in self.hourly_averages and hour in self.hourly_averages[weekday]:
            values = self.hourly_averages[weekday][hour]
            if len(values) >= 3:
                # Use weighted average (more recent = higher weight)
                weights = [1 + i * 0.1 for i in range(len(values))]
                weighted_avg = sum(v * w for v, w in zip(values, weights)) / sum(weights)
                return round(weighted_avg, 2)

        # Fall back to global hourly average
        if hour in self.global_hourly_avg:
            values = self.global_hourly_avg[hour]
            if values:
                return round(sum(values) / len(values), 2)

        # Default estimates based on typical household patterns
        # Higher consumption: morning (6-9), evening (17-22)
        # Lower consumption: night (0-5), midday (10-16)
        default_pattern = {
            0: 1.5, 1: 1.2, 2: 1.0, 3: 1.0, 4: 1.2, 5: 1.5,
            6: 2.5, 7: 3.0, 8: 2.5, 9: 2.0, 10: 1.8, 11: 2.0,
            12: 2.5, 13: 2.5, 14: 2.0, 15: 1.8, 16: 2.0, 17: 2.5,
            18: 3.0, 19: 3.5, 20: 3.0, 21: 2.5, 22: 2.0, 23: 1.8
        }

        base = default_pattern.get(hour, 2.0)
        # Weekend adjustment (-20% typically)
        if is_weekend:
            base *= 0.8

        return round(base, 2)

    def predict_24h(self, start_dt: datetime = None) -> dict:
        """Predict consumption for next 24 hours."""
        if start_dt is None:
            start_dt = datetime.now().replace(minute=0, second=0, microsecond=0)

        predictions = {}
        total = 0.0

        for i in range(24):
            target_dt = start_dt + timedelta(hours=i)
            hour_key = target_dt.strftime('%Y-%m-%d %H:00')
            consumption = self.predict_hour(target_dt)
            predictions[hour_key] = consumption
            total += consumption

        return {
            'predictions': predictions,
            'total_24h': round(total, 2),
            'average_hourly': round(total / 24, 2),
            'generated_at': datetime.now().isoformat()
        }


class OptimalSOCCalculator:
    """Calculate optimal Target SOC based on predictions and forecasts."""

    def __init__(self, predictor: ConsumptionPredictor):
        self.predictor = predictor
        self.battery_capacity = 15.0  # kWh usable capacity (Huawei Luna 2000)
        self.min_soc = 20  # Minimum safe SOC %
        self.max_soc = 80  # Maximum safe SOC %

    def get_pv_forecast(self) -> dict:
        """Fetch PV forecast from Home Assistant."""
        forecasts = {}
        sensors = [
            'sensor.prognoza_pv_dzisiaj',
            'sensor.prognoza_pv_jutro',
        ]

        for sensor in sensors:
            try:
                url = f"{HA_URL}/api/states/{sensor}"
                headers = {"Authorization": f"Bearer {HA_TOKEN}"}
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    forecasts[sensor] = float(data.get('state', 0))
            except Exception as e:
                print(f"Error fetching {sensor}: {e}")
                forecasts[sensor] = 0

        return forecasts

    def get_current_soc(self) -> float:
        """Get current battery SOC from Home Assistant."""
        try:
            url = f"{HA_URL}/api/states/sensor.akumulatory_stan_pojemnosci"
            headers = {"Authorization": f"Bearer {HA_TOKEN}"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                return float(data.get('state', 50))
        except Exception as e:
            print(f"Error fetching SOC: {e}")
            return 50.0

    def get_tariff_schedule(self, start_dt: datetime) -> dict:
        """Get tariff schedule for next 24h (G12w)."""
        schedule = {}

        for i in range(24):
            target_dt = start_dt + timedelta(hours=i)
            hour = target_dt.hour
            is_weekend = self.predictor.is_weekend_or_holiday(target_dt)

            # G12w tariff: L2 (cheap) 22:00-06:00, 13:00-15:00, weekends all day
            # L1 (expensive) rest
            if is_weekend:
                tariff = 'L2'
            elif hour in [22, 23, 0, 1, 2, 3, 4, 5, 13, 14]:
                tariff = 'L2'
            else:
                tariff = 'L1'

            hour_key = target_dt.strftime('%Y-%m-%d %H:00')
            schedule[hour_key] = {
                'tariff': tariff,
                'price': 0.72 if tariff == 'L2' else 1.11  # PLN/kWh approximate
            }

        return schedule

    def calculate_optimal_soc(self) -> dict:
        """Calculate optimal Target SOC for tonight's charging."""
        now = datetime.now()

        # Get predictions and forecasts
        consumption_pred = self.predictor.predict_24h(now)
        pv_forecast = self.get_pv_forecast()
        current_soc = self.get_current_soc()
        tariff_schedule = self.get_tariff_schedule(now)

        # Calculate energy needs
        total_consumption_24h = consumption_pred['total_24h']
        pv_today = pv_forecast.get('sensor.prognoza_pv_dzisiaj', 0)
        pv_tomorrow = pv_forecast.get('sensor.prognoza_pv_jutro', 0)

        # Calculate L1 consumption (expensive hours)
        l1_consumption = 0
        l2_consumption = 0

        for hour_key, consumption in consumption_pred['predictions'].items():
            tariff_info = tariff_schedule.get(hour_key, {})
            if tariff_info.get('tariff') == 'L1':
                l1_consumption += consumption
            else:
                l2_consumption += consumption

        # Energy balance calculation
        # We want battery to cover L1 consumption
        # PV will help during daytime L1 hours

        # Estimate PV contribution during L1 hours (rough: 60% of daily PV)
        pv_during_l1 = pv_tomorrow * 0.6 if now.hour >= 22 else pv_today * 0.6

        # Net energy needed from battery during L1
        net_l1_need = max(0, l1_consumption - pv_during_l1)

        # Convert to SOC percentage
        soc_needed = (net_l1_need / self.battery_capacity) * 100

        # Calculate target SOC
        # Start with what we need for L1, add safety margin
        safety_margin = 10  # %
        optimal_soc = min(self.max_soc, max(self.min_soc,
                                             current_soc + soc_needed + safety_margin))

        # Adjustments based on PV forecast
        if pv_tomorrow >= 25:
            # Excellent PV - don't charge much, PV will handle it
            optimal_soc = min(optimal_soc, 40)
        elif pv_tomorrow >= 20:
            # Good PV - charge less
            optimal_soc = min(optimal_soc, 50)
        elif pv_tomorrow >= 15:
            # Moderate PV
            optimal_soc = min(optimal_soc, 60)
        elif pv_tomorrow < 10:
            # Poor PV - charge more
            optimal_soc = max(optimal_soc, 70)
        elif pv_tomorrow < 5:
            # Very poor PV - charge to max
            optimal_soc = self.max_soc

        # Round to nearest 5%
        optimal_soc = round(optimal_soc / 5) * 5
        optimal_soc = max(self.min_soc, min(self.max_soc, optimal_soc))

        return {
            'optimal_target_soc': int(optimal_soc),
            'current_soc': round(current_soc, 1),
            'reasoning': {
                'total_consumption_24h': round(total_consumption_24h, 1),
                'l1_consumption': round(l1_consumption, 1),
                'l2_consumption': round(l2_consumption, 1),
                'pv_today': pv_today,
                'pv_tomorrow': pv_tomorrow,
                'pv_during_l1_estimate': round(pv_during_l1, 1),
                'net_l1_need': round(net_l1_need, 1),
                'soc_needed_percent': round(soc_needed, 1),
            },
            'consumption_predictions': consumption_pred['predictions'],
            'tariff_schedule': tariff_schedule,
            'generated_at': datetime.now().isoformat()
        }


def main():
    """Main function - calculate and display optimal SOC."""
    import argparse

    parser = argparse.ArgumentParser(description='ML Consumption Predictor & Optimal SOC Calculator')
    parser.add_argument('--predict', action='store_true', help='Show 24h consumption prediction')
    parser.add_argument('--optimal-soc', action='store_true', help='Calculate optimal Target SOC')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    # Initialize predictor
    predictor = ConsumptionPredictor()
    predictor.load_history()

    if args.predict or (not args.predict and not args.optimal_soc):
        prediction = predictor.predict_24h()

        if args.json:
            print(json.dumps(prediction, indent=2))
        else:
            print("\n=== Predykcja zużycia na 24h ===\n")
            for hour, consumption in prediction['predictions'].items():
                print(f"  {hour}: {consumption:.2f} kWh")
            print(f"\n  SUMA: {prediction['total_24h']:.1f} kWh")
            print(f"  Średnia: {prediction['average_hourly']:.2f} kWh/h")

    if args.optimal_soc:
        calculator = OptimalSOCCalculator(predictor)
        result = calculator.calculate_optimal_soc()

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("\n=== Optymalny Target SOC ===\n")
            print(f"  Zalecany Target SOC: {result['optimal_target_soc']}%")
            print(f"  Aktualny SOC: {result['current_soc']}%")
            print(f"\n  Uzasadnienie:")
            r = result['reasoning']
            print(f"    - Zużycie 24h: {r['total_consumption_24h']} kWh")
            print(f"    - Zużycie L1 (droga): {r['l1_consumption']} kWh")
            print(f"    - Zużycie L2 (tania): {r['l2_consumption']} kWh")
            print(f"    - Prognoza PV dziś: {r['pv_today']} kWh")
            print(f"    - Prognoza PV jutro: {r['pv_tomorrow']} kWh")
            print(f"    - PV w godzinach L1: ~{r['pv_during_l1_estimate']} kWh")
            print(f"    - Netto potrzeba z baterii: {r['net_l1_need']} kWh")


if __name__ == '__main__':
    main()
