# 🚀 INSTRUKCJE WDROŻENIA - Fix: Target SOC Charging

**Branch:** `claude/fix-target-soc-charging-012QQLrBxYShrL6sUbZQpgw6`
**Commit:** `e04df42`
**Data:** 2025-11-17
**Autor:** Claude Code

---

## 📋 PODSUMOWANIE ZMIAN

### Problem 1: System nie zatrzymywał ładowania przy Target SOC
- **Przyczyna:** Algorytm ustawiał `charge_soc_limit`, ale polegał na inwenterze Huawei, który mógł przekraczać Target SOC
- **Rozwiązanie:** Dodano explicite zatrzymanie ładowania w `execute_strategy()` gdy SOC >= Target SOC

### Problem 2: Bug warunku L2 + SOC >= 40 blokował ładowanie w dni powszednie
- **Przyczyna:** Warunek `tariff == 'L2' and soc >= 40` działał też w dni powszednie (22:00-05:59), blokując ładowanie
- **Rozwiązanie:** Dodano sprawdzenie `binary_sensor.dzien_roboczy` - warunek działa TYLKO w weekendy/święta

### Zmienione pliki:
- `config/python_scripts/battery_algorithm.py` (37 linii dodanych, 1 usunięta)

---

## 🔧 INSTRUKCJE WDROŻENIA NA PRODUKCJĘ

### Krok 1: Backup obecnej konfiguracji

```bash
# SSH do Home Assistant
sshpass -p 'Keram1qazXSW@' ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no marekbodynek@192.168.0.106

# Backup obecnego pliku
cd /config/python_scripts/
cp battery_algorithm.py battery_algorithm.py.backup_$(date +%Y%m%d_%H%M%S)
ls -lh battery_algorithm.py*
```

### Krok 2: Pull zmian z GitHub

```bash
# Przejdź do katalogu config
cd /config

# Sprawdź obecny branch i status
git status
git branch

# Fetch zmian z GitHub
git fetch origin claude/fix-target-soc-charging-012QQLrBxYShrL6sUbZQpgw6

# Checkout do brancha z fixem
git checkout claude/fix-target-soc-charging-012QQLrBxYShrL6sUbZQpgw6

# Pull najnowszych zmian
git pull origin claude/fix-target-soc-charging-012QQLrBxYShrL6sUbZQpgw6

# Sprawdź czy plik się zmienił
git log -1 --stat
```

### Krok 3: Weryfikacja zmian

```bash
# Sprawdź składnię Python
python3 -m py_compile /config/python_scripts/battery_algorithm.py
echo "✅ Składnia OK" || echo "❌ Błąd składni!"

# Sprawdź różnice względem backupu
diff battery_algorithm.py.backup_* battery_algorithm.py | head -50
```

### Krok 4: Restart Python Scripts

```bash
# Wywołaj restart Home Assistant przez API (lub restart core z UI)
# Opcja 1: Restart całego Home Assistant (bezpieczniejsze)
curl -X POST -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
     -H "Content-Type: application/json" \
     http://localhost:8123/api/services/homeassistant/restart

# Opcja 2: Reload tylko Python Scripts (szybsze, ale może nie załadować zmian)
# W Home Assistant UI: Ustawienia → Serwer → YAML → ZAŁADUJ PONOWNIE: Python Scripts
```

### Krok 5: Manualne uruchomienie algorytmu

Po restarcie (po ~2 minutach):

```bash
# Wywołaj algorytm ręcznie przez API
curl -X POST -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
     -H "Content-Type: application/json" \
     http://localhost:8123/api/services/python_script/battery_algorithm
```

---

## 🧪 TESTY DO WYKONANIA

### Test 1: Zatrzymanie ładowania przy Target SOC

**Scenariusz:**
1. Ustaw Target SOC na 70% (`input_number.battery_target_soc`)
2. Uruchom ładowanie (nocą L2 lub ręcznie)
3. Monitoruj SOC - czy zatrzymuje się przy 70%?

**Oczekiwany rezultat:**
- ✅ Ładowanie zatrzymuje się przy SOC >= 70%
- ✅ `switch.akumulatory_ladowanie_z_sieci` przełącza się na OFF
- ✅ `number.akumulatory_maksymalna_moc_ladowania` ustawia się na 0W
- ✅ `input_text.battery_decision_reason` pokazuje: "✅ Target SOC osiągnięty (70% >= 70%) - ZATRZYMANO ładowanie"

**Weryfikacja:**
```bash
# Sprawdź stan sensora decision_reason
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
     http://localhost:8123/api/states/input_text.battery_decision_reason | python3 -m json.tool
```

### Test 2: Ładowanie w dni powszednie (fix buga L2 + SOC >= 40)

**Scenariusz:**
1. Dzień roboczy (poniedziałek-piątek)
2. Godzina 22:00-05:59 (noc L2)
3. SOC = 45% (czyli >= 40)
4. Target SOC = 70%

**Przed fixem:**
- ❌ Warunek `tariff == 'L2' and soc >= 40` zwracał `mode='grid_to_home'`
- ❌ Bateria NIE ładowała się (blokada!)
- ❌ SOC pozostawał na 45%, nigdy nie osiągał 70%

**Po fixie:**
- ✅ Warunek sprawdza `not is_workday` → FALSE (dzień roboczy)
- ✅ Przechodzi do `should_charge_from_grid()`
- ✅ Bateria ładuje się do Target SOC (70%)

**Weryfikacja:**
```bash
# Sprawdź sensor dzień roboczy
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
     http://localhost:8123/api/states/binary_sensor.dzien_roboczy | python3 -m json.tool

# Sprawdź czy ładowanie aktywne
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
     http://localhost:8123/api/states/switch.akumulatory_ladowanie_z_sieci | python3 -m json.tool
```

### Test 3: Weekend/święto - oszczędzanie baterii (bug NIE powinien wpływać)

**Scenariusz:**
1. Weekend (sobota/niedziela) lub święto
2. SOC = 50% (czyli >= 40)
3. Tariff = L2 (całą dobę 24h)

**Oczekiwany rezultat:**
- ✅ Warunek `tariff == 'L2' and soc >= 40 and not is_workday` → TRUE
- ✅ Zwraca `mode='grid_to_home'`
- ✅ Reason: "L2 niedziela/święto (tania 0.72 zł) - pobieraj z sieci, oszczędzaj baterię na poniedziałek"

---

## 📊 MONITORING PO WDROŻENIU

### Kluczowe sensory do obserwacji:

1. **`input_text.battery_decision_reason`**
   - Czy pojawia się komunikat "✅ Target SOC osiągnięty"?

2. **`sensor.akumulatory_stan_pojemnosci`**
   - Czy zatrzymuje się przy Target SOC (nie przekracza o więcej niż 2-3%)?

3. **`switch.akumulatory_ladowanie_z_sieci`**
   - Czy wyłącza się przy osiągnięciu Target SOC?

4. **`number.akumulatory_maksymalna_moc_ladowania`**
   - Czy ustawia się na 0W przy Target SOC?
   - Czy wraca na 5000W w kolejnym cyklu?

5. **Logi Home Assistant:**
   ```bash
   # Sprawdź logi algorytmu
   tail -f /config/home-assistant.log | grep -i "battery\|algorytm\|target"
   ```

### Dashboard do monitorowania:

W Lovelace dodaj kartę (opcjonalnie):

```yaml
type: entities
title: 🔍 Monitoring Target SOC Fix
entities:
  - entity: sensor.akumulatory_stan_pojemnosci
  - entity: input_number.battery_target_soc
  - entity: switch.akumulatory_ladowanie_z_sieci
  - entity: number.akumulatory_maksymalna_moc_ladowania
  - entity: input_text.battery_decision_reason
  - entity: binary_sensor.dzien_roboczy
  - entity: sensor.strefa_taryfowa
```

---

## 🔄 ROLLBACK PLAN (gdyby coś poszło nie tak)

### Opcja 1: Przywrócenie backupu

```bash
# SSH do Home Assistant
sshpass -p 'Keram1qazXSW@' ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no marekbodynek@192.168.0.106

cd /config/python_scripts/

# Znajdź backup
ls -lh battery_algorithm.py.backup_*

# Przywróć backup (zastąp YYYYMMDD_HHMMSS datą backupu)
cp battery_algorithm.py.backup_YYYYMMDD_HHMMSS battery_algorithm.py

# Restart Home Assistant
curl -X POST -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
     -H "Content-Type: application/json" \
     http://localhost:8123/api/services/homeassistant/restart
```

### Opcja 2: Git revert

```bash
cd /config

# Checkout do poprzedniego commita
git checkout HEAD~1 -- python_scripts/battery_algorithm.py

# Lub checkout do głównego brancha (jeśli istnieje)
git checkout main python_scripts/battery_algorithm.py

# Restart Home Assistant
```

### Opcja 3: Manualne wyłączenie algorytmu (awaryjne)

```bash
# Wyłącz automatyzację wykonywania algorytmu
curl -X POST -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
     -H "Content-Type: application/json" \
     -d '{"entity_id": "automation.bateria_wykonaj_strategie_co_1h"}' \
     http://localhost:8123/api/services/automation/turn_off

# Ustaw tryb awaryjny - Maximise Self Consumption
curl -X POST -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
     -H "Content-Type: application/json" \
     -d '{"entity_id": "select.akumulatory_tryb_pracy", "option": "maximise_self_consumption"}' \
     http://localhost:8123/api/services/select/select_option
```

---

## ⚠️ POTENCJALNE PROBLEMY I ROZWIĄZANIA

### Problem 1: Sensor `binary_sensor.dzien_roboczy` nie istnieje

**Objawy:** Błąd w logach: "Entity not found: binary_sensor.dzien_roboczy"

**Rozwiązanie:**
```bash
# Sprawdź czy sensor istnieje
curl -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
     http://localhost:8123/api/states/binary_sensor.dzien_roboczy

# Jeśli nie istnieje, dodaj do configuration.yaml:
# binary_sensor:
#   - platform: workday
#     country: PL
#     name: "Dzień roboczy"
```

### Problem 2: Algorytm nie działa (żadne decyzje)

**Objawy:** `input_text.battery_decision_reason` nie aktualizuje się

**Rozwiązanie:**
```bash
# Sprawdź logi
tail -100 /config/home-assistant.log | grep -i "error\|exception\|battery"

# Sprawdź czy python_script działa
ls -lh /config/python_scripts/battery_algorithm.py

# Spróbuj ręcznie uruchomić
curl -X POST -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
     -H "Content-Type: application/json" \
     http://localhost:8123/api/services/python_script/battery_algorithm
```

### Problem 3: Moc ładowania nie przywraca się na 5000W

**Objawy:** `number.akumulatory_maksymalna_moc_ladowania` pozostaje na 0W

**Rozwiązanie:**
```bash
# Ręcznie ustaw na 5000W
curl -X POST -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
     -H "Content-Type: application/json" \
     -d '{"entity_id": "number.akumulatory_maksymalna_moc_ladowania", "value": 5000}' \
     http://localhost:8123/api/services/number/set_value

# Sprawdź logikę w kodzie (linia 86-92)
```

---

## 📝 CHECKLIST WDROŻENIA

- [ ] Backup obecnej konfiguracji
- [ ] Pull zmian z GitHub
- [ ] Weryfikacja składni Python
- [ ] Restart Home Assistant / Python Scripts
- [ ] Test 1: Zatrzymanie ładowania przy Target SOC
- [ ] Test 2: Ładowanie w dni powszednie (SOC >= 40)
- [ ] Test 3: Weekend/święto - oszczędzanie baterii
- [ ] Monitoring przez 24h
- [ ] Sprawdzenie logów pod kątem błędów
- [ ] Dokumentacja wdrożenia (data, wyniki testów)

---

## 📞 KONTAKT W RAZIE PROBLEMÓW

- **GitHub Issue:** https://github.com/MarekBodynek/home-assistant-huawei/issues
- **Branch:** `claude/fix-target-soc-charging-012QQLrBxYShrL6sUbZQpgw6`
- **Commit:** `e04df42`

---

## 🎯 EXPECTED OUTCOMES

Po pomyślnym wdrożeniu:

1. ✅ Bateria zatrzymuje ładowanie precyzyjnie przy Target SOC (np. 70%)
2. ✅ Brak przekraczania Target SOC (max +1-2% przez opóźnienie sensora)
3. ✅ Ładowanie w dni powszednie działa poprawnie niezależnie od SOC
4. ✅ Weekend/święta - strategia oszczędzania baterii działa jak wcześniej
5. ✅ Dashboard pokazuje komunikat "✅ Target SOC osiągnięty"
6. ✅ Moc ładowania wraca automatycznie na 5000W w kolejnym cyklu

---

**Powodzenia w wdrożeniu! 🚀**

---

_Dokument wygenerowany przez Claude Code_
_Data: 2025-11-17_
