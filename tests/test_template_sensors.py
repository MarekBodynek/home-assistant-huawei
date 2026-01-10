"""
Testy dla template sensors Home Assistant
Testuje logikę stref taryfowych, świąt, i innych sensorów obliczeniowych.
"""

import pytest
from datetime import datetime


# ============================================
# DANE TESTOWE
# ============================================

# Polskie święta stałe (MM-DD)
HOLIDAYS_FIXED = [
    '01-01',  # Nowy Rok
    '01-06',  # Trzech Króli
    '05-01',  # Święto Pracy
    '05-03',  # Konstytucja 3 Maja
    '08-15',  # Wniebowzięcie NMP
    '11-01',  # Wszystkich Świętych
    '11-11',  # Niepodległość
    '12-25',  # Boże Narodzenie
    '12-26'   # 2. dzień Bożego Narodzenia
]

# Święta ruchome 2024-2026
MOVABLE_HOLIDAYS = [
    '2024-03-31', '2024-04-01', '2024-05-30',  # Wielkanoc, Pon. Wielk., Boże Ciało 2024
    '2025-04-20', '2025-04-21', '2025-06-19',  # 2025
    '2026-04-05', '2026-04-06', '2026-06-04'   # 2026
]


# ============================================
# FUNKCJE LOGIKI SENSORÓW (kopie z template_sensors.yaml)
# ============================================

def is_workday(dt):
    """
    Sprawdza czy data to dzień roboczy (Pn-Pt bez świąt)
    Logika z binary_sensor.dzien_roboczy
    """
    weekday = dt.weekday()  # 0=Pn, 4=Pt, 5=Sob, 6=Ndz
    is_weekend = weekday >= 5

    today_str = dt.strftime('%m-%d')
    today_full = dt.strftime('%Y-%m-%d')

    is_holiday = today_str in HOLIDAYS_FIXED or today_full in MOVABLE_HOLIDAYS

    return not is_weekend and not is_holiday


def get_tariff_zone(dt):
    """
    Oblicza strefę taryfową G12w
    Logika z sensor.strefa_taryfowa
    """
    h = dt.hour
    is_working_day = is_workday(dt)

    if not is_working_day:
        return 'L2'  # Weekend/święto = cały dzień L2
    elif h >= 22 or h < 6:
        return 'L2'  # Noc
    elif 13 <= h < 15:
        return 'L2'  # Południe
    else:
        return 'L1'  # Szczyt


def is_cwu_window(dt):
    """
    Sprawdza czy teraz jest okno CWU
    Logika z binary_sensor.okno_cwu
    """
    h = dt.hour
    m = dt.minute
    time_decimal = h + (m / 60.0)
    is_working_day = is_workday(dt)

    if is_working_day:
        # Dzień roboczy: 04:30-06:00, 13:00-15:00, 20:00-24:00
        return ((time_decimal >= 4.5 and time_decimal < 6) or
                (time_decimal >= 13 and time_decimal < 15) or
                (time_decimal >= 20 and time_decimal < 24))
    else:
        # Weekend: 07:00-24:00
        return time_decimal >= 7 and time_decimal < 24


def is_heating_season(temp_outdoor):
    """
    Sprawdza czy jest sezon grzewczy
    Logika z binary_sensor.sezon_grzewczy
    """
    return temp_outdoor < 12


# ============================================
# TESTY is_workday
# ============================================

class TestIsWorkday:
    """Testy dla binary_sensor.dzien_roboczy"""

    def test_monday_is_workday(self):
        """Poniedziałek (bez święta) = dzień roboczy"""
        dt = datetime(2025, 11, 24, 12, 0)  # Poniedziałek
        assert is_workday(dt) == True

    def test_friday_is_workday(self):
        """Piątek (bez święta) = dzień roboczy"""
        dt = datetime(2025, 11, 28, 12, 0)  # Piątek
        assert is_workday(dt) == True

    def test_saturday_not_workday(self):
        """Sobota = nie dzień roboczy"""
        dt = datetime(2025, 11, 29, 12, 0)  # Sobota
        assert is_workday(dt) == False

    def test_sunday_not_workday(self):
        """Niedziela = nie dzień roboczy"""
        dt = datetime(2025, 11, 30, 12, 0)  # Niedziela
        assert is_workday(dt) == False

    def test_christmas_not_workday(self):
        """Boże Narodzenie = nie dzień roboczy"""
        dt = datetime(2025, 12, 25, 12, 0)
        assert is_workday(dt) == False

    def test_new_year_not_workday(self):
        """Nowy Rok = nie dzień roboczy"""
        dt = datetime(2025, 1, 1, 12, 0)
        assert is_workday(dt) == False

    def test_independence_day_not_workday(self):
        """Święto Niepodległości (11.11) = nie dzień roboczy"""
        dt = datetime(2025, 11, 11, 12, 0)
        assert is_workday(dt) == False

    def test_easter_monday_2025_not_workday(self):
        """Poniedziałek Wielkanocny 2025 = nie dzień roboczy"""
        dt = datetime(2025, 4, 21, 12, 0)
        assert is_workday(dt) == False

    def test_corpus_christi_2025_not_workday(self):
        """Boże Ciało 2025 = nie dzień roboczy"""
        dt = datetime(2025, 6, 19, 12, 0)
        assert is_workday(dt) == False


# ============================================
# TESTY get_tariff_zone
# ============================================

class TestGetTariffZone:
    """Testy dla sensor.strefa_taryfowa"""

    def test_workday_morning_l1(self):
        """Dzień roboczy rano (6-12) = L1"""
        for hour in [6, 7, 8, 9, 10, 11, 12]:
            dt = datetime(2025, 11, 24, hour, 0)  # Poniedziałek
            assert get_tariff_zone(dt) == 'L1', f"Godzina {hour} powinna być L1"

    def test_workday_afternoon_l1(self):
        """Dzień roboczy popołudnie (15-21) = L1"""
        for hour in [15, 16, 17, 18, 19, 20, 21]:
            dt = datetime(2025, 11, 24, hour, 0)
            assert get_tariff_zone(dt) == 'L1', f"Godzina {hour} powinna być L1"

    def test_workday_night_l2(self):
        """Dzień roboczy noc (22-05) = L2"""
        for hour in [22, 23, 0, 1, 2, 3, 4, 5]:
            dt = datetime(2025, 11, 24, hour, 0)
            assert get_tariff_zone(dt) == 'L2', f"Godzina {hour} powinna być L2"

    def test_workday_midday_l2(self):
        """Dzień roboczy południe (13-14) = L2"""
        for hour in [13, 14]:
            dt = datetime(2025, 11, 24, hour, 0)
            assert get_tariff_zone(dt) == 'L2', f"Godzina {hour} powinna być L2"

    def test_weekend_all_day_l2(self):
        """Weekend = cały dzień L2"""
        for hour in range(24):
            dt = datetime(2025, 11, 29, hour, 0)  # Sobota
            assert get_tariff_zone(dt) == 'L2', f"Weekend godzina {hour} powinna być L2"

    def test_holiday_all_day_l2(self):
        """Święto = cały dzień L2"""
        for hour in range(24):
            dt = datetime(2025, 12, 25, hour, 0)  # Boże Narodzenie
            assert get_tariff_zone(dt) == 'L2', f"Święto godzina {hour} powinna być L2"


# ============================================
# TESTY is_cwu_window
# ============================================

class TestIsCwuWindow:
    """Testy dla binary_sensor.okno_cwu"""

    def test_workday_morning_window(self):
        """Dzień roboczy rano 04:30-06:00 = okno CWU"""
        # 04:30
        dt = datetime(2025, 11, 24, 4, 30)
        assert is_cwu_window(dt) == True

        # 05:00
        dt = datetime(2025, 11, 24, 5, 0)
        assert is_cwu_window(dt) == True

        # 05:59
        dt = datetime(2025, 11, 24, 5, 59)
        assert is_cwu_window(dt) == True

    def test_workday_before_morning_window(self):
        """Dzień roboczy przed oknem 04:00 = brak okna"""
        dt = datetime(2025, 11, 24, 4, 0)
        assert is_cwu_window(dt) == False

    def test_workday_midday_window(self):
        """Dzień roboczy południe 13:00-15:00 = okno CWU"""
        for hour in [13, 14]:
            dt = datetime(2025, 11, 24, hour, 0)
            assert is_cwu_window(dt) == True

    def test_workday_evening_window(self):
        """Dzień roboczy wieczór 20:00-24:00 = okno CWU"""
        for hour in [20, 21, 22, 23]:
            dt = datetime(2025, 11, 24, hour, 0)
            assert is_cwu_window(dt) == True

    def test_workday_no_window_afternoon(self):
        """Dzień roboczy popołudnie 15:00-19:59 = brak okna"""
        for hour in [15, 16, 17, 18, 19]:
            dt = datetime(2025, 11, 24, hour, 0)
            assert is_cwu_window(dt) == False

    def test_weekend_window(self):
        """Weekend 07:00-24:00 = okno CWU"""
        for hour in range(7, 24):
            dt = datetime(2025, 11, 29, hour, 0)  # Sobota
            assert is_cwu_window(dt) == True

    def test_weekend_no_window_early(self):
        """Weekend przed 07:00 = brak okna"""
        for hour in range(0, 7):
            dt = datetime(2025, 11, 29, hour, 0)
            assert is_cwu_window(dt) == False


# ============================================
# TESTY is_heating_season
# ============================================

class TestIsHeatingSeason:
    """Testy dla binary_sensor.sezon_grzewczy"""

    def test_cold_is_heating_season(self):
        """Temperatura < 12°C = sezon grzewczy"""
        for temp in [-10, -5, 0, 5, 10, 11]:
            assert is_heating_season(temp) == True

    def test_warm_no_heating_season(self):
        """Temperatura >= 12°C = brak sezonu grzewczego"""
        for temp in [12, 15, 20, 25, 30]:
            assert is_heating_season(temp) == False

    def test_threshold_12(self):
        """Próg 12°C - granica"""
        assert is_heating_season(11.9) == True
        assert is_heating_season(12.0) == False
        assert is_heating_season(12.1) == False


# ============================================
# TESTY INTEGRACYJNE - SCENARIUSZE
# ============================================

class TestIntegrationScenarios:
    """Testy integracyjne - sprawdzenie scenariuszy"""

    def test_workday_morning_l1_no_cwu(self):
        """Poniedziałek 10:00: L1, brak okna CWU"""
        dt = datetime(2025, 11, 24, 10, 0)
        assert get_tariff_zone(dt) == 'L1'
        assert is_cwu_window(dt) == False

    def test_workday_midday_l2_cwu(self):
        """Poniedziałek 13:30: L2, okno CWU"""
        dt = datetime(2025, 11, 24, 13, 30)
        assert get_tariff_zone(dt) == 'L2'
        assert is_cwu_window(dt) == True

    def test_workday_evening_l1_cwu(self):
        """Poniedziałek 20:30: L1 (przed 22), okno CWU"""
        dt = datetime(2025, 11, 24, 20, 30)
        assert get_tariff_zone(dt) == 'L1'
        assert is_cwu_window(dt) == True

    def test_workday_night_l2_cwu(self):
        """Poniedziałek 22:30: L2, okno CWU"""
        dt = datetime(2025, 11, 24, 22, 30)
        assert get_tariff_zone(dt) == 'L2'
        assert is_cwu_window(dt) == True

    def test_weekend_all_l2(self):
        """Sobota: cały dzień L2"""
        for hour in range(24):
            dt = datetime(2025, 11, 29, hour, 0)
            assert get_tariff_zone(dt) == 'L2'

    def test_winter_heating_season(self):
        """Zima (temp 5°C) = sezon grzewczy"""
        assert is_heating_season(5) == True

    def test_summer_no_heating(self):
        """Lato (temp 25°C) = brak sezonu"""
        assert is_heating_season(25) == False


# ============================================
# TESTY EDGE CASES
# ============================================

class TestEdgeCases:
    """Testy przypadków brzegowych"""

    def test_midnight_boundary(self):
        """Północ (00:00) - granica dnia"""
        dt = datetime(2025, 11, 24, 0, 0)  # Poniedziałek 00:00
        assert get_tariff_zone(dt) == 'L2'  # Noc = L2

    def test_hour_21_59(self):
        """21:59 = L1 (przed nocą)"""
        dt = datetime(2025, 11, 24, 21, 59)
        assert get_tariff_zone(dt) == 'L1'

    def test_hour_22_00(self):
        """22:00 = L2 (początek nocy)"""
        dt = datetime(2025, 11, 24, 22, 0)
        assert get_tariff_zone(dt) == 'L2'

    def test_hour_05_59(self):
        """05:59 = L2 (koniec nocy)"""
        dt = datetime(2025, 11, 24, 5, 59)
        assert get_tariff_zone(dt) == 'L2'

    def test_hour_06_00(self):
        """06:00 = L1 (początek dnia)"""
        dt = datetime(2025, 11, 24, 6, 0)
        assert get_tariff_zone(dt) == 'L1'

    def test_hour_12_59(self):
        """12:59 = L1 (przed południem L2)"""
        dt = datetime(2025, 11, 24, 12, 59)
        assert get_tariff_zone(dt) == 'L1'

    def test_hour_13_00(self):
        """13:00 = L2 (początek południa)"""
        dt = datetime(2025, 11, 24, 13, 0)
        assert get_tariff_zone(dt) == 'L2'

    def test_hour_14_59(self):
        """14:59 = L2 (koniec południa)"""
        dt = datetime(2025, 11, 24, 14, 59)
        assert get_tariff_zone(dt) == 'L2'

    def test_hour_15_00(self):
        """15:00 = L1 (początek popołudnia)"""
        dt = datetime(2025, 11, 24, 15, 0)
        assert get_tariff_zone(dt) == 'L1'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
