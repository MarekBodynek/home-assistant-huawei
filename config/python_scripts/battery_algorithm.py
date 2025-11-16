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
BATTERY_HIGH = 70
BATTERY_MAX = 75  # Bezpiecznie poniżej 80%

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
            'target_soc': int(float(get_state('input_number.battery_target_soc') or 70)),
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
            'target_soc': 35,
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
    if tariff == 'L2' and soc >= 40:
        return {
            'mode': 'grid_to_home',
            'priority': 'normal',
            'reason': f'L2 niedziela/święto (tania 0.72 zł) - pobieraj z sieci, oszczędzaj baterię na poniedziałek (droga 1.11 zł)'
        }

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

        # Jeśli bateria już naładowana
        if energy_to_store <= 0.5:  # mniej niż 0.5 kWh
            return False, "Bateria już naładowana do Target SOC", []

        # 2. Ile godzin słonecznych zostało?
        if hour < 6:
            sun_hours_left = 12  # 6-18h
        elif hour >= 18:
            sun_hours_left = 0  # już ciemno
        else:
            sun_hours_left = 18 - hour

        if sun_hours_left == 0:
            return False, "Już po zachodzie słońca", []

        # 3. Ile godzin potrzeba na naładowanie?
        if forecast_today <= 0:
            hours_needed = sun_hours_left  # brak prognozy, magazynuj wszystko
        else:
            avg_pv_per_hour = forecast_today / 12  # średnio w ciągu 12h słonecznych
            hours_needed = min(int(energy_to_store / avg_pv_per_hour) + 1, sun_hours_left)

        hours_needed = max(1, hours_needed)  # minimum 1 godzina

        # 4. Pobierz ceny godzinowe z Pstryk
        pstryk_sensor = hass.states.get('sensor.pstryk_current_sell_price')
        if not pstryk_sensor:
            # Brak sensora Pstryk
            return None, "Brak danych Pstryk", []

        all_prices = pstryk_sensor.attributes.get('All prices', [])
        if not all_prices:
            # Brak cen godzinowych
            return None, "Brak cen godzinowych", []

        # Filtruj tylko dzisiejsze godziny słoneczne (6-18h)
        # Pobierz dzisiejszą datę z sensora
        date_state = hass.states.get('sensor.date')
        today_str = date_state.state if date_state else "2025-11-16"
        sun_prices = []

        for price_entry in all_prices:
            try:
                start_str = price_entry.get('start', '')
                price_val = price_entry.get('price')

                if not start_str or price_val is None:
                    continue

                # Parse datetime ręcznie: "2025-11-16T14:00:00" -> date="2025-11-16", hour=14
                if 'T' in start_str:
                    date_part = start_str.split('T')[0]
                    time_part = start_str.split('T')[1].split(':')[0]
                    price_hour = int(time_part)
                else:
                    continue

                # Tylko dzisiaj + godziny słoneczne
                if date_part == today_str and 6 <= price_hour < 18:
                    sun_prices.append({
                        'hour': price_hour,
                        'price': float(price_val)
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

        if is_cheap_hour:
            current_price = next((p['price'] for p in sun_prices if p['hour'] == hour), None)
            reason = f"TANIA godzina ({hour}h: {current_price:.3f} zł) - top {hours_needed} najtańszych - MAGAZYNUJ"
        else:
            current_price = next((p['price'] for p in sun_prices if p['hour'] == hour), None)
            cheapest_price = sun_prices_sorted[0]['price']
            reason = f"DROGA godzina ({hour}h: {current_price:.3f} zł vs najtańsza {cheapest_price:.3f} zł) - SPRZEDAJ"

        # Zapisz status do input_text dla wyświetlenia na dashboardzie
        status_msg = f"Potrzeba: {hours_needed}h | Najtańsze: {cheapest_hours} | Teraz: {hour}h"
        hass.services.call('input_text', 'set_value', {
            'entity_id': 'input_text.battery_storage_status',
            'value': status_msg[:255]
        })

        hass.services.call('input_text', 'set_value', {
            'entity_id': 'input_text.battery_cheapest_hours',
            'value': str(cheapest_hours)[:100]
        })

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
            if soc > 25:
                return {
                    'mode': 'discharge_to_home',
                    'priority': 'critical',
                    'reason': f'PC pracuje w L1 (temp {temp:.1f}°C) - oszczędzaj L1!'
                }
            else:
                return {
                    'mode': 'charge_from_grid',
                    'priority': 'high',
                    'reason': 'SOC niskie w L1 z PC - doładuj!'
                }
        else:  # L2
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

    # WIOSNA/JESIEŃ - doładowanie w oknie L2 13-15h (miesiące: III, IV, V, IX, X, XI)
    if data['month'] in [3, 4, 5, 9, 10, 11]:
        if hour in [13, 14, 15] and tariff == 'L2' and soc < 80:
            # Oszacowanie dziennego zużycia energii
            daily_consumption = 35 if heating_mode == 'heating_season' else 20
            forecast_today = data['forecast_today']

            # Jeśli produkcja PV nie wystarczy na dzienne potrzeby
            if forecast_today < daily_consumption:
                return {
                    'should_charge': True,
                    'target_soc': 80,
                    'priority': 'high',
                    'reason': f'Wiosna/jesień: PV {forecast_today:.1f} < potrzeby {daily_consumption} kWh - doładowanie w L2 13-15h'
                }

    # NOC L2 - główne ładowanie
    if tariff == 'L2' and hour in [22, 23, 0, 1, 2, 3, 4, 5]:
        if soc < target_soc:
            if forecast_tomorrow < 15:
                priority = 'critical'
                reason = f'Noc L2 + pochmurno jutro ({forecast_tomorrow:.1f} kWh) - ładuj do {target_soc}%!'
            elif forecast_tomorrow < 25:
                priority = 'high'
                reason = f'Noc L2 + średnio jutro - ładuj do {target_soc}%'
            else:
                priority = 'medium'
                reason = f'Noc L2 + słonecznie jutro - ładuj do {target_soc}%'

            if heating_mode == 'heating_season':
                if priority == 'medium':
                    priority = 'high'
                elif priority == 'high':
                    priority = 'critical'

            return {
                'should_charge': True,
                'target_soc': target_soc,
                'priority': priority,
                'reason': reason
            }

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
    if soc < 15:
        return {
            'should_charge': True,
            'target_soc': 30,
            'priority': 'critical',
            'reason': 'SOC krytyczne - bezpieczeństwo'
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
        set_huawei_mode('time_of_use_luna2000', charge_from_grid=True, charge_soc_limit=target_soc, urgent_charge=urgent_charge)

    elif mode == 'discharge_to_home':
        set_huawei_mode('maximise_self_consumption', charge_from_grid=False)

    elif mode == 'discharge_to_grid':
        min_soc = strategy.get('target_soc', 30)
        set_huawei_mode('fully_fed_to_grid', discharge_soc_limit=min_soc)

    elif mode == 'grid_to_home':
        # W L2 - BLOKUJ rozładowywanie baterii! Ustaw max moc rozładowania na 0W
        # Tryb TOU + moc 0W = bateria nie rozładowuje się
        set_huawei_mode('time_of_use_luna2000', charge_from_grid=False, max_discharge_power=0)

    elif mode == 'idle':
        set_huawei_mode('maximise_self_consumption', charge_from_grid=False)

    return True


def set_huawei_mode(working_mode, **kwargs):
    """Ustawia tryb pracy baterii Huawei"""
    try:
        # Pobierz device_id dynamicznie z encji Huawei
        battery_entity = hass.states.get('select.akumulatory_tryb_pracy')
        device_id = None
        if battery_entity and hasattr(battery_entity, 'attributes'):
            device_id = battery_entity.attributes.get('device_id')

        # Fallback do hardcoded jeśli nie znaleziono (backward compatibility)
        if not device_id:
            device_id = '450d2d6fd853d7876315d70559e1dd83'

        # Ustaw tryb pracy
        hass.services.call('select', 'select_option', {
            'entity_id': 'select.akumulatory_tryb_pracy',
            'option': working_mode
        })

        # Ustaw ładowanie z sieci
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

        # Ustaw maksymalną moc rozładowania (0W = blokada rozładowania)
        if 'max_discharge_power' in kwargs:
            hass.services.call('number', 'set_value', {
                'entity_id': 'number.akumulatory_maksymalna_moc_rozladowania',
                'value': kwargs['max_discharge_power']
            })
        # Przywróć normalną moc rozładowania (5000W) jeśli nie ustawiono max_discharge_power
        elif working_mode != 'time_of_use_luna2000' or kwargs.get('charge_from_grid', False):
            hass.services.call('number', 'set_value', {
                'entity_id': 'number.akumulatory_maksymalna_moc_rozladowania',
                'value': 5000
            })

        # Ustaw harmonogram TOU dla ładowania z sieci
        if 'charge_from_grid' in kwargs and kwargs['charge_from_grid']:
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

            hass.services.call('huawei_solar', 'set_tou_periods', {
                'device_id': device_id,
                'periods': tou_periods
            })

        # logger.info(f"Huawei mode set: {working_mode}")
        return True

    except Exception as e:
        # logger.error(f"Błąd ustawiania trybu Huawei: {e}")
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
    """Loguje decyzję"""
    # Logging disabled in python_script
    pass


# ============================================
# URUCHOMIENIE
# ============================================

execute_strategy()
