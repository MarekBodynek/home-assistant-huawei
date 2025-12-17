# Chat Session - 2025-12-17 (sesja 2)

## Podsumowanie sesji

Kontynuacja pracy nad systemem Home Assistant + Huawei Solar. Główny temat: problemy z integracją Aquarea Smart Cloud.

---

## 1. Problem: CWU nie uruchomiło się o 13:00

### Diagnoza
Użytkownik zgłosił, że harmonogram CWU z Aquarea Cloud nie zadziałał o 13:00.

### Analiza logów
```
12:06-12:08 → Internal server error, Failed communication with adaptor
14:06 → TOKEN_EXPIRED - Token expires
```

### Przyczyna
- Integracja Aquarea Smart Cloud traciła połączenie z serwerami Panasonic
- Harmonogram CWU jest w chmurze Panasonic, nie w HA
- Awaria komunikacji = harmonogram nie zadziałał

### Stan CWU po diagnozie
- Temperatura wody: 41°C
- Temperatura cel: 55°C
- Stan: off (nie grzeje)

---

## 2. Rozwiązanie: Watchdog Aquarea

**Automatyzacja:** `aquarea_watchdog_token`

### Działanie:
- Uruchamia się co godzinę o :47
- Sprawdza czy `water_heater.bodynek_nb_tank` jest `unavailable`
- Jeśli tak → przeładowuje integrację Aquarea
- Powiadomienia o statusie naprawy

### Parametry:
| Parametr | Wartość |
|----------|---------|
| Entry ID | `01KCFK1ETFE13JR1S6C97PT0QY` |
| Częstotliwość | Co godzinę o :47 |
| Timeout naprawy | 30 sekund |

---

## 3. Rozwiązanie: CWU backup harmonogram 13:02

**Automatyzacja:** `cwu_scheduled_1300`

### Działanie:
- Backup harmonogramu chmury Panasonic
- Uruchamia się o 13:02 (2 min po harmonogramie chmury)
- Sprawdza:
  - Integracja dostępna?
  - CWU nie grzeje? (chmura nie zadziałała)
  - Temp < cel?
- Włącza wymuszenie CWU
- Wyłącza gdy temp >= cel lub po 2h (timeout)

### Logika:
```
13:00 → Harmonogram Panasonic Cloud
13:02 → Backup HA:
        ├─ CWU grzeje? → skip (chmura zadziałała)
        └─ CWU nie grzeje + temp < cel? → włącz wymuszenie
```

---

## 4. Obliczenia czasu grzania CWU

| Parametr | Wartość |
|----------|---------|
| Zbiornik | 385 litrów |
| Pompa | 9 kW (Panasonic T-CAP) |
| ΔT | 20°C (35→55°C) |
| Energia | 8.96 kWh |

### Czas grzania:
| Scenariusz | Moc | Czas |
|------------|-----|------|
| Pełna moc | 9 kW | ~1h |
| 70% mocy | 6.3 kW | ~1h 25min |
| 50% mocy | 4.5 kW | ~2h |

**Timeout 2h** - bezpieczny margines dla trybu CWU.

---

## 5. Pliki zmodyfikowane w sesji

| Plik | Zmiany |
|------|--------|
| `config/automations_battery.yaml` | Watchdog Aquarea, CWU harmonogram 13:02 |
| `docs/DOKUMENTACJA_KOMPLETNA.md` | v3.13, sekcje 4.6-4.7, changelog |
| `docs/DOKUMENTACJA_KOMPLETNA_PUBLIC.md` | v3.13, zanonimizowana wersja |
| `docs/chat.md` | Podsumowanie sesji |

---

## 6. Komendy użyte w sesji

### Sprawdzanie logów Aquarea
```bash
ssh -o ProxyCommand="cloudflared access ssh --hostname rpi-ssh.bodino.us.kg" bodino@rpi-ssh.bodino.us.kg \
  "sudo docker logs homeassistant --since='2025-12-17T12:00:00' 2>&1 | grep -i aquarea"
```

### Upload i restart HA
```bash
scp -o ProxyCommand="cloudflared access ssh --hostname rpi-ssh.bodino.us.kg" \
  config/automations_battery.yaml bodino@rpi-ssh.bodino.us.kg:~/homeassistant/
ssh ... "sudo docker restart homeassistant"
```

---

## 7. Aktualny stan systemu (na koniec sesji)

- **Integracja Aquarea:** Działa po restarcie HA
- **Watchdog:** Aktywny (sprawdza co :47)
- **CWU backup:** Aktywny (uruchamia o 13:02)
- **Dokumentacja:** v3.13

---

**Koniec sesji: 2025-12-17**
