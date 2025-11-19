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
    Oblicza cel ładowania na noc
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

        # SEZON GRZEWCZY
        if heating_mode == 'heating_season':
            # Zużycie CO w L1
            if temp < -10:
                co_l1_base = 60  # kWh
            elif temp < 0:
                co_l1_base = 50
            elif temp < 5:
                co_l1_base = 40
            else:
                co_l1_base = 30

            dom_l1 = 26  # kWh
            suma_l1 = co_l1_base + dom_l1

            # Ile PV pokryje?
            pokrycie_pv = min(forecast_tomorrow * 0.7, suma_l1 * 0.3)

            # Ile z baterii?
            z_baterii = min(suma_l1 - pokrycie_pv, 15)

            target_soc = int((z_baterii / 15) * 100)
            target_soc = max(20, min(80, target_soc))  # Limity Huawei: 20-80% (bezpieczne)

            # W mrozy więcej
            if temp < -5:
                target_soc = max(target_soc, 75)  # Max 80% (limit Huawei)

            # Przy bardzo niskiej prognozie PV → maksymalne ładowanie
            if forecast_tomorrow < 5:
                target_soc = 80  # Pochmurno - ładuj do max
            elif forecast_tomorrow < 10:
                target_soc = max(target_soc, 75)  # Częściowo pochmurno

            reason = f'Sezon grzewczy: temp {temp:.1f}°C, CO+dom={suma_l1:.0f}kWh, PV={pokrycie_pv:.0f}kWh, bateria={z_baterii:.0f}kWh, prognoza={forecast_tomorrow:.1f}kWh'

        # POZA SEZONEM
        else:
            dom_l1 = 28  # kWh

            # Ile PV pokryje?
            pokrycie_pv = min(forecast_tomorrow * 0.8, dom_l1 * 0.6)

            # Ile z baterii?
            z_baterii = min(dom_l1 - pokrycie_pv, 15)

            target_soc = int((z_baterii / 15) * 100)
            target_soc = max(20, min(80, target_soc))  # ✅ ZAWSZE 20-80% (bezpieczeństwo Huawei)

            # Poza sezonem - target SOC zależny od prognozy PV
            if forecast_tomorrow < 5:
                target_soc = 80  # Bardzo pochmurno - ładuj do max
            elif forecast_tomorrow < 10:
                target_soc = 70  # Pochmurno - ładuj więcej
            elif forecast_tomorrow < 15:
                target_soc = 60  # Średnio - umiarkowane ładowanie
            elif forecast_tomorrow < 20:
                target_soc = 50  # Częściowo słonecznie
            elif forecast_tomorrow < 30:
                target_soc = 40  # Słonecznie
            else:
                target_soc = 30  # Bardzo słonecznie - minimum

            reason = f'Bez CO: dom={dom_l1:.0f}kWh, PV={pokrycie_pv:.0f}kWh, bateria={z_baterii:.0f}kWh'

        # Zapisz target_soc
        hass.services.call('input_number', 'set_value', {
            'entity_id': 'input_number.battery_target_soc',
            'value': target_soc
        })

        logger.info(f"Daily strategy calculated: Target SOC = {target_soc}% | {reason}")

        # Wyślij notyfikację
        hass.services.call('persistent_notification', 'create', {
            'title': '📊 Strategia dzienna obliczona',
            'message': f'**Target SOC:** {target_soc}%\n\n{reason}\n\n'
                       f'Prognoza jutro: {forecast_tomorrow:.1f} kWh\n'
                       f'Temperatura: {temp:.1f}°C'
        })

        return {
            'target_soc': target_soc,
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
