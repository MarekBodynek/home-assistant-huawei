# Prompt dla Claude Code - Nowa instalacja

Użyj tego promptu w nowej instancji Claude Code, aby zainstalować system zarządzania baterią Huawei Solar.

---

## Prompt

```
Zainstaluj system zarządzania baterią Huawei Solar według instrukcji w pliku:
docs/INSTRUKCJA_NOWA_INSTALACJA.md

Repozytorium: https://github.com/MarekBodynek/home-assistant-huawei

PARAMETRY DO DOSTOSOWANIA (podaj przed rozpoczęciem):
- Lokalizacja GPS: [szerokość, długość geograficzna]
- Instalacja PV: [moc kWp, liczba paneli na każdą orientację]
- Pojemność baterii: [kWh]
- Taryfa: G12w / G12 / G11

KROKI:
1. Sklonuj repozytorium
2. Przeczytaj całą instrukcję docs/INSTRUKCJA_NOWA_INSTALACJA.md
3. Dostosuj parametry w plikach konfiguracyjnych
4. Zainstaluj wymagane integracje HACS
5. Skopiuj pliki do /config Home Assistant
6. Zrestartuj HA i zweryfikuj sensory

Instrukcja zawiera kompletny kod wszystkich plików - skopiuj i dostosuj.
```

---

## Przykład użycia

```
Zainstaluj system zarządzania baterią Huawei Solar według instrukcji w pliku:
docs/INSTRUKCJA_NOWA_INSTALACJA.md

Repozytorium: https://github.com/MarekBodynek/home-assistant-huawei

PARAMETRY:
- Lokalizacja GPS: 52.2297, 21.0122 (Warszawa)
- Instalacja PV: 10 kWp, 25 paneli (15 południe, 10 wschód)
- Pojemność baterii: 10 kWh (LUNA 2000-10)
- Taryfa: G12w

Wykonaj pełną instalację według instrukcji.
```

---

## Co zawiera instrukcja

1. **Kompletny kod** wszystkich plików konfiguracyjnych
2. **Parametry do zmiany** - lista wartości do dostosowania
3. **Integracje HACS** - które zainstalować i jak skonfigurować
4. **Dashboard** - tabela cen RCE z kolorowymi kropkami
5. **Troubleshooting** - rozwiązywanie typowych problemów

## Link do instrukcji

https://github.com/MarekBodynek/home-assistant-huawei/blob/main/docs/INSTRUKCJA_NOWA_INSTALACJA.md
