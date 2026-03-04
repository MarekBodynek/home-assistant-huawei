"""
Pytest fixtures for Home Assistant battery algorithm tests.

Mock Home Assistant 'hass' object and related entities.
"""

import pytest
from unittest.mock import MagicMock, patch
import sys
from types import ModuleType


class MockState:
    """Mock Home Assistant state object."""

    def __init__(self, state, attributes=None):
        self.state = state
        self.attributes = attributes or {}


class MockHass:
    """Mock Home Assistant hass object."""

    def __init__(self):
        self.states = MockStates()
        self.services = MockServices()


class MockStates:
    """Mock hass.states."""

    def __init__(self):
        self._states = {}

    def get(self, entity_id):
        return self._states.get(entity_id)

    def set(self, entity_id, state, attributes=None):
        """Helper method for tests to set entity states."""
        self._states[entity_id] = MockState(state, attributes)


class MockServices:
    """Mock hass.services."""

    def __init__(self):
        self.calls = []

    def call(self, domain, service, data):
        """Record service calls for verification."""
        self.calls.append({
            'domain': domain,
            'service': service,
            'data': data
        })


@pytest.fixture
def mock_hass():
    """Create a fresh mock hass object for each test."""
    return MockHass()


@pytest.fixture
def default_sensor_states():
    """Default sensor states for standard test scenarios."""
    return {
        'sensor.time': '12:00',
        'sensor.date': '2025-01-15',
        'binary_sensor.dzien_roboczy': 'on',
        'sensor.rce_pse_cena_za_kwh': '0.45',
        'sensor.rce_srednia_wieczorna': '0.55',
        'sensor.akumulatory_stan_pojemnosci': '50',
        'sensor.akumulatory_moc_ladowania_rozladowania': '0',
        'sensor.bateria_temperatura_maksymalna': '25',
        'sensor.inwerter_moc_wejsciowa': '5000',  # 5kW PV
        'sensor.pomiar_mocy_moc_czynna': '2000',  # 2kW consumption
        'sensor.prognoza_pv_dzisiaj': '20',
        'sensor.prognoza_pv_jutro': '15',
        'sensor.prognoza_pv_6h': '10',
        'sensor.temperatura_zewnetrzna': '10',
        'binary_sensor.sezon_grzewczy': 'off',
        'binary_sensor.pc_co_aktywne': 'off',
        'binary_sensor.okno_cwu': 'off',
        'input_number.battery_target_soc': '80',
        'binary_sensor.bateria_bezpieczna_temperatura': 'on',
        'switch.akumulatory_ladowanie_z_sieci': 'off',
        'binary_sensor.awaria_zasilania_sieci': 'off',
    }


@pytest.fixture
def setup_hass_states(mock_hass, default_sensor_states):
    """Setup mock hass with default sensor states."""
    for entity_id, state in default_sensor_states.items():
        mock_hass.states.set(entity_id, state)
    return mock_hass


def get_seasonal_soc_limits(month):
    """Helper function matching the algorithm's seasonal limits."""
    if month in [11, 12, 1, 2]:      # Zima
        return (10, 90)
    elif month in [3, 4]:            # Wiosna
        return (15, 85)
    elif month in [5, 6, 7, 8, 9]:   # Lato
        return (20, 80)
    elif month == 10:                # Jesień
        return (15, 85)
    else:
        return (20, 80)


def create_test_data(overrides=None):
    """Create test input data with optional overrides."""
    month = 1  # Default January (winter)
    if overrides and 'month' in overrides:
        month = overrides['month']

    soc_min, soc_max = get_seasonal_soc_limits(month)

    data = {
        'timestamp': '12:00',
        'hour': 12,
        'weekday': 2,  # Wednesday
        'month': month,
        'tariff_zone': 'L1',
        'rce_now': 0.45,
        'rce_evening_avg': 0.55,
        'soc': 50.0,
        'battery_power': 0.0,
        'battery_temp': 25.0,
        'pv_power': 5.0,  # kW
        'home_load': 2.0,  # kW
        'grid_power': 2.0,
        'forecast_today': 20.0,
        'forecast_tomorrow': 15.0,
        'forecast_6h': 10.0,
        'temp_outdoor': 10.0,
        'heating_mode': 'no_heating',
        'pc_co_active': False,
        'cwu_window': False,
        'is_backup_mode': False,
        'target_soc': min(80, soc_max),  # Z suwaka (domyślnie 80), ale max zgodne z sezonem
        'soc_min': soc_min,
        'soc_max': soc_max,
    }
    if overrides:
        data.update(overrides)
        # Recalculate soc_min/soc_max/target_soc if month changed
        if 'month' in overrides and 'soc_min' not in overrides:
            soc_min, soc_max = get_seasonal_soc_limits(data['month'])
            data['soc_min'] = soc_min
            data['soc_max'] = soc_max
            # target_soc = min(80, soc_max) chyba że explicite nadpisane
            if 'target_soc' not in overrides:
                data['target_soc'] = min(80, soc_max)
    return data


# Expose helper to tests
@pytest.fixture
def test_data_factory():
    """Factory for creating test data with custom values."""
    return create_test_data
