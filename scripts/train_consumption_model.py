#!/usr/bin/env python3
"""
Trenuje model ML do predykcji zużycia energii.

Model: RandomForestRegressor (scikit-learn)
Features:
- hour (0-23)
- day_of_week (0-6)
- is_weekend (0/1)
- is_holiday (0/1)
- month (1-12)
- is_heating_season (0/1)

Output: consumption_kwh (zużycie godzinowe)

Autor: Claude Code
Data: 2025-11-28
"""

import csv
import os
import pickle
import json
from datetime import datetime
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'ml_training_data.csv')
MODEL_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'consumption_model.pkl')
PROFILE_PATH = os.path.join(SCRIPT_DIR, '..', 'data', 'ml_hourly_profile.json')

# Polskie święta 2024-2026
POLISH_HOLIDAYS = {
    '2024-01-01', '2024-01-06', '2024-04-01', '2024-05-01', '2024-05-03',
    '2024-05-30', '2024-08-15', '2024-11-01', '2024-11-11', '2024-12-25', '2024-12-26',
    '2025-01-01', '2025-01-06', '2025-04-20', '2025-04-21', '2025-05-01',
    '2025-05-03', '2025-06-19', '2025-08-15', '2025-11-01', '2025-11-11',
    '2025-12-25', '2025-12-26',
    '2026-01-01', '2026-01-06', '2026-04-05', '2026-04-06', '2026-05-01',
    '2026-05-03', '2026-08-15', '2026-11-01', '2026-11-11', '2026-12-25', '2026-12-26',
}

HEATING_MONTHS = {10, 11, 12, 1, 2, 3}  # X-III


def is_holiday(date):
    """Check if date is a Polish holiday."""
    return date.strftime('%Y-%m-%d') in POLISH_HOLIDAYS


def is_weekend(date):
    """Check if date is weekend."""
    return date.weekday() >= 5


def is_heating_season(date):
    """Check if date is in heating season."""
    return date.month in HEATING_MONTHS


def extract_features(timestamp):
    """Extract ML features from timestamp."""
    if isinstance(timestamp, str):
        ts = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
    else:
        ts = timestamp

    return {
        'hour': ts.hour,
        'day_of_week': ts.weekday(),
        'is_weekend': 1 if is_weekend(ts) else 0,
        'is_holiday': 1 if is_holiday(ts) else 0,
        'month': ts.month,
        'is_heating_season': 1 if is_heating_season(ts) else 0,
        # Cyclical encoding for hour (sine/cosine)
        'hour_sin': np.sin(2 * np.pi * ts.hour / 24),
        'hour_cos': np.cos(2 * np.pi * ts.hour / 24),
        # Cyclical encoding for day of week
        'dow_sin': np.sin(2 * np.pi * ts.weekday() / 7),
        'dow_cos': np.cos(2 * np.pi * ts.weekday() / 7),
    }


def load_training_data():
    """Load and prepare training data."""
    X = []
    y = []

    with open(DATA_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                consumption = float(row['consumption_kwh'])
                if consumption <= 0 or consumption > 10:  # Filter outliers
                    continue

                features = extract_features(row['timestamp'])
                X.append([
                    features['hour'],
                    features['day_of_week'],
                    features['is_weekend'],
                    features['is_holiday'],
                    features['month'],
                    features['is_heating_season'],
                    features['hour_sin'],
                    features['hour_cos'],
                    features['dow_sin'],
                    features['dow_cos'],
                ])
                y.append(consumption)
            except (ValueError, KeyError):
                continue

    return np.array(X), np.array(y)


def train_model():
    """Train and evaluate the consumption prediction model."""
    print("=" * 60)
    print("TRENOWANIE MODELU ML - Predykcja zużycia energii")
    print("=" * 60)

    # Load data
    print("\n1. Ładowanie danych...")
    X, y = load_training_data()
    print(f"   Rekordów: {len(X)}")
    print(f"   Średnie zużycie: {y.mean():.2f} kWh")
    print(f"   Min/Max: {y.min():.2f} / {y.max():.2f} kWh")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"   Train: {len(X_train)}, Test: {len(X_test)}")

    # Train models and compare
    print("\n2. Trenowanie modeli...")

    models = {
        'RandomForest': RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        ),
        'GradientBoosting': GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
    }

    best_model = None
    best_score = float('inf')
    best_name = None

    for name, model in models.items():
        print(f"\n   {name}:")
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        print(f"     MAE:  {mae:.3f} kWh")
        print(f"     RMSE: {rmse:.3f} kWh")
        print(f"     R²:   {r2:.3f}")

        # Cross-validation
        cv_scores = cross_val_score(model, X, y, cv=5, scoring='neg_mean_absolute_error')
        cv_mae = -cv_scores.mean()
        print(f"     CV MAE: {cv_mae:.3f} kWh (±{cv_scores.std():.3f})")

        if mae < best_score:
            best_score = mae
            best_model = model
            best_name = name

    print(f"\n   Najlepszy model: {best_name} (MAE={best_score:.3f} kWh)")

    # Feature importance
    print("\n3. Ważność cech:")
    feature_names = [
        'hour', 'day_of_week', 'is_weekend', 'is_holiday',
        'month', 'is_heating_season', 'hour_sin', 'hour_cos',
        'dow_sin', 'dow_cos'
    ]

    if hasattr(best_model, 'feature_importances_'):
        importances = best_model.feature_importances_
        for name, imp in sorted(zip(feature_names, importances), key=lambda x: -x[1]):
            bar = '█' * int(imp * 50)
            print(f"   {name:<18} {imp:.3f} {bar}")

    # Save model
    print("\n4. Zapisywanie modelu...")
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)

    model_data = {
        'model': best_model,
        'model_name': best_name,
        'feature_names': feature_names,
        'metrics': {
            'mae': best_score,
            'rmse': rmse,
            'r2': r2,
        },
        'training_samples': len(X_train),
        'trained_at': datetime.now().isoformat(),
    }

    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model_data, f)
    print(f"   Zapisano: {MODEL_PATH}")

    # Generate predictions for profile
    print("\n5. Generowanie profilu godzinowego...")
    generate_hourly_profile(best_model)

    # Test predictions
    print("\n6. Przykładowe predykcje (jutro):")
    test_predictions(best_model)

    return best_model


def generate_hourly_profile(model):
    """Generate hourly profile from model predictions."""
    from datetime import timedelta

    # Predict for typical weekday and weekend
    now = datetime.now()
    tomorrow = now + timedelta(days=1)

    profile = {'by_hour': {}, 'by_hour_weekend': {}}

    # Weekday profile (Monday)
    test_date = datetime(2025, 11, 24)  # Monday
    for hour in range(24):
        ts = test_date.replace(hour=hour)
        features = extract_features(ts)
        X = np.array([[
            features['hour'], features['day_of_week'], features['is_weekend'],
            features['is_holiday'], features['month'], features['is_heating_season'],
            features['hour_sin'], features['hour_cos'], features['dow_sin'], features['dow_cos']
        ]])
        pred = model.predict(X)[0]
        profile['by_hour'][str(hour)] = round(pred, 2)

    # Weekend profile (Saturday)
    test_date = datetime(2025, 11, 29)  # Saturday
    for hour in range(24):
        ts = test_date.replace(hour=hour)
        features = extract_features(ts)
        X = np.array([[
            features['hour'], features['day_of_week'], features['is_weekend'],
            features['is_holiday'], features['month'], features['is_heating_season'],
            features['hour_sin'], features['hour_cos'], features['dow_sin'], features['dow_cos']
        ]])
        pred = model.predict(X)[0]
        profile['by_hour_weekend'][str(hour)] = round(pred, 2)

    # Add metadata
    profile['source'] = 'ml_model_trained'
    profile['model'] = 'RandomForest/GradientBoosting'
    profile['generated'] = datetime.now().isoformat()

    # Save profile
    with open(PROFILE_PATH, 'w') as f:
        json.dump(profile, f, indent=2)

    # Also save to config/data
    config_path = os.path.join(SCRIPT_DIR, '..', 'config', 'data', 'ml_hourly_profile.json')
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(profile, f, indent=2)

    print(f"   Zapisano profil: {PROFILE_PATH}")

    # Display profile
    print("\n   Profil godzinowy (dzień roboczy):")
    total = sum(profile['by_hour'].values())
    for h in range(24):
        val = profile['by_hour'][str(h)]
        bar = '█' * int(val * 3)
        zone = 'L2' if h in [22, 23, 0, 1, 2, 3, 4, 5, 13, 14] else 'L1'
        print(f"     {h:02d}:00  {val:5.2f} kWh  {zone}  {bar}")
    print(f"\n   Suma dzienna: {total:.1f} kWh")


def test_predictions(model):
    """Test model predictions for tomorrow."""
    from datetime import timedelta

    now = datetime.now()
    tomorrow = now + timedelta(days=1)

    total = 0
    l1_total = 0
    l2_total = 0

    print(f"   Data: {tomorrow.strftime('%Y-%m-%d')} ({['Pon', 'Wt', 'Śr', 'Czw', 'Pt', 'Sob', 'Nie'][tomorrow.weekday()]})")
    print()

    for hour in range(24):
        ts = tomorrow.replace(hour=hour, minute=0, second=0)
        features = extract_features(ts)
        X = np.array([[
            features['hour'], features['day_of_week'], features['is_weekend'],
            features['is_holiday'], features['month'], features['is_heating_season'],
            features['hour_sin'], features['hour_cos'], features['dow_sin'], features['dow_cos']
        ]])
        pred = model.predict(X)[0]

        is_wknd = features['is_weekend']
        if is_wknd or hour in [22, 23, 0, 1, 2, 3, 4, 5, 13, 14]:
            zone = 'L2'
            l2_total += pred
        else:
            zone = 'L1'
            l1_total += pred

        total += pred

        if hour in [0, 6, 12, 13, 18, 22]:
            print(f"     {hour:02d}:00  {pred:.2f} kWh  {zone}")

    print(f"\n   Suma:     {total:.1f} kWh")
    print(f"   L1 (droga): {l1_total:.1f} kWh ({l1_total/total*100:.0f}%)")
    print(f"   L2 (tania): {l2_total:.1f} kWh ({l2_total/total*100:.0f}%)")


def predict_consumption(model_path=MODEL_PATH):
    """Load model and predict consumption for next 24 hours."""
    from datetime import timedelta

    # Load model
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)

    model = model_data['model']

    now = datetime.now()
    predictions = {}

    for i in range(24):
        ts = now + timedelta(hours=i)
        ts = ts.replace(minute=0, second=0, microsecond=0)

        features = extract_features(ts)
        X = np.array([[
            features['hour'], features['day_of_week'], features['is_weekend'],
            features['is_holiday'], features['month'], features['is_heating_season'],
            features['hour_sin'], features['hour_cos'], features['dow_sin'], features['dow_cos']
        ]])

        pred = model.predict(X)[0]
        predictions[ts.strftime('%Y-%m-%d %H:00')] = round(pred, 2)

    return predictions


if __name__ == '__main__':
    train_model()
