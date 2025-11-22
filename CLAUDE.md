# CLAUDE.md - Wytyczne dla Claude Code

## Projekt: Home Assistant Huawei Solar Battery Management

System zarządzania baterią Huawei LUNA 2000 z optymalizacją kosztów energii.

## Struktura projektu

- `config/` - Konfiguracja Home Assistant
  - `automations/` - Automatyzacje (battery algorithm, notifications)
  - `template_sensors.yaml` - Sensory obliczeniowe
  - `packages/` - Pakiety konfiguracji
- `docs/` - Dokumentacja

## Wymagania testowe

- **Pisz testy dla wszystkich nowych funkcji** chyba że wyraźnie powiedziano inaczej
- **Uruchamiaj testy przed commitem** aby zapewnić jakość i poprawność kodu
- Użyj `npm run test` aby zweryfikować że wszystkie testy przechodzą przed commitem
- Testy powinny pokrywać zarówno happy path jak i edge cases dla nowych funkcjonalności

## Kluczowe sensory

- `sensor.rce_pse_cena` - Cena energii RCE PSE (PLN/MWh, dzielić przez 1000)
- `sensor.akumulatory_stan_pojemnosci` - SOC baterii (%)
- `sensor.prognoza_pv_dzisiaj` - Prognoza produkcji PV (kWh)
- `sensor.strefa_taryfowa` - Aktualna strefa (L1/L2)

## Dostęp do Mac Mini

- SSH via Cloudflare: `ssh ssh.bodino.us.kg`
- User: `marekbodynek`
- HA config path: `/Users/marekbodynek/home-assistant-huawei/config`
- Docker: `/Applications/Docker.app/Contents/Resources/bin/docker`

## Commit conventions

Używaj emoji na początku commit message:
- `🔧` - Fix
- `📊` - Dokumentacja/dashboard
- `🔋` - Bateria/algorytm
- `🌡️` - Temperatura
- `🔢` - Formatowanie/liczby
- `🔄` - Zmiana integracji
