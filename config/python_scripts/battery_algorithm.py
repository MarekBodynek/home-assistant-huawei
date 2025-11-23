"""
Algorytm zarządzania baterią Huawei Luna 15kWh
Implementacja zgodna z ALGORITHM.md

Autor: Claude Code
Data: 2025-11-11
"""

# ============================================
# KONFIGURACJA - PROGI
# ============================================

# Progi cenowe RCE (zł/kWh)
RCE_NEGATIVE = 0.00
RCE_VERY_LOW = 0.20
RCE_LOW = 0.35
RCE_MEDIUM = 0.45
RCE_HIGH = 0.55
RCE_VERY_HIGH = 0.65
RCE_EXTREME = 0.75

# Progi prognozy PV (kWh)
FORECAST_EXCELLENT = 30
FORECAST_VERY_GOOD = 25
FORECAST_GOOD = 20
FORECAST_MEDIUM = 15
FORECAST_POOR = 12
FORECAST_BAD = 8
FORECAST_VERY_BAD = 5

# Progi baterii (%) - LIMITY HUAWEI: 20% min, 80% max
BATTERY_CRITICAL = 25  # Blisko dolnego limitu 20%
BATTERY_LOW = 30
BATTERY_RESERVE_SUMMER = 35
BATTERY_RESERVE_WINTER = 50
BATTERY_GOOD = 65
BATTERY_HIGH = 80  # Limit Huawei: 80%
BATTERY_MAX = 80  # Limit Huawei: 80%

# Temperatura i PC
TEMP_HEATING_THRESHOLD = 12  # °C
TEMP_FROST = -10
TEMP_WINTER = 0
TEMP_COLD = 5


# ============================================
# FUNKCJA GŁÓWNA - EXECUTE_STRATEGY
# ============================================

def execute_strategy():
    """
    Główna funkcja wykonywana co godzinę
    """
    data = collect_input_data()

    if not validate_data(data):
        # logger.error("Dane niekompletne - fallback mode")
        strategy = get_fallback_strategy(data)
        apply_battery_mode(strategy)
        return

    # PRIORYTET 0: Sprawdź temperaturę baterii - jeśli niebezpieczna, ZATRZYMAJ ładowanie NATYCHMIAST!
    temp_safe_state = hass.states.get('binary_sensor.bateria_bezpieczna_temperatura')
    if temp_safe_state and temp_safe_state.state == 'off':
        # Temperatura niebezpieczna - zatrzymaj natychmiast!
        charging_active = hass.states.get('switch.akumulatory_ladowanie_z_sieci')
        if charging_active and charging_active.state == 'on':
            # Zatrzymaj ładowanie
            hass.services.call('switch', 'turn_off', {
                'entity_id': 'switch.akumulatory_ladowanie_z_sieci'
            })
            # Ustaw max moc ładowania na 0W (dodatkowe zabezpieczenie)
            hass.services.call('number', 'set_value', {
                'entity_id': 'number.akumulatory_maksymalna_moc_ladowania',
                'value': 0
            })
            # Zapisz powód decyzji
            battery_temp = data.get('battery_temp', 'N/A')
            hass.services.call('input_text', 'set_value', {
                'entity_id': 'input_text.battery_decision_reason',
                'value': f'🚨 ZATRZYMANO - temperatura baterii ({battery_temp}°C) poza bezpiecznym zakresem!'
            })
            return

    # PRIORYTET 1: Sprawdź czy osiągnięto Target SOC - jeśli tak, ZATRZYMAJ ładowanie
    soc = data['soc']
    target_soc = data['target_soc']

    if soc >= target_soc:
        # Bateria naładowana do Target SOC - zatrzymaj ładowanie
        charging_active = hass.states.get('switch.akumulatory_ladowanie_z_sieci')
        if charging_active and charging_active.state == 'on':
            # Explicite zatrzymaj ładowanie
            hass.services.call('switch', 'turn_off', {
                'entity_id': 'switch.akumulatory_ladowanie_z_sieci'
            })
            # Ustaw max moc ładowania na 0W (dodatkowe zabezpieczenie)
            hass.services.call('number', 'set_value', {
                'entity_id': 'number.akumulatory_maksymalna_moc_ladowania',
                'value': 0
            })
            # Zapisz powód decyzji
            hass.services.call('input_text', 'set_value', {
                'entity_id': 'input_text.battery_decision_reason',
                'value': f'✅ Target SOC osiągnięty ({soc:.0f}% >= {target_soc}%) - ZATRZYMANO ładowanie'
            })
            return
        # Jeśli ładowanie już wyłączone, ale przywróć moc ładowania na normalną (5000W)
        # Bo mogła być ustawiona na 0W w poprzednim cyklu
        else:
            hass.services.call('number', 'set_value', {
                'entity_id': 'number.akumulatory_maksymalna_moc_ladowania',
                'value': 5000
            })

    balance = calculate_power_balance(data)

    # ZAWSZE obliczaj najtańsze godziny - niezależnie od nadwyżki PV
    # To wypełnia input_text.battery_storage_status i input_text.battery_cheapest_hours
    try:
        calculate_cheapest_hours_to_store(data)
    except Exception as e:
        # Jeśli błąd - zapisz info
        hass.services.call('input_text', 'set_value', {
            'entity_id': 'input_text.battery_storage_status',
            'value': f"Błąd analizy: {str(e)[:200]}"
        })

    strategy = decide_strategy(data, balance)
    result = apply_battery_mode(strategy)

    log_decision(data, balance, strategy, result)
    return result


# ============================================
# ZBIERANIE DANYCH
# ============================================

def collect_input_data():
    """Zbiera wszystkie dane z sensorów"""
    try:
        # Pobierz czas z Home Assistant
        now_state = hass.states.get('sensor.time')
        time_str = now_state.state if now_state else "12:00"
        hour = int(time_str.split(':')[0])

        # Pobierz datę z Home Assistant
        date_state = hass.states.get('sensor.date')
        if date_state:
            date_parts = date_state.state.split('-')
            month = int(date_parts[1]) if len(date_parts) >= 2 else 1
        else:
            month = 1

        return {
            'timestamp': time_str,
            'hour': hour,
            'weekday': 0,  # uproszczenie - nie używane w logice
            'month': month,

            # Taryfa
            'tariff_zone': get_state('sensor.strefa_taryfowa'),

            # Ceny RCE
            'rce_now': float(get_state('sensor.tge_rce_current') or 0.45),
            'rce_evening_avg': float(get_state('sensor.rce_srednia_wieczorna') or 0.55),

            # Bateria
            'soc': float(get_state('sensor.akumulatory_stan_pojemnosci') or 50),
            'battery_power': float(get_state('sensor.akumulatory_moc_ladowania_rozladowania') or 0) / 1000,
            'battery_temp': float(get_state('sensor.bateria_temperatura_maksymalna') or 25),

            # PV i zużycie
            'pv_power': float(get_state('sensor.inwerter_moc_wejsciowa') or 0) / 1000,
            'home_load': abs(float(get_state('sensor.pomiar_mocy_moc_czynna') or 0)) / 1000,
            'grid_power': float(get_state('sensor.pomiar_mocy_moc_czynna') or 0) / 1000,

            # Prognozy
            'forecast_today': float(get_state('sensor.prognoza_pv_dzisiaj') or 0),
            'forecast_tomorrow': float(get_state('sensor.prognoza_pv_jutro') or 0),
            'forecast_6h': float(get_state('sensor.prognoza_pv_6h') or 0),

            # Temperatura i PC
            'temp_outdoor': float(get_state('sensor.temperatura_zewnetrzna') or 10),
            'heating_mode': 'heating_season' if get_state('binary_sensor.sezon_grzewczy') == 'on' else 'no_heating',
            'pc_co_active': get_state('binary_sensor.pc_co_aktywne') == 'on',
            'cwu_window': get_state('binary_sensor.okno_cwu') == 'on',

            # Target SOC
            'target_soc': int(float(get_state('input_number.battery_target_soc') or 80)),
        }
    except Exception as e:
        # Błąd zbierania danych
        return {}


def validate_data(data):
    """Sprawdza czy dane są kompletne"""
    if not data:
        return False

    critical = ['soc', 'tariff_zone', 'pv_power', 'home_load', 'temp_outdoor']

    for field in critical:
        if field not in data or data[field] is None:
            # Brak danych
            return False

    if not (0 <= data['soc'] <= 100):
        # SOC poza zakresem
        return False

    return True


def calculate_power_balance(data):
    """Oblicza bilansy mocy"""
    pv = data['pv_power']
    load = data['home_load']

    if pv > load:
        surplus = pv - load
        deficit = 0
    else:
        surplus = 0
        deficit = load - pv

    return {
        'surplus': surplus,
        'deficit': deficit,
        'pv': pv,
        'load': load
    }


# ============================================
# GŁÓWNA LOGIKA DECYZYJNA
# ============================================

def decide_strategy(data, balance):
    """Główna funkcja decyzyjna"""
    soc = data['soc']

    # BEZPIECZEŃSTWO (limity Huawei: 20-80%)
    # SUPER PILNY: SOC < 5% - ładuj NATYCHMIAST 24/7!
    if soc < 5:
        return {
            'mode': 'charge_from_grid',
            'target_soc': 35,
            'priority': 'critical',
            'reason': 'SOC < 5% - SUPER PILNE! Ładowanie NATYCHMIAST 24/7!',
            'urgent_charge': True  # Ładuj przez całą dobę bez czekania na L2
        }

    # PILNY: SOC < 20% - ładuj w najbliższym oknie L2
    if soc < 20:
        return {
            'mode': 'charge_from_grid',
            'target_soc': 20,
            'priority': 'critical',
            'reason': 'SOC < 20% - PILNE ładowanie w najbliższym oknie L2!'
        }

    if soc >= 80:
        tariff = data['tariff_zone']

        # W L2 (tania taryfa) - nie rozładowuj baterii, pobieraj z sieci!
        if tariff == 'L2':
            return {
                'mode': 'grid_to_home',
                'priority': 'low',
                'reason': 'SOC 80% w L2 - zachowaj baterię na L1, pobieraj z sieci (tanie 0.41 zł/kWh)'
            }

        # W L1 (droga taryfa) - używaj baterii
        if balance['surplus'] > 0:
            return {
                'mode': 'discharge_to_grid',
                'priority': 'high',
                'reason': 'SOC 80%, nadwyżka PV - sprzedaj'
            }
        else:
            return {
                'mode': 'discharge_to_home',
                'priority': 'normal',
                'reason': 'SOC 80% w L1 - rozładowuj do domu (oszczędzaj drogi L1)'
            }

    # W L2 (tania taryfa weekend/święta) - oszczędzaj baterię na L1!
    tariff = data['tariff_zone']
    # WAŻNE: Ten warunek dotyczy TYLKO weekendów/świąt (L2 przez całą dobę 24h)
    # NIE dni powszednich 22-06h (tam ładujemy do Target SOC!)
    workday_state = hass.states.get('binary_sensor.dzien_roboczy')
    is_workday = workday_state and workday_state.state == 'on'

    if tariff == 'L2' and soc >= 40 and not is_workday:
        return {
            'mode': 'grid_to_home',
            'priority': 'normal',
            'reason': f'L2 niedziela/święto (tania 0.72 zł) - pobieraj z sieci, oszczędzaj baterię na poniedziałek (droga 1.11 zł)'
        }

    # ŁADOWANIE W L2 - INTELIGENTNE ZARZĄDZANIE PV vs SIEĆ
    # PRIORYTET: PV (darmowe) > Sieć L2 (tanie 0.72 zł) > Sieć L1 (drogie 1.11 zł)
    hour = data['hour']
    target_soc = data['target_soc']
    forecast_today = data['forecast_today']
    forecast_tomorrow = data['forecast_tomorrow']
    pv_surplus = balance['surplus']

    # ===========================================
    # POPRAWKA 1: L2 (noc/południe) - CHROŃ baterię gdy SOC >= Target
    # ===========================================
    if tariff == 'L2':
        is_night_l2 = hour in [22, 23, 0, 1, 2, 3, 4, 5]
        is_midday_l2 = hour in [13, 14]

        if (is_night_l2 or is_midday_l2) and soc >= target_soc:
            return {
                'mode': 'grid_to_home',
                'priority': 'normal',
                'reason': f'L2 - SOC {soc:.0f}% >= Target {target_soc}% - pobieraj z sieci, zachowaj baterię na L1'
            }

    # ===========================================
    # POPRAWKA 2: L1 (droga taryfa) - ROZŁADOWUJ baterię
    # ===========================================
    if tariff == 'L1' and soc > 20:
        # Sprawdź czy nie ma nadwyżki PV do sprzedaży
        if pv_surplus > 0.5:  # >500W nadwyżki
            # Nadwyżka PV - pozwól handle_pv_surplus zdecydować (może sprzedać)
            pass
        else:
            # Brak znaczącej nadwyżki - rozładowuj do domu
            return {
                'mode': 'discharge_to_home',
                'priority': 'high',
                'reason': f'L1 droga taryfa (1.11 zł) - rozładowuj baterię (SOC {soc:.0f}%)'
            }

    # L2 NOC (22-06h) - główne ładowanie do Target SOC (zawsze z sieci, bo brak PV)
    if tariff == 'L2' and hour in [22, 23, 0, 1, 2, 3, 4, 5] and soc < target_soc:
        if forecast_tomorrow < 15:
            priority = 'critical'
            reason = f'Noc L2 + pochmurno jutro ({forecast_tomorrow:.1f} kWh) - ładuj do {target_soc}%!'
        elif forecast_tomorrow < 25:
            priority = 'high'
            reason = f'Noc L2 + średnio jutro - ładuj do {target_soc}%'
        else:
            priority = 'medium'
            reason = f'Noc L2 + słonecznie jutro - ładuj do {target_soc}%'

        return {
            'mode': 'charge_from_grid',
            'target_soc': target_soc,
            'priority': priority,
            'reason': reason
        }

    # L2 POŁUDNIE (13-15h) - INTELIGENTNE ZARZĄDZANIE: PV vs SIEĆ
    if tariff == 'L2' and hour in [13, 14] and soc < 80:
        # Warunek: warto ładować (niska prognoza LUB SOC < Target)
        should_charge = forecast_today < 5 or soc < target_soc

        if should_charge:
            # PRIORYTET 1: Jeśli duża nadwyżka PV (>1.5 kW) - magazynuj TYLKO z PV (darmowe!)
            if pv_surplus > 1.5:
                return {
                    'mode': 'charge_from_pv',
                    'priority': 'medium',
                    'reason': f'L2 13-15h: nadwyżka PV {pv_surplus:.1f} kW - magazynuj z PV (darmowe!), sieć niepotrzebna'
                }

            # PRIORYTET 2: Mała nadwyżka PV (0.5-1.5 kW) lub balans
            # Oblicz ile godzin zostało do końca okna L2 (15:00)
            hours_left_l2 = 15 - hour
            # Ile kWh trzeba doładować?
            kwh_needed = (target_soc - soc) * 15 / 100  # 15 kWh nominalna
            # Czy PV + pozostały czas wystarczą?
            kwh_from_pv_estimate = pv_surplus * hours_left_l2 * 0.7  # 70% efektywność

            if kwh_from_pv_estimate >= kwh_needed:
                # PV wystarczy do naładowania do Target SOC
                return {
                    'mode': 'charge_from_pv',
                    'priority': 'medium',
                    'reason': f'L2 13-15h: PV wystarczy ({kwh_from_pv_estimate:.1f} kWh z {pv_surplus:.1f} kW), ładuj z PV'
                }
            else:
                # PV NIE wystarczy - uzupełnij z sieci (hybryda)
                return {
                    'mode': 'charge_from_grid',
                    'target_soc': min(80, target_soc),
                    'priority': 'high',
                    'reason': f'L2 13-15h: PV ({pv_surplus:.1f} kW) nie wystarczy, uzupełnij z sieci do {target_soc}%'
                }

            # PRIORYTET 3: Brak/małe PV - ładuj z sieci
            # (Ten kod nigdy się nie wykona bo powyższe case'y pokrywają wszystko, ale zostawiam dla przejrzystości)

    # AUTOCONSUMPTION
    if balance['surplus'] > 0:
        return handle_pv_surplus(data, balance)
    elif balance['deficit'] > 0:
        return handle_power_deficit(data, balance)
    else:
        return {
            'mode': 'idle',
            'priority': 'low',
            'reason': 'PV = Load, idealny balans'
        }


def calculate_cheapest_hours_to_store(data):
    """
    Oblicza N najtańszych godzin słonecznych do magazynowania energii.

    Algorytm:
    1. Ile kWh trzeba zmagazynować? (Target SOC - Current SOC)
    2. Ile godzin słonecznych zostało? (do zachodu słońca)
    3. Ile godzin potrzeba na naładowanie?
    4. Wybierz N najtańszych godzin sprzedaży RCE (bo wtedy nie opłaca się sprzedawać)

    Returns: (is_cheap_hour, reason, cheapest_hours_list)
    """
    try:
        soc = data['soc']
        target_soc = data['target_soc']
        hour = data['hour']
        forecast_today = data['forecast_today']

        # 1. Ile kWh trzeba zmagazynować?
        battery_capacity_nominal = 15  # kWh nominalna
        # Rzeczywista pojemność użytkowa: 60% (9 kWh) w zakresie SOC 20-80%
        energy_to_store = max(0, (target_soc - soc) / 100 * battery_capacity_nominal)

        # Zapamiętaj czy bateria naładowana (użyjemy później)
        battery_already_charged = energy_to_store <= 0.5

        # 2. Ile godzin słonecznych zostało? (użyj rzeczywistych czasów wschodu/zachodu)
        # Pobierz wschód i zachód słońca z sun.sun
        sun_state = hass.states.get('sun.sun')
        if sun_state:
            # next_rising i next_setting są w formacie ISO: "2025-11-16T07:30:00+01:00"
            next_rising_str = sun_state.attributes.get('next_rising', '')
            next_setting_str = sun_state.attributes.get('next_setting', '')

            # Parse godziny (ekstrahuj "HH" z "YYYY-MM-DDTHH:MM:SS")
            if 'T' in next_rising_str:
                sunrise_hour = int(next_rising_str.split('T')[1].split(':')[0])
            else:
                sunrise_hour = 6  # fallback

            if 'T' in next_setting_str:
                sunset_hour = int(next_setting_str.split('T')[1].split(':')[0])
            else:
                sunset_hour = 18  # fallback
        else:
            # Fallback jeśli sun.sun nie istnieje
            sunrise_hour = 6
            sunset_hour = 18

        # Oblicz ile godzin słonecznych zostało
        if hour < sunrise_hour:
            sun_hours_left = sunset_hour - sunrise_hour  # pełny dzień słoneczny
        elif hour >= sunset_hour:
            sun_hours_left = 0  # już po zachodzie
        else:
            sun_hours_left = sunset_hour - hour

        # ZAWSZE OBLICZ I WYPEŁNIJ POLA - nawet po zachodzie słońca!
        # Po zachodzie: pokaż dzisiejsze godziny słoneczne (analiza historyczna)

        # 3. Ile godzin potrzeba na naładowanie?
        # Po zachodzie (sun_hours_left == 0) użyj wszystkich godzin słonecznych dnia (12h)
        hours_for_calculation = sun_hours_left if sun_hours_left > 0 else 12

        if forecast_today <= 0:
            hours_needed = hours_for_calculation  # brak prognozy
        else:
            avg_pv_per_hour = forecast_today / 12  # średnio w ciągu 12h słonecznych
            hours_needed = min(int(energy_to_store / avg_pv_per_hour) + 1, hours_for_calculation)

        hours_needed = max(1, hours_needed)  # minimum 1 godzina

        # 4. Pobierz ceny godzinowe z RCE PSE
        rce_sensor = hass.states.get('sensor.rce_pse_cena')
        if not rce_sensor or rce_sensor.state in ['unavailable', 'unknown', None]:
            # Brak sensora RCE PSE - zapisz status i zakończ
            hass.services.call('input_text', 'set_value', {
                'entity_id': 'input_text.battery_storage_status',
                'value': f"Brak danych RCE PSE | Teraz: {hour}h"[:255]
            })
            hass.services.call('input_text', 'set_value', {
                'entity_id': 'input_text.battery_cheapest_hours',
                'value': "Brak danych"[:100]
            })
            return None, "Brak danych RCE PSE", []

        # RCE PSE używa atrybutu 'prices' z formatem dtime/rce_pln
        all_prices = rce_sensor.attributes.get('prices', [])
        if not all_prices:
            # Brak cen godzinowych - zapisz status i zakończ
            hass.services.call('input_text', 'set_value', {
                'entity_id': 'input_text.battery_storage_status',
                'value': f"Brak cen RCE | Teraz: {hour}h"[:255]
            })
            hass.services.call('input_text', 'set_value', {
                'entity_id': 'input_text.battery_cheapest_hours',
                'value': "Brak danych"[:100]
            })
            return None, "Brak cen godzinowych", []

        # Filtruj tylko dzisiejsze godziny słoneczne (sunrise - sunset)
        # Pobierz dzisiejszą datę z sensora
        date_state = hass.states.get('sensor.date')
        today_str = date_state.state if date_state else "2025-11-16"
        sun_prices = []

        for price_entry in all_prices:
            try:
                # RCE PSE format: dtime="2025-11-22 00:15:00", rce_pln=497.22 (PLN/MWh)
                start_str = price_entry.get('dtime', '') or price_entry.get('start', '') or price_entry.get('datetime', '')
                price_val = price_entry.get('rce_pln') or price_entry.get('price') or price_entry.get('value')

                if not start_str or price_val is None:
                    continue

                # Parse datetime: "2025-11-22 14:00:00" lub "2025-11-22T14:00:00"
                if ' ' in start_str:
                    date_part = start_str.split(' ')[0]
                    time_part = start_str.split(' ')[1].split(':')[0]
                    price_hour = int(time_part)
                elif 'T' in start_str:
                    date_part = start_str.split('T')[0]
                    time_part = start_str.split('T')[1].split(':')[0]
                    price_hour = int(time_part)
                else:
                    continue

                # RCE PSE zwraca ceny w PLN/MWh - przelicz na PLN/kWh
                price_float = float(price_val)
                if price_float > 10:  # Powyżej 10 = PLN/MWh
                    price_float = price_float / 1000  # Przelicz na PLN/kWh

                # Tylko dzisiaj + godziny słoneczne (sunrise <= hour < sunset)
                if date_part == today_str and sunrise_hour <= price_hour < sunset_hour:
                    sun_prices.append({
                        'hour': price_hour,
                        'price': price_float
                    })
            except Exception as e:
                # Błąd parsowania ceny
                continue

        if not sun_prices:
            return None, "Brak cen dla dzisiejszych godzin słonecznych", []

        # 5. Sortuj godziny po cenie (rosnąco - najtańsze pierwsze)
        sun_prices_sorted = sorted(sun_prices, key=lambda x: x['price'])

        # 6. Wybierz N najtańszych godzin
        cheapest_hours = [p['hour'] for p in sun_prices_sorted[:hours_needed]]

        # 7. Czy aktualna godzina jest w najtańszych?
        is_cheap_hour = hour in cheapest_hours

        # Znajdź cenę dla aktualnej godziny (bez użycia next())
        current_price = None
        for p in sun_prices:
            if p['hour'] == hour:
                current_price = p['price']
                break

        if is_cheap_hour:
            if current_price is not None:
                reason = f"TANIA godzina ({hour}h: {current_price:.3f} zł) - top {hours_needed} najtańszych - MAGAZYNUJ"
            else:
                reason = f"TANIA godzina ({hour}h) - top {hours_needed} najtańszych - MAGAZYNUJ"
        else:
            cheapest_price = sun_prices_sorted[0]['price']
            if current_price is not None:
                reason = f"DROGA godzina ({hour}h: {current_price:.3f} zł vs najtańsza {cheapest_price:.3f} zł) - SPRZEDAJ"
            else:
                reason = f"DROGA godzina ({hour}h vs najtańsza {cheapest_price:.3f} zł) - SPRZEDAJ"

        # Zapisz status do input_text dla wyświetlenia na dashboardzie
        if battery_already_charged:
            # Bateria naładowana - pokaż informację + najtańsze godziny
            status_msg = f"Bateria OK ({int(soc)}%) | Najtańsze: {cheapest_hours} | Teraz: {hour}h"
        else:
            # Normalny tryb - pokazuj potrzebę magazynowania
            status_msg = f"Potrzeba: {hours_needed}h | Najtańsze: {cheapest_hours} | Teraz: {hour}h"

        hass.services.call('input_text', 'set_value', {
            'entity_id': 'input_text.battery_storage_status',
            'value': status_msg[:255]
        })

        hass.services.call('input_text', 'set_value', {
            'entity_id': 'input_text.battery_cheapest_hours',
            'value': str(cheapest_hours)[:100]
        })

        # Jeśli bateria naładowana, nie wykonuj strategii magazynowania
        if battery_already_charged:
            return False, f"Bateria naładowana ({int(soc)}%) - nie trzeba magazynować", cheapest_hours

        return is_cheap_hour, reason, cheapest_hours

    except Exception as e:
        # Błąd w calculate_cheapest_hours_to_store
        hass.services.call('input_text', 'set_value', {
            'entity_id': 'input_text.battery_storage_status',
            'value': f"Błąd: {str(e)[:200]}"
        })
        return None, f"Błąd: {e}", []


def handle_pv_surplus(data, balance):
    """
    NADWYŻKA PV (słońce): oblicz tak, żeby zmagazynować najtańszą energię w ciągu dnia

    STRATEGIA OPTYMALIZACJI:
    - Oblicz ile godzin potrzeba na naładowanie baterii
    - Wybierz N najtańszych godzin sprzedaży (RCE)
    - W tych godzinach → MAGAZYNUJ (bo nie opłaca się sprzedawać tanio)
    - W pozostałych godzinach → SPRZEDAJ (bo cena lepsza)

    Priorytet decyzji:
    1. RCE ujemne lub < 0.15 zł → MAGAZYNUJ (ultra tanio)
    2. Jutro pochmurno → MAGAZYNUJ (zabezpieczenie)
    3. Zima → MAGAZYNUJ (każda kWh cenna)
    4. CZY TERAZ TANIA GODZINA? → Algorytm wyboru najtańszych godzin
    5. DEFAULT → SPRZEDAJ
    """
    soc = data['soc']
    rce_now = data['rce_now']
    forecast_tomorrow = data['forecast_tomorrow']
    hour = data['hour']
    month = data['month']

    # 1. RCE ujemne lub ultra niskie → MAGAZYNUJ
    if rce_now < 0.15 and soc < BATTERY_MAX:
        return {
            'mode': 'charge_from_pv',
            'priority': 'critical',
            'reason': f'RCE ultra niskie ({rce_now:.3f} zł) - nie oddawaj za bezcen! MAGAZYNUJ'
        }

    # 2. Jutro pochmurno → MAGAZYNUJ
    if forecast_tomorrow < FORECAST_POOR and soc < BATTERY_HIGH:
        return {
            'mode': 'charge_from_pv',
            'priority': 'very_high',
            'reason': f'Jutro pochmurno ({forecast_tomorrow:.1f} kWh) - MAGAZYNUJ'
        }

    # 3. Zima → MAGAZYNUJ
    if month in [11, 12, 1, 2] and soc < BATTERY_HIGH:
        return {
            'mode': 'charge_from_pv',
            'priority': 'high',
            'reason': 'Zima - każda kWh cenna! MAGAZYNUJ'
        }

    # 4. ALGORYTM WYBORU NAJTAŃSZYCH GODZIN
    is_cheap_hour, reason, cheapest_hours = calculate_cheapest_hours_to_store(data)

    if is_cheap_hour is None:
        # Błąd w algorytmie - fallback do prostej logiki
        # logger.warning(f"Algorytm magazynowania niedostępny: {reason}")
        # Fallback: porównaj z średnią
        if rce_now < 0.35 and soc < BATTERY_GOOD:
            return {
                'mode': 'charge_from_pv',
                'priority': 'medium',
                'reason': f'RCE poniżej średniej ({rce_now:.3f} zł) - MAGAZYNUJ'
            }
    elif is_cheap_hour:
        # TANIA godzina → MAGAZYNUJ
        return {
            'mode': 'charge_from_pv',
            'priority': 'high',
            'reason': reason,
            'cheapest_hours': cheapest_hours
        }

    # 5. DEFAULT: SPRZEDAJ (droga godzina lub bateria pełna)
    return {
        'mode': 'discharge_to_grid',
        'priority': 'normal',
        'reason': reason if reason else f'Warunki OK - SPRZEDAJ po RCE {rce_now:.3f} zł/kWh (× 1.23 = {rce_now * 1.23:.3f} zł/kWh)'
    }


def handle_power_deficit(data, balance):
    """Deficyt mocy - skąd pokryć?"""
    soc = data['soc']
    tariff = data['tariff_zone']
    hour = data['hour']
    temp = data['temp_outdoor']
    heating_mode = data['heating_mode']
    target_soc = data['target_soc']

    # Czy ładować z sieci?
    charge_decision = should_charge_from_grid(data)
    if charge_decision['should_charge']:
        return {
            'mode': 'charge_from_grid',
            'target_soc': charge_decision['target_soc'],
            'priority': charge_decision['priority'],
            'reason': charge_decision['reason']
        }

    # Arbitraż wieczorny?
    if hour in [19, 20, 21]:
        arbitrage = check_arbitrage_opportunity(data)
        if arbitrage['should_sell']:
            return {
                'mode': 'discharge_to_grid',
                'target_soc': arbitrage['min_soc'],
                'priority': 'high',
                'reason': arbitrage['reason']
            }

    # Sezon grzewczy
    if heating_mode == 'heating_season':
        if tariff == 'L1':
            # W L1 (droga taryfa 1.11 zł/kWh) - MINIMALIZUJ pobór z sieci!
            # Używaj baterii ile się da, NIE ładuj (czekaj na tanie L2 22:00)
            if soc > 20:
                return {
                    'mode': 'discharge_to_home',
                    'priority': 'critical',
                    'reason': f'PC w L1 (temp {temp:.1f}°C) - rozładowuj baterię, oszczędzaj drogą L1!'
                }
            else:
                # SOC ≤ 20%: NIE ŁADUJ w drogiej L1!
                # Czekaj na L2 22:00 (tanie 0.72 zł vs 1.11 zł - oszczędność 54%!)
                # Wyjątek: SOC ≤5% jest obsłużony wcześniej w decide_strategy (linia 248)
                return {
                    'mode': 'idle',
                    'priority': 'high',
                    'reason': f'SOC {soc:.0f}% w L1 - CZEKAJ na L2 22:00 (oszczędność 54%!), nie marnuj pieniędzy!'
                }
        else:  # L2
            # ===========================================
            # POPRAWKA 3: L2 noc - ładuj lub trzymaj baterię
            # ===========================================
            is_night_l2 = hour in [22, 23, 0, 1, 2, 3, 4, 5]

            if is_night_l2:
                if soc < target_soc:
                    return {
                        'mode': 'charge_from_grid',
                        'target_soc': target_soc,
                        'priority': 'high',
                        'reason': f'Noc L2 + deficit - ładuj do {target_soc}%'
                    }
                else:
                    return {
                        'mode': 'grid_to_home',
                        'priority': 'normal',
                        'reason': f'Noc L2, SOC {soc:.0f}% OK - pobieraj z sieci, zachowaj baterię'
                    }

            if data['cwu_window']:
                if soc > 70:
                    return {
                        'mode': 'grid_to_home',
                        'priority': 'medium',
                        'reason': 'PC CWU w L2 (tanie), oszczędzaj baterię na L1'
                    }
                else:
                    return {
                        'mode': 'charge_from_grid',
                        'target_soc': target_soc,
                        'priority': 'high',
                        'reason': 'PC w L2 + doładuj baterię na L1'
                    }

    # Poza sezonem
    else:
        if tariff == 'L1' and soc > 20:
            return {
                'mode': 'discharge_to_home',
                'priority': 'high',
                'reason': 'Oszczędzaj L1 (bez CO)'
            }
        elif data['cwu_window']:
            return {
                'mode': 'grid_to_home',
                'priority': 'low',
                'reason': 'CWU w L2 (tanie), oszczędzaj baterię'
            }

    # DEFAULT
    if soc > 15:
        return {
            'mode': 'discharge_to_home',
            'priority': 'normal',
            'reason': 'Standardowe użycie baterii'
        }
    else:
        return {
            'mode': 'grid_to_home',
            'priority': 'critical',
            'reason': 'SOC za niskie - pobór z sieci'
        }


def should_charge_from_grid(data):
    """Czy ładować z sieci?"""
    soc = data['soc']
    tariff = data['tariff_zone']
    hour = data['hour']
    rce_now = data['rce_now']
    forecast_tomorrow = data['forecast_tomorrow']
    heating_mode = data['heating_mode']
    target_soc = data['target_soc']
    battery_temp = data['battery_temp']

    # BEZPIECZEŃSTWO TERMICZNE
    # Nie ładuj jeśli temperatura baterii jest poza bezpiecznym zakresem
    if battery_temp > 40:
        return {
            'should_charge': False,
            'target_soc': None,
            'priority': 'critical',
            'reason': f'🔥 BLOKADA: Temp baterii {battery_temp:.1f}°C > 40°C! Ryzyko przegrzania!'
        }

    if battery_temp < 5:
        return {
            'should_charge': False,
            'target_soc': None,
            'priority': 'high',
            'reason': f'❄️ BLOKADA: Temp baterii {battery_temp:.1f}°C < 5°C! Ryzyko uszkodzenia ogniw!'
        }

    # RCE ujemne
    if rce_now < 0 and soc < 80:
        return {
            'should_charge': True,
            'target_soc': 80,
            'priority': 'critical',
            'reason': f'RCE ujemne ({rce_now:.3f})! Płacą Ci za pobór! (max 80%)'
        }

    # RCE bardzo niskie w południe
    if rce_now < 0.15 and hour in [11, 12, 13, 14]:
        if forecast_tomorrow < 10 and soc < 70:
            return {
                'should_charge': True,
                'target_soc': 80,
                'priority': 'high',
                'reason': f'RCE bardzo niskie ({rce_now:.3f}) + pochmurno jutro'
            }

    # UWAGA: Ładowanie L2 NOC (22-06h) i POŁUDNIE (13-15h) przeniesione do decide_strategy()
    # aby działało NIEZALEŻNIE od bilansu mocy (surplus/deficit)
    # Te warunki były tutaj, ale powodowały problem: nie uruchamiały się gdy była nadwyżka PV!

    # Rano przed końcem L2
    if tariff == 'L2' and hour in [4, 5]:
        if forecast_tomorrow < 12 and soc < 70:
            return {
                'should_charge': True,
                'target_soc': 80,
                'priority': 'critical',
                'reason': f'Ostatnia szansa w L2! Pochmurno jutro ({forecast_tomorrow:.1f} kWh) (max 80%)'
            }

    # SOC krytyczne
    if soc < 5:
        return {
            'should_charge': True,
            'target_soc': 20,
            'priority': 'critical',
            'reason': 'SOC krytyczne < 5% - ładuj do 20%!'
        }

    return {
        'should_charge': False,
        'target_soc': None,
        'priority': None,
        'reason': 'Brak warunków do ładowania z sieci'
    }


def check_arbitrage_opportunity(data):
    """Czy sprzedawać do sieci (arbitraż)?"""
    soc = data['soc']
    rce_now = data['rce_now']
    forecast_tomorrow = data['forecast_tomorrow']
    temp = data['temp_outdoor']
    heating_mode = data['heating_mode']
    hour = data['hour']
    month = data['month']

    if hour not in [19, 20, 21]:
        return {'should_sell': False, 'min_soc': None, 'reason': 'Nie wieczór'}

    # PRÓG ARBITRAŻU: Dynamiczny w zależności od sezonu
    # Koszt: L2 (0.72 zł) + cykl (0.33 zł) = 1.054 zł
    # Przychód: RCE × 1.23 > 1.054 → RCE > 0.86 zł
    # Sezon grzewczy: 0.90 zł (potrzebujesz baterii, wyższy próg)
    # Poza sezonem: 0.88 zł (niższy próg = więcej okazji do zarobku)
    arbitrage_threshold = 0.90 if heating_mode == 'heating_season' else 0.88

    if rce_now < arbitrage_threshold:
        return {
            'should_sell': False,
            'min_soc': None,
            'reason': f'RCE za niskie ({rce_now:.3f}) do arbitrażu (min {arbitrage_threshold:.2f} zł)'
        }

    # Sezon grzewczy
    if heating_mode == 'heating_season':
        if temp < -5:
            min_soc_required = 50
        elif temp < 5:
            min_soc_required = 45
        else:
            min_soc_required = 40

        if soc < min_soc_required + 20:
            return {
                'should_sell': False,
                'min_soc': None,
                'reason': f'SOC {soc}% za niskie (min {min_soc_required + 20}%) - PC potrzebuje!'
            }

        if forecast_tomorrow < 25:
            return {
                'should_sell': False,
                'min_soc': None,
                'reason': f'Jutro pochmurno ({forecast_tomorrow:.1f} kWh) + PC - nie sprzedawaj!'
            }

        # W sezonie grzewczym z PC próg jeszcze wyższy (potrzebujemy baterii!)
        if rce_now < 1.00:
            return {
                'should_sell': False,
                'min_soc': None,
                'reason': f'RCE {rce_now:.3f} za niskie przy PC (min 1.00 zł)'
            }

        min_soc = min_soc_required

    # Poza sezonem
    else:
        if soc < 55:
            return {
                'should_sell': False,
                'min_soc': None,
                'reason': f'SOC {soc}% za niskie do arbitrażu'
            }

        if forecast_tomorrow < 20:
            return {
                'should_sell': False,
                'min_soc': None,
                'reason': f'Jutro pochmurno ({forecast_tomorrow:.1f} kWh) - nie sprzedawaj'
            }

        if rce_now < 0.55:
            return {
                'should_sell': False,
                'min_soc': None,
                'reason': f'RCE {rce_now:.3f} za niskie (min 0.55)'
            }

        if month in [5, 6, 7, 8]:
            min_soc = 30
        else:
            min_soc = 35

    potential_kwh = (soc - min_soc) / 100 * 15
    revenue = potential_kwh * rce_now * 1.23

    return {
        'should_sell': True,
        'min_soc': min_soc,
        'reason': f'ARBITRAŻ! RCE {rce_now:.3f} × 1.23 = {rce_now * 1.23:.3f} zł/kWh, '
                  f'jutro {forecast_tomorrow:.1f} kWh PV. '
                  f'Sprzedaj ~{potential_kwh:.1f} kWh = ~{revenue:.2f} zł'
    }


# ============================================
# APLIKACJA TRYBU BATERII
# ============================================

def apply_battery_mode(strategy):
    """Aplikuje strategię do baterii"""
    mode = strategy['mode']
    reason = strategy.get('reason', 'Brak powodu')

    # logger.info(f"Applying strategy: {mode} - {reason}")

    # Zapisz powód decyzji do wyświetlenia na dashboardzie
    hass.services.call('input_text', 'set_value', {
        'entity_id': 'input_text.battery_decision_reason',
        'value': reason[:255]
    })

    if mode == 'charge_from_pv':
        set_huawei_mode('maximise_self_consumption', charge_from_grid=False)

    elif mode == 'charge_from_grid':
        target_soc = strategy.get('target_soc', 80)
        urgent_charge = strategy.get('urgent_charge', False)
        # WAŻNE: W L2 podczas ładowania BLOKUJ rozładowanie (oszczędzaj baterię na L1!)
        # Tryb time_of_use_luna2000 + harmonogram TOU + grid charging
        set_huawei_mode('time_of_use_luna2000', charge_from_grid=True, charge_soc_limit=target_soc,
                       urgent_charge=urgent_charge, max_discharge_power=0)

    elif mode == 'discharge_to_home':
        set_huawei_mode('maximise_self_consumption', charge_from_grid=False)

    elif mode == 'discharge_to_grid':
        min_soc = strategy.get('target_soc', 30)
        set_huawei_mode('maximise_self_consumption',
                       discharge_soc_limit=min_soc,
                       max_charge_power=0,
                       max_discharge_power=5000,
                       charge_from_grid=False)

    elif mode == 'grid_to_home':
        # W L2 - BLOKUJ rozładowywanie baterii! Ustaw max moc rozładowania na 0W
        # Tryb time_of_use_luna2000 + moc 0W = bateria nie rozładowuje się
        set_huawei_mode('time_of_use_luna2000', charge_from_grid=False, max_discharge_power=0)

    elif mode == 'idle':
        # ===========================================
        # POPRAWKA 4: W L2 chroń baterię, w L1 normalne zachowanie
        # ===========================================
        tariff_state = hass.states.get('sensor.strefa_taryfowa')
        if tariff_state and tariff_state.state == 'L2':
            # W L2 - blokuj rozładowanie baterii
            set_huawei_mode('time_of_use_luna2000', charge_from_grid=False, max_discharge_power=0)
        else:
            # W L1 - normalne zachowanie
            set_huawei_mode('maximise_self_consumption', charge_from_grid=False)

    return True


def set_huawei_mode(working_mode, **kwargs):
    """Ustawia tryb pracy baterii Huawei"""
    try:
        # Poprawny device_id dla Huawei Luna 2000 (Connected Energy Storage)
        # Znaleziony w .storage/core.entity_registry dla sensor.akumulatory_tou_charging_and_discharging_periods
        device_id = '7aa193fa5ec07dc7da9f5034f97e6987'

        # Ustaw tryb pracy
        hass.services.call('select', 'select_option', {
            'entity_id': 'select.akumulatory_tryb_pracy',
            'option': working_mode
        })

        # WAŻNE: Ustaw harmonogram TOU PRZED włączeniem switcha ładowania!
        # Tryb time_of_use_luna2000 wymaga harmonogramu NAJPIERW
        if 'charge_from_grid' in kwargs and kwargs['charge_from_grid']:
            try:
                # SUPER PILNY (SOC < 5%): Ładuj NATYCHMIAST przez całą dobę!
                if kwargs.get('urgent_charge', False):
                    tou_periods = "00:00-23:59/1234567/+"
                # NORMALNY/PILNY: Ładuj tylko w godzinach L2
                else:
                    # Sprawdź czy dzisiaj jest dzień roboczy (wykrywa święta + weekendy)
                    workday_state = hass.states.get('binary_sensor.dzien_roboczy')
                    is_workday = workday_state and workday_state.state == 'on'

                    if is_workday:
                        # Dzień powszedni: ładuj w godzinach L2 (22:00-06:00 + 13:00-15:00)
                        tou_periods = (
                            "22:00-23:59/12345/+\n"  # Pn-Pt wieczór (22-24h)
                            "00:00-05:59/12345/+\n"  # Pn-Pt noc (0-6h)
                            "13:00-14:59/12345/+"    # Pn-Pt południe (13-15h)
                        )
                    else:
                        # Weekend lub ŚWIĘTO: ładuj całą dobę (L2 przez 24h)
                        tou_periods = "00:00-23:59/67/+"

                # Wywołaj serwis z poprawnym device_id
                hass.services.call('huawei_solar', 'set_tou_periods', {
                    'device_id': device_id,
                    'periods': tou_periods
                })
            except Exception as tou_err:
                # Loguj błąd jeśli TOU periods się nie ustawiły
                try:
                    error_msg = f"TOU setup błąd: {str(tou_err)[:150]}"
                    hass.services.call('input_text', 'set_value', {
                        'entity_id': 'input_text.battery_decision_reason',
                        'value': error_msg
                    })
                except:
                    pass

        # Teraz można bezpiecznie włączyć ładowanie z sieci (harmonogram już ustawiony)
        if 'charge_from_grid' in kwargs:
            service = 'turn_on' if kwargs['charge_from_grid'] else 'turn_off'
            hass.services.call('switch', service, {
                'entity_id': 'switch.akumulatory_ladowanie_z_sieci'
            })

        # Ustaw limit SOC ładowania
        if 'charge_soc_limit' in kwargs:
            hass.services.call('number', 'set_value', {
                'entity_id': 'number.akumulatory_lmit_ladowania_z_sieci_soc',
                'value': kwargs['charge_soc_limit']
            })

        # Ustaw limit SOC rozładowania
        if 'discharge_soc_limit' in kwargs:
            hass.services.call('number', 'set_value', {
                'entity_id': 'number.akumulatory_koniec_rozladowania_soc',
                'value': kwargs['discharge_soc_limit']
            })

        # Ustaw maksymalną moc rozładowania
        # Domyślnie 5000W (normalne rozładowanie), chyba że explicite ustawiono inaczej
        max_discharge = kwargs.get('max_discharge_power', 5000)
        hass.services.call('number', 'set_value', {
            'entity_id': 'number.akumulatory_maksymalna_moc_rozladowania',
            'value': max_discharge
        })

        # Ustaw maksymalną moc ładowania
        # Domyślnie 5000W (normalne ładowanie), chyba że explicite ustawiono inaczej
        max_charge = kwargs.get('max_charge_power', 5000)
        hass.services.call('number', 'set_value', {
            'entity_id': 'number.akumulatory_maksymalna_moc_ladowania',
            'value': max_charge
        })

        # logger.info(f"Huawei mode set: {working_mode}")
        return True

    except Exception as e:
        # logger.error(f"Błąd ustawiania trybu Huawei: {e}")
        # Zapisz błąd do input_text żeby było widoczne na dashboardzie
        try:
            error_msg = f"BŁĄD set_huawei_mode: {str(e)[:200]}"
            hass.services.call('input_text', 'set_value', {
                'entity_id': 'input_text.battery_decision_reason',
                'value': error_msg
            })
        except:
            pass
        return False


# ============================================
# FUNKCJE POMOCNICZE
# ============================================

def get_state(entity_id):
    """Pobiera stan encji"""
    try:
        state = hass.states.get(entity_id)
        if state is None:
            # logger.warning(f"Encja nie znaleziona: {entity_id}")
            return None
        return state.state
    except Exception as e:
        # logger.error(f"Błąd pobierania stanu {entity_id}: {e}")
        return None


def get_fallback_strategy(data):
    """Strategia awaryjna"""
    soc = data.get('soc', 50)

    if soc < 30:
        return {
            'mode': 'charge_from_grid',
            'target_soc': 50,
            'priority': 'high',
            'reason': 'FALLBACK: Brak danych, ładuj'
        }
    else:
        return {
            'mode': 'idle',
            'priority': 'low',
            'reason': 'FALLBACK: Brak danych, idle'
        }


def log_decision(data, balance, strategy, result):
    """
    Loguje decyzję do Event Log (rotacja 5 slotów)

    Format JSON: {"ts":"ISO8601","lvl":"INFO/WARNING/ERROR","cat":"CATEGORY","msg":"..."}

    Kategorie:
    - DECISION: Główna decyzja algorytmu
    - CHARGE: Start/stop ładowania
    - DISCHARGE: Start/stop rozładowania
    - MODE: Zmiana trybu pracy
    - PRICE: Alert cenowy
    - SAFETY: Alarm bezpieczeństwa
    - ERROR: Błąd systemu
    """
    # UWAGA: W python_scripts HA nie można używać import!
    # Używamy wbudowanych funkcji

    # Określ poziom i kategorię na podstawie wyniku
    reason = result.get('reason', '') if result else ''
    mode = result.get('mode', 'unknown') if result else 'unknown'
    priority = result.get('priority', 'normal') if result else 'normal'

    # Określ level
    if 'BŁĄD' in reason or 'ERROR' in reason or '🚨' in reason:
        level = 'ERROR'
    elif 'ZATRZYMANO' in reason or priority == 'critical':
        level = 'ERROR'
    elif 'OSTRZEŻENIE' in reason or priority == 'high':
        level = 'WARNING'
    else:
        level = 'INFO'

    # Określ kategorię
    if 'temperatura' in reason.lower() or 'temp' in reason.lower():
        category = 'SAFETY'
    elif mode in ['charge_from_grid', 'charge_from_pv']:
        category = 'CHARGE'
    elif mode == 'discharge_to_grid':
        category = 'DISCHARGE'
    elif 'cena' in reason.lower() or 'RCE' in reason:
        category = 'PRICE'
    elif 'BŁĄD' in reason or 'ERROR' in reason:
        category = 'ERROR'
    else:
        category = 'DECISION'

    # Skróć wiadomość do 150 znaków (żeby zmieścić się w JSON w 255 znakach)
    msg = reason[:150] if reason else f"Mode: {mode}"
    # Escapuj cudzysłowy w wiadomości
    msg = msg.replace('"', "'")

    # Utwórz event JSON ręcznie (bez import json)
    # W python_scripts datetime jest dostępny bezpośrednio jako datetime (nie datetime.datetime)
    try:
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    except:
        timestamp = '2025-01-01T00:00:00'  # fallback
    event_json = '{"ts":"' + timestamp + '","lvl":"' + level + '","cat":"' + category + '","msg":"' + msg + '"}'

    # Rotacja: przesuń wszystkie sloty (5 -> usuń, 4->5, 3->4, 2->3, 1->2, new->1)
    # Odczytaj obecne wartości
    slots = []
    for i in range(1, 6):
        state = hass.states.get(f'input_text.event_log_{i}')
        slots.append(state.state if state else '')

    # Przesuń (slot 5 wypada, nowy wchodzi na slot 1)
    # slots[0] = event_log_1 (najnowszy)
    # slots[4] = event_log_5 (najstarszy)

    # Zapisz do slotów (od najstarszego do najnowszego)
    # slot 5 <- slot 4
    hass.services.call('input_text', 'set_value', {
        'entity_id': 'input_text.event_log_5',
        'value': slots[3]  # stary slot 4
    })
    # slot 4 <- slot 3
    hass.services.call('input_text', 'set_value', {
        'entity_id': 'input_text.event_log_4',
        'value': slots[2]  # stary slot 3
    })
    # slot 3 <- slot 2
    hass.services.call('input_text', 'set_value', {
        'entity_id': 'input_text.event_log_3',
        'value': slots[1]  # stary slot 2
    })
    # slot 2 <- slot 1
    hass.services.call('input_text', 'set_value', {
        'entity_id': 'input_text.event_log_2',
        'value': slots[0]  # stary slot 1
    })
    # slot 1 <- nowy event
    hass.services.call('input_text', 'set_value', {
        'entity_id': 'input_text.event_log_1',
        'value': event_json
    })

    # Dodatkowo loguj ERROR/WARNING do system_log
    if level in ['ERROR', 'WARNING']:
        hass.services.call('system_log', 'write', {
            'message': f'[{category}] {msg}',
            'level': level.lower(),
            'logger': 'homeassistant.components.battery_algorithm'
        })


# ============================================
# URUCHOMIENIE
# ============================================

try:
    execute_strategy()
except Exception as e:
    # ZAWSZE aktualizuj decision_reason - nawet przy błędzie!
    # To zapobiega alertom watchdoga gdy algorytm się wysypie
    error_msg = f"🚨 BŁĄD ALGORYTMU: {str(e)[:200]}"
    try:
        hass.services.call('input_text', 'set_value', {
            'entity_id': 'input_text.battery_decision_reason',
            'value': error_msg
        })
        # Ustaw tryb awaryjny - bezpieczny fallback
        hass.services.call('select', 'select_option', {
            'entity_id': 'select.akumulatory_tryb_pracy',
            'option': 'maximise_self_consumption'
        })
        # Wyłącz ładowanie z sieci (bezpieczeństwo)
        hass.services.call('switch', 'turn_off', {
            'entity_id': 'switch.akumulatory_ladowanie_z_sieci'
        })
    except:
        pass  # Jeśli nawet to nie działa, nie możemy nic zrobić
