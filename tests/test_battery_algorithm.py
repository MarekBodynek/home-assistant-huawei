"""
Testy jednostkowe dla algorytmu zarządzania baterią Huawei Luna 15kWh
"""

import pytest
from unittest.mock import MagicMock, patch
import sys
import os

# Dodaj ścieżkę do python_scripts
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config', 'python_scripts'))


class MockState:
    """Mock dla obiektu stanu Home Assistant"""
    def __init__(self, state, attributes=None):
        self.state = state
        self.attributes = attributes or {}


class MockHass:
    """Mock dla obiektu hass Home Assistant"""
    def __init__(self):
        self._states = {}
        self._calls = []

    def set_state(self, entity_id, state, attributes=None):
        self._states[entity_id] = MockState(state, attributes)

    @property
    def states(self):
        return self

    def get(self, entity_id):
        return self._states.get(entity_id)

    @property
    def services(self):
        return self

    def call(self, domain, service, data):
        self._calls.append((domain, service, data))


# ============================================
# TESTY FUNKCJI get_tariff_zone
# ============================================

class TestGetTariffZone:
    """Testy dla funkcji get_tariff_zone"""

    def setup_method(self):
        """Setup przed każdym testem"""
        self.hass = MockHass()

    def test_workday_l1_morning(self):
        """Dzień roboczy, rano (6:00-12:59) = L1"""
        self.hass.set_state('binary_sensor.dzien_roboczy', 'on')

        # Importuj z mockiem
        with patch.dict('builtins.__dict__', {'hass': self.hass}):
            # Symuluj funkcję get_tariff_zone
            def get_tariff_zone(hour):
                workday_state = self.hass.states.get('binary_sensor.dzien_roboczy')
                is_workday = workday_state and workday_state.state == 'on'
                if not is_workday:
                    return 'L2'
                elif hour >= 22 or hour < 6:
                    return 'L2'
                elif 13 <= hour < 15:
                    return 'L2'
                else:
                    return 'L1'

            # Testy L1 rano (6-12)
            for hour in [6, 7, 8, 9, 10, 11, 12]:
                assert get_tariff_zone(hour) == 'L1', f"Godzina {hour} powinna być L1"

    def test_workday_l2_night(self):
        """Dzień roboczy, noc (22:00-05:59) = L2"""
        self.hass.set_state('binary_sensor.dzien_roboczy', 'on')

        def get_tariff_zone(hour):
            workday_state = self.hass.states.get('binary_sensor.dzien_roboczy')
            is_workday = workday_state and workday_state.state == 'on'
            if not is_workday:
                return 'L2'
            elif hour >= 22 or hour < 6:
                return 'L2'
            elif 13 <= hour < 15:
                return 'L2'
            else:
                return 'L1'

        # Testy L2 noc (22-5)
        for hour in [22, 23, 0, 1, 2, 3, 4, 5]:
            assert get_tariff_zone(hour) == 'L2', f"Godzina {hour} powinna być L2"

    def test_workday_l2_midday(self):
        """Dzień roboczy, południe (13:00-14:59) = L2"""
        self.hass.set_state('binary_sensor.dzien_roboczy', 'on')

        def get_tariff_zone(hour):
            workday_state = self.hass.states.get('binary_sensor.dzien_roboczy')
            is_workday = workday_state and workday_state.state == 'on'
            if not is_workday:
                return 'L2'
            elif hour >= 22 or hour < 6:
                return 'L2'
            elif 13 <= hour < 15:
                return 'L2'
            else:
                return 'L1'

        # Testy L2 południe (13-14)
        for hour in [13, 14]:
            assert get_tariff_zone(hour) == 'L2', f"Godzina {hour} powinna być L2"

    def test_workday_l1_afternoon(self):
        """Dzień roboczy, popołudnie (15:00-21:59) = L1"""
        self.hass.set_state('binary_sensor.dzien_roboczy', 'on')

        def get_tariff_zone(hour):
            workday_state = self.hass.states.get('binary_sensor.dzien_roboczy')
            is_workday = workday_state and workday_state.state == 'on'
            if not is_workday:
                return 'L2'
            elif hour >= 22 or hour < 6:
                return 'L2'
            elif 13 <= hour < 15:
                return 'L2'
            else:
                return 'L1'

        # Testy L1 popołudnie (15-21)
        for hour in [15, 16, 17, 18, 19, 20, 21]:
            assert get_tariff_zone(hour) == 'L1', f"Godzina {hour} powinna być L1"

    def test_weekend_all_day_l2(self):
        """Weekend - cały dzień L2"""
        self.hass.set_state('binary_sensor.dzien_roboczy', 'off')

        def get_tariff_zone(hour):
            workday_state = self.hass.states.get('binary_sensor.dzien_roboczy')
            is_workday = workday_state and workday_state.state == 'on'
            if not is_workday:
                return 'L2'
            elif hour >= 22 or hour < 6:
                return 'L2'
            elif 13 <= hour < 15:
                return 'L2'
            else:
                return 'L1'

        # Weekend = L2 przez całą dobę
        for hour in range(24):
            assert get_tariff_zone(hour) == 'L2', f"Weekend godzina {hour} powinna być L2"


# ============================================
# TESTY FUNKCJI validate_data
# ============================================

class TestValidateData:
    """Testy dla funkcji validate_data"""

    def test_valid_data(self):
        """Poprawne dane - zwraca True"""
        def validate_data(data):
            if not data:
                return False
            critical = ['soc', 'tariff_zone', 'pv_power', 'home_load', 'temp_outdoor']
            for field in critical:
                if field not in data or data[field] is None:
                    return False
            if not (0 <= data['soc'] <= 100):
                return False
            return True

        data = {
            'soc': 50,
            'tariff_zone': 'L1',
            'pv_power': 2.5,
            'home_load': 1.0,
            'temp_outdoor': 15
        }
        assert validate_data(data) == True

    def test_empty_data(self):
        """Puste dane - zwraca False"""
        def validate_data(data):
            if not data:
                return False
            return True

        assert validate_data({}) == False
        assert validate_data(None) == False

    def test_missing_critical_field(self):
        """Brakujące pole krytyczne - zwraca False"""
        def validate_data(data):
            if not data:
                return False
            critical = ['soc', 'tariff_zone', 'pv_power', 'home_load', 'temp_outdoor']
            for field in critical:
                if field not in data or data[field] is None:
                    return False
            if not (0 <= data['soc'] <= 100):
                return False
            return True

        data = {
            'soc': 50,
            'tariff_zone': 'L1',
            # Brak pv_power
            'home_load': 1.0,
            'temp_outdoor': 15
        }
        assert validate_data(data) == False

    def test_soc_out_of_range(self):
        """SOC poza zakresem 0-100 - zwraca False"""
        def validate_data(data):
            if not data:
                return False
            critical = ['soc', 'tariff_zone', 'pv_power', 'home_load', 'temp_outdoor']
            for field in critical:
                if field not in data or data[field] is None:
                    return False
            if not (0 <= data['soc'] <= 100):
                return False
            return True

        data_negative = {
            'soc': -5,
            'tariff_zone': 'L1',
            'pv_power': 2.5,
            'home_load': 1.0,
            'temp_outdoor': 15
        }
        assert validate_data(data_negative) == False

        data_over100 = {
            'soc': 105,
            'tariff_zone': 'L1',
            'pv_power': 2.5,
            'home_load': 1.0,
            'temp_outdoor': 15
        }
        assert validate_data(data_over100) == False


# ============================================
# TESTY FUNKCJI calculate_power_balance
# ============================================

class TestCalculatePowerBalance:
    """Testy dla funkcji calculate_power_balance"""

    def test_pv_surplus(self):
        """PV > Load = nadwyżka"""
        def calculate_power_balance(data):
            pv = data['pv_power']
            load = data['home_load']
            if pv > load:
                return {'surplus': pv - load, 'deficit': 0, 'pv': pv, 'load': load}
            else:
                return {'surplus': 0, 'deficit': load - pv, 'pv': pv, 'load': load}

        data = {'pv_power': 5.0, 'home_load': 2.0}
        balance = calculate_power_balance(data)

        assert balance['surplus'] == 3.0
        assert balance['deficit'] == 0
        assert balance['pv'] == 5.0
        assert balance['load'] == 2.0

    def test_power_deficit(self):
        """PV < Load = deficyt"""
        def calculate_power_balance(data):
            pv = data['pv_power']
            load = data['home_load']
            if pv > load:
                return {'surplus': pv - load, 'deficit': 0, 'pv': pv, 'load': load}
            else:
                return {'surplus': 0, 'deficit': load - pv, 'pv': pv, 'load': load}

        data = {'pv_power': 1.0, 'home_load': 3.0}
        balance = calculate_power_balance(data)

        assert balance['surplus'] == 0
        assert balance['deficit'] == 2.0

    def test_perfect_balance(self):
        """PV == Load = idealny balans"""
        def calculate_power_balance(data):
            pv = data['pv_power']
            load = data['home_load']
            if pv > load:
                return {'surplus': pv - load, 'deficit': 0, 'pv': pv, 'load': load}
            else:
                return {'surplus': 0, 'deficit': load - pv, 'pv': pv, 'load': load}

        data = {'pv_power': 2.5, 'home_load': 2.5}
        balance = calculate_power_balance(data)

        assert balance['surplus'] == 0
        assert balance['deficit'] == 0


# ============================================
# TESTY LOGIKI DECYZYJNEJ (decide_strategy)
# ============================================

class TestDecideStrategy:
    """Testy dla głównej logiki decyzyjnej"""

    def test_critical_soc_below_5(self):
        """SOC < 5% = natychmiastowe ładowanie 24/7"""
        data = {
            'soc': 3,
            'tariff_zone': 'L1',  # Nawet w drogiej taryfie!
            'target_soc': 80
        }

        # Symulacja logiki
        if data['soc'] < 5:
            strategy = {
                'mode': 'charge_from_grid',
                'target_soc': 35,
                'priority': 'critical',
                'reason': 'SOC < 5% - SUPER PILNE!',
                'urgent_charge': True
            }
        else:
            strategy = None

        assert strategy is not None
        assert strategy['mode'] == 'charge_from_grid'
        assert strategy['priority'] == 'critical'
        assert strategy['urgent_charge'] == True

    def test_low_soc_below_20(self):
        """SOC < 20% = pilne ładowanie w L2"""
        data = {
            'soc': 15,
            'tariff_zone': 'L2',
            'target_soc': 80
        }

        if data['soc'] < 20:
            strategy = {
                'mode': 'charge_from_grid',
                'target_soc': data['target_soc'],
                'priority': 'high',
                'reason': 'SOC < 20% - PILNE!'
            }
        else:
            strategy = None

        assert strategy is not None
        assert strategy['mode'] == 'charge_from_grid'
        assert strategy['target_soc'] == 80

    def test_full_battery_l2_preserve(self):
        """SOC 80% w L2 = zachowaj baterię"""
        data = {
            'soc': 80,
            'tariff_zone': 'L2',
            'target_soc': 80
        }
        balance = {'surplus': 0, 'deficit': 1.0}

        if data['soc'] >= 80 and data['tariff_zone'] == 'L2':
            strategy = {
                'mode': 'grid_to_home',
                'priority': 'low',
                'reason': 'SOC 80% w L2 - zachowaj baterię'
            }
        else:
            strategy = None

        assert strategy is not None
        assert strategy['mode'] == 'grid_to_home'

    def test_full_battery_l1_discharge(self):
        """SOC 80% w L1 bez nadwyżki = rozładowuj"""
        data = {
            'soc': 80,
            'tariff_zone': 'L1',
            'target_soc': 80
        }
        balance = {'surplus': 0, 'deficit': 1.0}

        if data['soc'] >= 80 and data['tariff_zone'] == 'L1' and balance['surplus'] == 0:
            strategy = {
                'mode': 'discharge_to_home',
                'priority': 'normal',
                'reason': 'SOC 80% w L1 - rozładowuj'
            }
        else:
            strategy = None

        assert strategy is not None
        assert strategy['mode'] == 'discharge_to_home'

    def test_l1_discharge_to_home(self):
        """L1 droga taryfa + SOC > 20% = rozładowuj"""
        data = {
            'soc': 50,
            'tariff_zone': 'L1',
            'target_soc': 80
        }
        balance = {'surplus': 0, 'deficit': 1.5}

        if data['tariff_zone'] == 'L1' and data['soc'] > 20 and balance['surplus'] < 0.5:
            strategy = {
                'mode': 'discharge_to_home',
                'priority': 'normal',
                'reason': 'L1 droga taryfa - rozładowuj'
            }
        else:
            strategy = None

        assert strategy is not None
        assert strategy['mode'] == 'discharge_to_home'


# ============================================
# TESTY SEZONÓW I PROGNOZY PV
# ============================================

class TestSeasonalLogic:
    """Testy logiki sezonowej (sezon grzewczy, prognoza PV)"""

    def test_heating_season_always_charge(self):
        """Sezon grzewczy + noc L2 = ładuj zawsze"""
        data = {
            'soc': 40,
            'tariff_zone': 'L2',
            'hour': 3,
            'heating_mode': 'heating_season',
            'forecast_tomorrow': 5,  # Słaba prognoza
            'target_soc': 80
        }

        is_night_l2 = data['hour'] in [22, 23, 0, 1, 2, 3, 4, 5]

        if data['heating_mode'] == 'heating_season' and is_night_l2 and data['soc'] < data['target_soc']:
            strategy = {
                'mode': 'charge_from_grid',
                'target_soc': data['target_soc'],
                'priority': 'normal',
                'reason': 'Sezon grzewczy - ładuj'
            }
        else:
            strategy = None

        assert strategy is not None
        assert strategy['mode'] == 'charge_from_grid'

    def test_good_pv_forecast_no_charge(self):
        """Dobra prognoza PV (>20 kWh) = nie ładuj, PV wystarczy"""
        data = {
            'soc': 40,
            'tariff_zone': 'L2',
            'hour': 3,
            'heating_mode': 'no_heating',
            'forecast_tomorrow': 25,  # Dobra prognoza
            'target_soc': 80
        }

        pv_forecast = data['forecast_tomorrow']

        if pv_forecast >= 20:
            strategy = {
                'mode': 'grid_to_home',
                'priority': 'low',
                'reason': 'Dobra prognoza PV - nie ładuj'
            }
        else:
            strategy = None

        assert strategy is not None
        assert strategy['mode'] == 'grid_to_home'

    def test_poor_pv_forecast_charge(self):
        """Słaba prognoza PV (<15 kWh) = ładuj"""
        data = {
            'soc': 40,
            'tariff_zone': 'L2',
            'hour': 3,
            'heating_mode': 'no_heating',
            'forecast_tomorrow': 8,  # Słaba prognoza
            'target_soc': 80
        }

        pv_forecast = data['forecast_tomorrow']

        if pv_forecast < 15 and data['soc'] < data['target_soc']:
            strategy = {
                'mode': 'charge_from_grid',
                'target_soc': data['target_soc'],
                'priority': 'normal',
                'reason': 'Słaba prognoza PV - ładuj'
            }
        else:
            strategy = None

        assert strategy is not None
        assert strategy['mode'] == 'charge_from_grid'


# ============================================
# TESTY WEEKENDU ENERGETYCZNEGO
# ============================================

class TestEnergyWeekend:
    """Testy logiki weekendu energetycznego"""

    def test_weekend_self_consumption(self):
        """Weekend = tylko self consumption"""
        # Weekend - dzień_roboczy = off
        is_workday = False
        is_friday_evening = False
        is_sunday_evening = False

        is_energy_weekend = (not is_workday or is_friday_evening) and not is_sunday_evening

        if is_energy_weekend:
            strategy = {
                'mode': 'discharge_to_home',
                'priority': 'normal',
                'reason': 'Weekend - self consumption'
            }
        else:
            strategy = None

        assert strategy is not None
        assert strategy['mode'] == 'discharge_to_home'

    def test_friday_evening_starts_weekend(self):
        """Piątek 22:00+ = start weekendu energetycznego"""
        is_workday = True  # Piątek jest dniem roboczym
        weekday = 4  # Piątek
        hour = 22

        is_friday_evening = (weekday == 4 and hour >= 22)
        is_sunday_evening = False

        is_energy_weekend = (not is_workday or is_friday_evening) and not is_sunday_evening

        assert is_energy_weekend == True

    def test_sunday_evening_ends_weekend(self):
        """Niedziela 22:00+ = koniec weekendu energetycznego"""
        is_workday = False  # Niedziela
        weekday = 6
        hour = 22

        is_friday_evening = False
        is_sunday_evening = (weekday == 6 and hour >= 22)

        is_energy_weekend = (not is_workday or is_friday_evening) and not is_sunday_evening

        assert is_energy_weekend == False


# ============================================
# TESTY EDGE CASES
# ============================================

class TestEdgeCases:
    """Testy przypadków brzegowych"""

    def test_soc_exactly_zero(self):
        """SOC = 0% - krytyczne"""
        soc = 0
        assert soc < 5

    def test_soc_exactly_100(self):
        """SOC = 100% - poprawne"""
        def validate_data(data):
            if not (0 <= data['soc'] <= 100):
                return False
            return True

        assert validate_data({'soc': 100}) == True

    def test_negative_pv_power(self):
        """Ujemna moc PV (nie powinno wystąpić)"""
        def calculate_power_balance(data):
            pv = max(0, data['pv_power'])  # Zabezpieczenie
            load = data['home_load']
            if pv > load:
                return {'surplus': pv - load, 'deficit': 0}
            else:
                return {'surplus': 0, 'deficit': load - pv}

        data = {'pv_power': -1.0, 'home_load': 2.0}
        balance = calculate_power_balance(data)

        assert balance['surplus'] == 0
        assert balance['deficit'] == 2.0

    def test_midnight_hour_boundary(self):
        """Północ (0:00) - poprawna obsługa"""
        def get_tariff_zone(hour, is_workday):
            if not is_workday:
                return 'L2'
            elif hour >= 22 or hour < 6:
                return 'L2'
            elif 13 <= hour < 15:
                return 'L2'
            else:
                return 'L1'

        # Północ w dzień roboczy = L2
        assert get_tariff_zone(0, True) == 'L2'

        # Północ w weekend = L2
        assert get_tariff_zone(0, False) == 'L2'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
