"""
Oblicza strategię dzienną - cel ładowania baterii (Target SOC)
Uruchamiany o 04:00

Autor: Claude Code
Data: 2025-11-11
"""

import logging
from datetime import datetime

logger = logging.getLogger("calculate_daily_strategy")


def calculate_daily_strategy():
    """
    Oblicza cel ładowania - NOWA STRATEGIA z 3 oknami L2 (22-06h + 13-15h)

    Strategia:
    - NOC (22:00-06:00): Ładuj ZAWSZE do 80% (max wykorzystanie taniego L2)
    - DZIEŃ (13:00-15:00): Doładuj tyle, żeby wystarczyło do 22:00
    """
    try:
        # Pobierz dane z bezpieczną obsługą błędów
        forecast_state = hass.states.get('sensor.prognoza_pv_jutro')
        temp_state = hass.states.get('sensor.temperatura_zewnetrzna')
        heating_state = hass.states.get('binary_sensor.sezon_grzewczy')

        if forecast_state is None or forecast_state.state in ['unknown', 'unavailable', None]:
            logger.warning("Sensor prognoza_pv_jutro not available, using 0")
            forecast_tomorrow = 0.0
        else:
            try:
                forecast_tomorrow = float(forecast_state.state)
            except (ValueError, TypeError):
                logger.warning(f"Invalid forecast value: {forecast_state.state}, using 0")
                forecast_tomorrow = 0.0

        if temp_state is None or temp_state.state in ['unknown', 'unavailable', None]:
            logger.warning("Sensor temperatura_zewnetrzna not available, using 10")
            temp = 10.0
        else:
            try:
                temp = float(temp_state.state)
            except (ValueError, TypeError):
                logger.warning(f"Invalid temp value: {temp_state.state}, using 10")
                temp = 10.0

        if heating_state is None or heating_state.state in ['unknown', 'unavailable', None]:
            logger.warning("Sensor sezon_grzewczy not available, using no_heating")
            heating_mode = 'no_heating'
        else:
            heating_mode = 'heating_season' if heating_state.state == 'on' else 'no_heating'

        month = datetime.now().month

        logger.info(f"Calculating daily strategy: forecast={forecast_tomorrow}kWh, temp={temp}°C, mode={heating_mode}")

        # ============================================
        # NOWA STRATEGIA: Agresywne wykorzystanie 3 okien L2
        # ============================================

        # NOC (22:00-06:00): ZAWSZE ładuj do MAX (80%)
        target_soc_night = 80

        # DZIEŃ (13:00-15:00): Oblicz ile potrzeba do wieczora (15:00-22:00 = 7h)

        # SEZON GRZEWCZY
        if heating_mode == 'heating_season':
            # Zużycie wieczorne 15:00-22:00 (7h L1)
            if temp < -10:
                evening_consumption = 25  # kWh (intensywne CO)
            elif temp < 0:
                evening_consumption = 20
            elif temp < 5:
                evening_consumption = 18
            else:
                evening_consumption = 15

            # Ile PV pokryje wieczorem? (słońce zachodzi ~16-17h)
            evening_pv = min(forecast_tomorrow * 0.15, evening_consumption * 0.2)

            # Ile z baterii?
            evening_battery_need = evening_consumption - evening_pv

            # Target dla okienka dziennego = ile potrzeba do wieczora
            target_soc_day = int((evening_battery_need / 15) * 100)
            target_soc_day = max(40, min(70, target_soc_day))  # Cap 40-70%

            reason = f'Sezon grzewczy: temp {temp:.1f}°C | NOC→80% | DZIEŃ→{target_soc_day}% (wieczór: {evening_consumption}kWh - {evening_pv:.1f}kWh PV)'

        # POZA SEZONEM
        else:
            # Zużycie wieczorne 15:00-22:00 (7h L1, tylko dom)
            evening_consumption = 12  # kWh (bez CO)

            # Ile PV pokryje wieczorem?
            evening_pv = min(forecast_tomorrow * 0.2, evening_consumption * 0.3)

            # Ile z baterii?
            evening_battery_need = evening_consumption - evening_pv

            # Target dla okienka dziennego
            target_soc_day = int((evening_battery_need / 15) * 100)
            target_soc_day = max(30, min(60, target_soc_day))  # Cap 30-60%

            # Latem jeszcze mniej (dużo PV)
            if forecast_tomorrow > 25:
                target_soc_day = max(30, target_soc_day - 10)

            reason = f'Bez CO | NOC→80% | DZIEŃ→{target_soc_day}% (wieczór: {evening_consumption}kWh - {evening_pv:.1f}kWh PV)'

        # ============================================
        # ZAPISZ TARGET SOC
        # ============================================
        # Dla NOC: ZAWSZE 80% (maksymalne wykorzystanie taniego L2)
        # Dla DZIEŃ: dynamiczny target (obliczany w battery_algorithm.py)

        hass.services.call('input_number', 'set_value', {
            'entity_id': 'input_number.battery_target_soc',
            'value': target_soc_night  # Nocny target = 80%
        })

        logger.info(f"Daily strategy calculated: NOC→{target_soc_night}% | DZIEŃ→{target_soc_day}% | {reason}")

        # Wyślij notyfikację
        hass.services.call('persistent_notification', 'create', {
            'title': '📊 Strategia dzienna obliczona',
            'message': f'**Target NOC:** {target_soc_night}%\n'
                       f'**Target DZIEŃ:** {target_soc_day}%\n\n'
                       f'{reason}\n\n'
                       f'Prognoza jutro: {forecast_tomorrow:.1f} kWh\n'
                       f'Temperatura: {temp:.1f}°C'
        })

        return {
            'target_soc_night': target_soc_night,
            'target_soc_day': target_soc_day,
            'reason': reason,
            'forecast': forecast_tomorrow,
            'temp': temp,
            'heating_mode': heating_mode
        }

    except Exception as e:
        logger.error(f"Błąd obliczania strategii: {e}")
        return None


# Uruchom
calculate_daily_strategy()
