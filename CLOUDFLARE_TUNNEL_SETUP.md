# Cloudflare Tunnel - Pełna Instrukcja Konfiguracji

## Etap 1: Przygotowanie domeny w Cloudflare

1. **Zaloguj się do Cloudflare**: https://dash.cloudflare.com/
2. **Dodaj swoją domenę** (jeśli jeszcze nie dodana):
   - Kliknij "Add a Site"
   - Wpisz nazwę domeny (np. `twojastrona.pl`)
   - Wybierz plan Free
   - Skopiuj nameservery z Cloudflare
   - Zmień nameservery u swojego rejestratora domeny na te z Cloudflare
   - Poczekaj na propagację DNS (może zająć do 24h, zwykle 1-2h)

## Etap 2: Utwórz Cloudflare Tunnel

1. **Przejdź do Zero Trust Dashboard**: https://one.dash.cloudflare.com/
2. **Jeśli to pierwsze użycie**:
   - Kliknij "Get started" i podaj nazwę dla swojego zespołu (np. "Home")
   - Wybierz plan Free
3. **Utwórz tunnel**:
   - W menu lewym wybierz: **Networks** → **Tunnels**
   - Kliknij **Create a tunnel**
   - Wybierz **Cloudflared** jako typ
   - Wpisz nazwę tunelu (np. `home-assistant-tunnel`)
   - Kliknij **Save tunnel**

## Etap 3: Skopiuj Token

Po utworzeniu tunelu zobaczysz ekran z instrukcjami instalacji.

**WAŻNE:** Skopiuj cały token z komendy instalacji. Token wygląda tak:

```
cloudflared tunnel --token eyJhbGci...bardzo_długi_ciąg_znaków...
```

**Skopiuj TYLKO token** (część po `--token`), np:
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2NvdW50X3RhZyI6IjEyMzQ1Njc4OTAiLCJjcmVkZW50aWFsX3RhZyI6IjEyMzQ1Njc4OTAiLCJ0dW5uZWxfaWQiOiIxMjM0NTY3OC0xMjM0LTEyMzQtMTIzNC0xMjM0NTY3ODkwMTIifQ.abcdefghijklmnopqrstuvwxyz1234567890
```

## Etap 4: Konfiguracja Public Hostname

1. **Na ekranie tunelu przejdź do zakładki "Public Hostname"**
2. **Kliknij "Add a public hostname"**
3. **Wypełnij formularz**:
   - **Subdomain**: `ha` (lub inna nazwa, np. `home`)
   - **Domain**: Wybierz swoją domenę z listy (np. `twojastrona.pl`)
   - **Path**: zostaw puste
   - **Type**: `HTTP`
   - **URL**: `homeassistant:8123` (nazwa serwisu z docker-compose)
4. **Kliknij "Save hostname"**

Twój Home Assistant będzie dostępny pod adresem: `https://ha.twojastrona.pl`

## Etap 5: Aktualizacja docker-compose.yml

Po uzyskaniu tokena, zaktualizuj plik `docker-compose.yml`:

```yaml
services:
  homeassistant:
    container_name: homeassistant
    image: "ghcr.io/home-assistant/home-assistant:stable"
    volumes:
      - ./config:/config
      - /etc/localtime:/etc/localtime:ro
    restart: unless-stopped
    privileged: true
    ports:
      - "8123:8123"
    environment:
      - TZ=Europe/Warsaw

  cloudflared:
    container_name: cloudflared
    image: cloudflare/cloudflared:latest
    restart: unless-stopped
    command: tunnel --no-autoupdate run --token TU_WSTAW_TOKEN
    depends_on:
      - homeassistant
```

**Zamień `TU_WSTAW_TOKEN`** na token skopiowany w Etapie 3.

## Etap 6: Uruchomienie

1. **Zatrzymaj obecne kontenery**:
```bash
ssh marekbodynek@192.168.0.106
cd ~/home-assistant-huawei
docker-compose down
```

2. **Uruchom z nową konfiguracją**:
```bash
docker-compose up -d
```

3. **Sprawdź logi cloudflared**:
```bash
docker logs cloudflared
```

Powinieneś zobaczyć:
```
INF Connection registered connIndex=0
INF Connection registered connIndex=1
INF Connection registered connIndex=2
INF Connection registered connIndex=3
```

## Etap 7: Konfiguracja Home Assistant

1. **Zaloguj się do HA lokalnie**: http://192.168.0.106:8123
2. **Przejdź do**: Settings → System → Network
3. **W sekcji "Home Assistant URL"**:
   - **Internet**: Wpisz `https://ha.twojastrona.pl`
   - **Local Network**: Zostaw `http://192.168.0.106:8123`

## Etap 8: Testowanie

1. **Z sieci lokalnej**: Otwórz `https://ha.twojastrona.pl`
2. **Z telefonu (wyłącz WiFi)**: Otwórz `https://ha.twojastrona.pl`
3. **Skonfiguruj aplikację mobilną**:
   - Otwórz Home Assistant Companion
   - Dodaj serwer: `https://ha.twojastrona.pl`
   - Zaloguj się

## Troubleshooting

### Tunnel nie działa
```bash
# Sprawdź logi
docker logs cloudflared -f

# Jeśli widzisz błąd autoryzacji - token jest nieprawidłowy
# Wygeneruj nowy token w Cloudflare Dashboard
```

### 502 Bad Gateway
```bash
# Sprawdź czy HA działa
docker logs homeassistant -f

# Sprawdź czy kontenery są w tej samej sieci
docker network inspect home-assistant-huawei_default
```

### Nie mogę się połączyć z zewnątrz
1. Sprawdź czy tunnel pokazuje status "Healthy" w Cloudflare Dashboard
2. Sprawdź czy Public Hostname jest prawidłowo skonfigurowany
3. Sprawdź czy domena jest poprawnie skonfigurowana w Cloudflare

## Bezpieczeństwo

Cloudflare Tunnel automatycznie zapewnia:
- ✅ Szyfrowanie TLS (HTTPS)
- ✅ Ochronę DDoS
- ✅ Firewall WAF (Web Application Firewall)
- ✅ Brak potrzeby otwierania portów w routerze
- ✅ Ukrycie prawdziwego IP serwera

## Co dalej?

Po skonfigurowaniu możesz dodać:
1. **Zasady dostępu** w Cloudflare Zero Trust (np. tylko z Polski)
2. **Uwierzytelnianie wieloskładnikowe** przed HA
3. **Rate limiting** dla dodatkowej ochrony
4. **Więcej subdomen** dla innych usług (np. `grafana.twojastrona.pl`)
