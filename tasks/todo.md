# TODO: Sezonowe zakresy SOC baterii

## Cel
Zmienić zakres ładowania baterii (min/max SOC) w zależności od miesiąca:

| Okres | Zakres SOC | Uzasadnienie |
|-------|------------|--------------|
| Listopad - Luty | 10-90% | Minimalna produkcja PV, wysokie zużycie |
| Marzec - Kwiecień | 15-85% | Przejściowo, PV rośnie |
| Maj - Wrzesień | 20-80% | PV ładuje baterię za darmo |
| Październik | 15-85% | Przejściowo, PV spada |

## Plan zmian

### 1. [ ] Dodać funkcję `get_seasonal_soc_limits(month)` w `battery_algorithm.py`
- Zwraca tuple `(min_soc, max_soc)` w zależności od miesiąca
- Logika sezonowa:
  - Listopad-Luty (11,12,1,2): (10, 90)
  - Marzec-Kwiecień (3,4): (15, 85)
  - Maj-Wrzesień (5,6,7,8,9): (20, 80)
  - Październik (10): (15, 85)

### 2. [ ] Zastąpić stałe `BATTERY_LOW` i `BATTERY_MAX` dynamicznymi wartościami
Miejsca w kodzie do zmiany:
- Linia 31-37: stałe BATTERY_* → użyj funkcji
- Linia 280: `if soc < 5` → `if soc < min_soc - 5` (5% poniżej minimum)
- Linia 290: `if soc < 20` → `if soc < min_soc`
- Linia 298: `if soc >= 80` → `if soc >= max_soc`
- Linia 482: `if soc < 80` → `if soc < max_soc`
- Linia 1063-1073: limity temperatury + SOC

### 3. [ ] Zaktualizować `input_numbers.yaml`
- Zmienić `min: 20` → `min: 10`
- Zmienić `max: 80` → `max: 90`

### 4. [ ] Dodać sensor `sensor.battery_soc_limits` w `template_sensors.yaml`
- Pokazuje aktualne sezonowe limity (min/max)
- Atrybuty: sezon, min_soc, max_soc

### 5. [ ] Test i weryfikacja
- Sprawdzić działanie algorytmu
- Sprawdzić dashboard

## Pliki do modyfikacji
1. `config/python_scripts/battery_algorithm.py`
2. `config/input_numbers.yaml`
3. `config/template_sensors.yaml`

## Uwagi
- KRYTYCZNE: Zachować bezpieczne zachowanie gdy brak danych o miesiącu (fallback na 20-80%)
- Limit 90% jest bezpieczny dla Huawei Luna 2000 (producent ogranicza tylko rozładowanie <20%)

---

## Review

### Zmiany wprowadzone (2026-01-23)

1. **battery_algorithm.py**
   - Dodano funkcję `get_seasonal_soc_limits(month)` zwracającą (min_soc, max_soc) w zależności od sezonu
   - Usunięto stałe `BATTERY_LOW` i `BATTERY_MAX` (teraz dynamiczne)
   - Dodano `soc_min` i `soc_max` do `collect_input_data()`
   - Zaktualizowano funkcje używające hardcoded SOC:
     - `decide_strategy()` - dynamiczne progi SOC
     - `handle_power_deficit()` - dynamiczne progi ładowania
     - `should_charge_from_grid()` - dynamiczne progi krytyczne
     - `handle_pv_surplus()` - dynamiczne max SOC
     - `check_arbitrage_opportunity()` - dynamiczne min SOC dla arbitrażu
     - `apply_battery_mode()` - dynamiczne fallbacki (data=None)
     - `get_fallback_strategy()` - dynamiczny próg ładowania (soc_min + 20)

2. **input_numbers.yaml**
   - Zmieniono zakres `battery_target_soc`: min 20→10, max 80→90

3. **template_sensors.yaml**
   - Dodano sensor `sensor.battery_soc_limits` pokazujący aktualne limity sezonowe

4. **Testy**
   - Dodano nową klasę `TestSeasonalSocLimits` (5 testów)
   - Zaktualizowano istniejące testy dla nowych limitów sezonowych
   - Wszystkie 49 testów przechodzi ✅

5. **Deployment**
   - Wgrano na RPi i zrestartowano HA ✅

### Harmonogram sezonowy
| Okres | Min SOC | Max SOC |
|-------|---------|---------|
| Listopad - Luty | 10% | 90% |
| Marzec - Kwiecień | 15% | 85% |
| Maj - Wrzesień | 20% | 80% |
| Październik | 15% | 85% |

---

### Rezerwa weekendowa (2026-01-23)

**Cel:** W weekendy i święta trzymaj 30% baterii jako rezerwę na wypadek awarii sieci (backup mode).

**Logika:**
- Weekend energetyczny (piątek 22:00 - niedziela 21:59):
  - SOC > 30%: `discharge_to_home` (normalnie używaj baterii)
  - SOC ≤ 30%: `grid_to_home` (zachowaj rezerwę, pobieraj z sieci)
  - Backup mode (awaria sieci): używaj całej baterii bez limitu!
  - SOC < 5%: nadal ładuj krytycznie (jak zawsze)

**Zmiany:**
1. **battery_algorithm.py**
   - Dodano `is_backup_mode` do `collect_input_data()` (sensor: `binary_sensor.awaria_zasilania_sieci`)
   - Zmodyfikowano logikę weekendu w `decide_strategy()` - rezerwa 30% z wyjątkiem backup mode

2. **Testy**
   - Dodano klasę `TestWeekendReserve` (5 testów)
   - Wszystkie 54 testy przechodzą ✅

3. **Deployment**
   - Wgrano na RPi i zrestartowano HA ✅

---

### Automatyczny Target SOC zgodny z sezonem (2026-01-23)

**Cel:** Target SOC powinien automatycznie odpowiadać sezonowemu soc_max (90% zima, 85% przejściowo, 80% lato).

**Obecny stan:**
- `target_soc` czytany z `input_number.battery_target_soc` (domyślnie 80%)
- `soc_max` obliczany dynamicznie z `get_seasonal_soc_limits(month)`

**Plan:**
1. [x] Zmienić `collect_input_data()` - `target_soc = min(suwak, soc_max)`
2. [x] Zaktualizować testy
3. [x] Wgrać na RPi i zrestartować HA ✅

**Nowa logika:**
- `target_soc = min(input_number.battery_target_soc, soc_max)`
- Użytkownik może ustawić niższy target przez suwak
- Ale nie wyższy niż sezonowy max (automatyczne przycięcie)

**Zmiany w plikach:**
1. **battery_algorithm.py** (linia 253):
   - `target_soc = min(suwak, soc_max)` - automatyczne przycięcie do sezonowego max

2. **calculate_daily_strategy.py**:
   - Dodano `get_seasonal_soc_limits(month)` - sezonowe limity
   - Zmieniono limity z hardcoded 20-80% na dynamiczne `soc_min/soc_max`
   - Fallback zmieniony z 70% na `soc_max - 10%`

3. **conftest.py** (testy):
   - `target_soc = min(80, soc_max)` - domyślnie 80%, ale max sezonowy

4. **Testy**: Wszystkie 54 przechodzą ✅

---

### Poprawki weekendowej rezerwy i suwaka (2026-01-23)

**Problemy zgłoszone przez użytkownika:**
1. W piątek po 22:00, gdy SOC < 30%, bateria nie ładowała się do 30%
2. Suwak Target SOC nie aktualizował się do sezonowego max

**Zmiany:**

1. **battery_algorithm.py** (linia 410-418):
   - Zmieniono logikę weekendową z `grid_to_home` na `charge_from_grid`
   - Teraz gdy SOC < 30% w weekend → ładuj do 30% (nie tylko blokuj rozładowanie!)
   ```python
   if soc < BATTERY_RESERVE:
       return {
           'mode': 'charge_from_grid',
           'target_soc': BATTERY_RESERVE,  # Ładuj tylko do 30%
           'priority': 'normal',
           'reason': f'Weekend - ładowanie do rezerwy {BATTERY_RESERVE}% (SOC {soc:.0f}%)'
       }
   ```

2. **automations_battery.yaml** (nowe automatyzacje):
   - `battery_seasonal_target_soc_startup` - przy starcie HA ustawia suwak na sezonowy max
   - `battery_seasonal_target_soc_monthly` - 1. dnia miesiąca o 00:05 aktualizuje suwak

3. **Testy** (test_battery_algorithm.py):
   - Zmieniono `test_weekend_soc_at_reserve_grid_to_home` → `test_weekend_soc_at_reserve_discharges`
   - Zmieniono `test_weekend_soc_below_reserve_grid_to_home` → `test_weekend_soc_below_reserve_charges_to_30`
   - Wszystkie 54 testy przechodzą ✅

4. **Deployment**: Wgrano na RPi i zrestartowano HA ✅

**Nowa logika weekendowa:**
| SOC | Tryb | Opis |
|-----|------|------|
| < 30% | `charge_from_grid` | Naładuj do 30% (rezerwa na backup) |
| >= 30% | `discharge_to_home` | Normalnie używaj baterii |
| Backup mode | `discharge_to_home` | Używaj całej baterii (awaria sieci) |
| < 5% | `charge_from_grid` | Ładowanie krytyczne 24/7 |

---

### Sezonowa rezerwa weekendowa (2026-01-23)

**Zmiana:** Rezerwa weekendowa teraz zależy od sezonu:
- **Zima (listopad-luty):** 80% (mało PV, duże zużycie)
- **Reszta roku (marzec-październik):** 30%

**Zmiany w plikach:**

1. **battery_algorithm.py**:
   - Usunięto stałą `BATTERY_RESERVE = 30`
   - Dodano funkcję `get_weekend_reserve(month)` zwracającą sezonową rezerwę
   - Dodano `weekend_reserve` do `collect_input_data()`
   - Zaktualizowano logikę weekendową w `decide_strategy()` - używa dynamicznej rezerwy

2. **conftest.py** (testy):
   - Dodano funkcję `get_weekend_reserve(month)`
   - Dodano `weekend_reserve` do `create_test_data()`

3. **test_battery_algorithm.py**:
   - Zaktualizowano `TestWeekendReserve` - osobne testy dla zimy (80%) i lata (30%)
   - Zaktualizowano `test_weekend_self_consumption` - używa letniego miesiąca

4. **Testy**: Wszystkie 55 przechodzą ✅
5. **Deployment**: Wgrano na RPi ✅ (załaduje się przy następnym wywołaniu)

**Sezonowa rezerwa weekendowa:**
| Okres | Rezerwa |
|-------|---------|
| Listopad - Luty | 80% |
| Marzec - Październik | 30% |

---

## AUDYT ALGORYTMU BATERII (2026-01-24)

### 1. HIERARCHIA PRIORYTETÓW W ALGORYTMIE

```
PRIORYTET 0 (execute_strategy, linia 129-150):
└── Temperatura baterii niebezpieczna → ZATRZYMAJ ŁADOWANIE

PRIORYTET 1 (execute_strategy, linia 152-178):
└── SOC >= target_soc → Zatrzymaj ładowanie (ale kontynuuj do decide_strategy!)

PRIORYTET 2 (decide_strategy, linia 370-377):
└── SOC < 5% (BATTERY_CRITICAL) → charge_from_grid 24/7 (priority=critical)

PRIORYTET 3 (decide_strategy, linia 379-386):
└── SOC < soc_min → charge_from_grid (priority=high)

PRIORYTET 4 (decide_strategy, linia 393-421):
└── WEEKEND ENERGETYCZNY:
    ├── backup_mode (awaria sieci) → discharge_to_home (priority=critical)
    ├── SOC < weekend_reserve → charge_from_grid do rezerwy (priority=normal)
    └── SOC >= weekend_reserve → grid_to_home (priority=low) ⚠️ PROBLEM!

PRIORYTET 5 (decide_strategy, linia 426-447):
└── DNI ROBOCZE - SOC >= soc_max:
    ├── L2 → grid_to_home (priority=low) ⚠️ PROBLEM!
    ├── L1 + nadwyżka PV → discharge_to_grid (priority=normal)
    └── L1 bez nadwyżki → discharge_to_home (priority=normal)

PRIORYTET 6 (decide_strategy, linia 458-467):
└── L2 NOC/POŁUDNIE - SOC >= target_soc → grid_to_home ⚠️ PROBLEM!

PRIORYTET 7 (decide_strategy, linia 472-483):
└── L1 - SOC > soc_min, brak nadwyżki → discharge_to_home

PRIORYTET 8 (decide_strategy, linia 489-560):
└── L2 NOC - inteligentne ładowanie (prognoza PV):
    ├── Sezon grzewczy + SOC < target → charge_from_grid
    ├── Prognoza >= 15 kWh → grid_to_home ⚠️ PROBLEM!
    └── Prognoza < 15 kWh + SOC < target → charge_from_grid

PRIORYTET 9 (decide_strategy, linia 563-598):
└── L2 POŁUDNIE - SOC < soc_max:
    ├── Nadwyżka PV > 1.5 kW → charge_from_pv
    ├── PV wystarczy → charge_from_pv
    └── PV nie wystarczy → charge_from_grid

PRIORYTET 10 (decide_strategy, linia 604-613):
└── AUTOCONSUMPTION:
    ├── nadwyżka PV → handle_pv_surplus()
    ├── deficyt → handle_power_deficit()
    └── balans → idle
```

### 2. MAPA TRYBÓW I ICH USTAWIEŃ

| Mode | working_mode | charge_from_grid | TOU periods | discharge_soc_limit |
|------|--------------|------------------|-------------|---------------------|
| charge_from_pv | maximise_self_consumption | False | - | soc_min |
| charge_from_grid | time_of_use_luna2000 | True | + (ładowanie) | soc_min |
| discharge_to_home | maximise_self_consumption | False | - | soc_min |
| discharge_to_grid | maximise_self_consumption | False | - | min_soc (custom) |
| **grid_to_home** | **time_of_use_luna2000** | **False** | **+ (ładowanie!)** | **soc_min** ⚠️ |
| **idle (L2)** | **time_of_use_luna2000** | **False** | **+ (ładowanie!)** | **soc_min** ⚠️ |
| idle (L1) | maximise_self_consumption | False | - | soc_min |

### 3. ZIDENTYFIKOWANE PROBLEMY

#### ⚠️ PROBLEM 1: `grid_to_home` używa TOU z harmonogramem `+`

**Lokalizacja:** `apply_battery_mode()` linia 1346-1350

**Kod:**
```python
elif mode == 'grid_to_home':
    set_huawei_mode('time_of_use_luna2000', charge_from_grid=False,
                   max_discharge_power=5000, set_tou_periods=True,
                   discharge_soc_limit=soc_min)
```

**Problem:**
- `set_tou_periods=True` ustawia harmonogram TOU z `+` (ładowanie dozwolone)
- W trybie TOU z `+`, inwerter kieruje PV do baterii jako PRIORYTET
- Dopiero gdy bateria pełna, PV idzie do domu
- To jest BŁĘDNE dla `grid_to_home` gdzie chcemy: PV → Dom, Bateria chroniona

**Dotknięte scenariusze:**
1. Weekend - rezerwa chroniona (linia 418)
2. Dni robocze - SOC >= soc_max w L2 (linia 430)
3. L2 noc/południe - SOC >= target_soc (linia 464)
4. L2 noc - dobra prognoza PV (linie 523, 531, 539)
5. handle_power_deficit() - kilka miejsc (linie 1066, 1082, 1097, 1111)

#### ⚠️ PROBLEM 2: `discharge_soc_limit` nie respektuje kontekstu

**Lokalizacja:** `apply_battery_mode()` linia 1350

**Problem:**
- Dla `grid_to_home` zawsze ustawiamy `discharge_soc_limit=soc_min`
- Ale dla weekendu powinno być `weekend_reserve` (80% zimą)
- Dla SOC >= soc_max powinno być `soc_max`
- Dla SOC >= target_soc powinno być `target_soc`

**Skutek:** Bateria może się rozładować poniżej oczekiwanego progu

#### ⚠️ PROBLEM 3: Brak automatyzacji na awarie sieci

**Problem:**
- Algorytm sprawdza `binary_sensor.awaria_zasilania_sieci` (linia 267)
- Ale nie ma automatyzacji która uruchomi algorytm gdy ten sensor się zmieni
- Algorytm uruchamia się tylko co godzinę lub przy progach SOC

**Ryzyko:** Opóźniona reakcja na awarię sieci (do 1h!)

### 4. ANALIZA SPÓJNOŚCI PRIORYTETÓW

| Scenariusz | Priorytet | Poprawność |
|------------|-----------|------------|
| SOC < 5% (krytyczne) | critical | ✅ OK - najwyższy |
| SOC < soc_min | high | ✅ OK - drugi |
| Weekend + backup mode | critical | ✅ OK |
| Weekend + SOC < reserve | normal | ✅ OK |
| Weekend + SOC >= reserve | low | ⚠️ Problem z TOU |
| SOC >= soc_max w L2 | low | ⚠️ Problem z TOU |
| SOC >= target w L2 | normal | ⚠️ Problem z TOU |
| L1 discharge | normal | ✅ OK |
| L2 noc charge | normal | ✅ OK |
| L2 południe charge | normal | ✅ OK |

### 5. PRZEPŁYW DECYZJI - PRZYKŁADY

#### Przykład 1: Weekend, SOC=81%, Zima
```
1. Temperatura OK? → TAK, kontynuuj
2. SOC >= target_soc (90%)? → NIE (81 < 90)
3. SOC < 5%? → NIE
4. SOC < soc_min (10%)? → NIE
5. Weekend? → TAK
6. Backup mode? → NIE
7. SOC < weekend_reserve (80%)? → NIE (81 >= 80)
8. → grid_to_home "Weekend - rezerwa 80% chroniona"
9. → apply_battery_mode:
   - Tryb: time_of_use_luna2000
   - charge_from_grid: False
   - TOU periods: + (ŁADOWANIE DOZWOLONE!) ⚠️
   - discharge_soc_limit: soc_min (10%) ⚠️ powinno być 80%!
```

#### Przykład 2: Dzień roboczy, L2 13:30, SOC=85%, soc_max=90%
```
1. Temperatura OK? → TAK
2. SOC >= target_soc? → NIE (zakładając target=90%)
3. SOC < 5%? → NIE
4. SOC < soc_min? → NIE
5. Weekend? → NIE
6. SOC >= soc_max (90%)? → NIE (85 < 90)
7. L2 i SOC >= target_soc? → NIE (85 < 90)
8. L1? → NIE (jest L2)
9. L2 NOC? → NIE (jest 13:30)
10. L2 POŁUDNIE (13-14h), SOC < soc_max? → TAK
11. Nadwyżka PV > 1.5kW? → (zależy od PV)
12. → charge_from_pv lub charge_from_grid
```

### 6. REKOMENDACJE NAPRAWY

#### Naprawa 1: Zmienić `grid_to_home` na `maximise_self_consumption`

**Zmiana w `apply_battery_mode()`:**
```python
elif mode == 'grid_to_home':
    # Pobierz limit rozładowania z kontekstu
    discharge_limit = strategy.get('discharge_limit', soc_min)
    # Użyj maximise_self_consumption żeby PV szło do domu
    set_huawei_mode('maximise_self_consumption',
                   charge_from_grid=False,
                   max_discharge_power=5000,  # backup działa
                   discharge_soc_limit=discharge_limit)
```

#### Naprawa 2: Dodać `discharge_limit` do strategii

**Zmiana w `decide_strategy()` - weekend:**
```python
return {
    'mode': 'grid_to_home',
    'discharge_limit': weekend_reserve,  # NOWE
    'priority': 'low',
    'reason': f'Weekend - rezerwa {weekend_reserve}% chroniona (SOC {soc:.0f}%)'
}
```

**Zmiana w `decide_strategy()` - SOC >= soc_max:**
```python
return {
    'mode': 'grid_to_home',
    'discharge_limit': soc_max,  # NOWE
    'priority': 'low',
    'reason': f'SOC {soc:.0f}% >= {soc_max}% (sezonowe max) w L2 - pobieraj z sieci'
}
```

#### Naprawa 3: Dodać automatyzację na awarie sieci

**Nowa automatyzacja w `automations_battery.yaml`:**
```yaml
- id: battery_grid_outage_trigger
  alias: "[Bateria] Awaria sieci - uruchom algorytm"
  trigger:
    - platform: state
      entity_id: binary_sensor.awaria_zasilania_sieci
      to: "on"
  action:
    - service: python_script.battery_algorithm
```

### 7. WPŁYW NA BACKUP MODE

**Pytanie:** Czy `discharge_soc_limit=80%` zablokuje backup przy awarii sieci?

**Odpowiedź:** NIE - Huawei Luna 2000 ma wbudowany EPS (Emergency Power Supply):
- EPS działa na poziomie SPRZĘTOWYM, niezależnie od Home Assistant
- Gdy sieć padnie, inwerter automatycznie przełącza się na backup
- EPS ignoruje ustawienia `discharge_soc_limit` z HA
- Bateria rozładowuje się do fizycznego minimum (~5%)

**Potwierdzenie:** Backup mode jest bezpieczny niezależnie od `discharge_soc_limit` w HA.

### 8. STATUS AUDYTU

- [x] Hierarchia priorytetów przeanalizowana
- [x] Wszystkie tryby zmapowane
- [x] Konflikty zidentyfikowane
- [x] Spójność discharge_soc_limit sprawdzona
- [x] Wpływ na backup mode zweryfikowany
- [x] Naprawy zaimplementowane (2026-01-24)

---

### 9. IMPLEMENTACJA NAPRAW (2026-01-24)

#### Fix 1: Zmieniono `grid_to_home` na `maximise_self_consumption`

**Zmiana w `apply_battery_mode()` (linia 1346-1354):**
```python
elif mode == 'grid_to_home':
    # Użyj maximise_self_consumption żeby PV szło do domu, nie do baterii
    # UWAGA: max_discharge_power=5000 (nie 0!) - żeby backup mode (EPS) działał
    # discharge_limit z kontekstu (weekend_reserve, soc_max lub target_soc)
    discharge_limit = strategy.get('discharge_limit', soc_min)
    set_huawei_mode('maximise_self_consumption',
                   charge_from_grid=False,
                   max_discharge_power=5000,
                   discharge_soc_limit=discharge_limit)
```

**Efekt:** PV teraz idzie do domu jako priorytet, nie do baterii.

#### Fix 2: Dodano `discharge_limit` do wszystkich strategii `grid_to_home`

Zaktualizowane miejsca:
1. **Weekend - rezerwa chroniona:** `discharge_limit: weekend_reserve` (80% zimą, 30% reszta roku)
2. **SOC >= soc_max w L2:** `discharge_limit: soc_max`
3. **SOC >= target_soc w L2 noc/południe:** `discharge_limit: target_soc`
4. **L2 noc z dobrą prognozą PV (>=15, >=20, >=25):** `discharge_limit: soc_min`
5. **handle_power_deficit() - 4 miejsca:** odpowiednie limity kontekstowe

#### Fix 3: Automatyzacja dla awarii sieci (POMINIĘTO)

**Powód:** EPS (Emergency Power Supply) w Huawei Luna 2000 działa na poziomie SPRZĘTOWYM, niezależnie od Home Assistant. Automatyzacja byłaby tylko informacyjna.

#### Testy

Wszystkie **55 testów przeszło** ✅

#### Deployment

Wgrano na RPi i zrestartowano HA ✅ (2026-01-24)

#### Bezpieczeństwo EPS

Potwierdzono w dokumentacji Huawei:
- **Backup SOC** (domyślnie 15%) to ODDZIELNY parametr od `discharge_soc_limit`
- Przy awarii sieci EPS używa **Backup SOC**, nie `discharge_soc_limit`
- Rozwiązanie z `discharge_limit` jest BEZPIECZNE dla EPS

Źródła:
- [Battery Control Settings - FusionSolar](https://support.huawei.com/enterprise/en/doc/EDOC1100387244/70525ea4/setting-battery-control)
- [SOC Change Description - LUNA2000 Manual](https://support.huawei.com/enterprise/en/doc/EDOC1100167258/eb79055c/soc-change-description)
