# Instrukcja: Fix weekendowej logiki PV surplus w algorytmie baterii

## Kontekst problemu

Na weekendach (sobota/niedziela) algorytm baterii (`config/python_scripts/battery_algorithm.py`) ustawia tryb `discharge_to_home` (maximise_self_consumption) i **cała nadwyżka PV automatycznie ładuje baterię** - niezależnie od cen RCE.

Algorytm najtańszych godzin (`calculate_cheapest_hours_to_store()`) oblicza które godziny mają najtańsze ceny RCE (np. 9-15), ale ta informacja **nie wpływa na decyzje weekendowe**, bo weekend check w `decide_strategy()` (linia ~357) zwraca wynik ZANIM kod dotrze do `handle_pv_surplus()` (linia ~550), która korzysta z najtańszych godzin.

**Skutek**: W drogie godziny RCE (np. 7-8) PV ładuje baterię zamiast sprzedawać do sieci po wyższej cenie.

## Dokładna zmiana do wykonania

### Plik: `config/python_scripts/battery_algorithm.py`

### Lokalizacja: funkcja `decide_strategy()`, blok `is_energy_weekend` (linie ~354-362)

### Obecny kod (DO ZASTĄPIENIA):

```python
if is_energy_weekend:
    return {
        'mode': 'discharge_to_home',
        'priority': 'normal',
        'reason': 'Weekend - tylko self consumption, bez ładowania z sieci'
    }
```

### Nowy kod (ZASTĄP POWYŻSZE TYM):

```python
if is_energy_weekend:
    # Weekend - BEZ ładowania z sieci, ale optymalizuj nadwyżkę PV
    if soc >= soc_max:
        # Bateria pełna
        if balance['surplus'] > 0:
            return {
                'mode': 'discharge_to_grid',
                'priority': 'normal',
                'reason': f'Weekend, bateria pełna ({soc:.0f}% >= {soc_max}%), nadwyżka PV - sprzedaj'
            }
        return {
            'mode': 'grid_to_home',
            'discharge_limit': soc_max,
            'priority': 'normal',
            'reason': f'Weekend, SOC {soc:.0f}% >= {soc_max}% - pobieraj z sieci'
        }

    if balance['surplus'] > 0:
        # Nadwyżka PV - użyj algorytmu najtańszych godzin (magazynuj/sprzedaj)
        return handle_pv_surplus(data, balance)

    # Brak nadwyżki PV - self consumption (rozładowuj baterię do domu)
    return {
        'mode': 'discharge_to_home',
        'priority': 'normal',
        'reason': 'Weekend - self consumption, brak nadwyżki PV'
    }
```

## Co zmiana robi

| Sytuacja weekendowa | PRZED (stary kod) | PO (nowy kod) |
|---|---|---|
| PV surplus + tania godzina RCE | Ładuj baterię (MSC) | Ładuj baterię (`handle_pv_surplus` → `charge_from_pv`) |
| PV surplus + droga godzina RCE | Ładuj baterię (MSC) | **Sprzedaj do sieci** (`handle_pv_surplus` → `discharge_to_grid`) |
| Brak PV surplus | Rozładowuj do domu | Rozładowuj do domu (bez zmian) |
| SOC >= soc_max + surplus | Rozładowuj do domu | Sprzedaj do sieci |
| SOC >= soc_max + brak surplus | Rozładowuj do domu | Pobieraj z sieci (grid_to_home) |

**Kluczowe**: Ładowanie z sieci (`charge_from_grid`) nadal jest ZABLOKOWANE na weekendach - `handle_pv_surplus()` nigdy nie zwraca `charge_from_grid`, zwraca tylko `charge_from_pv` lub `discharge_to_grid`.

## Zabezpieczenia wbudowane w `handle_pv_surplus()`

Funkcja `handle_pv_surplus()` (linia ~866) ma własne zabezpieczenia:
1. RCE < 0.15 zł → MAGAZYNUJ (nie oddawaj za bezcen)
2. Jutro pochmurno (< 12 kWh) → MAGAZYNUJ (zabezpieczenie)
3. Tania godzina RCE → MAGAZYNUJ (algorytm najtańszych godzin)
4. Droga godzina RCE → SPRZEDAJ

## Testy

1. Uruchom `npm run test` i upewnij się że wszystkie testy przechodzą
2. Jeśli istnieją testy dla `decide_strategy` - sprawdź czy pokrywają scenariusz weekendowy
3. Jeśli nie ma testów weekendowych - dodaj testy pokrywające:
   - Weekend + PV surplus + tania godzina RCE → powinno magazynować
   - Weekend + PV surplus + droga godzina RCE → powinno sprzedawać
   - Weekend + brak surplus → powinno rozładowywać do domu
   - Weekend + SOC >= soc_max + surplus → powinno sprzedawać
   - Weekend + SOC < soc_min → powinno ładować z sieci (safety check PRZED blokiem weekendowym)

## Deployment na Raspberry Pi

Po zatwierdzeniu zmian:

```bash
# SSH do RPi
ssh -o ProxyCommand="cloudflared access ssh --hostname rpi-ssh.bodino.us.kg" bodino@rpi-ssh.bodino.us.kg

# Skopiuj zmieniony plik
scp -o ProxyCommand="cloudflared access ssh --hostname rpi-ssh.bodino.us.kg" \
  config/python_scripts/battery_algorithm.py \
  bodino@rpi-ssh.bodino.us.kg:~/homeassistant/python_scripts/

# Restart HA
sudo docker restart homeassistant

# Sprawdź logi po restarcie
sudo docker logs homeassistant -f --since=1m
```

## Weryfikacja po wdrożeniu

Po restarcie HA, w weekend sprawdź:
1. `input_text.battery_decision_reason` - powinien pokazywać decyzje z `handle_pv_surplus` zamiast "Weekend - tylko self consumption"
2. `input_text.battery_cheapest_hours` - powinien pokazywać najtańsze godziny (bez zmian)
3. `switch.akumulatory_ladowanie_z_sieci` - powinien być OFF (bez ładowania z sieci)
4. W drogie godziny RCE: PV powinno sprzedawać do sieci, nie ładować baterię

## Dodatkowa rekomendacja (nie jest częścią tej zmiany)

Stare automatyzacje w `config/automations.yaml` mogą kolidować z algorytmem:
- `huawei_weather_optimization` - `forcible_charge` 3000W na 8h przy pochmurnej pogodzie
- `huawei_cheap_charging_start` - TOU periods o 22:00
- `huawei_pv_priority_mode` - TOU periods o 06:00
- `huawei_emergency_charging` - `forcible_charge` przy SOC<15%

Te automatyzacje powinny być **wyłączone w HA** (nie usuwane z pliku, tylko disabled), bo algorytm w `battery_algorithm.py` obsługuje wszystkie te scenariusze.
