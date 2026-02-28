# Plan naprawy: Weekend nie korzysta z algorytmu najtańszych godzin

## Problem
Na weekendach algorytm baterii ustawia tryb `discharge_to_home` (MSC) i cała nadwyżka PV
automatycznie ładuje baterię - niezależnie od cen RCE. Algorytm najtańszych godzin oblicza
dane (np. 9-15), ale te dane nie wpływają na decyzje weekendowe.

## Przyczyna
W `battery_algorithm.py` linia 357: `if is_energy_weekend` → return `discharge_to_home`
Ten return jest PRZED logiką PV surplus (linia 550), więc `handle_pv_surplus()` nigdy
nie jest wywoływane na weekendach.

## Plan naprawy

### Zadanie 1: Modyfikacja logiki weekendowej w `decide_strategy()`
- [ ] Zmienić blok `is_energy_weekend` (linie 354-362) żeby:
  - Gdy jest nadwyżka PV → przekazać do `handle_pv_surplus()` (która korzysta z najtańszych godzin)
  - Gdy brak nadwyżki PV → zachować obecne `discharge_to_home`
  - Gdy SOC >= soc_max → obsłużyć osobno (sprzedaj lub grid_to_home)
  - ZACHOWAĆ blokadę ładowania z sieci na weekendach (nie zmieniamy tego)

### Zadanie 2: Sprawdzić stare automatyzacje
- [ ] Sprawdzić (lub poprosić użytkownika o sprawdzenie) czy stare automatyzacje
  w `automations.yaml` są włączone w HA:
  - `huawei_weather_optimization` - forcible_charge 8h przy pochmurnej pogodzie
  - `huawei_cheap_charging_start` - TOU periods o 22:00
  - `huawei_pv_priority_mode` - TOU periods o 06:00
  - `huawei_emergency_charging` - forcible_charge przy SOC<15%
  Te automatyzacje mogą kolidować z algorytmem i powinny być wyłączone.

### Zadanie 3: Testy
- [ ] Uruchomić `npm run test` żeby sprawdzić czy zmiana nie łamie nic

## Zmiana w kodzie (Zadanie 1)

Obecny kod (linie 354-362):
```python
if is_energy_weekend:
    return {
        'mode': 'discharge_to_home',
        'priority': 'normal',
        'reason': 'Weekend - tylko self consumption, bez ładowania z sieci'
    }
```

Proponowany kod:
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

## Co się zmieni
- W **tanie godziny RCE** (np. 9-15): PV nadal ładuje baterię (MAGAZYNUJ - bo nie opłaca się sprzedawać tanio)
- W **drogie godziny RCE** (np. 7-8): PV sprzedaje do sieci (SPRZEDAJ - bo cena lepsza)
- **Ładowanie z sieci**: nadal ZABLOKOWANE na weekendach (bez zmian)
- **Brak PV**: nadal `discharge_to_home` (bez zmian)

## Ryzyka
- Minimalne - zmieniamy tylko weekendową logikę PV surplus
- `handle_pv_surplus` ma wbudowane zabezpieczenia (jutro pochmurno → MAGAZYNUJ, RCE ultra niskie → MAGAZYNUJ)
- Ładowanie z sieci nadal blokowane przez brak `charge_from_grid` w handle_pv_surplus

## Review
(do wypełnienia po implementacji)
