"""
Konfiguracja pytest dla testów Home Assistant Huawei Solar
"""

import pytest
import sys
import os

# Dodaj ścieżki do modułów
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'config', 'python_scripts'))


@pytest.fixture
def mock_hass():
    """Fixture dla mockowanego obiektu hass"""
    from unittest.mock import MagicMock

    hass = MagicMock()
    hass.states = MagicMock()
    hass.services = MagicMock()

    return hass


@pytest.fixture
def sample_data():
    """Fixture z przykładowymi danymi wejściowymi"""
    return {
        'timestamp': '12:00',
        'hour': 12,
        'weekday': 0,
        'month': 11,
        'tariff_zone': 'L1',
        'rce_now': 0.55,
        'rce_evening_avg': 0.60,
        'soc': 50,
        'battery_power': 0,
        'battery_temp': 25,
        'pv_power': 3.5,
        'home_load': 1.5,
        'grid_power': -2.0,
        'forecast_today': 20,
        'forecast_tomorrow': 18,
        'forecast_6h': 8,
        'temp_outdoor': 12,
        'heating_mode': 'no_heating',
        'pc_co_active': False,
        'cwu_window': False,
        'target_soc': 80
    }
