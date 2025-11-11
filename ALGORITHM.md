# 🧠 ALGORYTM ZARZĄDZANIA BATERIĄ HUAWEI LUNA 15kWh

## Taryfa G12w + RCE Godzinowa + Pompa Ciepła

-----

## 📅 HARMONOGRAM URUCHAMIANIA

```
04:00  → fetch_forecast_pv() + calculate_daily_strategy()
04:30  → execute_strategy() [początek okna CWU]
06:00  → execute_strategy() [zmiana L2→L1]
12:00  → fetch_forecast_pv() + recalculate_strategy()
13:00  → execute_strategy() [zmiana L1→L2]
15:00  → execute_strategy() [zmiana L2→L1]
18:00  → fetch_rce_prices() [random 0-15min delay]
19:00  → execute_strategy() [SZCZYT + arbitraż]
20:00  → fetch_forecast_pv() + finalize_night_strategy()
22:00  → execute_strategy() [zmiana L1→L2 + ładowanie]

CO 1h (XX:00) → execute_strategy() [główna pętla]
CO 1min → monitor_critical_states()
```

-----

## 🎯 GŁÓWNA FUNKCJA DECYZYJNA

```python
def execute_strategy():
    """
    Główna funkcja wykonywana co godzinę (XX:00)
    oraz przy zmianach stref i w kluczowych momentach
    """

    # ============================================
    # KROK 1: ZBIERZ DANE WEJŚCIOWE
    # ============================================

    data = collect_input_data()

    # Walidacja danych
    if not validate_data(data):
        log_error("Dane niekompletne")
        fallback_mode = get_fallback_strategy(data)
        apply_battery_mode(fallback_mode)
        return

    # ============================================
    # KROK 2: OBLICZ BILANSY
    # ============================================

    balance = calculate_power_balance(data)

    # ============================================
    # KROK 3: WYBIERZ STRATEGIĘ
    # ============================================

    strategy = decide_strategy(data, balance)

    # ============================================
    # KROK 4: WYKONAJ AKCJĘ
    # ============================================

    result = apply_battery_mode(strategy)

    # ============================================
    # KROK 5: LOGOWANIE
    # ============================================

    log_decision(data, balance, strategy, result)

    return result


# ============================================
# FUNKCJE POMOCNICZE - DANE WEJŚCIOWE
# ============================================

def collect_input_data():
    """
    Zbiera wszystkie potrzebne dane z sensorów
    """
    return {
        # Czas
        'timestamp': now(),
        'hour': current_hour(),
        'weekday': current_weekday(),
        'is_holiday': is_holiday(),

        # Taryfa
        'tariff_zone': get_tariff_zone(),  # 'L1' lub 'L2'

        # Ceny RCE
        'rce_now': get_rce_current(),
        'rce_next': get_rce_next_hour(),
        'rce_evening_avg': get_rce_evening_avg(),  # 19-22h

        # Bateria
        'soc': get_battery_soc(),  # %
        'battery_power': get_battery_power(),  # kW (+ładowanie, -rozładowanie)
        'battery_temp': get_battery_temp(),

        # PV i zużycie
        'pv_power': get_pv_power(),  # kW
        'home_load': get_home_load(),  # kW
        'grid_power': get_grid_power(),  # kW (+pobór, -oddawanie)

        # Prognozy
        'forecast_today': get_forecast_today(),  # kWh
        'forecast_tomorrow': get_forecast_tomorrow(),  # kWh
        'forecast_6h': get_forecast_next_6h(),  # kWh

        # Temperatura i PC
        'temp_outdoor': get_outdoor_temp(),
        'heating_mode': get_heating_mode(),  # 'heating_season' lub 'no_heating'
        'pc_co_active': is_temp_below_12(),
        'cwu_window': is_cwu_window(),  # 04:30-06:00 lub 13:00-15:00

        # Strategia obliczona wcześniej
        'target_soc': get_calculated_target_soc(),
        'charge_allowed': is_charging_window(),
    }


def validate_data(data):
    """
    Sprawdza czy wszystkie krytyczne dane są dostępne
    """
    critical_fields = [
        'soc', 'tariff_zone', 'pv_power',
        'home_load', 'temp_outdoor'
    ]

    for field in critical_fields:
        if data[field] is None or data[field] == 'unavailable':
            return False

    # SOC w rozsądnym zakresie
    if not (0 <= data['soc'] <= 100):
        return False

    return True


def calculate_power_balance(data):
    """
    Oblicza bilansy mocy
    """
    pv = data['pv_power']
    load = data['home_load']

    if pv > load:
        surplus = pv - load
        deficit = 0
    else:
        surplus = 0
        deficit = load - pv

    return {
        'surplus': surplus,    # kW nadwyżki PV
        'deficit': deficit,    # kW deficytu
        'pv': pv,
        'load': load
    }


# ============================================
# GŁÓWNA LOGIKA DECYZYJNA
# ============================================

def decide_strategy(data, balance):
    """
    Główna funkcja decyzyjna - wybiera strategię

    Returns:
        {
            'mode': str,           # 'charge_from_pv', 'charge_from_grid',
                                   # 'discharge_to_home', 'discharge_to_grid', 'idle'
            'target_power': float, # kW (opcjonalnie)
            'target_soc': int,     # % (dla ładowania)
            'priority': str,       # 'critical', 'high', 'medium', 'low'
            'reason': str          # Uzasadnienie
        }
    """

    # ============================================
    # PRIORYTET 0: BEZPIECZEŃSTWO BATERII
    # ============================================

    if data['soc'] <= 10:
        return {
            'mode': 'charge_from_grid',
            'target_soc': 20,
            'priority': 'critical',
            'reason': 'SOC krytycznie niskie - bezpieczeństwo baterii'
        }

    if data['soc'] >= 95:
        if balance['surplus'] > 0:
            return {
                'mode': 'discharge_to_grid',
                'priority': 'high',
                'reason': 'SOC max, nadwyżka PV - sprzedaj'
            }
        else:
            return {
                'mode': 'idle',
                'priority': 'low',
                'reason': 'SOC max - stop ładowania'
            }

    # ============================================
    # PRIORYTET 1: AUTOCONSUMPTION
    # ============================================

    if balance['surplus'] > 0:
        # Mamy nadwyżkę PV
        return handle_pv_surplus(data, balance)

    elif balance['deficit'] > 0:
        # Mamy deficyt
        return handle_power_deficit(data, balance)

    else:
        # Idealny balans
        return {
            'mode': 'idle',
            'priority': 'low',
            'reason': 'PV = Load, idealny balans'
        }


# ============================================
# OBSŁUGA NADWYŻKI PV
# ============================================

def handle_pv_surplus(data, balance):
    """
    Decyzja: Co zrobić z nadwyżką PV?
    - Magazynować w baterii?
    - Sprzedać do sieci?
    """

    soc = data['soc']
    rce_now = data['rce_now']
    forecast_tomorrow = data['forecast_tomorrow']
    forecast_6h = data['forecast_6h']
    hour = data['hour']

    # ============================================
    # CASE 1: RCE UJEMNE lub BARDZO NISKIE
    # ============================================

    if rce_now < 0.20:
        if soc < 95:
            return {
                'mode': 'charge_from_pv',
                'priority': 'critical',
                'reason': f'RCE bardzo niskie ({rce_now:.3f}), nie oddawaj za bezcen!'
            }

    # ============================================
    # CASE 2: JUTRO POCHMURNO
    # ============================================

    if forecast_tomorrow < 12:
        if soc < 85:
            return {
                'mode': 'charge_from_pv',
                'priority': 'very_high',
                'reason': f'Jutro pochmurno ({forecast_tomorrow:.1f} kWh), magazynuj!'
            }

    # ============================================
    # CASE 3: WKRÓTCE DROGI WIECZÓR
    # ============================================

    if hour in [13, 14, 15, 16]:
        rce_evening = data['rce_evening_avg']
        if rce_evening > 0.55 and soc < 70:
            return {
                'mode': 'charge_from_pv',
                'priority': 'high',
                'reason': f'Za chwilę drogi wieczór (RCE {rce_evening:.3f}), magazynuj!'
            }

    # ============================================
    # CASE 4: ZIMA - magazynuj każdą kWh
    # ============================================

    month = data['timestamp'].month
    if month in [11, 12, 1, 2] and soc < 80:
        return {
            'mode': 'charge_from_pv',
            'priority': 'high',
            'reason': 'Zima - każda kWh cenna!'
        }

    # ============================================
    # CASE 5: SŁABA PROGNOZA NA 6h
    # ============================================

    if forecast_6h < 5 and soc < 60:
        return {
            'mode': 'charge_from_pv',
            'priority': 'medium',
            'reason': f'Słaba prognoza 6h ({forecast_6h:.1f} kWh), magazynuj'
        }

    # ============================================
    # DEFAULT: Sprzedaj normalnie
    # ============================================

    return {
        'mode': 'discharge_to_grid',
        'priority': 'normal',
        'reason': f'Warunki OK, sprzedaj po RCE {rce_now:.3f} (× 1.23 = {rce_now * 1.23:.3f})'
    }


# ============================================
# OBSŁUGA DEFICYTU MOCY
# ============================================

def handle_power_deficit(data, balance):
    """
    Decyzja: Skąd pokryć deficyt?
    - Z baterii?
    - Z sieci?
    - Ładować z sieci?
    """

    soc = data['soc']
    tariff = data['tariff_zone']
    hour = data['hour']
    temp = data['temp_outdoor']
    heating_mode = data['heating_mode']
    forecast_tomorrow = data['forecast_tomorrow']
    target_soc = data['target_soc']

    # ============================================
    # SPRAWDŹ: Czy powinniśmy ŁADOWAĆ z sieci?
    # ============================================

    charge_decision = should_charge_from_grid(data)

    if charge_decision['should_charge']:
        return {
            'mode': 'charge_from_grid',
            'target_soc': charge_decision['target_soc'],
            'priority': charge_decision['priority'],
            'reason': charge_decision['reason']
        }

    # ============================================
    # SPRAWDŹ: Czy to SZCZYT wieczorny + ARBITRAŻ?
    # ============================================

    if hour in [19, 20, 21]:
        arbitrage = check_arbitrage_opportunity(data)

        if arbitrage['should_sell']:
            return {
                'mode': 'discharge_to_grid',
                'target_soc': arbitrage['min_soc'],
                'priority': 'high',
                'reason': arbitrage['reason']
            }

    # ============================================
    # SPRAWDŹ: Czy używać baterii do domu?
    # ============================================

    # SEZON GRZEWCZY - PC pracuje cały dzień
    if heating_mode == 'heating_season':
        # W L1 ZAWSZE używaj baterii (oszczędzaj drogą L1!)
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

        # W L2 pozwól PC brać z sieci (tanie!)
        else:  # L2
            if data['cwu_window']:
                # Okno CWU - PC może z sieci
                if soc > 70:
                    # Bateria wysoka - oszczędzaj na L1
                    return {
                        'mode': 'grid_to_home',  # PC z sieci
                        'priority': 'medium',
                        'reason': 'PC CWU w L2 (tanie), oszczędzaj baterię na L1'
                    }
                else:
                    # Bateria niska - doładuj w L2!
                    return {
                        'mode': 'charge_from_grid',
                        'target_soc': target_soc,
                        'priority': 'high',
                        'reason': 'PC w L2 + doładuj baterię na L1'
                    }

    # POZA SEZONEM - tylko dom + CWU w oknach
    else:  # no_heating
        # W L1 zawsze oszczędzaj
        if tariff == 'L1':
            if soc > 20:
                return {
                    'mode': 'discharge_to_home',
                    'priority': 'high',
                    'reason': 'Oszczędzaj L1 (bez CO)'
                }

        # W L2 podczas CWU - PC może z sieci
        elif data['cwu_window']:
            return {
                'mode': 'grid_to_home',
                'priority': 'low',
                'reason': 'CWU w L2 (tanie), oszczędzaj baterię'
            }

    # ============================================
    # DEFAULT: Bateria → Dom (jeśli SOC OK)
    # ============================================

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


# ============================================
# DECYZJA: CZY ŁADOWAĆ Z SIECI?
# ============================================

def should_charge_from_grid(data):
    """
    Sprawdza czy powinniśmy ładować baterię z sieci

    Returns:
        {
            'should_charge': bool,
            'target_soc': int,
            'priority': str,
            'reason': str
        }
    """

    soc = data['soc']
    tariff = data['tariff_zone']
    hour = data['hour']
    rce_now = data['rce_now']
    forecast_tomorrow = data['forecast_tomorrow']
    temp = data['temp_outdoor']
    heating_mode = data['heating_mode']
    target_soc = data['target_soc']

    # ============================================
    # CASE 1: RCE UJEMNE (rzadkie!)
    # ============================================

    if rce_now < 0:
        if soc < 95:
            return {
                'should_charge': True,
                'target_soc': 95,
                'priority': 'critical',
                'reason': f'RCE ujemne ({rce_now:.3f})! Płacą Ci za pobór!'
            }

    # ============================================
    # CASE 2: RCE BARDZO NISKIE w południe
    # ============================================

    if rce_now < 0.15 and hour in [11, 12, 13, 14]:
        if forecast_tomorrow < 10 and soc < 70:
            return {
                'should_charge': True,
                'target_soc': 75,
                'priority': 'high',
                'reason': f'RCE bardzo niskie ({rce_now:.3f}) + pochmurno jutro'
            }

    # ============================================
    # CASE 3: NOC L2 - GŁÓWNE ŁADOWANIE
    # ============================================

    if tariff == 'L2' and hour in [22, 23, 0, 1, 2, 3, 4, 5]:
        # Oblicz cel ładowania
        if soc < target_soc:
            # Priorytet zależy od prognozy
            if forecast_tomorrow < 15:
                priority = 'critical'
                reason = f'Noc L2 + pochmurno jutro ({forecast_tomorrow:.1f} kWh) - ładuj do {target_soc}%!'
            elif forecast_tomorrow < 25:
                priority = 'high'
                reason = f'Noc L2 + średnio jutro - ładuj do {target_soc}%'
            else:
                priority = 'medium'
                reason = f'Noc L2 + słonecznie jutro - ładuj do {target_soc}%'

            # W sezoniegrzewczym ZAWSZE priorytet wyższy!
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

    # ============================================
    # CASE 4: RANO przed końcem L2 (04:00-06:00)
    # ============================================

    if tariff == 'L2' and hour in [4, 5]:
        if forecast_tomorrow < 12 and soc < 85:
            return {
                'should_charge': True,
                'target_soc': 90,
                'priority': 'critical',
                'reason': f'Ostatnia szansa w L2! Pochmurno jutro ({forecast_tomorrow:.1f} kWh)'
            }

    # ============================================
    # CASE 5: SOC KRYTYCZNIE NISKI (bezpieczeństwo)
    # ============================================

    if soc < 15:
        return {
            'should_charge': True,
            'target_soc': 30,
            'priority': 'critical',
            'reason': 'SOC krytyczne - bezpieczeństwo'
        }

    # ============================================
    # DEFAULT: Nie ładuj z sieci
    # ============================================

    return {
        'should_charge': False,
        'target_soc': None,
        'priority': None,
        'reason': 'Brak warunków do ładowania z sieci'
    }


# ============================================
# DECYZJA: CZY SPRZEDAWAĆ DO SIECI (ARBITRAŻ)?
# ============================================

def check_arbitrage_opportunity(data):
    """
    Sprawdza czy opłaca się sprzedawać energię z baterii do sieci
    (tylko wieczór 19-22h, gdy RCE wysokie)

    Returns:
        {
            'should_sell': bool,
            'min_soc': int,      # Do jakiego poziomu sprzedawać
            'reason': str
        }
    """

    soc = data['soc']
    rce_now = data['rce_now']
    forecast_tomorrow = data['forecast_tomorrow']
    temp = data['temp_outdoor']
    heating_mode = data['heating_mode']
    hour = data['hour']
    month = data['timestamp'].month

    # Tylko wieczór!
    if hour not in [19, 20, 21]:
        return {'should_sell': False, 'min_soc': None, 'reason': 'Nie wieczór'}

    # ============================================
    # WARUNEK 1: RCE musi być wysokie
    # ============================================

    if rce_now < 0.50:
        return {
            'should_sell': False,
            'min_soc': None,
            'reason': f'RCE za niskie ({rce_now:.3f}) do arbitrażu'
        }

    # ============================================
    # WARUNEK 2: SOC musi być odpowiednie
    # ============================================

    # W sezonie grzewczym - ostrożniej!
    if heating_mode == 'heating_season':
        # Potrzeba rezerwowa na PC do rana
        if temp < -5:
            min_soc_required = 50  # Mróz - duża rezerwa
        elif temp < 5:
            min_soc_required = 45  # Zima
        else:
            min_soc_required = 40  # Umiarkowanie

        if soc < min_soc_required + 20:
            return {
                'should_sell': False,
                'min_soc': None,
                'reason': f'SOC {soc}% za niskie (min {min_soc_required + 20}%) - PC potrzebuje!'
            }

    # Poza sezonem - można więcej sprzedać
    else:
        min_soc_required = 30

        if soc < 55:
            return {
                'should_sell': False,
                'min_soc': None,
                'reason': f'SOC {soc}% za niskie do arbitrażu'
            }

    # ============================================
    # WARUNEK 3: Jutro musi być prognoza OK
    # ============================================

    # W sezonie grzewczym
    if heating_mode == 'heating_season':
        forecast_threshold = 25  # Potrzeba więcej PV

        if forecast_tomorrow < forecast_threshold:
            return {
                'should_sell': False,
                'min_soc': None,
                'reason': f'Jutro pochmurno ({forecast_tomorrow:.1f} kWh) + PC - nie sprzedawaj!'
            }

        # Sprawdź czy RCE na tyle wysokie że warto
        if rce_now < 0.65:
            return {
                'should_sell': False,
                'min_soc': None,
                'reason': f'RCE {rce_now:.3f} za niskie przy PC (min 0.65)'
            }

    # Poza sezonem
    else:
        forecast_threshold = 20

        if forecast_tomorrow < forecast_threshold:
            return {
                'should_sell': False,
                'min_soc': None,
                'reason': f'Jutro pochmurno ({forecast_tomorrow:.1f} kWh) - nie sprzedawaj'
            }

        # Niższy próg RCE wystarczy
        if rce_now < 0.55:
            return {
                'should_sell': False,
                'min_soc': None,
                'reason': f'RCE {rce_now:.3f} za niskie (min 0.55)'
            }

    # ============================================
    # WSZYSTKO OK - SPRZEDAWAJ!
    # ============================================

    # Oblicz ile można sprzedać
    if heating_mode == 'heating_season':
        # Zostaw więcej na PC
        if month in [5, 6, 7, 8]:  # Lato z CO (rzadko)
            min_soc = 40
        elif month in [3, 4, 9, 10]:  # Przejściówka
            min_soc = 45
        else:  # Zima
            min_soc = min_soc_required
    else:
        # Bez CO można więcej
        if month in [5, 6, 7, 8]:  # Lato
            min_soc = 30
        else:  # Przejściówka
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
# OBLICZANIE CELU ŁADOWANIA
# ============================================

def calculate_daily_strategy():
    """
    Oblicza strategię na dzień - wywoływana o 04:00
    Ustawia cel ładowania na noc
    """

    data = collect_input_data()

    forecast_tomorrow = data['forecast_tomorrow']
    temp = data['temp_outdoor']
    heating_mode = data['heating_mode']
    month = data['timestamp'].month

    # ============================================
    # SEZON GRZEWCZY
    # ============================================

    if heating_mode == 'heating_season':
        # Bazowe zużycie CO w L1 (zależy od temperatury)
        if temp < -10:
            co_l1_base = 60  # kWh - Mróz
        elif temp < 0:
            co_l1_base = 50  # kWh - Zima
        elif temp < 5:
            co_l1_base = 40  # kWh - Chłodno
        else:  # 5-12°C
            co_l1_base = 30  # kWh - Umiarkowanie

        dom_l1 = 26  # kWh - reszta domu
        suma_l1 = co_l1_base + dom_l1

        # Ile PV pokryje?
        pokrycie_pv = min(forecast_tomorrow * 0.7, suma_l1 * 0.3)

        # Ile potrzeba z baterii?
        z_baterii = min(suma_l1 - pokrycie_pv, 15)

        target_soc = int((z_baterii / 15) * 100)
        target_soc = max(60, min(90, target_soc))

        # W mrozy ZAWSZE więcej
        if temp < -5:
            target_soc = max(target_soc, 85)

        reason = f'Sezon grzewczy: temp {temp:.1f}°C, CO+dom={suma_l1:.0f}kWh, ' \
                 f'PV={pokrycie_pv:.0f}kWh, bateria={z_baterii:.0f}kWh'

    # ============================================
    # POZA SEZONEM
    # ============================================

    else:
        dom_l1 = 28  # kWh - tylko dom

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

        reason = f'Bez CO: dom={dom_l1:.0f}kWh, PV={pokrycie_pv:.0f}kWh, ' \
                 f'bateria={z_baterii:.0f}kWh'

    # Zapisz obliczony cel
    set_target_soc(target_soc, reason)

    return {
        'target_soc': target_soc,
        'reason': reason,
        'forecast': forecast_tomorrow,
        'temp': temp,
        'heating_mode': heating_mode
    }


# ============================================
# MONITOROWANIE STANÓW KRYTYCZNYCH
# ============================================

def monitor_critical_states():
    """
    Uruchamiana co 1 minutę
    Monitoruje stany krytyczne i reaguje natychmiast
    """

    data = collect_input_data()
    soc = data['soc']
    battery_temp = data['battery_temp']

    # SOC krytycznie niskie
    if soc <= 10:
        log_alert('CRITICAL', f'SOC={soc}% - krytyczne!')
        force_charge_from_grid(target_soc=20, reason='SOC krytyczne')
        send_notification('🚨 Bateria krytycznie niska!', f'SOC: {soc}%')

    # SOC bardzo niskie + L1
    elif soc <= 20 and data['tariff_zone'] == 'L1':
        log_alert('WARNING', f'SOC={soc}% w L1 - za nisko!')
        send_notification('⚠️ Bateria niska w L1', f'SOC: {soc}%')

    # SOC za wysokie
    elif soc >= 95:
        log_info('INFO', f'SOC={soc}% - max osiągnięty')
        stop_charging(reason='SOC max')

    # Temperatura baterii
    if battery_temp > 45:
        log_alert('WARNING', f'Temp baterii: {battery_temp}°C - wysoka!')
        reduce_charge_power(reason='Temperatura wysoka')

    # Brak danych RCE
    rce_age = get_rce_data_age_hours()
    if rce_age > 24:
        log_alert('WARNING', f'Brak świeżych cen RCE ({rce_age:.1f}h)')
        send_notification('⚠️ Brak cen RCE', 'Sprawdź połączenie z API')


# ============================================
# APLIKACJA TRYBU BATERII
# ============================================

def apply_battery_mode(strategy):
    """
    Aplikuje wybraną strategię do baterii Huawei

    Args:
        strategy: dict ze strategią z decide_strategy()
    """

    mode = strategy['mode']

    if mode == 'charge_from_pv':
        # Ładowanie tylko z PV
        set_huawei_mode(
            working_mode='Maximise Self Consumption',
            charge_from_grid=False
        )

    elif mode == 'charge_from_grid':
        # Ładowanie z sieci
        target_soc = strategy.get('target_soc', 80)
        set_huawei_mode(
            working_mode='Time Of Use',
            charge_from_grid=True,
            charge_soc_limit=target_soc
        )

    elif mode == 'discharge_to_home':
        # Rozładowanie do domu
        set_huawei_mode(
            working_mode='Maximise Self Consumption',
            charge_from_grid=False
        )

    elif mode == 'discharge_to_grid':
        # Rozładowanie do sieci (arbitraż)
        min_soc = strategy.get('target_soc', 30)
        set_huawei_mode(
            working_mode='Fully Fed To Grid',
            discharge_soc_limit=min_soc
        )

    elif mode == 'grid_to_home':
        # PC/Dom bezpośrednio z sieci (nie używaj baterii)
        set_huawei_mode(
            working_mode='Maximise Self Consumption',
            charge_from_grid=False
        )

    elif mode == 'idle':
        # Idle - nie rób nic
        set_huawei_mode(
            working_mode='Maximise Self Consumption',
            charge_from_grid=False
        )

    log_info('STRATEGY_APPLIED', f'{mode}: {strategy["reason"]}')

    return True


# ============================================
# POBIERANIE DANYCH Z API
# ============================================

def fetch_rce_prices():
    """
    Pobiera ceny RCE z API PSE
    Uruchamiana: 18:00 (+ retry 19, 20, 21, 22)
    """

    # Randomizacja 0-15 min
    random_delay = random.randint(0, 900)  # sekundy
    sleep(random_delay)

    try:
        url = 'https://api.raporty.pse.pl/api/rce-pln'
        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            data = response.json()
            prices = parse_rce_data(data)
            save_rce_prices(prices)

            log_info('RCE_FETCH', f'Pobrano ceny RCE: {len(prices)} godzin')
            return True
        else:
            log_error('RCE_FETCH', f'HTTP {response.status_code}')
            return False

    except Exception as e:
        log_error('RCE_FETCH', f'Błąd: {str(e)}')
        return False


def fetch_forecast_pv():
    """
    Pobiera prognozę PV z Forecast.Solar
    Uruchamiana: 04:00, 12:00, 20:00
    """

    # Randomizacja 0-10 min
    random_delay = random.randint(0, 600)
    sleep(random_delay)

    try:
        # API Forecast.Solar
        # (lub użyj integracji HA)
        forecast_today = get_forecast_solar_today()
        forecast_tomorrow = get_forecast_solar_tomorrow()

        log_info('FORECAST_PV',
                 f'Dziś: {forecast_today:.1f} kWh, Jutro: {forecast_tomorrow:.1f} kWh')

        return True

    except Exception as e:
        log_error('FORECAST_PV', f'Błąd: {str(e)}')
        return False


# ============================================
# FUNKCJE POMOCNICZE
# ============================================

def get_fallback_strategy(data):
    """
    Strategia awaryjnakomunikować gdy brak danych
    """

    soc = data.get('soc', 50)

    # Bardzo konserwatywna strategia
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
    Loguje podjętą decyzję do bazy/pliku
    """

    log_entry = {
        'timestamp': data['timestamp'],
        'hour': data['hour'],
        'tariff': data['tariff_zone'],
        'soc': data['soc'],
        'rce': data['rce_now'],
        'pv': balance['pv'],
        'load': balance['load'],
        'mode': strategy['mode'],
        'reason': strategy['reason'],
        'priority': strategy['priority'],
        'result': result
    }

    # Zapisz do bazy lub loga
    save_log(log_entry)


# ============================================
# PRZYKŁAD URUCHOMIENIA
# ============================================

if __name__ == '__main__':
    """
    Główna pętla - uruchamiana co godzinę przez scheduler
    """

    # Wykonaj strategię
    execute_strategy()
```

-----

## 🔑 KLUCZOWE PARAMETRY (do konfiguracji)

```python
# Progi cenowe RCE
RCE_NEGATIVE = 0.00
RCE_VERY_LOW = 0.20
RCE_LOW = 0.35
RCE_MEDIUM = 0.45
RCE_HIGH = 0.55
RCE_VERY_HIGH = 0.65
RCE_EXTREME = 0.75

# Progi prognozy PV
FORECAST_EXCELLENT = 30  # kWh
FORECAST_VERY_GOOD = 25
FORECAST_GOOD = 20
FORECAST_MEDIUM = 15
FORECAST_POOR = 12
FORECAST_BAD = 8
FORECAST_VERY_BAD = 5

# Progi baterii
BATTERY_CRITICAL = 10  # %
BATTERY_LOW = 20
BATTERY_RESERVE_SUMMER = 30
BATTERY_RESERVE_WINTER = 45
BATTERY_GOOD = 70
BATTERY_HIGH = 85
BATTERY_MAX = 95

# Temperatura i PC
TEMP_HEATING_THRESHOLD = 12  # °C - poniżej włącza się CO
TEMP_FROST = -10
TEMP_WINTER = 0
TEMP_COLD = 5

# Taryfa G12w
L2_NIGHT_START = 22  # Godzina
L2_NIGHT_END = 6
L2_AFTERNOON_START = 13
L2_AFTERNOON_END = 15

# Okna CWU
CWU_MORNING_START = 4.5  # 04:30
CWU_MORNING_END = 6
CWU_AFTERNOON_START = 13
CWU_AFTERNOON_END = 15
```

-----

## 📊 STRUKTURA DANYCH

### Input Data

```python
{
    'timestamp': datetime,
    'hour': int (0-23),
    'weekday': int (0-6),
    'is_holiday': bool,
    'tariff_zone': str ('L1' | 'L2'),
    'rce_now': float,  # zł/kWh
    'rce_evening_avg': float,
    'soc': int (0-100),  # %
    'battery_power': float,  # kW
    'pv_power': float,  # kW
    'home_load': float,  # kW
    'forecast_today': float,  # kWh
    'forecast_tomorrow': float,  # kWh
    'temp_outdoor': float,  # °C
    'heating_mode': str ('heating_season' | 'no_heating'),
    'pc_co_active': bool,
    'cwu_window': bool,
    'target_soc': int  # %
}
```

### Strategy Output

```python
{
    'mode': str,  # 'charge_from_pv' | 'charge_from_grid' |
                  # 'discharge_to_home' | 'discharge_to_grid' | 'idle'
    'target_soc': int | None,  # % (dla ładowania)
    'target_power': float | None,  # kW (opcjonalnie)
    'priority': str,  # 'critical' | 'high' | 'medium' | 'low'
    'reason': str  # Uzasadnienie decyzji
}
```

-----

## ⚙️ TRYBY HUAWEI

```python
# Dostępne tryby pracy baterii Huawei:

HUAWEI_MODES = {
    'Maximise Self Consumption': {
        'description': 'PV → Dom → Bateria → Sieć',
        'use': 'Standardowy tryb, autoconsumption'
    },

    'Time Of Use': {
        'description': 'Ładowanie w określonych godzinach z sieci',
        'use': 'Ładowanie w L2',
        'params': ['charge_from_grid', 'charge_soc_limit']
    },

    'Fully Fed To Grid': {
        'description': 'PV + Bateria → Sieć',
        'use': 'Arbitraż wieczorny',
        'params': ['discharge_soc_limit']
    },

    'Idle': {
        'description': 'Bateria nieaktywna',
        'use': 'Awaryjnie'
    }
}
```

-----

## 🎯 PRZYKŁADOWE SCENARIUSZE

### Scenariusz 1: Zimowy dzień (mróz -10°C, pochmurno)

```
04:00 → calculate_daily_strategy()
  Prognoza: 5 kWh
  Temp: -10°C (CO aktywne)
  TARGET_SOC = 85% (PC będzie ciężko pracować!)

04:30 → execute_strategy()
  PC CWU w L2, SOC 42% < 85%
  DECYZJA: Ładuj z sieci L2 + PC CWU może brać

06:00 → execute_strategy()
  Zmiana L2→L1, PC CO pracuje 6 kW!
  SOC 85%, deficyt
  DECYZJA: BATERIA→DOM (oszczędzaj L1!)

19:00 → execute_strategy()
  L1, PC 5 kW, SOC 35%
  RCE = 0.72 (wysokie!)
  Ale: mróz + pochmurno jutro
  DECYZJA: BATERIA→DOM (nie sprzedawaj, PC potrzebuje!)

22:00 → execute_strategy()
  Zmiana L1→L2, SOC 28%
  DECYZJA: Ładuj do 85% (jutro będzie ciężko)
```

### Scenariusz 2: Letni dzień (20°C, słonecznie)

```
04:00 → calculate_daily_strategy()
  Prognoza: 35 kWh
  Temp: 20°C (CO wyłączone!)
  TARGET_SOC = 30% (PV wystarczy)

13:00 → execute_strategy()
  L2, PC CWU 3 kW, PV 8 kW
  Nadwyżka 5 kW, SOC 45%
  DECYZJA: PV→BATERIA (magazynuj na wieczór L1!)

19:00 → execute_strategy()
  L1, SOC 75%, RCE = 0.68
  Prognoza jutro: 38 kWh ✅
  Brak CO = więcej miejsca!
  DECYZJA: BATERIA→SIEĆ (sprzedaj do 30%!)
  Zysk: 6.75 kWh × 0.836 zł = ~5.64 zł
```

-----

## 📈 METRYKI SUKCESU

```python
def calculate_daily_metrics():
    """
    Oblicza metryki sukcesu strategii
    """

    return {
        # Oszczędności
        'l1_avoided_kwh': float,  # Ile kWh L1 uniknięto
        'l1_avoided_cost': float,  # Ile zł zaoszczędzono

        # Arbitraż
        'sold_to_grid_kwh': float,
        'arbitrage_revenue': float,  # Przychód ze sprzedaży

        # Bateria
        'battery_cycles': float,  # Liczba cykli
        'battery_efficiency': float,  # %

        # Autoconsumption
        'pv_to_home_direct': float,  # kWh
        'pv_to_battery': float,
        'pv_to_grid': float,
        'autoconsumption_rate': float,  # %

        # Całkowite
        'total_savings': float,  # Oszczędności + arbitraż
        'daily_cost': float  # Ile zapłacono za energię
    }
```

-----

## 🚀 NASTĘPNE KROKI

1. **Implementacja w Python** (Claude Code)
1. **Integracja z Huawei Solar API**
1. **Testy jednostkowe** dla logiki decyzyjnej
1. **Dashboard** (Grafana/HA)
1. **Monitoring** i alerty
1. **Optymalizacja** parametrów na podstawie danych

-----

Ten algorytm jest gotowy do implementacji! 💪
