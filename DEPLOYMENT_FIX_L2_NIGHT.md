# 🔧 WDROŻENIE: Fix trybu baterii w nocy L2

**Branch:** `claude/fix-l2-tariff-mode-014CJT6v5HsTKVYMdECVgnjU`
**Commit:** `2f7d99c`
**Data:** 2025-11-17
**Priorytet:** 🔴 WYSOKI (bug w produkcji - bateria traci energię w nocy)

---

## 📋 OPIS PROBLEMU

### Symptomy:
W nocy L2 (22:00-06:00), gdy bateria osiągnęła Target SOC:
- ❌ Tryb: **"Maximise Self Consumption"** zamiast **"Taryfa Luna 2000"**
- ❌ Moc rozładowania: **5000W** zamiast **0W**
- ❌ Ładowanie z sieci: **OFF** ✓ (ok)
- ❌ **Bateria rozładowywała się w nocy**, tracąc energię zamiast zachować ją na drogi L1

### Przyczyna:
Logika w `decide_strategy()` przechodziła do `handle_power_deficit()` → `discharge_to_home`,
który nie blokował rozładowania baterii w nocy L2.

### Wpływ:
- Strata ~2-5 kWh w nocy (rozładowanie baterii zamiast zachowania)
- Brak oszczędności w L1 następnego dnia
- Bateria może spaść poniżej Target SOC przed świtem

---

## ✅ ROZWIĄZANIE

Dodano specjalną obsługę dla nocy L2 gdy `soc >= target_soc`:

**Lokalizacja:** `config/python_scripts/battery_algorithm.py:283-290`

```python
# NOC L2 - specjalna obsługa gdy bateria już naładowana
# Jeśli jesteśmy w nocy L2 i bateria >= Target SOC, to BLOKUJ rozładowanie
if tariff == 'L2' and hour in [22, 23, 0, 1, 2, 3, 4, 5] and soc >= target_soc:
    return {
        'mode': 'grid_to_home',
        'priority': 'normal',
        'reason': f'Noc L2, bateria naładowana ({soc:.0f}% >= {target_soc}%) - zachowaj na L1, blokuj rozładowanie (moc 0W)'
    }
```

### Efekt po wdrożeniu:
- ✅ Tryb: **"Taryfa Luna 2000"**
- ✅ Moc rozładowania: **0W** (bateria nie rozładowuje się!)
- ✅ Ładowanie z sieci: **OFF** (bo już naładowana)
- ✅ Dom pobiera z sieci (tanie 0.72 zł/kWh)
- ✅ Bateria zachowana na drogi L1 (1.11 zł/kWh)

---

## 🚀 WDROŻENIE

### Środowisko:
- **Raspberry Pi 4** (`marekbodynek@192.168.0.106`)
- **Home Assistant Core** w Docker
- **Katalog:** `/home/marekbodynek/home-assistant-huawei`

### Krok 1: Backup (WYMAGANE!)

```bash
# SSH do Raspberry Pi
ssh marekbodynek@192.168.0.106

# Backup aktualnej wersji
cd /home/marekbodynek/home-assistant-huawei
cp config/python_scripts/battery_algorithm.py config/python_scripts/battery_algorithm.py.backup-$(date +%Y%m%d-%H%M%S)

# Weryfikuj backup
ls -lh config/python_scripts/battery_algorithm.py.backup-*
```

### Krok 2: Pobranie zmian

```bash
cd /home/marekbodynek/home-assistant-huawei

# Sprawdź aktualny branch
git status

# Pobierz zmiany
git fetch origin

# Merge fixa
git pull origin claude/fix-l2-tariff-mode-014CJT6v5HsTKVYMdECVgnjU
```

### Krok 3: Weryfikacja kodu

```bash
# Sprawdź czy zmiana jest na miejscu (linie 283-290)
sed -n '283,290p' config/python_scripts/battery_algorithm.py
```

**Oczekiwany output:**
```python
    # NOC L2 - specjalna obsługa gdy bateria już naładowana
    # Jeśli jesteśmy w nocy L2 i bateria >= Target SOC, to BLOKUJ rozładowanie
    if tariff == 'L2' and hour in [22, 23, 0, 1, 2, 3, 4, 5] and soc >= target_soc:
        return {
            'mode': 'grid_to_home',
            'priority': 'normal',
            'reason': f'Noc L2, bateria naładowana ({soc:.0f}% >= {target_soc}%) - zachowaj na L1, blokuj rozładowanie (moc 0W)'
        }
```

### Krok 4: Restart Home Assistant

**Opcja A: Przez UI (zalecane)**
```
1. Otwórz Home Assistant: http://192.168.0.106:8123
2. Settings → System → Restart
3. Poczekaj ~30 sekund na restart
```

**Opcja B: Przez SSH**
```bash
# Restart kontenera HA (jeśli w Docker)
docker restart homeassistant

# LUB restart serwisu (jeśli systemd)
sudo systemctl restart home-assistant@homeassistant
```

### Krok 5: Weryfikacja działania

**A. Sprawdź logi HA (opcjonalne)**
```bash
# Logi Home Assistant
docker logs -f homeassistant | grep battery_algorithm

# Szukaj błędów
docker logs homeassistant --since 5m | grep -i error
```

**B. Sprawdź dashboard HA**
```
1. Otwórz: http://192.168.0.106:8123
2. Przejdź do dashboardu z baterią
3. Sprawdź pole "battery_decision_reason"
4. Sprawdź "Tryb pracy baterii"
```

**C. Test ręczny (opcjonalnie - jeśli nie jest noc L2)**
```
1. Home Assistant → Developer Tools → Services
2. Service: python_script.battery_algorithm
3. Call Service
4. Sprawdź input_text.battery_decision_reason
```

---

## ✅ WERYFIKACJA W PRODUKCJI

### Test 1: Noc L2 (22:00-06:00) - Bateria >= Target SOC

**Warunki:**
- Godzina: 22:00-05:59
- Strefa taryfowa: L2
- SOC >= Target SOC (np. 65% >= 65%)

**Oczekiwane zachowanie:**
```
Dashboard → battery_decision_reason:
"Noc L2, bateria naładowana (XX% >= YY%) - zachowaj na L1, blokuj rozładowanie (moc 0W)"

Tryb baterii: "Taryfa Luna 2000"
Moc rozładowania: 0W
Ładowanie z sieci: OFF
```

### Test 2: Noc L2 - Bateria < Target SOC

**Warunki:**
- Godzina: 22:00-05:59
- Strefa taryfowa: L2
- SOC < Target SOC (np. 45% < 65%)

**Oczekiwane zachowanie:**
```
Dashboard → battery_decision_reason:
"Noc L2 + ... - ładuj do XX%"

Tryb baterii: "Taryfa Luna 2000"
Ładowanie z sieci: ON
Limit SOC: Target SOC (XX%)
```

### Test 3: Dzień L1 - Bez wpływu fixa

**Warunki:**
- Godzina: 06:00-22:00
- Strefa taryfowa: L1

**Oczekiwane zachowanie:**
```
Normalny algorytm autoconsumption (bez zmian)
```

---

## 🔄 ROLLBACK (w razie problemów)

### Opcja A: Przywróć backup

```bash
cd /home/marekbodynek/home-assistant-huawei

# Listuj backupy
ls -lh config/python_scripts/battery_algorithm.py.backup-*

# Przywróć ostatni backup
cp config/python_scripts/battery_algorithm.py.backup-YYYYMMDD-HHMMSS config/python_scripts/battery_algorithm.py

# Restart HA
docker restart homeassistant
```

### Opcja B: Git revert

```bash
cd /home/marekbodynek/home-assistant-huawei

# Wróć do poprzedniego commita
git revert 2f7d99c

# Restart HA
docker restart homeassistant
```

---

## 📊 MONITORING PO WDROŻENIU

### Metryki do obserwacji (przez 3 dni):

1. **Noc L2 (22:00-06:00)**
   - SOC o 22:00 vs SOC o 06:00 → różnica powinna być ~0-2% (nie 10-15%!)
   - Tryb baterii: "Taryfa Luna 2000"
   - Moc rozładowania: 0W

2. **Dzień L1 (06:00-22:00)**
   - SOC spadek z wykorzystania baterii
   - Oszczędności na L1 (kWh × 1.11 zł)

3. **Logi błędów**
   ```bash
   docker logs homeassistant --since 24h | grep -i "battery_algorithm\|error"
   ```

### Spodziewane oszczędności:
- **Przed fixem:** Bateria traciła ~2-5 kWh w nocy L2 (rozładowanie)
- **Po fixie:** Bateria utrzymuje SOC w nocy L2 (strata max 0-2 kWh na samoodpowietrzenie)
- **Korzyść:** ~3-5 kWh × 1.11 zł/kWh = **~3-6 zł/dzień oszczędności**

---

## 📝 CHANGELOG

### `config/python_scripts/battery_algorithm.py`

**Dodano:** Linie 283-290
```diff
+    # NOC L2 - specjalna obsługa gdy bateria już naładowana
+    # Jeśli jesteśmy w nocy L2 i bateria >= Target SOC, to BLOKUJ rozładowanie
+    if tariff == 'L2' and hour in [22, 23, 0, 1, 2, 3, 4, 5] and soc >= target_soc:
+        return {
+            'mode': 'grid_to_home',
+            'priority': 'normal',
+            'reason': f'Noc L2, bateria naładowana ({soc:.0f}% >= {target_soc}%) - zachowaj na L1, blokuj rozładowanie (moc 0W)'
+        }
+
```

**Zmieniono:** Linia 270 (dodano `hour = data['hour']`)
```diff
     tariff = data['tariff_zone']
+    hour = data['hour']
```

---

## ❓ FAQ

### Q: Co jeśli bateria ma 64% a Target SOC to 65% o 23:00?
**A:** Fix NIE zadziała (warunek: `soc >= target_soc`). Algorytm uruchomi ładowanie do 65%.

### Q: Czy fix wpływa na weekend/święta (L2 przez całą dobę)?
**A:** NIE. Warunek `hour in [22, 23, 0, 1, 2, 3, 4, 5]` działa tylko w nocy.
Weekend/święta obsługuje poprzedni warunek (linia 276).

### Q: Czy fix działa w godzinach 13-15 (L2 w dzień)?
**A:** NIE. Warunek dotyczy tylko nocy `[22, 23, 0, 1, 2, 3, 4, 5]`.

### Q: Co jeśli SOC spadnie poniżej Target SOC w nocy (np. z 65% do 64%)?
**A:** Algorytm wykryje to w następnym cyklu (co 1h) i uruchomi ładowanie do Target SOC.

---

## 🎯 CHECKLIST WDROŻENIA

- [ ] Backup pliku `battery_algorithm.py`
- [ ] Git pull z branch `claude/fix-l2-tariff-mode-014CJT6v5HsTKVYMdECVgnjU`
- [ ] Weryfikacja kodu (linie 283-290)
- [ ] Restart Home Assistant
- [ ] Sprawdzenie logów (brak błędów)
- [ ] Test w następnej nocy L2 (22:00-06:00)
- [ ] Monitoring przez 3 dni
- [ ] Merge do `main` po weryfikacji

---

## 📞 KONTAKT

**W razie problemów:**
- Przywróć backup
- Restart HA
- Sprawdź logi: `docker logs homeassistant --since 1h`
- Zgłoś issue na GitHub

**Autor:** Claude Code
**Commit:** `2f7d99c`
**Branch:** `claude/fix-l2-tariff-mode-014CJT6v5HsTKVYMdECVgnjU`
