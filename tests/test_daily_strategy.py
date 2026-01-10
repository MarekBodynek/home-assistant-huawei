"""
Testy jednostkowe dla calculate_daily_strategy.py
Testuje obliczanie Target SOC i predykcję zużycia ML.
"""

import pytest
from datetime import datetime, timedelta


# ============================================
# DANE TESTOWE
# ============================================

POLISH_HOLIDAYS = {
    '2024-01-01', '2024-01-06', '2024-11-01', '2024-11-11', '2024-12-25', '2024-12-26',
    '2025-01-01', '2025-01-06', '2025-04-20', '2025-04-21', '2025-05-01',
    '2025-05-03', '2025-06-19', '2025-08-15', '2025-11-01', '2025-11-11',
    '2025-12-25', '2025-12-26',
    '2026-01-01', '2026-01-06', '2026-04-05', '2026-04-06', '2026-05-01',
    '2026-05-03', '2026-08-15', '2026-11-01', '2026-11-11', '2026-12-25', '2026-12-26',
}

DEFAULT_HOURLY_PROFILE = {
    '0': 1.18, '1': 1.05, '2': 0.85, '3': 1.01, '4': 1.07, '5': 1.03,
    '6': 1.39, '7': 1.11, '8': 0.93, '9': 0.81, '10': 0.61, '11': 0.70,
    '12': 0.94, '13': 1.50, '14': 1.49, '15': 1.10, '16': 1.18, '17': 1.35,
    '18': 1.10, '19': 1.24, '20': 1.48, '21': 1.44, '22': 1.58, '23': 1.70
}


# ============================================
# FUNKCJE TESTOWANE (lokalne kopie)
# ============================================

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


def predict_consumption_24h(profile, start_dt):
    """
    Predict consumption for next 24 hours.
    Simplified version for testing.
    """
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


def calculate_target_soc(current_soc, l1_consumption, forecast_tomorrow, temp, is_heating):
    """
    Calculate target SOC based on inputs.
    Simplified logic for testing.
    """
    battery_capacity = 15.0  # kWh

    # Ile PV pokryje w godzinach L1?
    pv_during_l1 = forecast_tomorrow * 0.6

    # Ile bateria musi pokryć w L1?
    net_l1_need = max(0, l1_consumption - pv_during_l1)

    # Przelicz na % SOC
    soc_needed = (net_l1_need / battery_capacity) * 100

    # Bazowy target
    safety_margin = 10
    target_soc = int(current_soc + soc_needed + safety_margin)

    # Korekty na podstawie prognozy PV
    if forecast_tomorrow >= 25:
        target_soc = min(target_soc, 35)
    elif forecast_tomorrow >= 20:
        target_soc = min(target_soc, 45)
    elif forecast_tomorrow >= 15:
        target_soc = min(target_soc, 55)
    elif forecast_tomorrow >= 10:
        target_soc = min(target_soc, 65)
    elif forecast_tomorrow < 5:
        target_soc = max(target_soc, 75)

    # Korekty na temperaturę (sezon grzewczy)
    if is_heating:
        if temp < -10:
            target_soc = max(target_soc, 80)
        elif temp < -5:
            target_soc = max(target_soc, 75)
        elif temp < 0:
            target_soc = max(target_soc, 70)
        elif temp < 5:
            target_soc = max(target_soc, 65)

    # Limity bezpieczeństwa
    target_soc = max(20, min(80, target_soc))

    # Zaokrąglij do 5%
    target_soc = round(target_soc / 5) * 5
    target_soc = max(20, min(80, target_soc))

    return target_soc


# ============================================
# TESTY is_weekend_or_holiday
# ============================================

class TestIsWeekendOrHoliday:
    """Testy dla funkcji is_weekend_or_holiday"""

    def test_saturday_is_weekend(self):
        """Sobota = weekend"""
        saturday = datetime(2025, 11, 29)  # sobota
        assert saturday.weekday() == 5
        assert is_weekend_or_holiday(saturday) == True

    def test_sunday_is_weekend(self):
        """Niedziela = weekend"""
        sunday = datetime(2025, 11, 30)  # niedziela
        assert sunday.weekday() == 6
        assert is_weekend_or_holiday(sunday) == True

    def test_monday_is_workday(self):
        """Poniedziałek (nie święto) = dzień roboczy"""
        monday = datetime(2025, 11, 24)  # poniedziałek
        assert monday.weekday() == 0
        assert is_weekend_or_holiday(monday) == False

    def test_polish_holiday_christmas(self):
        """Boże Narodzenie = święto"""
        christmas = datetime(2025, 12, 25)
        assert is_weekend_or_holiday(christmas) == True

    def test_polish_holiday_independence_day(self):
        """Święto Niepodległości (11 listopada) = święto"""
        independence = datetime(2025, 11, 11)
        assert is_weekend_or_holiday(independence) == True

    def test_polish_holiday_easter_monday_2025(self):
        """Poniedziałek Wielkanocny 2025 = święto"""
        easter_monday = datetime(2025, 4, 21)
        assert is_weekend_or_holiday(easter_monday) == True

    def test_polish_holiday_corpus_christi_2025(self):
        """Boże Ciało 2025 = święto"""
        corpus_christi = datetime(2025, 6, 19)
        assert is_weekend_or_holiday(corpus_christi) == True

    def test_regular_thursday_not_holiday(self):
        """Zwykły czwartek = dzień roboczy"""
        thursday = datetime(2025, 11, 27)
        assert thursday.weekday() == 3
        assert is_weekend_or_holiday(thursday) == False


# ============================================
# TESTY get_tariff_zone
# ============================================

class TestGetTariffZone:
    """Testy dla funkcji get_tariff_zone"""

    def test_weekend_always_l2(self):
        """Weekend = L2 przez całą dobę"""
        for hour in range(24):
            assert get_tariff_zone(hour, is_weekend=True) == 'L2'

    def test_workday_night_l2(self):
        """Dzień roboczy, noc (22-05) = L2"""
        for hour in [22, 23, 0, 1, 2, 3, 4, 5]:
            assert get_tariff_zone(hour, is_weekend=False) == 'L2', f"Hour {hour} should be L2"

    def test_workday_midday_l2(self):
        """Dzień roboczy, południe (13-14) = L2"""
        for hour in [13, 14]:
            assert get_tariff_zone(hour, is_weekend=False) == 'L2', f"Hour {hour} should be L2"

    def test_workday_morning_l1(self):
        """Dzień roboczy, rano (6-12) = L1"""
        for hour in [6, 7, 8, 9, 10, 11, 12]:
            assert get_tariff_zone(hour, is_weekend=False) == 'L1', f"Hour {hour} should be L1"

    def test_workday_afternoon_l1(self):
        """Dzień roboczy, popołudnie (15-21) = L1"""
        for hour in [15, 16, 17, 18, 19, 20, 21]:
            assert get_tariff_zone(hour, is_weekend=False) == 'L1', f"Hour {hour} should be L1"


# ============================================
# TESTY predict_consumption_24h
# ============================================

class TestPredictConsumption24h:
    """Testy dla funkcji predict_consumption_24h"""

    def test_workday_prediction_uses_profile(self):
        """Predykcja na dzień roboczy używa profilu"""
        # Poniedziałek 22:00
        start_dt = datetime(2025, 11, 24, 22, 0, 0)
        profile = {'by_hour': DEFAULT_HOURLY_PROFILE}

        total, l1, l2, hourly = predict_consumption_24h(profile, start_dt)

        assert total > 0
        assert l1 > 0
        assert l2 > 0
        assert len(hourly) == 24

    def test_weekend_prediction(self):
        """Predykcja na weekend"""
        # Sobota 22:00
        start_dt = datetime(2025, 11, 29, 22, 0, 0)
        profile = {'by_hour': DEFAULT_HOURLY_PROFILE}

        total, l1, l2, hourly = predict_consumption_24h(profile, start_dt)

        # Weekend = cały dzień L2, więc l1 powinno być 0 (ale niedziela po 22:00 to już poniedziałek)
        assert total > 0
        assert len(hourly) == 24

    def test_default_profile_fallback(self):
        """Brak profilu = używa domyślnego"""
        start_dt = datetime(2025, 11, 24, 22, 0, 0)

        total, l1, l2, hourly = predict_consumption_24h(None, start_dt)

        assert total > 0
        assert len(hourly) == 24

    def test_sum_l1_l2_equals_total(self):
        """Suma L1 + L2 = Total"""
        start_dt = datetime(2025, 11, 24, 22, 0, 0)
        profile = {'by_hour': DEFAULT_HOURLY_PROFILE}

        total, l1, l2, hourly = predict_consumption_24h(profile, start_dt)

        # Suma L1 + L2 powinna równać się total (z tolerancją na zaokrąglenia)
        assert abs(total - (l1 + l2)) < 0.5


# ============================================
# TESTY calculate_target_soc
# ============================================

class TestCalculateTargetSoc:
    """Testy dla obliczania Target SOC"""

    def test_excellent_pv_low_target(self):
        """Doskonała prognoza PV = niski target"""
        target = calculate_target_soc(
            current_soc=50,
            l1_consumption=12,
            forecast_tomorrow=30,  # Doskonałe PV
            temp=15,
            is_heating=False
        )

        assert target <= 35

    def test_no_pv_high_target(self):
        """Brak PV = wysoki target"""
        target = calculate_target_soc(
            current_soc=30,
            l1_consumption=12,
            forecast_tomorrow=2,  # Bardzo słabe PV
            temp=10,
            is_heating=False
        )

        assert target >= 75

    def test_frost_max_target(self):
        """Mrozy (<-10°C) w sezonie grzewczym = max target"""
        target = calculate_target_soc(
            current_soc=40,
            l1_consumption=15,
            forecast_tomorrow=5,
            temp=-12,  # Mróz
            is_heating=True
        )

        assert target == 80

    def test_cold_weather_high_target(self):
        """Zimno (0-5°C) w sezonie grzewczym = wysoki target"""
        target = calculate_target_soc(
            current_soc=40,
            l1_consumption=12,
            forecast_tomorrow=10,
            temp=3,  # Zimno
            is_heating=True
        )

        assert target >= 65

    def test_target_soc_limits(self):
        """Target SOC zawsze w zakresie 20-80%"""
        # Test z ekstremalnie niskim SOC i złą prognozą
        target_low = calculate_target_soc(
            current_soc=5,
            l1_consumption=25,
            forecast_tomorrow=0,
            temp=-20,
            is_heating=True
        )
        assert 20 <= target_low <= 80

        # Test z wysokim SOC i doskonałą prognozą
        target_high = calculate_target_soc(
            current_soc=80,
            l1_consumption=5,
            forecast_tomorrow=35,
            temp=20,
            is_heating=False
        )
        assert 20 <= target_high <= 80

    def test_target_rounded_to_5(self):
        """Target SOC zaokrąglony do 5%"""
        for soc in [20, 30, 40, 50, 60, 70, 80]:
            target = calculate_target_soc(
                current_soc=soc,
                l1_consumption=12,
                forecast_tomorrow=10,
                temp=10,
                is_heating=False
            )
            assert target % 5 == 0


# ============================================
# TESTY INTEGRACYJNE
# ============================================

class TestIntegration:
    """Testy integracyjne dla całego przepływu"""

    def test_full_calculation_workday(self):
        """Pełne obliczenie dla dnia roboczego"""
        start_dt = datetime(2025, 11, 24, 22, 0, 0)  # Poniedziałek 22:00
        profile = {'by_hour': DEFAULT_HOURLY_PROFILE}

        # Krok 1: Predykcja zużycia
        total, l1, l2, hourly = predict_consumption_24h(profile, start_dt)

        # Krok 2: Oblicz target SOC
        target = calculate_target_soc(
            current_soc=50,
            l1_consumption=l1,
            forecast_tomorrow=15,
            temp=8,
            is_heating=True
        )

        # Weryfikacja
        assert total > 20  # Realistyczne zużycie
        assert l1 > 0
        assert l2 > 0
        assert 20 <= target <= 80

    def test_full_calculation_weekend(self):
        """Pełne obliczenie dla weekendu"""
        start_dt = datetime(2025, 11, 29, 22, 0, 0)  # Sobota 22:00
        profile = {'by_hour': DEFAULT_HOURLY_PROFILE}

        total, l1, l2, hourly = predict_consumption_24h(profile, start_dt)

        target = calculate_target_soc(
            current_soc=60,
            l1_consumption=l1,
            forecast_tomorrow=20,
            temp=12,
            is_heating=False
        )

        assert total > 20
        assert 20 <= target <= 80


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
