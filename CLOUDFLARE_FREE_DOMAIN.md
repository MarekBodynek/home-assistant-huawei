# Cloudflare Tunnel - DARMOWA Subdomena (bez własnej domeny!)

## Zalety tego rozwiązania:
✅ **Całkowicie darmowe** - nie potrzebujesz kupować domeny
✅ **Gotowe w 2 minuty** - nie trzeba konfigurować DNS
✅ **Automatyczny HTTPS** - Cloudflare zajmuje się certyfikatami
✅ **Nie wymaga konta Cloudflare** - działa od razu
✅ **Losowy URL** - np. `https://abc-def-123.trycloudflare.com`

## Minusy:
⚠️ URL zmienia się po każdym restarcie kontenera
⚠️ URL jest losowy (nie możesz wybrać nazwy)
⚠️ Brak zaawansowanych opcji (firewall, rate limiting)

---

## Instalacja (SUPER SZYBKA - 3 kroki!)

### Krok 1: Uruchom tunnel

```bash
ssh marekbodynek@192.168.0.106
cd ~/home-assistant-huawei
git pull
docker-compose down
docker-compose up -d
```

### Krok 2: Sprawdź URL

```bash
docker logs cloudflared
```

Poszukaj linii:
```
INF +--------------------------------------------------------------------------------------------+
INF |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
INF |  https://abc-def-123.trycloudflare.com                                                      |
INF +--------------------------------------------------------------------------------------------+
```

**To jest Twój adres!** Skopiuj go.

### Krok 3: Skonfiguruj Home Assistant

1. Otwórz lokalnie: http://192.168.0.106:8123
2. Settings → System → Network
3. **Home Assistant URL**:
   - **Internet**: Wklej adres z logów (np. `https://abc-def-123.trycloudflare.com`)
   - **Local Network**: Zostaw `http://192.168.0.106:8123`
4. Kliknij **Save**

### Gotowe! 🎉

Otwórz adres z logów w przeglądarce lub aplikacji mobilnej.

---

## Jak znaleźć URL po restarcie?

Jeśli zrestartowałeś Docker, URL się zmieni. Aby znaleźć nowy:

```bash
docker logs cloudflared | grep trycloudflare.com
```

Albo:

```bash
docker logs cloudflared --tail 50
```

---

## Jak zrobić URL stały (nie zmienia się)?

Musisz użyć **Named Tunnel** z własną domeną. Masz 3 opcje:

### Opcja A: Tania domena (~30 zł/rok)

**Polecane domeny:**
- **.pl** - ~30 zł/rok (OVH, nazwa.pl, home.pl)
- **.com.pl** - ~20 zł/rok
- **.eu** - ~15 zł/rok (niektórzy rejestratorzy)

**Gdzie kupić:**
1. **OVH.pl** - https://www.ovhcloud.com/pl/domains/
2. **nazwa.pl** - https://www.nazwa.pl/
3. **home.pl** - https://home.pl/domeny

**Po zakupie:**
- Dodaj domenę do Cloudflare (Free plan)
- Użyj instrukcji z `CLOUDFLARE_TUNNEL_SETUP.md`

### Opcja B: Darmowa domena (ograniczenia)

⚠️ **Uwaga**: Większość darmowych domen ma problemy:
- Freenom (.tk, .ml, .ga, .cf, .gq) - często blokowane przez Cloudflare
- afraid.org - tylko subdomeny, niewiele opcji
- No-IP - głównie do DDNS, nie do Cloudflare Tunnel

**Nie polecam** - lepiej zapłacić 30 zł/rok za stabilną domenę .pl

### Opcja C: DuckDNS (dla zaawansowanych)

Możesz użyć DuckDNS + Let's Encrypt zamiast Cloudflare Tunnel:
- Darmowa subdomena `.duckdns.org`
- Wymaga otworzenia portów w routerze (443)
- Wymaga konfiguracji certyfikatów SSL w HA
- Bardziej skomplikowane, ale działa

---

## Troubleshooting

### Nie widzę URL w logach

```bash
# Sprawdź czy kontener działa
docker ps | grep cloudflared

# Jeśli nie działa, sprawdź błędy
docker logs cloudflared --tail 100
```

### 502 Bad Gateway

```bash
# Sprawdź czy HA działa
docker ps | grep homeassistant
docker logs homeassistant --tail 50
```

### URL nie działa po kilku dniach

Quick Tunnel może wygasnąć po dłuższym czasie. Restart:

```bash
docker restart cloudflared
docker logs cloudflared | grep trycloudflare.com
```

---

## Rekomendacja

**Dla testów (teraz):** Użyj Quick Tunnel (darmowa subdomena)
**Na dłużej:** Kup tanią domenę .pl za ~30 zł/rok i skonfiguruj Named Tunnel

Named Tunnel z własną domeną daje:
✅ Stały URL (nie zmienia się)
✅ Własna nazwa (np. `ha.mojdom.pl`)
✅ Firewall i ochrona DDoS
✅ Logi dostępu
✅ Możliwość dodania więcej subdomen

---

## Potrzebujesz pomocy z domeną?

Jeśli kupisz domenę, powiedz mi - skonfiguruję Named Tunnel automatycznie!

**Potrzebne będzie tylko:**
1. Nazwa domeny
2. Token z Cloudflare Dashboard (dam Ci dokładne kroki)

Koszt: **~30 zł/rok** (mniej niż 3 zł/miesiąc) za pełną kontrolę i stabilność.
