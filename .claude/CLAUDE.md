# CLAUDE.md - Wytyczne dla Claude Code

## Projekt: Home Assistant Huawei Solar Battery Management

System zarządzania baterią Huawei LUNA 2000 z optymalizacją kosztów energii.

## Na start sesji

**WAŻNE:** Na początku każdej nowej sesji przeczytaj:
- `docs/DOKUMENTACJA_KOMPLETNA.md` - historia zmian, znane problemy, konfiguracja
- `docs/chat.md` - podsumowanie ostatniej sesji (kontekst rozmowy)

## Zasady pracy Claude Code

  1.	Najpierw przemyśl problem, przeczytaj bazę kodu i znajdź odpowiednie pliki, a następnie zapisz plan działania w pliku tasks/todo.md.
	2.	Plan powinien zawierać listę zadań, które można odznaczać w miarę ich realizacji.
	3.	Zanim zaczniesz pracę, skonsultuj plan ze mną — potwierdzę, czy jest poprawny.
	4.	Następnie rozpocznij realizację zadań, oznaczając je jako ukończone w miarę postępów.
	5.	Na każdym etapie przedstawiaj mi ogólne, wysokopoziomowe wyjaśnienie, jakie zmiany zostały wprowadzone.
	6.	Każde zadanie i każda zmiana w kodzie powinny być możliwie najprostsze. Unikaj skomplikowanych lub dużych zmian. Każda zmiana powinna wpływać na jak najmniejszą część kodu. Wszystko ma być maksymalnie uproszczone.
	7.	Na końcu dodaj sekcję review do pliku todo.md z podsumowaniem wprowadzonych zmian i innymi istotnymi informacjami.
	8.	NIE BĄDŹ LENIWY. NIGDY NIE BĄDŹ LENIWY. JEŚLI WYSTĘPUJE BŁĄD — ZNAJDŹ PRAWDZIWĄ PRZYCZYNĘ I GO NAPRAW. ŻADNYCH TYMCZASOWYCH ROZWIĄZAŃ. ŻADNYCH ROZWIĄZAŃ NA SKRÓTY JESTEŚ STARSZYM PROGRAMISTĄ (SENIOR DEVELOPER). NIGDY NIE BĄDŹ LENIWY.
	9.	WSZYSTKIE POPRAWKI I ZMIANY W KODZIE MAJĄ BYĆ TAK PROSTE, JAK TO TYLKO MOŻLIWE. MAJĄ WPŁYWAĆ WYŁĄCZNIE NA KOD ISTOTNY DLA ZADANIA I NIC PONADTO. TWOIM CELEM JEST NIE WPROWADZAĆ NOWYCH BŁĘDÓW. LICZY SIĘ TYLKO PROSTOTA.
	10.	**PRACUJ AUTONOMICZNIE.** Zawsze wykonuj zadania sam, wykorzystując wszystkie dostępne narzędzia (SSH, API, curl, SCP, itp.). NIE dawaj użytkownikowi instrukcji do wykonania ręcznie, jeśli możesz to zrobić sam. Jeśli coś wymaga instalacji, konfiguracji, restartu - zrób to sam przez SSH/API. Pytaj użytkownika TYLKO wtedy, gdy:
		- Brakuje Ci uprawnień lub dostępu, którego nie da się obejść
		- Wypróbowałeś wszystkie możliwe metody i żadna nie zadziałała
	11.	**DECYZJE BIZNESOWE ZAWSZE KONSULTUJ.** Nigdy nie podejmuj samodzielnie decyzji biznesowych (np. który wariant wybrać, jaka architektura, jakie priorytety). Zawsze przedstaw opcje użytkownikowi i poczekaj na jego decyzję przed implementacją.


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

## Dostęp do Raspberry Pi 5 (Home Assistant)

| Parametr | Wartość |
|----------|---------|
| User | `bodino` |
| Hasło | `Keram1qazXSW@` |
| IP lokalne | `192.168.0.188` |
| IP Tailscale | `100.112.174.109` |
| Hostname Cloudflare | `rpi-ssh.bodino.us.kg` |
| Home Assistant URL | `https://ha.bodino.us.kg` |

### SSH przez Cloudflare (z dowolnego miejsca):
```bash
ssh -o ProxyCommand="cloudflared access ssh --hostname rpi-ssh.bodino.us.kg" bodino@rpi-ssh.bodino.us.kg
```

### Ścieżki na RPi:
- HA config: `/home/bodino/homeassistant/`
- Docker: `sudo docker`

### Komendy zarządzania HA:
```bash
# Status
sudo docker ps | grep homeassistant

# Logi
sudo docker logs homeassistant -f

# Restart
sudo docker restart homeassistant

# Wgranie zmian config (po edycji plików)
scp -o ProxyCommand="cloudflared access ssh --hostname rpi-ssh.bodino.us.kg" config/*.yaml bodino@rpi-ssh.bodino.us.kg:~/homeassistant/
sudo docker restart homeassistant
```

## Dostęp do Mac Mini (backup, Jellyfin)

| Parametr | Wartość |
|----------|---------|
| User | `marekbodynek` |
| Hasło | `Keram1qazXSW@3edcV` |
| IP lokalne | `192.168.0.106` |
| IP Tailscale | `100.103.147.52` |
| Hostname Cloudflare | `macmini-ssh.bodino.us.kg` |

### SSH przez Cloudflare:
```bash
ssh -o ProxyCommand="cloudflared access ssh --hostname macmini-ssh.bodino.us.kg" marekbodynek@macmini-ssh.bodino.us.kg
```

### Ścieżki na Mac Mini:
- Repozytorium: `/Users/marekbodynek/home-assistant-huawei/`
- Docker: `/Applications/Docker.app/Contents/Resources/bin/docker`

## Dokumentacja

**WAŻNE:** Przy każdej zmianie dokumentacji aktualizuj OBA pliki:
- `docs/DOKUMENTACJA_KOMPLETNA.md` - pełna wersja (z danymi osobowymi)
- `docs/DOKUMENTACJA_KOMPLETNA_PUBLIC.md` - zanonimizowana wersja (do udostępnienia)

Zanonimizowane dane w wersji PUBLIC:
- `Marek Bodynek` → `[Autor]`
- `marek.bodynek@gmail.com` → `your.email@example.com`
- `marekbodynek` → `username`
- `bodino.us.kg` → `example.com`
- `192.168.0.106` → `192.168.x.x`

## Commit conventions

Używaj emoji na początku commit message:
- `🔧` - Fix
- `📊` - Dokumentacja/dashboard
- `🔋` - Bateria/algorytm
- `🌡️` - Temperatura
- `🔢` - Formatowanie/liczby
- `🔄` - Zmiana integracji
- `📚` - Dokumentacja
