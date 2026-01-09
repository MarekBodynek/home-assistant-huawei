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
BATTERY_CRITICAL = 5   # SOC krytyczne - natychmiastowe ładowanie 24/7
BATTERY_LOW = 20       # SOC niskie - pilne ładowanie w L2
BATTERY_RESERVE = 30   # Rezerwa weekendowa (stała, niezależna od sezonu)
BATTERY_GOOD = 65      # SOC dobre
BATTERY_HIGH = 70      # SOC wysokie
BATTERY_MAX = 80       # Limit Huawei: 80%

# Temperatura i PC
TEMP_HEATING_THRESHOLD = 12  # °C
TEMP_FROST = -10
TEMP_WINTER = 0
TEMP_COLD = 5


# ============================================
# TARYFA G12w - OBLICZANIE Z GODZINY
# ============================================

def get_tariff_zone(hour):
    """
    Oblicz taryfę G12w bezpośrednio z godziny i dnia roboczego.
    Eliminuje race condition - nie czeka na aktualizację sensora.

    Logika G12w:
    - Weekend/święto: L2 cały dzień
    - Dzień roboczy:
      - L2: 22:00-05:59 (noc), 13:00-14:59 (południe)
      - L1: 06:00-12:59, 15:00-21:59
    """
    workday_state = hass.states.get('binary_sensor.dzien_roboczy')
    is_workday = workday_state and workday_state.state == 'on'

    if not is_workday:
        return 'L2'  # Weekend/święto = cały dzień L2
    elif hour >= 22 or hour < 6:
        return 'L2'  # Noc
    elif 13 <= hour < 15:
        return 'L2'  # Południe
    else:
        return 'L1'  # Dzień roboczy, godziny szczytu


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
    # ALE kontynuuj do decide_strategy() żeby obsłużyć L1/L2/weekend!
    soc = data['soc']
    target_soc = data['target_soc']

    if soc >= target_soc:
        # Bateria naładowana do Target SOC - zatrzymaj ładowanie (jeśli włączone)
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
            # NIE ROBIMY RETURN! Kontynuujemy do decide_strategy()
            # żeby obsłużyć rozładowywanie w L1, weekend, itp.
        else:
            # Jeśli ładowanie już wyłączone - przywróć moc ładowania na normalną (5000W)
            # Bo mogła być ustawiona na 0W w poprzednim cyklu
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

    # Event Log - logowanie decyzji
    try:
        log_decision(data, balance, strategy, result)
    except Exception as e:
        # Loguj błąd do input_text żeby zobaczyć co jest nie tak
        hass.services.call('input_text', 'set_value', {
            'entity_id': 'input_text.event_log_1',
            'value': '{"ts":"","lvl":"ERROR","cat":"DEBUG","msg":"log_decision error: ' + str(e)[:100].replace('"', "'") + '"}'
        })
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

            # Taryfa - obliczana z godziny (eliminuje race condition)
            'tariff_zone': get_tariff_zone(hour),

            # Ceny RCE
            'rce_now': float(get_state('sensor.rce_pse_cena_za_kwh') or 0.45),
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
            'target_soc': data['target_soc'],  # Użyj Target SOC z danych
            'priority': 'high',  # Było 'critical' - to pilne ale nie błąd
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
                'priority': 'normal',  # Normalna operacja przy pełnej baterii
                'reason': 'SOC 80%, nadwyżka PV - sprzedaj'
            }
        else:
            return {
                'mode': 'discharge_to_home',
                'priority': 'normal',
                'reason': 'SOC 80% w L1 - rozładowuj do domu (oszczędzaj drogi L1)'
            }

    # W L2 (tania taryfa weekend/święta) - oszczędzaj baterię
    # O północy dzień zmieni się na roboczy i algorytm automatycznie zacznie ładować
    tariff = data['tariff_zone']
    hour = data['hour']
    target_soc = data['target_soc']

    # Sprawdź czy dziś jest dzień roboczy
    workday_state = hass.states.get('binary_sensor.dzien_roboczy')
    is_workday = workday_state and workday_state.state == 'on'

    # Weekend energetyczny: piątek 22:00 → niedziela 22:00
    # W tym czasie: NIE ładuj z sieci, czekaj na PV, oszczędzaj baterię
    # Oblicz dzień tygodnia bez importu datetime (algorytm Tomohiko Sakamoto)
    date_sensor = hass.states.get('sensor.date')
    today_str = date_sensor.state if date_sensor else ''
    if today_str and len(today_str) >= 10:
        y = int(today_str[0:4])
        m = int(today_str[5:7])
        d = int(today_str[8:10])
        # Algorytm: zwraca 0=niedziela, 1=pon, ... 5=pt, 6=sob
        t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4]
        if m < 3:
            y = y - 1
        dow = (y + y//4 - y//100 + y//400 + t[m-1] + d) % 7
        # Konwersja na format Python: 0=pon, 4=pt, 5=sob, 6=ndz
        weekday = (dow + 6) % 7
    else:
        weekday = 0  # Fallback na poniedziałek
    is_friday_evening = (weekday == 4 and hour >= 22)   # Piątek 22:00+ = START weekendu
    is_sunday_evening = (weekday == 6 and hour >= 22)   # Niedziela 22:00+ = KONIEC weekendu

    # Weekend energetyczny = (weekend/święto LUB piątek wieczór) ALE NIE niedziela wieczór
    is_energy_weekend = (not is_workday or is_friday_evening) and not is_sunday_evening

    # WEEKEND ENERGETYCZNY (piątek 22:00 - niedziela 21:59)
    # ZAWSZE self consumption - NIE ładuj z sieci, nawet gdy SOC spadnie
    # Wyjątek: SOC < 5% (obsłużone wyżej jako ładowanie krytyczne 24/7)
    # Ładowanie do Target SOC dopiero w niedzielę 22:00+
    if is_energy_weekend:
        return {
            'mode': 'discharge_to_home',
            'priority': 'normal',
            'reason': 'Weekend - tylko self consumption, bez ładowania z sieci'
        }

    # ŁADOWANIE W L2 - INTELIGENTNE ZARZĄDZANIE PV vs SIEĆ
    # PRIORYTET: PV (darmowe) > Sieć L2 (tanie 0.72 zł) > Sieć L1 (drogie 1.11 zł)
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
                'priority': 'normal',  # Normalna operacja w L1
                'reason': f'L1 droga taryfa (1.11 zł) - rozładowuj baterię (SOC {soc:.0f}%)'
            }

    # L2 NOC (22-06h) - inteligentne ładowanie z uwzględnieniem prognozy PV
    # O północy forecast_today = prognoza na NOWY dzień (np. poniedziałek)
    heating_mode = data['heating_mode']

    if tariff == 'L2' and hour in [22, 23, 0, 1, 2, 3, 4, 5]:
        # Określ prognozę na nadchodzący dzień
        # Przed północą (22-23h): patrzymy na jutro
        # Po północy (0-5h): patrzymy na dzisiaj (bo już jest nowy dzień)
        if hour >= 22:
            pv_forecast = forecast_tomorrow
            forecast_label = "jutro"
        else:
            pv_forecast = forecast_today
            forecast_label = "dziś"

        # === SEZON GRZEWCZY: ZAWSZE ŁADUJ ===
        # PC CO potrzebuje energii rano, a zimowe PV jest słabe
        if heating_mode == 'heating_season' and soc < target_soc:
            if pv_forecast < 15:
                priority = 'normal'  # Normalne ładowanie w sezonie grzewczym
                reason = f'Noc L2 + sezon grzewczy + pochmurno {forecast_label} ({pv_forecast:.1f} kWh) - ładuj do {target_soc}%!'
            else:
                priority = 'normal'  # Normalna decyzja
                reason = f'Noc L2 + sezon grzewczy - ładuj do {target_soc}% (PC potrzebuje energii rano)'
            return {
                'mode': 'charge_from_grid',
                'target_soc': target_soc,
                'priority': priority,
                'reason': reason
            }

        # === POZA SEZONEM GRZEWCZYM: INTELIGENTNE ŁADOWANIE ===
        # Jeśli prognoza PV dobra - pozwól słońcu naładować baterię za darmo!
        # UWAGA: Próg krytyczny SOC < 20% obsługiwany wcześniej (linie 266-272)

        # Doskonała prognoza (>25 kWh) → NIE ŁADUJ - słońce naładuje za darmo
        if pv_forecast >= 25:
            return {
                'mode': 'grid_to_home',
                'priority': 'low',
                'reason': f'Noc L2 + słonecznie {forecast_label} ({pv_forecast:.1f} kWh) - PV naładuje baterię za darmo! (SOC {soc:.0f}%)'
            }

        # Bardzo dobra prognoza (>20 kWh) → NIE ŁADUJ
        if pv_forecast >= 20:
            return {
                'mode': 'grid_to_home',
                'priority': 'low',
                'reason': f'Noc L2 + dobra prognoza {forecast_label} ({pv_forecast:.1f} kWh) - PV wystarczy! (SOC {soc:.0f}%)'
            }

        # Dobra prognoza (>15 kWh) → NIE ŁADUJ
        if pv_forecast >= 15:
            return {
                'mode': 'grid_to_home',
                'priority': 'low',
                'reason': f'Noc L2 + prognoza {forecast_label} {pv_forecast:.1f} kWh - PV powinno wystarczyć (SOC {soc:.0f}%)'
            }

        # Słaba prognoza (<15 kWh) → ŁADUJ
        if soc < target_soc:
            if pv_forecast < 10:
                priority = 'normal'  # Było 'critical' - normalne ładowanie
                reason = f'Noc L2 + bardzo pochmurno {forecast_label} ({pv_forecast:.1f} kWh) - ładuj do {target_soc}%!'
            elif pv_forecast < 15:
                priority = 'normal'  # Było 'high' - normalne ładowanie
                reason = f'Noc L2 + pochmurno {forecast_label} ({pv_forecast:.1f} kWh) - ładuj do {target_soc}%'
            else:
                priority = 'normal'  # Było 'medium'
                reason = f'Noc L2 + SOC {soc:.0f}% < próg - ładuj do {target_soc}%'
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
                    'priority': 'normal',  # Normalne ładowanie w L2
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
        # UWAGA: sun.sun zwraca czasy UTC! W Polsce (CET/CEST) trzeba dodać 1-2h
        # Dla uproszczenia używamy stałych sezonowych dla Polski:
        # - Listopad-Luty: wschód ~7:00, zachód ~15:30-16:30
        # - Marzec-Kwiecień: wschód ~6:00, zachód ~18:00-19:00
        # - Maj-Sierpień: wschód ~5:00, zachód ~20:00-21:00
        # - Wrzesień-Październik: wschód ~6:30, zachód ~17:00-18:00
        month = data.get('month', 11)

        if month in [11, 12, 1, 2]:  # Zima
            sunrise_hour = 7
            sunset_hour = 16  # bezpieczny margines (faktycznie 15:30-16:30)
        elif month in [3, 4]:  # Wiosna
            sunrise_hour = 6
            sunset_hour = 18
        elif month in [5, 6, 7, 8]:  # Lato
            sunrise_hour = 5
            sunset_hour = 20
        else:  # month in [9, 10] - Jesień
            sunrise_hour = 6
            sunset_hour = 17

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

        # 4. Określ czy pokazujemy dziś czy jutro (po zachodzie słońca → jutro)
        date_state = hass.states.get('sensor.date')
        today_str = date_state.state if date_state else "2025-01-07"

        # Oblicz jutrzejszą datę
        year = int(today_str[0:4])
        month_num = int(today_str[5:7])
        day_num = int(today_str[8:10])
        days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            days_in_month[2] = 29
        day_num += 1
        if day_num > days_in_month[month_num]:
            day_num = 1
            month_num += 1
            if month_num > 12:
                month_num = 1
                year += 1
        tomorrow_str = f"{year:04d}-{month_num:02d}-{day_num:02d}"

        # Po zachodzie słońca → używaj danych na jutro
        if hour >= sunset_hour:
            target_date = tomorrow_str
            day_label = "Jutro"
            rce_sensor_name = 'sensor.rce_pse_cena_jutro'
        else:
            target_date = today_str
            day_label = "Dziś"
            rce_sensor_name = 'sensor.rce_pse_cena'

        # Pobierz ceny godzinowe z odpowiedniego sensora RCE PSE
        rce_sensor = hass.states.get(rce_sensor_name)
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

        # POPRAWKA: RCE PSE zwraca dane co 15 min, więc dla każdej godziny są 4 wpisy
        # Zbieramy wszystkie ceny per godzina, potem liczymy średnią
        hourly_prices_sum = {}  # {hour: suma_cen}
        hourly_prices_count = {}  # {hour: liczba_wpisów}

        for price_entry in all_prices:
            try:
                # RCE PSE format: dtime="2025-11-29 01:00:00", period="00:45 - 01:00", rce_pln=452.86
                # UWAGA: dtime to KONIEC okresu! Parsujemy START z pola "period"
                price_val = price_entry.get('rce_pln') or price_entry.get('price') or price_entry.get('value')
                if price_val is None:
                    continue

                # Pobierz datę z dtime (format: "2025-11-29 00:15:00")
                dtime_str = price_entry.get('dtime', '')
                if ' ' in dtime_str:
                    date_part = dtime_str.split(' ')[0]
                elif 'T' in dtime_str:
                    date_part = dtime_str.split('T')[0]
                else:
                    continue

                # Pobierz godzinę z dtime (KONIEC okresu) - spójne z template_sensors.yaml
                # Format dtime: "2025-12-09 09:00:00" → godzina 9
                # Dla okresu 08:45-09:00, dtime=09:00, przypisujemy do h09 (jak w dashboard)
                if ' ' in dtime_str:
                    time_part = dtime_str.split(' ')[1].split(':')[0]
                    price_hour = int(time_part)
                elif 'T' in dtime_str:
                    time_part = dtime_str.split('T')[1].split(':')[0]
                    price_hour = int(time_part)
                else:
                    continue

                # RCE PSE zwraca ceny w PLN/MWh - przelicz na PLN/kWh
                price_float = float(price_val)
                if price_float > 10:  # Powyżej 10 = PLN/MWh
                    price_float = price_float / 1000  # Przelicz na PLN/kWh

                # Tylko target_date (dziś lub jutro) + godziny słoneczne (sunrise <= hour < sunset)
                if date_part == target_date and sunrise_hour <= price_hour < sunset_hour:
                    # Agreguj ceny per godzina
                    # UWAGA: RestrictedPython nie pozwala na += dla dict items!
                    if price_hour not in hourly_prices_sum:
                        hourly_prices_sum[price_hour] = 0
                        hourly_prices_count[price_hour] = 0
                    hourly_prices_sum[price_hour] = hourly_prices_sum[price_hour] + price_float
                    hourly_prices_count[price_hour] = hourly_prices_count[price_hour] + 1
            except Exception as e:
                # Błąd parsowania ceny
                continue

        # Oblicz średnią cenę dla każdej godziny
        sun_prices = []
        for h in hourly_prices_sum:
            avg_price = hourly_prices_sum[h] / hourly_prices_count[h]
            sun_prices.append({
                'hour': h,
                'price': avg_price
            })

        if not sun_prices:
            # Brak danych - zaktualizuj kafelki z informacją
            no_data_msg = f"Brak cen RCE na {day_label.lower()}"
            hass.services.call('input_text', 'set_value', {
                'entity_id': 'input_text.battery_storage_status',
                'value': f"{no_data_msg} | Teraz: {hour}h"
            })
            hass.services.call('input_text', 'set_value', {
                'entity_id': 'input_text.battery_cheapest_hours',
                'value': f"[{day_label}] Brak danych"
            })
            return None, no_data_msg, []

        # 5. Sortuj godziny po średniej cenie (rosnąco - najtańsze pierwsze)
        sun_prices_sorted = sorted(sun_prices, key=lambda x: x['price'])

        # 6. Wybierz N najtańszych UNIKALNYCH godzin
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
        # Sortuj cheapest_hours chronologicznie (nie po cenie!)
        cheapest_hours_sorted = sorted(cheapest_hours)
        if battery_already_charged:
            # Bateria naładowana - pokaż informację + najtańsze godziny
            status_msg = f"Bateria OK ({int(soc)}%) | {day_label}: {cheapest_hours_sorted} | Teraz: {hour}h"
        else:
            # Normalny tryb - pokazuj potrzebę magazynowania
            status_msg = f"Potrzeba: {hours_needed}h | {day_label}: {cheapest_hours_sorted} | Teraz: {hour}h"

        hass.services.call('input_text', 'set_value', {
            'entity_id': 'input_text.battery_storage_status',
            'value': status_msg[:255]
        })

        # Formatuj wszystkie godziny słoneczne z kolorowymi kropkami
        # Używaj percentyli z odpowiedniego sensora (dziś lub jutro)
        # Pobierz progi z sensora (te same co na dashboard)
        try:
            if day_label == "Jutro":
                progi_state = hass.states.get('sensor.rce_progi_cenowe_jutro')
            else:
                progi_state = hass.states.get('sensor.rce_progi_cenowe')
            if progi_state and progi_state.attributes:
                p33 = float(progi_state.attributes.get('p33', 0.5))
                p66 = float(progi_state.attributes.get('p66', 0.7))
            else:
                p33 = 0.5
                p66 = 0.7
        except:
            p33 = 0.5
            p66 = 0.7

        hours_display_parts = []
        for p in sorted(sun_prices, key=lambda x: x['hour']):
            h = p['hour']
            # WAŻNE: Zaokrąglij cenę do 2 miejsc, żeby być spójnym z wyświetlaną wartością w tabeli
            price = round(p['price'], 2)
            # Progi: 💚 < 0.20 | 🟢 < p33 | 🟡 < p66 | 🔴 >= p66
            if price < 0.20:
                dot = '💚'
            elif price < p33:
                dot = '🟢'
            elif price < p66:
                dot = '🟡'
            else:
                dot = '🔴'
            hours_display_parts.append(str(h) + dot)
        hours_display = ' '.join(hours_display_parts)

        # Zawsze dodaj prefix z dniem (Dziś/Jutro)
        hours_display = f"[{day_label}] {hours_display}"

        hass.services.call('input_text', 'set_value', {
            'entity_id': 'input_text.battery_cheapest_hours',
            'value': hours_display[:100]
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
            'priority': 'normal',  # Okazja cenowa, nie ostrzeżenie
            'reason': f'RCE ultra niskie ({rce_now:.3f} zł) - nie oddawaj za bezcen! MAGAZYNUJ'
        }

    # 2. Jutro pochmurno → MAGAZYNUJ
    if forecast_tomorrow < FORECAST_POOR and soc < BATTERY_HIGH:
        return {
            'mode': 'charge_from_pv',
            'priority': 'normal',  # Normalna decyzja oparta na prognozie
            'reason': f'Jutro pochmurno ({forecast_tomorrow:.1f} kWh) - MAGAZYNUJ'
        }

    # 3. Zima → MAGAZYNUJ
    if month in [11, 12, 1, 2] and soc < BATTERY_HIGH:
        return {
            'mode': 'charge_from_pv',
            'priority': 'normal',  # Normalna sezonowa strategia
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
            'priority': 'normal',  # Normalna decyzja magazynowania
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
                'priority': 'normal',  # Normalna decyzja arbitrażowa
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
                    'priority': 'normal',  # Normalna operacja PC w L1
                    'reason': f'PC w L1 (temp {temp:.1f}°C) - rozładowuj baterię, oszczędzaj drogą L1!'
                }
            else:
                # SOC ≤ 20%: NIE ŁADUJ w drogiej L1!
                # Czekaj na L2 22:00 (tanie 0.72 zł vs 1.11 zł - oszczędność 54%!)
                # Wyjątek: SOC ≤5% jest obsłużony wcześniej w decide_strategy (linia 248)
                return {
                    'mode': 'idle',
                    'priority': 'normal',  # Normalne czekanie na L2
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
                        'priority': 'normal',  # Normalne nocne ładowanie
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
                        'priority': 'normal',  # Normalne ładowanie przy PC
                        'reason': 'PC w L2 + doładuj baterię na L1'
                    }

    # Poza sezonem
    else:
        if tariff == 'L1' and soc > 20:
            return {
                'mode': 'discharge_to_home',
                'priority': 'normal',  # Normalna operacja w L1
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
            'priority': 'normal',  # Było 'critical' - to normalny fallback
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
            'priority': 'normal',  # Okazja cenowa, nie ostrzeżenie
            'reason': f'RCE ujemne ({rce_now:.3f})! Płacą Ci za pobór! (max 80%)'
        }

    # RCE bardzo niskie w południe
    if rce_now < 0.15 and hour in [11, 12, 13, 14]:
        if forecast_tomorrow < 10 and soc < 70:
            return {
                'should_charge': True,
                'target_soc': 80,
                'priority': 'normal',  # Okazja cenowa
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
                'priority': 'normal',  # Normalna decyzja o ostatnim ładowaniu
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
        # Tryb time_of_use_luna2000 + harmonogram TOU + grid charging
        # UWAGA: max_discharge_power=5000 (nie 0!) - żeby backup mode działał
        set_huawei_mode('time_of_use_luna2000', charge_from_grid=True, charge_soc_limit=target_soc,
                       urgent_charge=urgent_charge, max_discharge_power=5000)

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
        # W L2 - tryb TOU kontroluje rozładowanie wg harmonogramu
        # UWAGA: max_discharge_power=5000 (nie 0!) - żeby backup mode działał
        # UWAGA: set_tou_periods=True żeby ustawić ochronę weekendową nawet przy restarcie
        set_huawei_mode('time_of_use_luna2000', charge_from_grid=False, max_discharge_power=5000, set_tou_periods=True)

    elif mode == 'idle':
        # ===========================================
        # POPRAWKA 4: W L2 chroń baterię, w L1 normalne zachowanie
        # ===========================================
        now_state = hass.states.get('sensor.time')
        current_hour = int(now_state.state.split(':')[0]) if now_state else 12
        current_tariff = get_tariff_zone(current_hour)
        if current_tariff == 'L2':
            # W L2 - tryb TOU kontroluje rozładowanie wg harmonogramu
            # UWAGA: max_discharge_power=5000 (nie 0!) - żeby backup mode działał
            # UWAGA: set_tou_periods=True żeby ustawić ochronę weekendową nawet przy restarcie
            set_huawei_mode('time_of_use_luna2000', charge_from_grid=False, max_discharge_power=5000, set_tou_periods=True)
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
        # Ustawiaj TOU periods gdy:
        # 1. charge_from_grid=True (ładowanie z sieci)
        # 2. set_tou_periods=True (ochrona weekendowa dla grid_to_home/idle)
        should_set_tou = (
            ('charge_from_grid' in kwargs and kwargs['charge_from_grid']) or
            kwargs.get('set_tou_periods', False)
        )

        if should_set_tou:
            try:
                # SUPER PILNY (SOC < 5%): Ładuj NATYCHMIAST przez całą dobę!
                if kwargs.get('urgent_charge', False):
                    tou_periods = "00:00-23:59/1234567/+"
                # NORMALNY/PILNY: Ładuj w godzinach L2 + chroń baterię w weekend
                # WAŻNE: NIE ładuj w weekend! Ładowanie tylko od niedzieli 22:00
                # Dni: 1=Pon, 2=Wt, 3=Śr, 4=Czw, 5=Pt, 6=Sob, 7=Ndz
                else:
                    tou_periods = (
                        "22:00-23:59/123457/+\n"   # Pon-Pt + Ndz wieczór: ładuj (22-24h)
                        "00:00-05:59/12345/+\n"    # Pon-Pt noc: ładuj (0-6h) - NIE weekend!
                        "13:00-14:59/12345/+\n"    # Pon-Pt południe: ładuj (13-15h) - NIE weekend!
                        "06:00-12:59/67/+\n"       # Weekend: rano - ochrona baterii
                        "15:00-21:59/67/+"         # Weekend: popołudnie - ochrona baterii
                    )

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
    """Pobiera stan encji, zwraca None dla unavailable/unknown"""
    try:
        state = hass.states.get(entity_id)
        if state is None:
            return None
        # Zwróć None dla unavailable/unknown żeby fallback values działały
        if state.state in ('unavailable', 'unknown', 'None', ''):
            return None
        return state.state
    except Exception as e:
        return None


def get_fallback_strategy(data):
    """Strategia awaryjna"""
    soc = data.get('soc', 50)

    if soc < 30:
        return {
            'mode': 'charge_from_grid',
            'target_soc': 50,
            'priority': 'normal',  # Fallback to nie błąd
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
    # UWAGA: result to True/False, strategy to słownik!
    # Używamy try/except bo isinstance() nie działa w python_scripts
    try:
        reason = str(strategy.get('reason', '') or '')
        mode = str(strategy.get('mode', 'unknown') or 'unknown')
        priority = str(strategy.get('priority', 'normal') or 'normal')
    except:
        reason = ''
        mode = 'unknown'
        priority = 'normal'

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
    # Pobierz czas z sensora HA zamiast datetime
    time_state = hass.states.get('sensor.time')
    date_state = hass.states.get('sensor.date')
    if time_state and date_state:
        timestamp = date_state.state + 'T' + time_state.state + ':00'
    else:
        timestamp = '2025-01-01T00:00:00'
    event_json = '{"ts":"' + timestamp + '","lvl":"' + level + '","cat":"' + category + '","msg":"' + msg + '"}'

    # Rotacja: przesuń wszystkie sloty (5 -> usuń, 4->5, 3->4, 2->3, 1->2, new->1)
    # Odczytaj obecne wartości - bez range() bo może nie być dostępne
    slot1 = hass.states.get('input_text.event_log_1')
    slot2 = hass.states.get('input_text.event_log_2')
    slot3 = hass.states.get('input_text.event_log_3')
    slot4 = hass.states.get('input_text.event_log_4')
    slots = [
        slot1.state if slot1 else '',
        slot2.state if slot2 else '',
        slot3.state if slot3 else '',
        slot4.state if slot4 else ''
    ]

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
