# 🔧 Instrukcja wdrożenia poprawki algorytmu baterii

**Data:** 2025-11-23
**Branch:** `claude/fix-battery-algorithm-01WS6mG8FMgdQNJ1nKwKm2s5`
**Bazuje na:** `origin/main` (commit `133200d`)

---

## 📋 Podsumowanie zmian

### Problem
Watchdog wykrywał brak aktualizacji algorytmu baterii przez >2h, mimo że system działał. Przyczyny:
1. Brak obsługi wyjątków na najwyższym poziomie skryptu Python
2. Brakujący sensor `binary_sensor.dzien_roboczy`
3. Sensor błędów pokazujący normalne decyzje jako błędy

### Rozwiązanie
Trzy poprawki w dwóch plikach:

| # | Plik | Zmiana |
|---|------|--------|
| 1 | `config/python_scripts/battery_algorithm.py` | Try-catch na najwyższym poziomie |
| 2 | `config/template_sensors.yaml` | Nowy sensor `binary_sensor.dzien_roboczy` |
| 3 | `config/template_sensors.yaml` | Poprawiony `sensor.system_ostatni_blad` |

### Kompatybilność
✅ Poprawka jest w pełni kompatybilna z nowym systemem **Event Log** (dodanym w main).
✅ Funkcja `log_decision()` z Event Log pozostaje bez zmian.
✅ Try-catch dodatkowo chroni cały system przed nieobsłużonymi wyjątkami.

---

## 🚀 Kroki wdrożenia

### Krok 1: Backup (WAŻNE!)
```bash
# Na serwerze Home Assistant
cd /config
cp -r python_scripts python_scripts.backup.$(date +%Y%m%d)
cp template_sensors.yaml template_sensors.yaml.backup.$(date +%Y%m%d)
```

### Krok 2: Pobranie zmian z repozytorium

**Opcja A: Merge do main (zalecane)**
```bash
cd /config
git fetch origin
git checkout main
git merge origin/claude/fix-battery-algorithm-01WS6mG8FMgdQNJ1nKwKm2s5
```

**Opcja B: Bezpośredni checkout brancha (do testów)**
```bash
cd /config
git fetch origin
git checkout claude/fix-battery-algorithm-01WS6mG8FMgdQNJ1nKwKm2s5
```

### Krok 3: Walidacja konfiguracji
```bash
# W Home Assistant UI:
# Developer Tools → YAML → Check Configuration

# LUB przez CLI:
ha core check
```

### Krok 4: Przeładowanie konfiguracji
```yaml
# W Home Assistant UI:
# Developer Tools → YAML → Reload:
# ✅ Template entities
# ✅ Automations (jeśli zmieniałeś automations_*.yaml)

# LUB pełny restart:
ha core restart
```

### Krok 5: Weryfikacja po wdrożeniu

#### 5.1 Sprawdź nowy sensor dni roboczych
```
Developer Tools → States → binary_sensor.dzien_roboczy
```
- **on** = dzień roboczy (Pn-Pt bez świąt)
- **off** = weekend lub święto

#### 5.2 Sprawdź sensor błędów
```
Developer Tools → States → sensor.system_ostatni_blad
```
- Powinien pokazywać "Brak błędów" (jeśli wszystko OK)
- NIE powinien pokazywać normalnych decyzji algorytmu

#### 5.3 Wywołaj algorytm ręcznie
```
Developer Tools → Services → python_script.battery_algorithm → Call Service
```
Sprawdź:
- `input_text.battery_decision_reason` - powinien się zaktualizować
- `input_text.event_log_1` - powinien zawierać JSON z decyzją

#### 5.4 Test obsługi błędów (opcjonalnie)
1. Tymczasowo wyłącz integrację Huawei Solar
2. Wywołaj `python_script.battery_algorithm`
3. Sprawdź czy `decision_reason` pokazuje `🚨 BŁĄD ALGORYTMU: ...`
4. Włącz integrację z powrotem

---

## 📁 Zmienione pliki

### 1. `config/python_scripts/battery_algorithm.py`

**Lokalizacja:** Linie 1307-1328 (koniec pliku)
**Zmiana:** Try-catch wokół `execute_strategy()`

```python
# ============================================
# URUCHOMIENIE
# ============================================

try:
    execute_strategy()
except Exception as e:
    # ZAWSZE aktualizuj decision_reason - nawet przy błędzie!
    error_msg = f"🚨 BŁĄD ALGORYTMU: {str(e)[:200]}"
    try:
        hass.services.call('input_text', 'set_value', {
            'entity_id': 'input_text.battery_decision_reason',
            'value': error_msg
        })
        # Tryb awaryjny + wyłączenie ładowania
        hass.services.call('select', 'select_option', {
            'entity_id': 'select.akumulatory_tryb_pracy',
            'option': 'maximise_self_consumption'
        })
        hass.services.call('switch', 'turn_off', {
            'entity_id': 'switch.akumulatory_ladowanie_z_sieci'
        })
    except:
        pass
```

**Efekt:**
- Watchdog nie będzie fałszywie alarmować
- Błędy widoczne na dashboardzie z konkretną treścią
- System automatycznie przechodzi w tryb awaryjny

---

### 2. `config/template_sensors.yaml` - Sensor dni roboczych

**Lokalizacja:** Linie 28-79
**Zmiana:** Nowy sensor `binary_sensor.dzien_roboczy`

```yaml
- binary_sensor:
    - name: "Dzień roboczy"
      unique_id: workday_sensor
      state: >
        {% set dominated_days = [0, 1, 2, 3, 4] %}
        {% set today = now().weekday() %}

        {# Lista polskich świąt stałych (MM-DD) #}
        {% set holidays = [
          '01-01', '01-06', '05-01', '05-03',
          '08-15', '11-01', '11-11', '12-25', '12-26'
        ] %}

        {# Święta ruchome 2024-2026 #}
        {% set movable_holidays = [
          '2024-03-31', '2024-04-01', '2024-05-30',
          '2025-04-20', '2025-04-21', '2025-06-19',
          '2026-04-05', '2026-04-06', '2026-06-04'
        ] %}

        {{ not is_weekend and not is_holiday }}
```

**Polskie święta uwzględnione:**
| Święto | Data |
|--------|------|
| Nowy Rok | 01.01 |
| Trzech Króli | 06.01 |
| Święto Pracy | 01.05 |
| Konstytucja 3 Maja | 03.05 |
| Wniebowzięcie NMP | 15.08 |
| Wszystkich Świętych | 01.11 |
| Niepodległości | 11.11 |
| Boże Narodzenie | 25-26.12 |
| Wielkanoc (ruchome) | 2024-2026 |
| Boże Ciało (ruchome) | 2024-2026 |

---

### 3. `config/template_sensors.yaml` - Sensor błędów

**Lokalizacja:** Linie 495-522
**Zmiana:** Poprawiony `sensor.system_ostatni_blad`

```yaml
- sensor:
    - name: "System - Ostatni Błąd"
      unique_id: system_last_error
      state: >
        {% set decision = states('input_text.battery_decision_reason') %}
        {% set is_algorithm_error = 'BŁĄD' in decision or 'ERROR' in decision or '🚨' in decision %}

        {% if is_algorithm_error %}
          {{ decision[:200] }}
        {% elif huawei_error %}
          Huawei Solar: {{ huawei_error }}
        {% elif rce_unavailable %}
          RCE PSE: niedostępny
        {% else %}
          Brak błędów
        {% endif %}
```

**Efekt:** Pokazuje tylko PRAWDZIWE błędy, nie normalne decyzje algorytmu.

---

## ⚠️ Znane ograniczenia

1. **Święta ruchome** - zdefiniowane tylko do 2026. Po tym czasie trzeba dodać nowe daty do `movable_holidays`.

2. **Alternatywa - integracja Workday**: Można użyć oficjalnej integracji `workday` zamiast ręcznego sensora:
   ```yaml
   # configuration.yaml
   binary_sensor:
     - platform: workday
       country: PL
   ```
   Wymaga zainstalowania integracji i restartu HA.

---

## 🔄 Rollback (w razie problemów)

```bash
# Przywróć backup
cd /config
cp template_sensors.yaml.backup.YYYYMMDD template_sensors.yaml
cp -r python_scripts.backup.YYYYMMDD/* python_scripts/

# Restart Home Assistant
ha core restart
```

---

## 📊 Commity w tej poprawce

| Hash | Opis |
|------|------|
| `48f5483` | 🛡️ FIX: Try-catch na najwyższym poziomie algorytmu |
| `c95071f` | 🔧 FIX: Kompletna poprawka (3 rozwiązania) |
| `240e446` | 📝 Dodano instrukcję wdrożenia |

---

## 📞 Kontakt / Troubleshooting

W razie problemów sprawdź:
1. **Logi HA:** `Settings → System → Logs`
2. **Filtruj po:** `python_script`, `template`, `battery_algorithm`
3. **Event Log:** `input_text.event_log_1` - `event_log_5`
4. **GitHub Issues:** https://github.com/MarekBodynek/home-assistant-huawei/issues
