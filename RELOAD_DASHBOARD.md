# Jak przeładować dashboard po zmianach

## Problem znaleziony
Dashboard używał nieprawidłowej składni `layout: { type: grid, columns: 3 }` która NIE jest wspierana przez Home Assistant natywnie. To powodowało że HA ignorował ustawienia layoutu i używał domyślnego masonry layout.

## Rozwiązanie
Przepisałem dashboard używając natywnych **grid cards** do kontroli układu kart.

## Struktura nowego dashboardu
- **Rząd 1**: Pogoda (karta weather-forecast, pełna szerokość)
- **Rząd 2**: Grid card z 3 kolumnami (Sezon grzewczy | Produkcja | Bateria)
- **Rząd 3**: Grid card z 3 kolumnami (Prognoza PV | Wymiana | Tryb pracy)
- **Rząd 4**: Grid card z 2 kolumnami (Ceny energii | Historia mocy)

## Jak załadować zmiany do Home Assistant

### Opcja 1: Przez SSH (jeśli masz dostęp)
```bash
# Połącz się z serwerem HA
ssh root@192.168.0.106

# Przejdź do katalogu config
cd /config

# Pobierz najnowsze zmiany z Git
git pull

# Przeładuj konfigurację Lovelace (opcjonalnie)
# Możesz też zrestartować HA lub przeładować przez UI
```

### Opcja 2: Przez webowy interfejs HA (ZALECANE)
1. Otwórz Home Assistant w przeglądarce
2. Przejdź do **Ustawienia** → **System** → **Konfiguracja YAML**
3. Kliknij **Przeładuj konfigurację Lovelace** (lub podobna opcja)
4. Jeśli nie ma takiej opcji, zrestartuj Home Assistant

### Opcja 3: Przeładowanie dashboard
1. Otwórz dashboard Huawei Solar PV
2. Kliknij trzy kropki (⋮) w prawym górnym rogu
3. Wybierz **Odśwież** lub **Przeładuj**
4. Jeśli to nie pomoże, wyczyść cache przeglądarki (CTRL+SHIFT+R)

### Opcja 4: Restart Home Assistant
Najprostszy sposób - po prostu zrestartuj Home Assistant:
1. **Ustawienia** → **System** → **Restart**
2. Poczekaj aż system się zrestartuje
3. Otwórz dashboard ponownie

## Sprawdzenie czy działa
Po przeładowaniu dashboard powinien wyglądać tak:
- **Pierwszy rząd**: Pogoda na pełną szerokość
- **Drugi rząd**: 3 karty obok siebie (Sezon | Produkcja | Bateria)
- **Trzeci rząd**: 3 karty obok siebie (Prognoza | Wymiana | Tryb)
- **Czwarty rząd**: 2 karty obok siebie (Ceny | Historia)

Jeśli nadal widzisz stary układ, spróbuj:
1. Wyczyść cache przeglądarki (CTRL+SHIFT+R)
2. Sprawdź czy zmiany zostały pobrane z Git (`git log` powinien pokazać commit "Przepisano dashboard na natywne grid cards")
3. Zrestartuj Home Assistant ponownie

## Co zostało zmienione
- ❌ Usunięto: `layout: { type: grid, columns: 3 }` (nieprawidłowa składnia)
- ❌ Usunięto: `view_layout: { grid-column: 1 / -1 }` (wymaga custom card)
- ✅ Dodano: Grid cards z parametrem `columns` do kontroli układu
- ✅ Dodano: `square: false` żeby karty miały naturalną wysokość

Wszystkie zmiany są już w repozytorium Git (commit b73028d).
