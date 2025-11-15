# Cloudflare Tunnel - Quick Start (5 kroków)

## Krok 1: Utwórz tunnel w Cloudflare

1. Idź na: https://one.dash.cloudflare.com/
2. Menu: **Networks → Tunnels**
3. Kliknij **Create a tunnel**
4. Nazwa: `home-assistant-tunnel`
5. **SKOPIUJ TOKEN** z ekranu instalacji (długi ciąg znaków po `--token`)

## Krok 2: Dodaj Public Hostname

1. W tunelu kliknij **Public Hostname** → **Add a public hostname**
2. Subdomain: `ha`
3. Domain: twoja domena (musi być już w Cloudflare)
4. Type: `HTTP`
5. URL: `homeassistant:8123`
6. Save

## Krok 3: Edytuj docker-compose.yml

Otwórz `docker-compose.yml` i odkomentuj sekcję `cloudflared`:

```yaml
  cloudflared:
    container_name: cloudflared
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    command: tunnel --no-autoupdate run --token TWOJ_TOKEN_TUTAJ
    depends_on:
      - homeassistant
```

Zamień `TWOJ_TOKEN_TUTAJ` na token z Kroku 1.

## Krok 4: Uruchom

```bash
ssh marekbodynek@192.168.0.106
cd ~/home-assistant-huawei
git pull
docker-compose down
docker-compose up -d
docker logs cloudflared
```

Poczekaj na: `INF Connection registered` (pojawi się 4 razy)

## Krok 5: Testuj

Otwórz w przeglądarce: `https://ha.twojadomena.pl`

## Gotowe!

Szczegółowa instrukcja: zobacz [CLOUDFLARE_TUNNEL_SETUP.md](CLOUDFLARE_TUNNEL_SETUP.md)

## Potrzebujesz pomocy?

**Problem:** Nie mam domeny
- Rozwiązanie: Kup domenę u dowolnego rejestratora (OVH, nazwa.pl, GoDaddy) lub użyj darmowej (Freenom)
- Dodaj domenę do Cloudflare (Free plan)

**Problem:** Tunnel pokazuje "Unhealthy"
```bash
docker logs cloudflared -f
# Sprawdź błędy, prawdopodobnie zły token
```

**Problem:** 502 Bad Gateway
```bash
# Sprawdź czy HA działa
docker ps
docker logs homeassistant
```

**Problem:** Nie mogę się połączyć
1. Sprawdź DNS: `nslookup ha.twojadomena.pl` - powinno pokazać Cloudflare IP
2. Sprawdź status tunelu w Cloudflare Dashboard
3. Sprawdź Public Hostname - URL musi być `homeassistant:8123`
