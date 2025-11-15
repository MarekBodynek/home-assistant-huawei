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
        # Pobierz dane
        forecast_tomorrow = float(hass.states.get('sensor.prognoza_pv_jutro').state or 0)
        temp = float(hass.states.get('sensor.temperatura_zewnetrzna').state or 10)
        heating_mode = 'heating_season' if hass.states.get('binary_sensor.sezon_grzewczy').state == 'on' else 'no_heating'
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
            target_soc = max(45, min(75, target_soc))  # Limity Huawei: 20-80%

            # W mrozy więcej
            if temp < -5:
                target_soc = max(target_soc, 70)  # Max 75% (limit Huawei 80%)

            reason = f'Sezon grzewczy: temp {temp:.1f}°C, CO+dom={suma_l1:.0f}kWh, PV={pokrycie_pv:.0f}kWh, bateria={z_baterii:.0f}kWh'

        # POZA SEZONEM
        else:
            dom_l1 = 28  # kWh

            # Ile PV pokryje?
            pokrycie_pv = min(forecast_tomorrow * 0.8, dom_l1 * 0.6)

            # Ile z baterii?
            z_baterii = min(dom_l1 - pokrycie_pv, 15)

            target_soc = int((z_baterii / 15) * 100)
            target_soc = max(30, min(70, target_soc))

            # Latem mniej
            if forecast_tomorrow > 30:
                target_soc = 30
            elif forecast_tomorrow > 20:
                target_soc = 40
            else:
                target_soc = 50

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
