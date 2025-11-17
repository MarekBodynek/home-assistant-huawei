# 🚀 Instrukcja wdrożenia: Fix parametrów baterii w L1

## 📋 Informacje o zmianie

**Branch:** `claude/fix-l1-status-change-01F4LFsBpwQq8TP3hqbNxxgK`
**Commit:** `a914a0a`
**Plik:** `config/python_scripts/battery_algorithm.py`

**Problem:** Po zmianie strefy L2→L1 o 15:00 status zmieniał się poprawnie na "SOC 80%, nadwyżka PV - sprzedaj", ale parametry baterii nie były aktualizowane.

**Rozwiązanie:** Dodano obsługę `max_charge_power` w funkcji `set_huawei_mode()` oraz poprawiono tryb dla `discharge_to_grid`.

---

## ⚠️ WAŻNE - Przed wdrożeniem

1. **Backup konfiguracji:**
   ```bash
   ssh marekbodynek@192.168.0.106
   cd /config
   cp python_scripts/battery_algorithm.py python_scripts/battery_algorithm.py.backup_$(date +%Y%m%d_%H%M%S)
   ```

2. **Sprawdź czy Home Assistant działa:**
   ```bash
   curl -s -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8123/api/ | python3 -m json.tool
   ```

---

## 🔧 WERSJA A: Wdrożenie przez Git Pull (ZALECANA)

### Krok 1: Zaloguj się na serwer Home Assistant

```bash
ssh marekbodynek@192.168.0.106
```

### Krok 2: Przejdź do katalogu repozytorium

```bash
cd /home/marekbodynek/home-assistant-huawei
# LUB (jeśli repo jest w innej lokalizacji)
cd /config
```

### Krok 3: Sprawdź aktualny branch i status

```bash
git status
git branch
```

### Krok 4: Pobierz najnowsze zmiany z GitHub

```bash
# Fetch wszystkich zmian
git fetch origin

# Sprawdź czy branch istnieje
git branch -r | grep claude/fix-l1-status-change
```

### Krok 5: Przełącz się na branch z fixem

```bash
git checkout claude/fix-l1-status-change-01F4LFsBpwQq8TP3hqbNxxgK
git pull origin claude/fix-l1-status-change-01F4LFsBpwQq8TP3hqbNxxgK
```

### Krok 6: Zweryfikuj zmiany

```bash
# Sprawdź czy plik został zmieniony
git log -1 --stat

# Zobacz zmiany w pliku
git diff HEAD~1 config/python_scripts/battery_algorithm.py
```

### Krok 7: Restart Home Assistant

**Opcja 1: Przez API** (szybsza, bez logowania)
```bash
curl -X POST \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
  http://localhost:8123/api/services/homeassistant/restart
```

**Opcja 2: Przez UI** (bezpieczniejsza)
1. Wejdź na: http://192.168.0.106:8123
2. Settings → System → Restart Home Assistant

**Opcja 3: Reload Python Scripts** (najszybsza - NIE wymaga restartu HA!)
```bash
curl -X POST \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
  http://localhost:8123/api/services/python_script/reload
```

---

## 🔧 WERSJA B: Wdrożenie przez skopiowanie pliku (ALTERNATYWNA)

Jeśli git pull nie działa lub repozytorium nie jest skonfigurowane na serwerze HA:

### Krok 1: Skopiuj zaktualizowany plik

**Z lokalnego repo do Home Assistant:**
```bash
# Na swoim komputerze (gdzie masz sklonowane repo)
cd /home/user/home-assistant-huawei
scp config/python_scripts/battery_algorithm.py \
    marekbodynek@192.168.0.106:/config/python_scripts/battery_algorithm.py
```

### Krok 2: Zweryfikuj na serwerze

```bash
ssh marekbodynek@192.168.0.106
ls -lh /config/python_scripts/battery_algorithm.py
```

### Krok 3: Reload Python Scripts

```bash
curl -X POST \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
  http://localhost:8123/api/services/python_script/reload
```

---

## ✅ WERYFIKACJA WDROŻENIA

### 1. Sprawdź czy algorytm działa

```bash
# Uruchom algorytm ręcznie
curl -X POST \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
  -H "Content-Type: application/json" \
  -d '{}' \
  http://localhost:8123/api/services/python_script/battery_algorithm
```

### 2. Sprawdź status decyzji

```bash
curl -s -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
  http://localhost:8123/api/states/input_text.battery_decision_reason | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['state'])"
```

### 3. Sprawdź parametry baterii

```bash
# Maksymalna moc ładowania
curl -s -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
  http://localhost:8123/api/states/number.akumulatory_maksymalna_moc_ladowania | \
  python3 -c "import sys, json; print('Max moc ładowania:', json.load(sys.stdin)['state'], 'W')"

# Maksymalna moc rozładowania
curl -s -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
  http://localhost:8123/api/states/number.akumulatory_maksymalna_moc_rozladowania | \
  python3 -c "import sys, json; print('Max moc rozładowania:', json.load(sys.stdin)['state'], 'W')"

# Tryb pracy
curl -s -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
  http://localhost:8123/api/states/select.akumulatory_tryb_pracy | \
  python3 -c "import sys, json; print('Tryb pracy:', json.load(sys.stdin)['state'])"
```

### 4. Sprawdź logi Home Assistant

```bash
ssh marekbodynek@192.168.0.106
tail -f /config/home-assistant.log | grep -i "battery\|algorytm"
```

---

## 🧪 TEST SCENARIUSZA (po 15:00)

**Warunki testowe:**
- Godzina: 15:00-21:00 (strefa L1)
- SOC: ≥ 80%
- PV surplus: > 0 kW (nadwyżka słoneczna)

**Oczekiwane wartości:**

| Parametr | Oczekiwana wartość |
|----------|-------------------|
| Status decyzji | "SOC 80%, nadwyżka PV - sprzedaj" lub podobny |
| Tryb pracy | `maximise_self_consumption` |
| Max moc ładowania | `0` W |
| Max moc rozładowania | `5000` W |
| Ładowanie z sieci | `off` |

**Jak przetestować ręcznie:**

```bash
# 1. Ustaw SOC na 80% (tylko jeśli możesz bezpiecznie zmienić)
# 2. Poczekaj na godzinę 15:00 LUB uruchom algorytm ręcznie:

curl -X POST \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
  -H "Content-Type: application/json" \
  -d '{}' \
  http://localhost:8123/api/services/python_script/battery_algorithm

# 3. Sprawdź wszystkie parametry (komendy z sekcji WERYFIKACJA)
```

---

## 🔄 ROLLBACK (w razie problemów)

### Jeśli coś pójdzie nie tak:

**Opcja 1: Przywróć backup**
```bash
ssh marekbodynek@192.168.0.106
cd /config/python_scripts
ls -lh battery_algorithm.py.backup_*
cp battery_algorithm.py.backup_YYYYMMDD_HHMMSS battery_algorithm.py

# Reload
curl -X POST \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
  http://localhost:8123/api/services/python_script/reload
```

**Opcja 2: Przywróć poprzedni commit**
```bash
cd /home/marekbodynek/home-assistant-huawei
git log --oneline -5  # znajdź poprzedni commit
git checkout <previous_commit_hash> config/python_scripts/battery_algorithm.py
cp config/python_scripts/battery_algorithm.py /config/python_scripts/

# Reload
curl -X POST \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk" \
  http://localhost:8123/api/services/python_script/reload
```

---

## 📝 CHECKLIST WDROŻENIA

- [ ] Utworzono backup aktualnego pliku `battery_algorithm.py`
- [ ] Sprawdzono działanie Home Assistant przed zmianą
- [ ] Pobrano zmiany z GitHub (git pull) lub skopiowano plik
- [ ] Zweryfikowano zawartość pliku (git diff lub cat)
- [ ] Wykonano reload Python Scripts lub restart HA
- [ ] Uruchomiono algorytm ręcznie i sprawdzono logi
- [ ] Sprawdzono status decyzji algorytmu
- [ ] Zweryfikowano parametry baterii (max_charge, max_discharge, tryb)
- [ ] Sprawdzono logi Home Assistant pod kątem błędów
- [ ] Zaplanowano test o 15:00 przy odpowiednich warunkach
- [ ] Przygotowano plan rollback w razie problemów

---

## 📞 TROUBLESHOOTING

### Problem: `python_script.reload` nie działa

**Rozwiązanie:** Restart całego Home Assistant
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8123/api/services/homeassistant/restart
```

### Problem: Algorytm nie uruchamia się

**Sprawdź logi:**
```bash
tail -n 100 /config/home-assistant.log | grep -i error
```

**Sprawdź składnię Python:**
```bash
python3 -m py_compile /config/python_scripts/battery_algorithm.py
```

### Problem: Parametry baterii się nie zmieniają

**Sprawdź czy encje istnieją:**
```bash
curl -s -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8123/api/states | \
  python3 -m json.tool | grep -i "akumulatory_maksymalna"
```

### Problem: Git pull kończy się błędem

**Rozwiązanie:**
```bash
git stash  # Zachowaj lokalne zmiany
git pull origin claude/fix-l1-status-change-01F4LFsBpwQq8TP3hqbNxxgK
git stash pop  # Przywróć lokalne zmiany (jeśli potrzebne)
```

---

## 📅 HARMONOGRAM WDROŻENIA

**ZALECANY CZAS:**
- Najlepiej wieczorem (19:00-22:00) w strefie L1
- Lub rano (6:00-9:00) gdy SOC jest niski i bateria nie jest krytyczna dla domu

**UNIKAJ:**
- Okien CWU (04:30-06:00)
- Godzin szczytu (19:00-21:00) jeśli SOC < 30%
- Restartów w nocy w L2 podczas ładowania

---

## ✅ POTWIERDZENIE WDROŻENIA

Po pomyślnym wdrożeniu wyślij potwierdzenie z:

1. **Output z weryfikacji:**
   ```
   Status decyzji: [wartość]
   Max moc ładowania: [wartość]
   Max moc rozładowania: [wartość]
   Tryb pracy: [wartość]
   ```

2. **Screenshot dashboardu** (opcjonalnie)

3. **Wynik testu o 15:00** (po pierwszym pełnym cyklu)

---

**Pytania? Problemy?** Sprawdź logi i sekcję Troubleshooting powyżej.

**Sukces?** Gratulacje! Fix jest wdrożony i działający. 🎉
