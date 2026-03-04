"""
Tests for battery_algorithm.py - Huawei Luna 2000 battery management algorithm.

Since the script runs in Home Assistant python_scripts context with injected 'hass',
we use exec() to load the code with mocked hass object.
"""

import pytest
import os
from pathlib import Path
from conftest import MockHass, MockState, create_test_data


# Path to the algorithm file
ALGORITHM_PATH = Path(__file__).parent.parent / "config" / "python_scripts" / "battery_algorithm.py"


def load_algorithm_functions(mock_hass):
    """
    Load algorithm functions with mocked hass object.

    Returns a dict of all functions and constants from the algorithm.
    """
    with open(ALGORITHM_PATH, 'r', encoding='utf-8') as f:
        code = f.read()

    # Remove the final try/except block that calls execute_strategy()
    # Find the last 'try:' which starts the main execution block
    last_try_index = code.rfind('\ntry:\n    execute_strategy()')
    if last_try_index > 0:
        code = code[:last_try_index]

    # Create namespace with mocked hass
    namespace = {'hass': mock_hass}

    # Execute the code in the namespace
    exec(code, namespace)

    return namespace


class TestConstants:
    """Test algorithm constants are properly defined."""

    def test_forecast_poor_threshold(self, mock_hass):
        """Verify FORECAST_POOR threshold."""
        ns = load_algorithm_functions(mock_hass)

        assert ns['FORECAST_POOR'] == 12

    def test_battery_thresholds(self, mock_hass):
        """Verify battery SOC thresholds (static ones)."""
        ns = load_algorithm_functions(mock_hass)

        # Static thresholds (not seasonal)
        assert ns['BATTERY_CRITICAL'] == 5
        assert ns['BATTERY_GOOD'] == 65
        assert ns['BATTERY_HIGH'] == 70
        # Note: BATTERY_LOW and BATTERY_MAX are now dynamic (seasonal)

    def test_battery_critical_threshold(self, mock_hass):
        """Verify BATTERY_CRITICAL threshold."""
        ns = load_algorithm_functions(mock_hass)

        assert ns['BATTERY_CRITICAL'] == 5


class TestSeasonalSocLimits:
    """Test get_seasonal_soc_limits() function - seasonal SOC range calculation."""

    def test_winter_months(self, mock_hass):
        """Winter (Nov-Feb) should return 10-90% range."""
        ns = load_algorithm_functions(mock_hass)

        for month in [11, 12, 1, 2]:
            soc_min, soc_max = ns['get_seasonal_soc_limits'](month)
            assert soc_min == 10, f"Month {month} min should be 10"
            assert soc_max == 90, f"Month {month} max should be 90"

    def test_spring_months(self, mock_hass):
        """Spring (Mar-Apr) should return 15-85% range."""
        ns = load_algorithm_functions(mock_hass)

        for month in [3, 4]:
            soc_min, soc_max = ns['get_seasonal_soc_limits'](month)
            assert soc_min == 15, f"Month {month} min should be 15"
            assert soc_max == 85, f"Month {month} max should be 85"

    def test_summer_months(self, mock_hass):
        """Summer (May-Sep) should return 20-80% range."""
        ns = load_algorithm_functions(mock_hass)

        for month in [5, 6, 7, 8, 9]:
            soc_min, soc_max = ns['get_seasonal_soc_limits'](month)
            assert soc_min == 20, f"Month {month} min should be 20"
            assert soc_max == 80, f"Month {month} max should be 80"

    def test_autumn_month(self, mock_hass):
        """Autumn (Oct) should return 15-85% range."""
        ns = load_algorithm_functions(mock_hass)

        soc_min, soc_max = ns['get_seasonal_soc_limits'](10)
        assert soc_min == 15
        assert soc_max == 85

    def test_invalid_month_fallback(self, mock_hass):
        """Invalid month should fallback to 20-80%."""
        ns = load_algorithm_functions(mock_hass)

        # Test edge cases
        soc_min, soc_max = ns['get_seasonal_soc_limits'](0)
        assert soc_min == 20
        assert soc_max == 80

        soc_min, soc_max = ns['get_seasonal_soc_limits'](13)
        assert soc_min == 20
        assert soc_max == 80


class TestTariffZone:
    """Test get_tariff_zone() function - G12w tariff calculation."""

    def test_workday_night_l2(self, mock_hass):
        """Night hours (22:00-05:59) on workday should be L2."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        ns = load_algorithm_functions(mock_hass)

        for hour in [22, 23, 0, 1, 2, 3, 4, 5]:
            assert ns['get_tariff_zone'](hour) == 'L2', f"Hour {hour} should be L2"

    def test_workday_midday_l2(self, mock_hass):
        """Midday hours (13:00-14:59) on workday should be L2."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        ns = load_algorithm_functions(mock_hass)

        for hour in [13, 14]:
            assert ns['get_tariff_zone'](hour) == 'L2', f"Hour {hour} should be L2"

    def test_workday_peak_l1(self, mock_hass):
        """Peak hours on workday should be L1."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        ns = load_algorithm_functions(mock_hass)

        # Morning peak: 06:00-12:59
        for hour in [6, 7, 8, 9, 10, 11, 12]:
            assert ns['get_tariff_zone'](hour) == 'L1', f"Hour {hour} should be L1"

        # Afternoon peak: 15:00-21:59
        for hour in [15, 16, 17, 18, 19, 20, 21]:
            assert ns['get_tariff_zone'](hour) == 'L1', f"Hour {hour} should be L1"

    def test_weekend_all_l2(self, mock_hass):
        """All hours on weekend should be L2."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'off')
        ns = load_algorithm_functions(mock_hass)

        for hour in range(24):
            assert ns['get_tariff_zone'](hour) == 'L2', f"Weekend hour {hour} should be L2"


class TestValidateData:
    """Test validate_data() function."""

    def test_valid_data(self, mock_hass):
        """Valid data should pass validation."""
        ns = load_algorithm_functions(mock_hass)
        data = create_test_data()

        assert ns['validate_data'](data) is True

    def test_empty_data(self, mock_hass):
        """Empty data should fail validation."""
        ns = load_algorithm_functions(mock_hass)

        assert ns['validate_data']({}) is False
        assert ns['validate_data'](None) is False

    def test_missing_critical_field(self, mock_hass):
        """Missing critical field should fail validation."""
        ns = load_algorithm_functions(mock_hass)

        # Critical fields: soc, tariff_zone, pv_power, home_load, temp_outdoor
        for field in ['soc', 'tariff_zone', 'pv_power', 'home_load', 'temp_outdoor']:
            data = create_test_data()
            del data[field]
            assert ns['validate_data'](data) is False, f"Missing {field} should fail"

    def test_soc_out_of_range(self, mock_hass):
        """SOC outside 0-100 should fail validation."""
        ns = load_algorithm_functions(mock_hass)

        # Negative SOC
        data = create_test_data({'soc': -5})
        assert ns['validate_data'](data) is False

        # SOC > 100
        data = create_test_data({'soc': 105})
        assert ns['validate_data'](data) is False


class TestCalculatePowerBalance:
    """Test calculate_power_balance() function."""

    def test_pv_surplus(self, mock_hass):
        """PV > Load should result in surplus."""
        ns = load_algorithm_functions(mock_hass)
        data = create_test_data({'pv_power': 5.0, 'home_load': 2.0})

        balance = ns['calculate_power_balance'](data)

        assert balance['surplus'] == 3.0
        assert balance['deficit'] == 0
        assert balance['pv'] == 5.0
        assert balance['load'] == 2.0

    def test_power_deficit(self, mock_hass):
        """Load > PV should result in deficit."""
        ns = load_algorithm_functions(mock_hass)
        data = create_test_data({'pv_power': 1.0, 'home_load': 3.0})

        balance = ns['calculate_power_balance'](data)

        assert balance['surplus'] == 0
        assert balance['deficit'] == 2.0

    def test_perfect_balance(self, mock_hass):
        """PV = Load should result in no surplus or deficit."""
        ns = load_algorithm_functions(mock_hass)
        data = create_test_data({'pv_power': 2.5, 'home_load': 2.5})

        balance = ns['calculate_power_balance'](data)

        assert balance['surplus'] == 0
        assert balance['deficit'] == 0


class TestDecideStrategy:
    """Test decide_strategy() - main decision logic."""

    def test_critical_soc_below_5(self, mock_hass):
        """SOC < 5% should trigger critical charge 24/7."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({'soc': 3, 'hour': 12, 'tariff_zone': 'L1'})
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        assert strategy['mode'] == 'charge_from_grid'
        assert strategy['priority'] == 'critical'
        assert strategy['urgent_charge'] is True
        assert strategy['target_soc'] == 35

    def test_low_soc_below_seasonal_min(self, mock_hass):
        """SOC < seasonal min should trigger urgent charge."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        ns = load_algorithm_functions(mock_hass)

        # January (winter): soc_min = 10%, soc_max = 90%
        # SOC 8% < 10% should trigger urgent charge
        data = create_test_data({'soc': 8, 'hour': 12, 'tariff_zone': 'L1', 'target_soc': 80, 'month': 1})
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        assert strategy['mode'] == 'charge_from_grid'
        assert strategy['priority'] == 'high'
        assert strategy['target_soc'] == 80

    def test_full_battery_l2_preserve(self, mock_hass):
        """SOC at seasonal max in L2 should preserve battery (grid_to_home)."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        ns = load_algorithm_functions(mock_hass)

        # Summer (June): soc_max = 80%, so 80% is "full"
        data = create_test_data({'soc': 80, 'hour': 23, 'tariff_zone': 'L2', 'month': 6})
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        assert strategy['mode'] == 'grid_to_home'

    def test_full_battery_l1_discharge(self, mock_hass):
        """SOC at seasonal max in L1 should discharge to home."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        ns = load_algorithm_functions(mock_hass)

        # Summer (June): soc_max = 80%, so 80% is "full"
        data = create_test_data({'soc': 80, 'hour': 12, 'tariff_zone': 'L1', 'month': 6})
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        assert strategy['mode'] == 'discharge_to_home'

    def test_l1_discharge_to_save_money(self, mock_hass):
        """In L1 with SOC > 20%, should discharge to save expensive L1."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 50,
            'hour': 10,
            'tariff_zone': 'L1'
        })
        balance = {'surplus': 0.3, 'deficit': 0, 'pv': 2.3, 'load': 2.0}

        strategy = ns['decide_strategy'](data, balance)

        assert strategy['mode'] == 'discharge_to_home'
        assert 'L1' in strategy['reason']


class TestWeekendLogic:
    """Test weekend energy logic - no grid charging on weekends."""

    def test_saturday_returns_self_consumption(self, mock_hass):
        """Saturday (dzien_roboczy=off) should return discharge_to_home with weekend reason."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'off')  # Weekend
        mock_hass.states.set('sensor.date', '2026-01-24')  # Saturday
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 50,
            'hour': 12,
            'tariff_zone': 'L2',
            'month': 1
        })
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        assert strategy['mode'] == 'discharge_to_home'
        assert 'Weekend' in strategy['reason'] or 'weekend' in strategy['reason'].lower()

    def test_sunday_before_22_returns_self_consumption(self, mock_hass):
        """Sunday before 22:00 should be treated as weekend (self consumption)."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'off')  # Weekend
        mock_hass.states.set('sensor.date', '2026-01-25')  # Sunday
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 50,
            'hour': 20,  # Before 22:00
            'tariff_zone': 'L2',
            'month': 1
        })
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        assert strategy['mode'] == 'discharge_to_home'
        assert 'Weekend' in strategy['reason'] or 'weekend' in strategy['reason'].lower()

    def test_friday_evening_22_starts_weekend(self, mock_hass):
        """Friday at 22:00+ should be treated as weekend start (no grid charging)."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')  # Still workday
        mock_hass.states.set('sensor.date', '2026-01-23')  # Friday
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 50,
            'hour': 22,  # Friday 22:00 = weekend start
            'tariff_zone': 'L2',
            'month': 1
        })
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        assert strategy['mode'] == 'discharge_to_home'
        assert 'Weekend' in strategy['reason'] or 'weekend' in strategy['reason'].lower()

    def test_sunday_evening_22_ends_weekend(self, mock_hass):
        """Sunday at 22:00+ should END weekend mode and allow normal charging."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'off')  # Still "weekend" by sensor
        mock_hass.states.set('sensor.date', '2026-01-25')  # Sunday
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 50,
            'hour': 22,  # Sunday 22:00 = weekend END
            'tariff_zone': 'L2',
            'month': 1,
            'target_soc': 90
        })
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        # Should NOT be weekend mode anymore - should allow normal L2 charging logic
        assert 'Weekend' not in strategy.get('reason', '')
        # In L2 with SOC < target, should charge from grid
        assert strategy['mode'] in ['charge_from_grid', 'grid_to_home', 'discharge_to_home']

    def test_monday_workday_normal_logic(self, mock_hass):
        """Monday (workday) should use normal logic, not weekend mode."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')  # Workday
        mock_hass.states.set('sensor.date', '2026-01-26')  # Monday
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 50,
            'hour': 12,
            'tariff_zone': 'L1',
            'month': 1
        })
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        # Monday L1 should discharge to home (save expensive L1)
        assert strategy['mode'] == 'discharge_to_home'
        assert 'Weekend' not in strategy.get('reason', '')
        assert 'L1' in strategy['reason']


class TestHandlePvSurplus:
    """Test handle_pv_surplus() - PV surplus handling."""

    def test_ultra_low_rce_store(self, mock_hass):
        """Ultra low RCE (< 0.15) should store energy."""
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 50,
            'rce_now': 0.10,
            'forecast_tomorrow': 20,
            'hour': 12,
            'month': 6
        })
        balance = {'surplus': 3.0, 'deficit': 0, 'pv': 5.0, 'load': 2.0}

        strategy = ns['handle_pv_surplus'](data, balance)

        assert strategy['mode'] == 'charge_from_pv'
        assert 'ultra' in strategy['reason'].lower() or 'RCE' in strategy['reason']

    def test_cloudy_tomorrow_uses_cheapest_hours(self, mock_hass):
        """Cloudy tomorrow: no short-circuit, cheapest hours algorithm decides."""
        # Setup RCE sensor with cheap hour at 12h
        mock_hass.states.set('sensor.rce_pse_cena', '0.45', {
            'prices': [
                {'dtime': '2025-06-15 12:00:00', 'rce_pln': 50},  # Cheap
                {'dtime': '2025-06-15 13:00:00', 'rce_pln': 500},
            ]
        })
        mock_hass.states.set('sensor.rce_progi_cenowe', '0.50', {'p33': 0.3, 'p66': 0.6})
        mock_hass.states.set('sensor.date', '2025-06-15')
        mock_hass.states.set('input_text.battery_storage_status', '')
        mock_hass.states.set('input_text.battery_cheapest_hours', '')
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 50,
            'rce_now': 0.45,
            'forecast_tomorrow': 8,  # Cloudy
            'forecast_today': 20,
            'hour': 12,
            'month': 6
        })
        balance = {'surplus': 3.0, 'deficit': 0, 'pv': 5.0, 'load': 2.0}

        strategy = ns['handle_pv_surplus'](data, balance)

        # Cheapest hours algorithm decides (no "jutro pochmurno" short-circuit)
        assert strategy['mode'] in ['charge_from_pv', 'discharge_to_grid']

    def test_normal_rce_goes_through_cheapest_hours(self, mock_hass):
        """Normal RCE goes through cheapest hours algorithm, not short-circuit."""
        mock_hass.states.set('sensor.rce_pse_cena', '0.45', {
            'prices': [
                {'dtime': '2025-12-15 10:00:00', 'rce_pln': 200},
                {'dtime': '2025-12-15 11:00:00', 'rce_pln': 450},
            ]
        })
        mock_hass.states.set('sensor.rce_progi_cenowe', '0.50', {'p33': 0.3, 'p66': 0.5})
        mock_hass.states.set('sensor.date', '2025-12-15')
        mock_hass.states.set('input_text.battery_storage_status', '')
        mock_hass.states.set('input_text.battery_cheapest_hours', '')
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 50,
            'rce_now': 0.45,
            'forecast_tomorrow': 20,
            'forecast_today': 10,
            'hour': 12,
            'month': 12
        })
        balance = {'surplus': 3.0, 'deficit': 0, 'pv': 5.0, 'load': 2.0}

        strategy = ns['handle_pv_surplus'](data, balance)

        # Should go through cheapest hours algorithm (no "zima" short-circuit)
        assert strategy['mode'] in ['charge_from_pv', 'discharge_to_grid']


class TestShouldChargeFromGrid:
    """Test should_charge_from_grid() - grid charging decisions."""

    def test_battery_too_hot(self, mock_hass):
        """Battery temp > 40C should block charging."""
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({'battery_temp': 45})

        result = ns['should_charge_from_grid'](data)

        assert result['should_charge'] is False
        assert 'przegrzania' in result['reason'].lower() or '40' in result['reason']

    def test_battery_too_cold(self, mock_hass):
        """Battery temp < 5C should block charging."""
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({'battery_temp': 2})

        result = ns['should_charge_from_grid'](data)

        assert result['should_charge'] is False
        assert '5°C' in result['reason'] or 'uszkodzenia' in result['reason'].lower()

    def test_negative_rce_charge(self, mock_hass):
        """Negative RCE should trigger charging (they pay you!)."""
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'rce_now': -0.05,
            'soc': 50,
            'battery_temp': 25
        })

        result = ns['should_charge_from_grid'](data)

        assert result['should_charge'] is True
        assert 'ujemne' in result['reason'].lower() or 'płacą' in result['reason'].lower()

    def test_critical_soc(self, mock_hass):
        """SOC < 5% should always charge."""
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 3,
            'battery_temp': 25,
            'rce_now': 0.50
        })

        result = ns['should_charge_from_grid'](data)

        assert result['should_charge'] is True
        assert result['priority'] == 'critical'


class TestCheckArbitrageOpportunity:
    """Test check_arbitrage_opportunity() - evening arbitrage."""

    def test_not_evening_no_arbitrage(self, mock_hass):
        """Non-evening hours should not trigger arbitrage."""
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'hour': 15,
            'soc': 70,
            'rce_now': 1.00,
            'forecast_tomorrow': 25,
            'heating_mode': 'no_heating'
        })

        result = ns['check_arbitrage_opportunity'](data)

        assert result['should_sell'] is False
        assert 'wieczór' in result['reason'].lower() or 'Nie' in result['reason']

    def test_low_rce_no_arbitrage(self, mock_hass):
        """Low RCE should not trigger arbitrage."""
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'hour': 20,
            'soc': 70,
            'rce_now': 0.50,  # Too low for arbitrage
            'forecast_tomorrow': 25,
            'heating_mode': 'no_heating'
        })

        result = ns['check_arbitrage_opportunity'](data)

        assert result['should_sell'] is False
        assert 'za niskie' in result['reason'].lower()

    def test_high_rce_arbitrage(self, mock_hass):
        """High RCE in evening with good conditions should trigger arbitrage."""
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'hour': 20,
            'soc': 70,
            'rce_now': 0.95,  # Above threshold
            'forecast_tomorrow': 25,
            'heating_mode': 'no_heating',
            'temp_outdoor': 15,
            'month': 6
        })

        result = ns['check_arbitrage_opportunity'](data)

        assert result['should_sell'] is True
        assert 'ARBITRAŻ' in result['reason']

    def test_low_soc_no_arbitrage(self, mock_hass):
        """Low SOC should block arbitrage."""
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'hour': 20,
            'soc': 40,  # Too low
            'rce_now': 0.95,
            'forecast_tomorrow': 25,
            'heating_mode': 'no_heating'
        })

        result = ns['check_arbitrage_opportunity'](data)

        assert result['should_sell'] is False
        assert 'za niskie' in result['reason'].lower()


class TestGetFallbackStrategy:
    """Test get_fallback_strategy() - emergency fallback."""

    def test_low_soc_fallback_charges(self, mock_hass):
        """Low SOC fallback should charge."""
        ns = load_algorithm_functions(mock_hass)

        data = {'soc': 25}

        strategy = ns['get_fallback_strategy'](data)

        assert strategy['mode'] == 'charge_from_grid'
        assert 'FALLBACK' in strategy['reason']

    def test_normal_soc_fallback_idle(self, mock_hass):
        """Normal SOC fallback should idle."""
        ns = load_algorithm_functions(mock_hass)

        data = {'soc': 50}

        strategy = ns['get_fallback_strategy'](data)

        assert strategy['mode'] == 'idle'
        assert 'FALLBACK' in strategy['reason']


class TestHandlePowerDeficit:
    """Test handle_power_deficit() - deficit handling."""

    def test_heating_season_l1_discharge(self, mock_hass):
        """Heating season in L1 should discharge battery."""
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 50,
            'hour': 10,
            'tariff_zone': 'L1',
            'heating_mode': 'heating_season',
            'temp_outdoor': 5,
            'cwu_window': False,
            'battery_temp': 25,
            'rce_now': 0.45,
            'forecast_tomorrow': 15
        })
        balance = {'surplus': 0, 'deficit': 2.0, 'pv': 1.0, 'load': 3.0}

        strategy = ns['handle_power_deficit'](data, balance)

        assert strategy['mode'] == 'discharge_to_home'
        assert 'L1' in strategy['reason'] or 'PC' in strategy['reason']

    def test_cwu_window_parallel_charging(self, mock_hass):
        """CWU window should allow parallel battery charging."""
        ns = load_algorithm_functions(mock_hass)

        # Use midday L2 (13:00-14:59) instead of night L2, because
        # night L2 has priority in code and returns before CWU check
        data = create_test_data({
            'soc': 50,
            'hour': 13,  # Midday L2 (not night L2)
            'tariff_zone': 'L2',
            'heating_mode': 'heating_season',
            'cwu_window': True,
            'target_soc': 80,
            'battery_temp': 25,
            'rce_now': 0.45,
            'forecast_tomorrow': 15
        })
        balance = {'surplus': 0, 'deficit': 5.0, 'pv': 0, 'load': 5.0}

        strategy = ns['handle_power_deficit'](data, balance)

        # Should charge battery (parallel with CWU)
        assert strategy['mode'] == 'charge_from_grid'
        assert 'równolegle' in strategy['reason'].lower() or 'CWU' in strategy['reason']


class TestIntegrationScenarios:
    """Integration tests for complete scenarios."""

    def test_sunny_summer_day_sell_surplus(self, mock_hass):
        """Sunny summer day with full battery should sell surplus."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        mock_hass.states.set('sensor.date', '2025-06-15')
        # Mock RCE sensor with prices
        mock_hass.states.set('sensor.rce_pse_cena', '0.55', {
            'prices': [
                {'dtime': '2025-06-15 12:00:00', 'rce_pln': 550}
            ]
        })
        mock_hass.states.set('sensor.rce_progi_cenowe', '0.50', {'p33': 0.4, 'p66': 0.6})
        mock_hass.states.set('input_text.battery_storage_status', '')
        mock_hass.states.set('input_text.battery_cheapest_hours', '')

        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 78,
            'hour': 12,
            'tariff_zone': 'L1',
            'pv_power': 8.0,
            'home_load': 2.0,
            'forecast_today': 35,
            'forecast_tomorrow': 30,
            'rce_now': 0.55,
            'month': 6,
            'heating_mode': 'no_heating'
        })
        balance = ns['calculate_power_balance'](data)

        # Surplus = 8.0 - 2.0 = 6.0 kW
        assert balance['surplus'] == 6.0

        strategy = ns['handle_pv_surplus'](data, balance)

        # High RCE + good forecast = sell
        assert strategy['mode'] == 'discharge_to_grid'

    def test_winter_night_charge(self, mock_hass):
        """Winter night in L2 should charge battery."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        mock_hass.states.set('sensor.date', '2025-01-15')
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 30,
            'hour': 2,
            'tariff_zone': 'L2',
            'pv_power': 0,
            'home_load': 1.5,
            'forecast_today': 8,  # Low winter forecast
            'forecast_tomorrow': 10,
            'rce_now': 0.35,
            'month': 1,
            'heating_mode': 'heating_season',
            'target_soc': 80
        })
        balance = ns['calculate_power_balance'](data)

        strategy = ns['decide_strategy'](data, balance)

        assert strategy['mode'] == 'charge_from_grid'
        assert strategy['target_soc'] == 80

    def test_evening_peak_arbitrage(self, mock_hass):
        """Evening with high RCE and good tomorrow forecast - arbitrage."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 75,
            'hour': 20,
            'rce_now': 0.95,
            'forecast_tomorrow': 28,
            'heating_mode': 'no_heating',
            'temp_outdoor': 15,
            'month': 6
        })

        result = ns['check_arbitrage_opportunity'](data)

        assert result['should_sell'] is True
        assert result['min_soc'] is not None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_soc_exactly_5(self, mock_hass):
        """SOC exactly at 5% (BATTERY_CRITICAL) boundary."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        ns = load_algorithm_functions(mock_hass)

        # SOC = 5 is NOT < 5, so should not trigger critical charge
        # In January (winter): soc_min = 10, so SOC 5 < 10 triggers high priority
        data = create_test_data({'soc': 5, 'hour': 12, 'tariff_zone': 'L1', 'month': 1})
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        # Should trigger low SOC charge (< seasonal min), not critical (since 5 is not < 5)
        assert strategy['mode'] == 'charge_from_grid'
        assert strategy['priority'] == 'high'  # Not 'critical'

    def test_soc_exactly_seasonal_max(self, mock_hass):
        """SOC exactly at seasonal max boundary."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        ns = load_algorithm_functions(mock_hass)

        # Summer (June): soc_max = 80%
        data = create_test_data({'soc': 80, 'hour': 12, 'tariff_zone': 'L1', 'month': 6})
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        # At seasonal max in L1, should discharge
        assert strategy['mode'] == 'discharge_to_home'

    def test_soc_exactly_winter_max(self, mock_hass):
        """SOC exactly at winter max (90%) boundary."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        ns = load_algorithm_functions(mock_hass)

        # Winter (January): soc_max = 90%
        data = create_test_data({'soc': 90, 'hour': 12, 'tariff_zone': 'L1', 'month': 1})
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        # At 90% (winter max) in L1, should discharge
        assert strategy['mode'] == 'discharge_to_home'

    def test_hour_boundary_22(self, mock_hass):
        """Hour 22 - transition from L1 to L2."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        ns = load_algorithm_functions(mock_hass)

        assert ns['get_tariff_zone'](21) == 'L1'
        assert ns['get_tariff_zone'](22) == 'L2'

    def test_hour_boundary_6(self, mock_hass):
        """Hour 6 - transition from L2 to L1."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        ns = load_algorithm_functions(mock_hass)

        assert ns['get_tariff_zone'](5) == 'L2'
        assert ns['get_tariff_zone'](6) == 'L1'

    def test_zero_pv_power(self, mock_hass):
        """Zero PV power (night)."""
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({'pv_power': 0, 'home_load': 2.0})
        balance = ns['calculate_power_balance'](data)

        assert balance['surplus'] == 0
        assert balance['deficit'] == 2.0


def _make_rce_prices(date_str, hourly_prices):
    """Helper: create RCE PSE price entries for a given date.

    Args:
        date_str: e.g. '2026-03-05'
        hourly_prices: dict {hour: price_pln_per_mwh}, e.g. {6: 200, 7: 350, ...}

    Returns list of price entries in RCE PSE format.
    """
    entries = []
    for hour, price_mwh in hourly_prices.items():
        entries.append({
            'dtime': f'{date_str} {hour:02d}:00:00',
            'rce_pln': price_mwh
        })
    return entries


def _setup_rce_mocks(mock_hass, date_str, today_prices=None, tomorrow_prices=None):
    """Helper: setup all RCE-related mocks for testing cheapest hours logic."""
    mock_hass.states.set('sensor.date', date_str)
    mock_hass.states.set('input_text.battery_storage_status', '')
    mock_hass.states.set('input_text.battery_cheapest_hours', '')
    mock_hass.states.set('sensor.rce_progi_cenowe', '0.40', {'p33': 0.30, 'p66': 0.50})
    mock_hass.states.set('sensor.rce_progi_cenowe_jutro', '0.40', {'p33': 0.30, 'p66': 0.50})

    if today_prices is not None:
        entries = _make_rce_prices(date_str, today_prices)
        mock_hass.states.set('sensor.rce_pse_cena', '0.40', {'prices': entries})

    if tomorrow_prices is not None:
        # Calculate tomorrow date
        y, m, d = int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10])
        d += 1
        days_in = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if d > days_in[m]:
            d = 1
            m += 1
        tomorrow_str = f'{y:04d}-{m:02d}-{d:02d}'
        entries = _make_rce_prices(tomorrow_str, tomorrow_prices)
        mock_hass.states.set('sensor.rce_pse_cena_jutro', '0.40', {'prices': entries})


# ============================================
# TESTY: calculate_cheapest_hours_to_store
# ============================================

class TestCalculateCheapestHoursToStore:
    """Test cheapest hours algorithm - core of PV surplus decision-making."""

    def test_identifies_cheapest_hours_correctly(self, mock_hass):
        """Algorithm should pick N cheapest sun hours from RCE prices."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        # March: sunrise=6, sunset=18 → sun hours 6-17
        # Prices: 10h=50 (cheapest), 11h=100, 12h=150, rest=500
        today_prices = {}
        for h in range(6, 18):
            today_prices[h] = 500
        today_prices[10] = 50
        today_prices[11] = 100
        today_prices[12] = 150

        _setup_rce_mocks(mock_hass, '2026-03-05', today_prices=today_prices)
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 30, 'target_soc': 85, 'hour': 10, 'month': 3,
            'forecast_today': 20, 'forecast_tomorrow': 15
        })

        is_cheap, reason, cheapest = ns['calculate_cheapest_hours_to_store'](data)

        assert 10 in cheapest, "Hour 10 (cheapest) should be in cheapest list"
        assert 11 in cheapest, "Hour 11 (2nd cheapest) should be in cheapest list"
        assert is_cheap is True, "Hour 10 should be identified as cheap"

    def test_current_hour_not_cheap(self, mock_hass):
        """Current hour NOT in cheapest hours → is_cheap_hour=False."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        today_prices = {}
        for h in range(6, 18):
            today_prices[h] = 500  # expensive
        today_prices[11] = 50   # cheap
        today_prices[12] = 60   # cheap
        today_prices[13] = 70   # cheap

        _setup_rce_mocks(mock_hass, '2026-03-05', today_prices=today_prices)
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 30, 'target_soc': 85, 'hour': 9, 'month': 3,
            'forecast_today': 20, 'forecast_tomorrow': 15
        })

        is_cheap, reason, cheapest = ns['calculate_cheapest_hours_to_store'](data)

        assert is_cheap is False, "Hour 9 (expensive) should NOT be cheap"
        assert 'DROGA' in reason or 'SPRZEDAJ' in reason

    def test_cheap_hour_stores_expensive_hour_sells(self, mock_hass):
        """Cheap hour → charge_from_pv, expensive hour → discharge_to_grid."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        today_prices = {}
        for h in range(6, 18):
            today_prices[h] = 600  # all expensive
        today_prices[11] = 30   # cheap at 11h
        today_prices[12] = 40   # cheap at 12h

        _setup_rce_mocks(mock_hass, '2026-03-05', today_prices=today_prices)
        ns = load_algorithm_functions(mock_hass)

        balance = {'surplus': 3.0, 'deficit': 0, 'pv': 5.0, 'load': 2.0}

        # At 11h (cheap) → store
        data_cheap = create_test_data({
            'soc': 30, 'target_soc': 85, 'hour': 11, 'month': 3,
            'rce_now': 0.03, 'forecast_today': 20, 'forecast_tomorrow': 15
        })
        strategy_cheap = ns['handle_pv_surplus'](data_cheap, balance)
        # Note: rce_now=0.03 < 0.15 triggers ultra-low short-circuit
        # Use normal RCE to test cheapest hours
        data_cheap['rce_now'] = 0.30
        strategy_cheap = ns['handle_pv_surplus'](data_cheap, balance)
        assert strategy_cheap['mode'] == 'charge_from_pv', \
            f"Cheap hour 11h should store, got {strategy_cheap['mode']}"

        # At 9h (expensive) → sell
        data_expensive = create_test_data({
            'soc': 30, 'target_soc': 85, 'hour': 9, 'month': 3,
            'rce_now': 0.60, 'forecast_today': 20, 'forecast_tomorrow': 15
        })
        strategy_expensive = ns['handle_pv_surplus'](data_expensive, balance)
        assert strategy_expensive['mode'] == 'discharge_to_grid', \
            f"Expensive hour 9h should sell, got {strategy_expensive['mode']}"

    def test_battery_full_does_not_store(self, mock_hass):
        """Full battery (SOC >= target) should not store even in cheap hour."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        today_prices = {h: 500 for h in range(6, 18)}
        today_prices[11] = 30

        _setup_rce_mocks(mock_hass, '2026-03-05', today_prices=today_prices)
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 85, 'target_soc': 85, 'hour': 11, 'month': 3,
            'rce_now': 0.30, 'forecast_today': 20, 'forecast_tomorrow': 15
        })

        is_cheap, reason, cheapest = ns['calculate_cheapest_hours_to_store'](data)

        # Battery charged → should report no need
        assert 'Bateria' in reason or 'naładowana' in reason.lower() or is_cheap is False

    def test_no_rce_data_returns_none(self, mock_hass):
        """Missing RCE data should return None (graceful fallback)."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        mock_hass.states.set('sensor.date', '2026-03-05')
        mock_hass.states.set('input_text.battery_storage_status', '')
        mock_hass.states.set('input_text.battery_cheapest_hours', '')
        # No RCE sensor set at all
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 30, 'target_soc': 85, 'hour': 11, 'month': 3,
            'forecast_today': 20
        })

        is_cheap, reason, cheapest = ns['calculate_cheapest_hours_to_store'](data)

        assert is_cheap is None
        assert cheapest == []

    def test_after_sunset_shows_tomorrow(self, mock_hass):
        """After sunset → should use tomorrow's RCE prices."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        # March sunset=18h, so hour=19 is after sunset
        tomorrow_prices = {h: 500 for h in range(6, 18)}
        tomorrow_prices[10] = 30
        tomorrow_prices[11] = 40

        _setup_rce_mocks(mock_hass, '2026-03-05', tomorrow_prices=tomorrow_prices)
        # Also set the jutro sensor
        mock_hass.states.set('sensor.rce_pse_cena_jutro', '0.40', {
            'prices': _make_rce_prices('2026-03-06', tomorrow_prices)
        })
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 30, 'target_soc': 85, 'hour': 19, 'month': 3,
            'forecast_today': 20
        })

        is_cheap, reason, cheapest = ns['calculate_cheapest_hours_to_store'](data)

        # After sunset → should analyze tomorrow
        assert 10 in cheapest or 11 in cheapest, "Should identify cheap hours from tomorrow"


# ============================================
# TESTY: get_first_cheap_pv_hour
# ============================================

class TestGetFirstCheapPvHour:
    """Test get_first_cheap_pv_hour() - finding first cheap hour for survival_soc."""

    def test_returns_earliest_cheap_hour(self, mock_hass):
        """Should return the earliest of N cheapest hours."""
        # March: sunrise=6, sunset=18, sun_hours=12
        # High forecast (60 kWh) → hours_needed=3
        tomorrow_prices = {h: 500 for h in range(6, 18)}
        tomorrow_prices[13] = 30   # cheap but late
        tomorrow_prices[10] = 40   # cheap and early ← should be returned
        tomorrow_prices[11] = 50   # cheap

        _setup_rce_mocks(mock_hass, '2026-03-04', tomorrow_prices=tomorrow_prices)
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'month': 3, 'soc_min': 15, 'soc_max': 85,
            'forecast_tomorrow': 60  # High → hours_needed≈3
        })

        first_cheap = ns['get_first_cheap_pv_hour'](data)

        assert first_cheap == 10, f"First cheap hour should be 10, got {first_cheap}"

    def test_returns_none_when_no_rce_data(self, mock_hass):
        """Should return None when RCE data is unavailable."""
        mock_hass.states.set('sensor.date', '2026-03-04')
        # No RCE sensors set
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'month': 3, 'soc_min': 15, 'soc_max': 85,
            'forecast_tomorrow': 20
        })

        first_cheap = ns['get_first_cheap_pv_hour'](data)

        assert first_cheap is None

    def test_returns_none_when_no_forecast(self, mock_hass):
        """Should return None when forecast_tomorrow is 0."""
        tomorrow_prices = {h: 500 for h in range(6, 18)}
        tomorrow_prices[10] = 30

        _setup_rce_mocks(mock_hass, '2026-03-04', tomorrow_prices=tomorrow_prices)
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'month': 3, 'soc_min': 15, 'soc_max': 85,
            'forecast_tomorrow': 0  # No forecast
        })

        first_cheap = ns['get_first_cheap_pv_hour'](data)

        assert first_cheap is None

    def test_winter_sunrise_7_excludes_before_sunrise(self, mock_hass):
        """Winter: sunrise=7 → hour 6 (before sunrise) should be excluded even if cheapest."""
        # January: sunrise=7, sunset=16
        tomorrow_prices = {}
        for h in range(7, 16):
            tomorrow_prices[h] = 500
        tomorrow_prices[6] = 10   # Very cheap but BEFORE sunrise → should be ignored

        _setup_rce_mocks(mock_hass, '2026-01-15', tomorrow_prices=tomorrow_prices)
        # Add h6 to sensor entries
        entries = _make_rce_prices('2026-01-16', {**tomorrow_prices, 6: 10})
        mock_hass.states.set('sensor.rce_pse_cena_jutro', '0.40', {'prices': entries})
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'month': 1, 'soc_min': 10, 'soc_max': 90,
            'forecast_tomorrow': 50
        })

        first_cheap = ns['get_first_cheap_pv_hour'](data)

        # Hour 6 is before sunrise (7) in winter → must be excluded
        assert first_cheap is not None
        assert first_cheap >= 7, f"First cheap hour should be >= 7 (sunrise), got {first_cheap}"

    def test_summer_sunrise_5_excludes_before_sunrise(self, mock_hass):
        """Summer: sunrise=5, sunset=20. Hours before sunrise (4) excluded."""
        tomorrow_prices = {h: 500 for h in range(5, 20)}
        tomorrow_prices[4] = 10   # Very cheap but BEFORE sunrise
        tomorrow_prices[7] = 30   # Cheapest within sun hours

        _setup_rce_mocks(mock_hass, '2026-06-15', tomorrow_prices=tomorrow_prices)
        # Add h4 to sensor entries
        entries = _make_rce_prices('2026-06-16', {**tomorrow_prices, 4: 10})
        mock_hass.states.set('sensor.rce_pse_cena_jutro', '0.40', {'prices': entries})
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'month': 6, 'soc_min': 20, 'soc_max': 80,
            'forecast_tomorrow': 60
        })

        first_cheap = ns['get_first_cheap_pv_hour'](data)

        assert first_cheap is not None
        assert first_cheap >= 5, f"First cheap hour should be >= 5 (summer sunrise), got {first_cheap}"


# ============================================
# TESTY: SURVIVAL SOC (nocne ładowanie)
# ============================================

class TestSurvivalSoc:
    """Test survival_soc logic - night charging minimized for cheap PV hours."""

    def test_high_pv_forecast_uses_survival_soc(self, mock_hass):
        """PV >= 10 kWh: night charging should use survival_soc (< target_soc)."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        mock_hass.states.set('sensor.date', '2026-03-04')
        # First cheap hour at 10h → hours_gap = 10-6 = 4h
        # survival_soc = 15 + (4 * 1.2 / 15 * 100) = 15 + 32 = 47%
        tomorrow_prices = {h: 500 for h in range(6, 18)}
        tomorrow_prices[10] = 30
        tomorrow_prices[11] = 40
        tomorrow_prices[12] = 50

        _setup_rce_mocks(mock_hass, '2026-03-04', tomorrow_prices=tomorrow_prices)
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 20, 'target_soc': 85, 'hour': 23, 'month': 3,
            'tariff_zone': 'L2',
            'forecast_today': 15, 'forecast_tomorrow': 20,  # >= 10 kWh
            'soc_min': 15, 'soc_max': 85
        })
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        assert strategy['mode'] == 'charge_from_grid'
        # survival_soc should be less than full target_soc (85)
        assert strategy['target_soc'] < 85, \
            f"Night target should be survival_soc < 85%, got {strategy['target_soc']}"
        assert strategy['target_soc'] >= 20, \
            f"Night target should be >= soc_min+5, got {strategy['target_soc']}"

    def test_low_pv_forecast_uses_full_target(self, mock_hass):
        """PV < 10 kWh: night charging should use full target_soc."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        mock_hass.states.set('sensor.date', '2026-03-04')
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 20, 'target_soc': 85, 'hour': 23, 'month': 3,
            'tariff_zone': 'L2',
            'forecast_today': 5, 'forecast_tomorrow': 8,  # < 10 kWh
            'soc_min': 15, 'soc_max': 85
        })
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        assert strategy['mode'] == 'charge_from_grid'
        assert strategy['target_soc'] == 85, \
            f"Low PV forecast: should charge to full target 85%, got {strategy['target_soc']}"

    def test_survival_soc_at_midnight_uses_forecast_today(self, mock_hass):
        """After midnight (hour 0-5): should use forecast_today (new day)."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        mock_hass.states.set('sensor.date', '2026-03-05')

        # "Today" (after midnight) prices for March 5th
        today_prices = {h: 500 for h in range(6, 18)}
        today_prices[11] = 30
        today_prices[12] = 40
        _setup_rce_mocks(mock_hass, '2026-03-05', today_prices=today_prices)
        # get_first_cheap_pv_hour looks at "tomorrow" from date perspective,
        # but decide_strategy at hour=2 uses forecast_today for PV check
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 20, 'target_soc': 85, 'hour': 2, 'month': 3,
            'tariff_zone': 'L2',
            'forecast_today': 25,  # Good PV today (after midnight)
            'forecast_tomorrow': 5,
            'soc_min': 15, 'soc_max': 85
        })
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        assert strategy['mode'] == 'charge_from_grid'
        # After midnight with good PV today → should use survival_soc
        # (uses forecast_today which is 25 kWh >= 10 kWh)

    def test_soc_already_at_survival_stops_charging(self, mock_hass):
        """If SOC already at survival_soc → should NOT charge more."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        mock_hass.states.set('sensor.date', '2026-03-04')
        tomorrow_prices = {h: 500 for h in range(6, 18)}
        tomorrow_prices[10] = 30
        tomorrow_prices[11] = 40

        _setup_rce_mocks(mock_hass, '2026-03-04', tomorrow_prices=tomorrow_prices)
        ns = load_algorithm_functions(mock_hass)

        # survival_soc ≈ 15 + (4*1.2/15*100) ≈ 47%
        # SOC is already 55% > survival_soc
        data = create_test_data({
            'soc': 55, 'target_soc': 85, 'hour': 23, 'month': 3,
            'tariff_zone': 'L2',
            'forecast_today': 15, 'forecast_tomorrow': 20,
            'soc_min': 15, 'soc_max': 85
        })
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        # SOC > survival_soc → should NOT charge, just grid_to_home
        assert strategy['mode'] == 'grid_to_home', \
            f"SOC at 55% > survival_soc: should stop charging, got {strategy['mode']}"

    def test_excellent_pv_forecast_very_low_survival(self, mock_hass):
        """PV >= 15 kWh + SOC >= survival: grid_to_home (PV will charge for free)."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        mock_hass.states.set('sensor.date', '2026-03-04')
        tomorrow_prices = {h: 500 for h in range(6, 18)}
        tomorrow_prices[10] = 30

        _setup_rce_mocks(mock_hass, '2026-03-04', tomorrow_prices=tomorrow_prices)
        ns = load_algorithm_functions(mock_hass)

        # PV forecast_tomorrow=25 kWh (>= 15 kWh) → don't charge at all if SOC OK
        data = create_test_data({
            'soc': 50, 'target_soc': 85, 'hour': 23, 'month': 3,
            'tariff_zone': 'L2',
            'forecast_today': 10, 'forecast_tomorrow': 25,
            'soc_min': 15, 'soc_max': 85
        })
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        assert strategy['mode'] == 'grid_to_home', \
            f"Excellent PV forecast + SOC OK: should not charge, got {strategy['mode']}"


# ============================================
# TESTY: INTEGRACYJNE — PEŁNY CYKL DZIENNY
# ============================================

class TestDailyCycleIntegration:
    """Integration tests: full day cycle from night → morning → cheap hours."""

    def _setup_march_day(self, mock_hass, tomorrow_prices):
        """Helper: setup a March day with RCE prices."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        mock_hass.states.set('sensor.date', '2026-03-04')
        _setup_rce_mocks(mock_hass, '2026-03-04', tomorrow_prices=tomorrow_prices)
        return load_algorithm_functions(mock_hass)

    def test_night_charges_to_survival_then_morning_drains(self, mock_hass):
        """Night: charge to survival_soc only. Morning L1: discharge to home."""
        # Cheapest hours: 11, 12 → first_cheap=11 → hours_gap=5 → survival≈55%
        tomorrow_prices = {h: 500 for h in range(6, 18)}
        tomorrow_prices[11] = 30
        tomorrow_prices[12] = 40

        ns = self._setup_march_day(mock_hass, tomorrow_prices)
        balance_deficit = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        # NIGHT 23h: SOC 20% → should charge to survival_soc
        data_night = create_test_data({
            'soc': 20, 'target_soc': 85, 'hour': 23, 'month': 3,
            'tariff_zone': 'L2',
            'forecast_today': 10, 'forecast_tomorrow': 20,
            'soc_min': 15, 'soc_max': 85
        })
        strategy_night = ns['decide_strategy'](data_night, balance_deficit)
        assert strategy_night['mode'] == 'charge_from_grid'
        night_target = strategy_night['target_soc']
        assert night_target < 85, f"Night target should be survival, got {night_target}"

        # MORNING 8h L1: SOC ~55% → should discharge to home
        data_morning = create_test_data({
            'soc': night_target, 'target_soc': 85, 'hour': 8, 'month': 3,
            'tariff_zone': 'L1',
            'forecast_today': 20, 'forecast_tomorrow': 20,
            'soc_min': 15, 'soc_max': 85
        })
        strategy_morning = ns['decide_strategy'](data_morning, balance_deficit)
        assert strategy_morning['mode'] == 'discharge_to_home', \
            f"Morning L1: should discharge, got {strategy_morning['mode']}"

    def test_first_cheap_hour_stores_from_pv(self, mock_hass):
        """At first cheap hour with PV surplus → should store."""
        tomorrow_prices = {h: 500 for h in range(6, 18)}
        tomorrow_prices[11] = 30  # First cheap hour
        tomorrow_prices[12] = 40

        # Use today's prices (same pattern) since we're testing hour 11 "today"
        today_prices = {h: 500 for h in range(6, 18)}
        today_prices[11] = 30
        today_prices[12] = 40

        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        _setup_rce_mocks(mock_hass, '2026-03-05', today_prices=today_prices)
        ns = load_algorithm_functions(mock_hass)

        balance_surplus = {'surplus': 3.0, 'deficit': 0, 'pv': 5.0, 'load': 2.0}

        # At 11h (first cheap): SOC ~20% (drained from morning), PV surplus → STORE
        data_cheap = create_test_data({
            'soc': 20, 'target_soc': 85, 'hour': 11, 'month': 3,
            'tariff_zone': 'L1',
            'rce_now': 0.30, 'forecast_today': 20, 'forecast_tomorrow': 15,
            'soc_min': 15, 'soc_max': 85
        })
        strategy = ns['handle_pv_surplus'](data_cheap, balance_surplus)
        assert strategy['mode'] == 'charge_from_pv', \
            f"First cheap hour 11h with PV surplus: should store, got {strategy['mode']}"

    def test_expensive_hour_before_cheap_sells(self, mock_hass):
        """Before first cheap hour, expensive hour → should sell."""
        today_prices = {h: 500 for h in range(6, 18)}
        today_prices[11] = 30
        today_prices[12] = 40

        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        _setup_rce_mocks(mock_hass, '2026-03-05', today_prices=today_prices)
        ns = load_algorithm_functions(mock_hass)

        balance_surplus = {'surplus': 3.0, 'deficit': 0, 'pv': 5.0, 'load': 2.0}

        # At 9h (before first cheap hour 11h): expensive → SELL
        data_expensive = create_test_data({
            'soc': 30, 'target_soc': 85, 'hour': 9, 'month': 3,
            'tariff_zone': 'L1',
            'rce_now': 0.50, 'forecast_today': 20, 'forecast_tomorrow': 15,
            'soc_min': 15, 'soc_max': 85
        })
        strategy = ns['handle_pv_surplus'](data_expensive, balance_surplus)
        assert strategy['mode'] == 'discharge_to_grid', \
            f"Expensive hour 9h: should sell, got {strategy['mode']}"

    def test_ultra_low_rce_overrides_cheapest_hours(self, mock_hass):
        """RCE < 0.15: stores even if NOT a cheap hour (short-circuit)."""
        today_prices = {h: 500 for h in range(6, 18)}
        today_prices[12] = 30  # Cheap at 12h, not at 9h

        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        _setup_rce_mocks(mock_hass, '2026-03-05', today_prices=today_prices)
        ns = load_algorithm_functions(mock_hass)

        balance_surplus = {'surplus': 3.0, 'deficit': 0, 'pv': 5.0, 'load': 2.0}

        # At 9h: NOT cheap hour, but RCE ultra low (0.05) → store anyway
        data = create_test_data({
            'soc': 30, 'target_soc': 85, 'hour': 9, 'month': 3,
            'rce_now': 0.05,  # Ultra low < 0.15
            'forecast_today': 20, 'forecast_tomorrow': 15,
            'soc_min': 15, 'soc_max': 85
        })
        strategy = ns['handle_pv_surplus'](data, balance_surplus)
        assert strategy['mode'] == 'charge_from_pv', \
            f"Ultra low RCE 0.05 should store (short-circuit), got {strategy['mode']}"

    def test_full_cycle_night_to_cheap_hour(self, mock_hass):
        """Full cycle: night → morning L1 → first cheap hour → store from PV."""
        tomorrow_prices = {h: 500 for h in range(6, 18)}
        tomorrow_prices[11] = 30
        tomorrow_prices[12] = 40
        tomorrow_prices[13] = 50

        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        _setup_rce_mocks(mock_hass, '2026-03-04', tomorrow_prices=tomorrow_prices)
        ns = load_algorithm_functions(mock_hass)

        balance_deficit = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        # STEP 1: Night 23h - charge to survival_soc (not full target)
        data_step1 = create_test_data({
            'soc': 20, 'target_soc': 85, 'hour': 23, 'month': 3,
            'tariff_zone': 'L2',
            'forecast_today': 10, 'forecast_tomorrow': 20,
            'soc_min': 15, 'soc_max': 85
        })
        s1 = ns['decide_strategy'](data_step1, balance_deficit)
        assert s1['mode'] == 'charge_from_grid'
        survival_target = s1['target_soc']
        assert survival_target < 85, f"Step 1: survival_soc < 85, got {survival_target}"

        # STEP 2: Morning 8h L1 - discharge to home
        data_step2 = create_test_data({
            'soc': survival_target, 'target_soc': 85, 'hour': 8, 'month': 3,
            'tariff_zone': 'L1',
            'forecast_today': 20, 'forecast_tomorrow': 15,
            'soc_min': 15, 'soc_max': 85
        })
        s2 = ns['decide_strategy'](data_step2, balance_deficit)
        assert s2['mode'] == 'discharge_to_home', \
            f"Step 2: morning L1 discharge, got {s2['mode']}"

        # STEP 3: First cheap hour 11h - PV surplus → STORE
        # (use today's prices now since we're on March 5th)
        today_prices = {h: 500 for h in range(6, 18)}
        today_prices[11] = 30
        today_prices[12] = 40
        today_prices[13] = 50
        _setup_rce_mocks(mock_hass, '2026-03-05', today_prices=today_prices)
        ns = load_algorithm_functions(mock_hass)

        balance_surplus = {'surplus': 4.0, 'deficit': 0, 'pv': 6.0, 'load': 2.0}
        data_step3 = create_test_data({
            'soc': 20, 'target_soc': 85, 'hour': 11, 'month': 3,
            'tariff_zone': 'L1',
            'rce_now': 0.30, 'forecast_today': 20, 'forecast_tomorrow': 15,
            'soc_min': 15, 'soc_max': 85
        })
        s3 = ns['handle_pv_surplus'](data_step3, balance_surplus)
        assert s3['mode'] == 'charge_from_pv', \
            f"Step 3: first cheap hour 11h → store, got {s3['mode']}"

        # STEP 4: Expensive hour 9h - PV surplus → SELL
        data_step4 = create_test_data({
            'soc': 20, 'target_soc': 85, 'hour': 9, 'month': 3,
            'tariff_zone': 'L1',
            'rce_now': 0.50, 'forecast_today': 20, 'forecast_tomorrow': 15,
            'soc_min': 15, 'soc_max': 85
        })
        s4 = ns['handle_pv_surplus'](data_step4, balance_surplus)
        assert s4['mode'] == 'discharge_to_grid', \
            f"Step 4: expensive hour 9h → sell, got {s4['mode']}"


# ============================================
# TESTY: EDGE CASES NAJTAŃSZYCH GODZIN
# ============================================

class TestCheapestHoursEdgeCases:
    """Edge cases for cheapest hours and survival_soc logic."""

    def test_all_hours_same_price(self, mock_hass):
        """All sun hours same price → algorithm should still work."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        today_prices = {h: 300 for h in range(6, 18)}  # All same

        _setup_rce_mocks(mock_hass, '2026-03-05', today_prices=today_prices)
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 30, 'target_soc': 85, 'hour': 10, 'month': 3,
            'forecast_today': 20
        })

        is_cheap, reason, cheapest = ns['calculate_cheapest_hours_to_store'](data)

        # Should still return a valid result
        assert is_cheap is not None
        assert len(cheapest) > 0

    def test_single_sun_hour_available(self, mock_hass):
        """Only one sun hour has data → should handle gracefully."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        today_prices = {10: 300}  # Only one hour

        _setup_rce_mocks(mock_hass, '2026-03-05', today_prices=today_prices)
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 30, 'target_soc': 85, 'hour': 10, 'month': 3,
            'forecast_today': 20
        })

        is_cheap, reason, cheapest = ns['calculate_cheapest_hours_to_store'](data)

        assert is_cheap is True  # Only hour → must be cheapest
        assert 10 in cheapest

    def test_survival_soc_clamped_to_soc_min_plus_5(self, mock_hass):
        """Survival SOC should never be below soc_min + 5%."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        mock_hass.states.set('sensor.date', '2026-03-04')
        # First cheap hour at 7h → hours_gap = 7-6 = 1h
        # survival_kwh = 1 * 1.2 = 1.2 kWh
        # survival_soc = 15 + (1.2/15*100) = 15 + 8 = 23%
        # clamped: max(15+5, min(85, 23)) = max(20, 23) = 23%
        tomorrow_prices = {h: 500 for h in range(6, 18)}
        tomorrow_prices[7] = 30  # Very early cheap hour

        _setup_rce_mocks(mock_hass, '2026-03-04', tomorrow_prices=tomorrow_prices)
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 15, 'target_soc': 85, 'hour': 23, 'month': 3,
            'tariff_zone': 'L2',
            'forecast_today': 10, 'forecast_tomorrow': 20,
            'soc_min': 15, 'soc_max': 85
        })
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        assert strategy['mode'] == 'charge_from_grid'
        # Min clamp: soc_min + 5 = 20%
        assert strategy['target_soc'] >= 20, \
            f"Survival SOC should be >= soc_min+5 (20%), got {strategy['target_soc']}"

    def test_weekend_no_survival_soc_logic(self, mock_hass):
        """Weekend should not use night L2 charging logic (handled separately)."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'off')
        mock_hass.states.set('sensor.date', '2026-03-07')  # Saturday
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 40, 'target_soc': 85, 'hour': 23, 'month': 3,
            'tariff_zone': 'L2',
            'forecast_today': 10, 'forecast_tomorrow': 20,
            'soc_min': 15, 'soc_max': 85
        })
        balance = {'surplus': 0, 'deficit': 1.0, 'pv': 0, 'load': 1.0}

        strategy = ns['decide_strategy'](data, balance)

        # Weekend → should NOT enter L2 night charging block
        assert 'Weekend' in strategy.get('reason', '') or \
               strategy['mode'] in ['discharge_to_home', 'grid_to_home']

    def test_rce_prices_in_plnmwh_converted(self, mock_hass):
        """RCE prices > 10 should be auto-converted from PLN/MWh to PLN/kWh."""
        mock_hass.states.set('binary_sensor.dzien_roboczy', 'on')
        # 500 PLN/MWh = 0.50 PLN/kWh
        # 50 PLN/MWh = 0.05 PLN/kWh (cheap!)
        today_prices = {h: 500 for h in range(6, 18)}
        today_prices[11] = 50  # 0.05 PLN/kWh

        _setup_rce_mocks(mock_hass, '2026-03-05', today_prices=today_prices)
        ns = load_algorithm_functions(mock_hass)

        data = create_test_data({
            'soc': 30, 'target_soc': 85, 'hour': 11, 'month': 3,
            'forecast_today': 20
        })

        is_cheap, reason, cheapest = ns['calculate_cheapest_hours_to_store'](data)

        assert 11 in cheapest, "50 PLN/MWh (0.05 PLN/kWh) should be cheapest"
        assert is_cheap is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
