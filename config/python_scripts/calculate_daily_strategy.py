"""
Oblicza strategię dzienną - cel ładowania baterii (Target SOC)
Uruchamiany o 21:05 (przed rozpoczęciem doby energetycznej 22:00-21:59)

INTEGRACJA ML:
- Używa profilu godzinowego z data/ml_hourly_profile.json
- Predykcja zużycia na 24h na podstawie ~5000 godzin historii
- Oblicza zużycie L1 vs L2 i optymalny Target SOC

Autor: Claude Code
Data: 2025-11-27
"""

import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger("calculate_daily_strategy")

# Polskie święta 2024-2026
POLISH_HOLIDAYS = {
    '2024-01-01', '2024-01-06', '2024-11-01', '2024-11-11', '2024-12-25', '2024-12-26',
    '2025-01-01', '2025-01-06', '2025-04-20', '2025-04-21', '2025-05-01',
    '2025-05-03', '2025-06-19', '2025-08-15', '2025-11-01', '2025-11-11',
    '2025-12-25', '2025-12-26',
    '2026-01-01', '2026-01-06', '2026-04-05', '2026-04-06', '2026-05-01',
    '2026-05-03', '2026-08-15', '2026-11-01', '2026-11-11', '2026-12-25', '2026-12-26',
}

# Domyślny profil godzinowy (sezon grzewczy) - używany gdy brak pliku JSON
# WYGENEROWANY 2025-11-28 przez model ML (GradientBoosting, MAE=0.35 kWh)
# Bazuje na ~4900 godzin danych (HA utility_meter + FusionSolar synthetic)
# Suma dzienna: ~28 kWh (L1: ~14 kWh, L2: ~14 kWh)
DEFAULT_HOURLY_PROFILE = {
    '0': 1.18, '1': 1.05, '2': 0.85, '3': 1.01, '4': 1.07, '5': 1.03,
    '6': 1.39, '7': 1.11, '8': 0.93, '9': 0.81, '10': 0.61, '11': 0.70,
    '12': 0.94, '13': 1.50, '14': 1.49, '15': 1.10, '16': 1.18, '17': 1.35,
    '18': 1.10, '19': 1.24, '20': 1.48, '21': 1.44, '22': 1.58, '23': 1.70
}


def is_weekend_or_holiday(date):
    """Check if date is weekend or Polish holiday."""
    return date.weekday() >= 5 or date.strftime('%Y-%m-%d') in POLISH_HOLIDAYS


def get_tariff_zone(hour, is_weekend):
    """Get G12w tariff zone for given hour."""
    if is_weekend:
        return 'L2'
    # L2: 22:00-06:00 i 13:00-15:00
    if hour in [22, 23, 0, 1, 2, 3, 4, 5, 13, 14]:
        return 'L2'
    return 'L1'


def load_ml_profile():
    """Load ML hourly profile from JSON file."""
    try:
        with open('/config/data/ml_hourly_profile.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load ML profile: {e}, using default")
        return None


def predict_consumption_24h(profile, start_hour=22):
    """
    Predict consumption for next 24 hours (energy day 22:00-21:59).
    Returns: total_24h, l1_consumption, l2_consumption, hourly_predictions

    INTEGRACJA ML:
    - Używa by_hour dla dni roboczych
    - Używa by_hour_weekend dla weekendów/świąt (jeśli dostępny)
    - Fallback do DEFAULT_HOURLY_PROFILE gdy brak danych
    """
    now = datetime.now()

    # Doba energetyczna: 22:00 dziś -> 21:59 jutro
    if start_hour == 22:
        start_dt = now.replace(hour=22, minute=0, second=0, microsecond=0)
    else:
        start_dt = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)

    # Profile z ML modelu
    weekday_profile = profile.get('by_hour', DEFAULT_HOURLY_PROFILE) if profile else DEFAULT_HOURLY_PROFILE
    weekend_profile = profile.get('by_hour_weekend', None) if profile else None

    total = 0.0
    l1_total = 0.0
    l2_total = 0.0
    predictions = {}

    for i in range(24):
        target_dt = start_dt + timedelta(hours=i)
        hour = target_dt.hour
        is_weekend = is_weekend_or_holiday(target_dt)
        tariff = get_tariff_zone(hour, is_weekend)

        # Wybierz odpowiedni profil (weekend vs dzień roboczy)
        if is_weekend and weekend_profile:
            consumption = float(weekend_profile.get(str(hour), 1.5))
        else:
            consumption = float(weekday_profile.get(str(hour), 1.5))

        predictions[target_dt.strftime('%H:00')] = round(consumption, 2)
        total += consumption

        if tariff == 'L1':
            l1_total += consumption
        else:
            l2_total += consumption

    return round(total, 1), round(l1_total, 1), round(l2_total, 1), predictions


def calculate_daily_strategy():
    """
    Oblicza cel ładowania na dobę energetyczną 22:00-21:59.
    Używa ML do predykcji zużycia zamiast stałych wartości.
    """
    try:
        # Pobierz dane z Home Assistant
        forecast_state = hass.states.get('sensor.prognoza_pv_jutro')
        temp_state = hass.states.get('sensor.temperatura_zewnetrzna')
        heating_state = hass.states.get('binary_sensor.sezon_grzewczy')
        current_soc_state = hass.states.get('sensor.akumulatory_stan_pojemnosci')

        # Parse wartości z bezpieczną obsługą błędów
        forecast_tomorrow = 0.0
        if forecast_state and forecast_state.state not in ['unknown', 'unavailable', None]:
            try:
                forecast_tomorrow = float(forecast_state.state)
            except (ValueError, TypeError):
                pass

        temp = 10.0
        if temp_state and temp_state.state not in ['unknown', 'unavailable', None]:
            try:
                temp = float(temp_state.state)
            except (ValueError, TypeError):
                pass

        current_soc = 50.0
        if current_soc_state and current_soc_state.state not in ['unknown', 'unavailable', None]:
            try:
                current_soc = float(current_soc_state.state)
            except (ValueError, TypeError):
                pass

        heating_mode = 'heating_season' if (heating_state and heating_state.state == 'on') else 'no_heating'
        is_heating = heating_mode == 'heating_season'

        # === PREDYKCJA ML ===
        ml_profile = load_ml_profile()
        total_24h, l1_consumption, l2_consumption, hourly_pred = predict_consumption_24h(ml_profile)

        logger.info(f"ML Prediction: total={total_24h}kWh, L1={l1_consumption}kWh, L2={l2_consumption}kWh")

        # === OBLICZENIE TARGET SOC ===
        battery_capacity = 15.0  # kWh (Huawei Luna 2000)

        # Ile PV pokryje w godzinach L1? (szacunek: 60% produkcji PV w L1)
        pv_during_l1 = forecast_tomorrow * 0.6

        # Ile bateria musi pokryć w L1?
        net_l1_need = max(0, l1_consumption - pv_during_l1)

        # Przelicz na % SOC
        soc_needed = (net_l1_need / battery_capacity) * 100

        # Bazowy target = aktualny SOC + potrzeba + margines bezpieczeństwa
        safety_margin = 10  # %
        target_soc = int(current_soc + soc_needed + safety_margin)

        # === KOREKTY NA PODSTAWIE PROGNOZY PV ===
        if forecast_tomorrow >= 25:
            # Doskonałe PV - nie ładuj dużo
            target_soc = min(target_soc, 35)
        elif forecast_tomorrow >= 20:
            target_soc = min(target_soc, 45)
        elif forecast_tomorrow >= 15:
            target_soc = min(target_soc, 55)
        elif forecast_tomorrow >= 10:
            target_soc = min(target_soc, 65)
        elif forecast_tomorrow < 5:
            # Bardzo słabe PV - ładuj maksymalnie
            target_soc = max(target_soc, 75)

        # === KOREKTY NA TEMPERATURĘ (sezon grzewczy) ===
        if is_heating:
            if temp < -10:
                target_soc = max(target_soc, 80)  # Mrozy - pełne ładowanie
            elif temp < -5:
                target_soc = max(target_soc, 75)
            elif temp < 0:
                target_soc = max(target_soc, 70)
            elif temp < 5:
                target_soc = max(target_soc, 65)

        # === LIMITY BEZPIECZEŃSTWA ===
        target_soc = max(20, min(80, target_soc))  # Huawei: 20-80%

        # Zaokrąglij do 5%
        target_soc = round(target_soc / 5) * 5
        target_soc = max(20, min(80, target_soc))

        # === ZAPISZ TARGET SOC ===
        hass.services.call('input_number', 'set_value', {
            'entity_id': 'input_number.battery_target_soc',
            'value': target_soc
        })

        # === UZASADNIENIE ===
        reason_parts = [
            f"ML: {total_24h}kWh/24h",
            f"L1={l1_consumption}kWh",
            f"L2={l2_consumption}kWh",
            f"PV={forecast_tomorrow:.0f}kWh",
            f"netto L1={net_l1_need:.0f}kWh"
        ]
        if is_heating:
            reason_parts.append(f"temp={temp:.0f}°C")
        reason = ', '.join(reason_parts)

        logger.info(f"Daily strategy: Target SOC = {target_soc}% | {reason}")

        # === NOTYFIKACJA ===
        message = f"""**Target SOC:** {target_soc}%

**Predykcja ML (doba 22:00-21:59):**
- Zużycie 24h: {total_24h} kWh
- 🔴 L1 (droga): {l1_consumption} kWh
- 🟢 L2 (tania): {l2_consumption} kWh

**Bilans energii:**
- Prognoza PV: {forecast_tomorrow:.1f} kWh
- PV w L1 (~60%): {pv_during_l1:.1f} kWh
- Potrzeba z baterii: {net_l1_need:.1f} kWh

**Warunki:**
- Temperatura: {temp:.1f}°C
- Sezon grzewczy: {'TAK' if is_heating else 'NIE'}
- Aktualny SOC: {current_soc:.0f}%"""

        hass.services.call('persistent_notification', 'create', {
            'title': '📊 Strategia ML obliczona (21:05)',
            'message': message,
            'notification_id': 'daily_strategy_ml'
        })

        return {
            'target_soc': target_soc,
            'total_24h': total_24h,
            'l1_consumption': l1_consumption,
            'l2_consumption': l2_consumption,
            'forecast_pv': forecast_tomorrow,
            'temp': temp,
            'heating_mode': heating_mode
        }

    except Exception as e:
        logger.error(f"Błąd obliczania strategii ML: {e}")
        # Fallback do prostej strategii
        hass.services.call('input_number', 'set_value', {
            'entity_id': 'input_number.battery_target_soc',
            'value': 70
        })
        return None


# Uruchom
calculate_daily_strategy()
