# DARMOWA Domena na ZAWSZE + Cloudflare Tunnel

## 🎯 Najlepsza opcja: NIC.US.KG (POLECAM!)

**100% darmowa domena `.us.kg` na zawsze**

### Zalety:
✅ Całkowicie darmowa - na zawsze (nie trial, nie promo)
✅ Odnawiana automatycznie co rok
✅ Działa z Cloudflare
✅ Maksymalnie 3 domeny na konto
✅ Szybka akceptacja (zwykle kilka minut do 24h)
✅ Prowadzona przez non-profit DigitalPlat Foundation
✅ Sponsorowana przez: Cloudflare, GitHub, 1Password, Twilio

### Minusy:
⚠️ Końcówka .us.kg (nie .com ani .pl)
⚠️ Wymaga weryfikacji KYC (BEZ uploadowania dokumentów!)
⚠️ Tylko wybrane emaile: Gmail, Outlook, Yahoo, iCloud, Hotmail, Zoho, Yandex

---

## 📝 INSTRUKCJA KROK PO KROKU

### Etap 1: Zarejestruj darmową domenę

1. **Wejdź na**: https://nic.us.kg/
2. **Kliknij**: "Register a new domain" lub "Sign Up"
3. **Podaj email** (musi być: Gmail, Outlook, Yahoo, iCloud, Hotmail, Zoho lub Yandex)
4. **Sprawdź email** - kliknij link aktywacyjny
5. **Uzupełnij KYC** (weryfikacja tożsamości):
   - Podaj imię i nazwisko
   - NIE MUSISZ uploadować dokumentów!
   - To tylko formularz weryfikacyjny
6. **Wybierz nazwę domeny**, np:
   - `mojeha.us.kg`
   - `homeassistant.us.kg`
   - `smart-home.us.kg`
   - `dom-marek.us.kg`
7. **Poczekaj na akceptację** (zwykle kilka minut do 24h)
8. **Email potwierdzający** - otrzymasz informację że domena została przydzielona

### Etap 2: Dodaj domenę do Cloudflare

1. **Zaloguj się do Cloudflare**: https://dash.cloudflare.com/
   - Jeśli nie masz konta - załóż (darmowe)
2. **Kliknij**: "Add a Site"
3. **Wpisz**: Twoją domenę (np. `mojeha.us.kg`)
4. **Wybierz plan**: Free
5. **Skopiuj nameservery** z Cloudflare, np:
   ```
   carla.ns.cloudflare.com
   hugh.ns.cloudflare.com
   ```

### Etap 3: Zmień nameservery w NIC.US.KG

1. **Zaloguj się**: https://nic.us.kg/
2. **Moje domeny** → wybierz swoją domenę
3. **Nameservers** → "Custom Nameservers"
4. **Wklej nameservery** z Cloudflare (z Etapu 2)
5. **Zapisz**
6. **Poczekaj 5-30 minut** na propagację DNS

### Etap 4: Weryfikuj w Cloudflare

1. **Wróć do Cloudflare Dashboard**
2. **Sprawdź status** domeny - powinien zmienić się na "Active"
3. **Jeśli nie**: Kliknij "Recheck nameservers"

### Etap 5: Utwórz Cloudflare Tunnel

1. **W Cloudflare Dashboard** przejdź do: https://one.dash.cloudflare.com/
2. **Menu**: Networks → Tunnels
3. **Kliknij**: Create a tunnel
4. **Typ**: Cloudflared
5. **Nazwa**: `home-assistant-tunnel`
6. **SKOPIUJ TOKEN** (bardzo długi ciąg znaków po `--token`)
   - Przykład: `eyJhbGci...bardzo_długi_ciąg...`
   - **WAŻNE**: Skopiuj cały token do bezpiecznego miejsca!

### Etap 6: Skonfiguruj Public Hostname

1. **W tym samym tunelu**: Zakładka "Public Hostname"
2. **Kliknij**: "Add a public hostname"
3. **Wypełnij**:
   - **Subdomain**: `ha` (lub zostaw puste dla głównej domeny)
   - **Domain**: Wybierz swoją domenę z listy (np. `mojeha.us.kg`)
   - **Path**: zostaw puste
   - **Type**: `HTTP`
   - **URL**: `homeassistant:8123`
4. **Save**

Twój Home Assistant będzie pod: `https://ha.mojeha.us.kg` (lub `https://mojeha.us.kg` jeśli nie dodałeś subdomeny)

### Etap 7: Aktualizuj docker-compose.yml

**Powiedz mi token z Etapu 5**, a ja automatycznie:
1. Zaktualizuję docker-compose.yml
2. Zcommituję do GitHub
3. Spulluję na serwer
4. Uruchomię tunnel
5. Sprawdzę logi
6. Przetestuję połączenie

**Albo zrób ręcznie:**

```bash
ssh marekbodynek@192.168.0.106
cd ~/home-assistant-huawei
nano docker-compose.yml
```

Znajdź sekcję cloudflared i zamień:

```yaml
  cloudflared:
    container_name: cloudflared
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    command: tunnel --no-autoupdate run --token TUTAJ_WKLEJ_SWÓJ_TOKEN
    depends_on:
      - homeassistant
```

Zapisz (Ctrl+O, Enter, Ctrl+X)

### Etap 8: Uruchom

```bash
docker compose down
docker compose up -d
docker logs cloudflared
```

Poszukaj:
```
INF Connection registered connIndex=0
INF Connection registered connIndex=1
INF Connection registered connIndex=2
INF Connection registered connIndex=3
```

### Etap 9: Konfiguruj Home Assistant

1. **Lokalnie**: http://192.168.0.106:8123
2. **Settings** → **System** → **Network**
3. **Home Assistant URL**:
   - **Internet**: `https://ha.mojeha.us.kg` (Twoja domena!)
   - **Local Network**: `http://192.168.0.106:8123`
4. **Save**

### ✅ GOTOWE!

Otwórz `https://ha.mojeha.us.kg` z dowolnego miejsca na świecie!

---

## 🔄 Alternatywa: EU.ORG (jeśli us.kg nie działa)

**Darmowa domena `.eu.org` na zawsze**

### Jak zarejestrować:

1. **Wejdź**: https://nic.eu.org/
2. **Create Account** → podaj email
3. **Wypełnij formularz rejestracji domeny**
4. **Poczekaj na akceptację** - może zająć 1-7 dni (wolniejsze niż us.kg)
5. **Zmień nameservery na Cloudflare** (jak w us.kg)
6. **Reszta identycznie** jak dla us.kg

**Minusy EU.ORG:**
- Dłuższa akceptacja (dni zamiast godzin)
- Wymaga więcej informacji przy rejestracji
- Bardziej rygorystyczne zasady użytkowania

**Zalety:**
- Bardziej znana końcówka (.eu.org vs .us.kg)
- Działają od 1996 roku (bardzo stabilne)

---

## ⚡ Co mogę zrobić ZA CIEBIE:

**Powiedz mi tylko:**
1. Jaką nazwę domeny wybrałeś? (np. `mojeha.us.kg`)
2. Czy zarejestrowałeś już domenę w nic.us.kg?
3. Czy dodałeś ją do Cloudflare?
4. Jaki token otrzymałeś z Cloudflare Tunnel?

**A ja automatycznie:**
✅ Skonfiguruję docker-compose.yml z Twoim tokenem
✅ Zcommituję do GitHub
✅ Spulluję na serwer
✅ Uruchomię wszystkie kontenery
✅ Sprawdzę logi
✅ Przetestuję czy działa
✅ Dam Ci gotowy link do Twojego HA!

**Oszczędzisz 90% czasu!**

---

## 🆘 Troubleshooting

### Domena nie została zaakceptowana
- Sprawdź czy email jest z dozwolonych (Gmail, Outlook, etc.)
- Sprawdź spam - link aktywacyjny mógł trafić do spamu
- Poczekaj 24h - czasem zajmuje to dłużej
- Spróbuj eu.org jako alternatywę

### Nameservery nie propagują się
```bash
# Sprawdź DNS
nslookup mojeha.us.kg

# Jeśli pokazuje Cloudflare IP - działa!
# Jeśli nie - poczekaj jeszcze 30 minut
```

### Tunnel nie łączy się
```bash
# Sprawdź logi
docker logs cloudflared -f

# Jeśli widzisz "authentication failed" - zły token
# Wygeneruj nowy token w Cloudflare Dashboard
```

### 502 Bad Gateway
```bash
# HA nie działa
docker logs homeassistant

# Sprawdź czy kontenery są w tej samej sieci
docker network inspect home-assistant-huawei_default
```

---

## 💰 Koszty

**US.KG lub EU.ORG:** 0 zł (darmowe na zawsze)
**Cloudflare:** 0 zł (plan Free wystarczy)
**Łącznie:** 0 zł/rok

**vs. Płatna domena .pl:** ~30 zł/rok

---

## 📌 Gotowy do konfiguracji?

**Zarejestruj domenę na nic.us.kg i daj mi znać!**

Mogę zrobić resztę za Ciebie - wystarczy że podasz token z Cloudflare Tunnel.
