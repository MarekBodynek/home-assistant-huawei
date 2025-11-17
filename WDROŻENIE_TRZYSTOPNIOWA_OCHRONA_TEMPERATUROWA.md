# Instrukcja wdrożenia: Trzystopniowa ochrona temperaturowa baterii

## 📋 Podsumowanie zmian

Zoptymalizowano algorytm bezpieczeństwa baterii, zastępując prosty mechanizm STOP/GO zaawansowanym trzystopniowym systemem ochrony temperaturowej.

### Nowy mechanizm bezpieczeństwa:

| Temperatura | Akcja | Moc ładowania | Opis |
|-------------|-------|---------------|------|
| **> 43°C** | 🚨 KRYTYCZNY | **0W** (STOP) | Całkowite zatrzymanie ładowania, dozwolone tylko rozładowanie (pomaga schłodzić) |
| **40-43°C** | 🔥 WYSOKA | **2500W** (-50%) | Znaczne zmniejszenie mocy ładowania |
| **38-40°C** | ⚠️ PODWYŻSZONA | **3500W** (-30%) | Umiarkowane zmniejszenie mocy ładowania |
| **5-38°C** | ✅ NORMALNA | **5000W** (100%) | Pełna moc ładowania |
| **< 5°C** | ❄️ NISKA | **3500W** (-30%) | Zmniejszenie mocy - baterie litowe nie lubią mrozu |

## 🔄 Zmienione pliki

1. **config/python_scripts/battery_algorithm.py**
   - Dodano funkcję `check_battery_temperature_safety(battery_temp)`
   - Zmodyfikowano `execute_strategy()` - PRIORYTET 0 z trzystopniowym mechanizmem
   - Zmodyfikowano `should_charge_from_grid()` - usunięto stary mechanizm temperatury
   - Zmodyfikowano `apply_battery_mode()` - przekazywanie limitu mocy
   - Zmodyfikowano `set_huawei_mode()` - stosowanie limitu mocy z temperatury

2. **config/input_text.yaml**
   - Dodano `battery_temp_status` - wyświetla status temperatury baterii

## 🚀 Instrukcja wdrożenia

### Krok 1: Backup (OBOWIĄZKOWY!)

```bash
# Utwórz kopię zapasową aktualnej konfiguracji
cp config/python_scripts/battery_algorithm.py config/python_scripts/battery_algorithm.py.backup
cp config/input_text.yaml config/input_text.yaml.backup
```

### Krok 2: Weryfikacja sensor temperatury baterii

Upewnij się, że sensor `sensor.bateria_temperatura_maksymalna` działa poprawnie:

```bash
# SSH do Home Assistant
ssh -p 22222 root@homeassistant.local

# Sprawdź czy sensor istnieje
ha states get sensor.bateria_temperatura_maksymalna
```

**Oczekiwany wynik:** Wartość temperatury (np. `25.5`)

Jeśli sensor nie istnieje, sprawdź:
- Integracja Huawei Solar działa poprawnie
- Sensor jest dostępny w integracji (Developer Tools → States)
- Nazwa sensora jest poprawna (może być `sensor.akumulatory_temperatura` lub podobna)

### Krok 3: Przeładowanie konfiguracji input_text

Po zmianie `config/input_text.yaml` (dodanie `battery_temp_status`):

**Opcja A: Przez UI**
1. Idź do: Developer Tools → YAML
2. Kliknij "HELPERS" (reloading input_text)
3. Sprawdź czy pojawił się nowy sensor: `input_text.battery_temp_status`

**Opcja B: Przez CLI**
```bash
ha core check  # Sprawdź poprawność konfiguracji
ha core restart  # Restart Home Assistant (jeśli check OK)
```

### Krok 4: Sprawdzenie poprawności Python Script

Nowy plik `battery_algorithm.py` został już zmodyfikowany. Sprawdź poprawność składni:

```bash
# W katalogu /config
python3 -m py_compile python_scripts/battery_algorithm.py

# Powinno nie zwrócić błędów
echo $?  # Powinno być 0
```

### Krok 5: Test algorytmu (SYMULACJA)

Przed włączeniem na produkcji, przetestuj algorytm:

```bash
# Developer Tools → Services
# Wywołaj: python_script.battery_algorithm
```

Sprawdź logi:

```bash
# Sprawdź logi Home Assistant
tail -f /config/home-assistant.log | grep -i "battery\|temp"
```

**Oczekiwane logi:**
- Brak błędów `AttributeError`, `KeyError`
- Poprawne wyświetlenie statusu temperatury w `input_text.battery_temp_status`
- Jeśli temperatura w zakresie 38-43°C, powinny być ustawione odpowiednie limity mocy

### Krok 6: Monitoring temperatury (pierwsze 24h)

Po wdrożeniu monitoruj przez 24 godziny:

1. **Sprawdź status temperatury:**
   - `input_text.battery_temp_status` - powinien pokazywać aktualny poziom bezpieczeństwa
   - `sensor.bateria_temperatura_maksymalna` - aktualna temperatura

2. **Sprawdź moce ładowania:**
   - `number.akumulatory_maksymalna_moc_ladowania` - powinna automatycznie zmieniać się w zależności od temperatury

3. **Sprawdź decyzje algorytmu:**
   - `input_text.battery_decision_reason` - powinien zawierać informacje o limitach temperatury

### Krok 7: Weryfikacja Dashboard (opcjonalnie)

Możesz dodać nowy sensor temperatury do dashboardu w `config/lovelace_huawei.yaml`:

```yaml
- type: entities
  title: "🌡️ Temperatura baterii"
  entities:
    - entity: sensor.bateria_temperatura_maksymalna
      name: "Temperatura baterii"
    - entity: input_text.battery_temp_status
      name: "Status temperatury"
```

## 🧪 Testy jednostkowe

### Test 1: Temperatura normalna (20°C)
```yaml
Oczekiwane:
- temp_max_charge_power: 5000W
- Status: "✅ NORMALNA: Temp 20.0°C (5-38°C) - pełna moc (5kW)"
```

### Test 2: Temperatura podwyższona (39°C)
```yaml
Oczekiwane:
- temp_max_charge_power: 3500W
- Status: "⚠️ PODWYŻSZONA: Temp 39.0°C (38-40°C) - moc ładowania -30% (3.5kW)"
```

### Test 3: Temperatura wysoka (42°C)
```yaml
Oczekiwane:
- temp_max_charge_power: 2500W
- Status: "🔥 WYSOKA: Temp 42.0°C (40-43°C) - moc ładowania -50% (2.5kW)"
```

### Test 4: Temperatura krytyczna (44°C)
```yaml
Oczekiwane:
- temp_max_charge_power: 0W
- Ładowanie zatrzymane (switch.akumulatory_ladowanie_z_sieci: OFF)
- Status: "🚨 KRYTYCZNE: Temp 44.0°C > 43°C! STOP ładowania!"
```

### Test 5: Temperatura niska (3°C)
```yaml
Oczekiwane:
- temp_max_charge_power: 3500W
- Status: "❄️ NISKA: Temp 3.0°C < 5°C - moc ładowania -30% (3.5kW) - baterie litowe nie lubią mrozu"
```

## 🔍 Rozwiązywanie problemów

### Problem 1: Sensor `battery_temp_status` nie istnieje
**Rozwiązanie:**
```bash
# Developer Tools → YAML → Reload "Helpers"
# Lub restart Home Assistant
ha core restart
```

### Problem 2: Temperatura nie jest sprawdzana
**Rozwiązanie:**
- Sprawdź czy sensor `sensor.bateria_temperatura_maksymalna` zwraca wartość liczbową
- Sprawdź logi: `tail -f /config/home-assistant.log | grep -i temp`

### Problem 3: Moc ładowania nie zmienia się
**Rozwiązanie:**
- Sprawdź czy `number.akumulatory_maksymalna_moc_ladowania` jest dostępne
- Sprawdź czy algorytm wykonuje się co godzinę (automacja)
- Sprawdź logi: `grep "set_huawei_mode" /config/home-assistant.log`

### Problem 4: Błąd Python "AttributeError"
**Rozwiązanie:**
- Upewnij się że wszystkie sensory w `collect_input_data()` istnieją
- Dodaj fallback dla brakujących sensorów

## 📊 Monitorowanie efektywności

Po tygodniu użytkowania sprawdź:

1. **Historia temperatury:**
   ```sql
   -- Developer Tools → Statistics
   SELECT * FROM states
   WHERE entity_id = 'sensor.bateria_temperatura_maksymalna'
   ORDER BY last_updated DESC LIMIT 100;
   ```

2. **Historia limitów mocy:**
   - Sprawdź czy limity są stosowane w odpowiednich zakresach temperatur
   - Czy bateria nie przegrzewa się podczas ładowania

3. **Bilans energetyczny:**
   - Czy nowe limity wpływają na efektywność ładowania
   - Czy temperatura baterii jest stabilniejsza

## ⚠️ Uwagi bezpieczeństwa

1. **NIE WYŁĄCZAJ** mechanizmu bezpieczeństwa - chroni baterię przed uszkodzeniem
2. **Jeśli temperatura przekracza 43°C często** - skontaktuj się z serwisem Huawei
3. **W przypadku temperatury > 50°C** - natychmiast odłącz baterię i wezwij serwis
4. **Zimą (< 0°C)** - bateria może pracować wolniej, to normalne

## 🔄 Rollback (przywrócenie starej wersji)

Jeśli coś pójdzie nie tak:

```bash
# Przywróć backupy
cp config/python_scripts/battery_algorithm.py.backup config/python_scripts/battery_algorithm.py
cp config/input_text.yaml.backup config/input_text.yaml

# Restart Home Assistant
ha core restart
```

## 📝 Changelog

**v1.0 - Trzystopniowa ochrona temperaturowa**
- ✅ Dodano 5 poziomów bezpieczeństwa (zamiast 2)
- ✅ Inteligentne ograniczenie mocy ładowania (zamiast STOP/GO)
- ✅ Ochrona przed mrozem (< 5°C)
- ✅ Dozwolone rozładowanie przy wysokiej temperaturze (pomaga schłodzić)
- ✅ Wizualizacja statusu na dashboardzie

---

**Autor:** Claude Code
**Data:** 2025-11-17
**Wersja:** 1.0
