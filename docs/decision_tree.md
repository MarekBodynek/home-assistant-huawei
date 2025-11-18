# Drzewo Decyzyjne Algorytmu Baterii

Data: 2025-11-18
Wersja: 3.2 (po fix L1 charging)

## Diagram Mermaid - Pełne Drzewo Decyzyjne

```mermaid
flowchart TD
    START([START: execute_strategy]) --> TEMP_CHECK{Temperatura<br/>bezpieczna?}

    TEMP_CHECK -->|OFF| TEMP_UNSAFE[🚨 ZATRZYMAJ ładowanie<br/>Ustaw moc=0W<br/>RETURN]
    TEMP_CHECK -->|ON| SOC_TARGET{SOC >= Target SOC?}

    SOC_TARGET -->|TAK| STOP_CHARGE[✅ Zatrzymaj ładowanie<br/>Przywróć moc=5000W]
    STOP_CHARGE --> CONTINUE[Kontynuuj dalej]
    SOC_TARGET -->|NIE| CONTINUE

    CONTINUE --> BALANCE[Oblicz bilans mocy:<br/>surplus vs deficit]
    BALANCE --> MAIN_DECISION[decide_strategy]

    MAIN_DECISION --> SOC_CRITICAL{SOC < 5%?}

    SOC_CRITICAL -->|TAK| EMERGENCY[🚨 KRYTYCZNE!<br/>charge_from_grid<br/>Target: 35%<br/>urgent_charge=True<br/>RETURN]

    SOC_CRITICAL -->|NIE| SOC_LOW{SOC < 20%?}

    SOC_LOW -->|TAK| URGENT[⚠️ PILNE!<br/>charge_from_grid<br/>Target: 20%<br/>Ładuj w L2<br/>RETURN]

    SOC_LOW -->|NIE| SOC_HIGH{SOC >= 80%?}

    SOC_HIGH -->|TAK| CHECK_TARIFF_HIGH{Taryfa?}
    CHECK_TARIFF_HIGH -->|L2| GRID_TO_HOME_L2[grid_to_home<br/>Oszczędzaj baterię<br/>RETURN]
    CHECK_TARIFF_HIGH -->|L1 + PV| DISCHARGE_GRID[discharge_to_grid<br/>Sprzedaj<br/>RETURN]
    CHECK_TARIFF_HIGH -->|L1 + brak PV| DISCHARGE_HOME[discharge_to_home<br/>RETURN]

    SOC_HIGH -->|NIE| WEEKEND{L2 + SOC≥40<br/>+ weekend/święto?}

    WEEKEND -->|TAK| SAVE_BATTERY[grid_to_home<br/>Oszczędzaj na poniedziałek<br/>RETURN]

    WEEKEND -->|NIE| L2_NIGHT{L2 NOC<br/>22-06h<br/>SOC<Target?}

    L2_NIGHT -->|TAK| L2_NIGHT_CHARGE[charge_from_grid<br/>Ładuj do Target<br/>Priorytet: zależy od<br/>prognozy jutro<br/>RETURN]

    L2_NIGHT -->|NIE| L2_MIDDAY{L2 POŁUDNIE<br/>13-14h<br/>SOC<80?}

    L2_MIDDAY -->|TAK| L2_MIDDAY_CHECK{Prognoza<5 kWh<br/>LUB<br/>SOC<Target?}

    L2_MIDDAY_CHECK -->|NIE| AUTOCONSUMPTION
    L2_MIDDAY_CHECK -->|TAK| PV_SURPLUS_HIGH{PV surplus<br/>>1.5 kW?}

    PV_SURPLUS_HIGH -->|TAK| CHARGE_PV_ONLY[charge_from_pv<br/>Magazynuj z PV<br/>darmowe!<br/>RETURN]

    PV_SURPLUS_HIGH -->|NIE| PV_SUFFICIENT{PV wystarczy<br/>do Target<br/>w czasie?}

    PV_SUFFICIENT -->|TAK| CHARGE_PV[charge_from_pv<br/>PV wystarczy<br/>RETURN]
    PV_SUFFICIENT -->|NIE| CHARGE_GRID_L2[charge_from_grid<br/>PV nie wystarczy<br/>uzupełnij z sieci<br/>RETURN]

    L2_MIDDAY -->|NIE| AUTOCONSUMPTION[AUTOCONSUMPTION<br/>logika]

    AUTOCONSUMPTION --> SURPLUS{Surplus > 0?}

    SURPLUS -->|TAK| HANDLE_SURPLUS[handle_pv_surplus]
    SURPLUS -->|NIE| DEFICIT{Deficit > 0?}

    DEFICIT -->|TAK| HANDLE_DEFICIT[handle_power_deficit]
    DEFICIT -->|NIE| IDLE_BALANCE[idle<br/>PV=Load<br/>RETURN]

    HANDLE_SURPLUS --> ARBITRAGE{Arbitraż<br/>opłacalny?}
    ARBITRAGE -->|TAK| DISCHARGE_ARBITRAGE[discharge_to_grid<br/>Sprzedaj<br/>RETURN]
    ARBITRAGE -->|NIE| HEATING{Sezon<br/>grzewczy?}

    HEATING -->|NIE| CHARGE_PV_SURPLUS[charge_from_pv<br/>Magazynuj nadwyżkę<br/>RETURN]

    HEATING -->|TAK| TARIFF_SURPLUS{Taryfa?}

    TARIFF_SURPLUS -->|L1| SOC_SURPLUS_L1{SOC > 20%?}
    SOC_SURPLUS_L1 -->|TAK| DISCHARGE_L1[discharge_to_home<br/>PC w L1 - oszczędzaj!<br/>RETURN]
    SOC_SURPLUS_L1 -->|NIE| IDLE_L1[idle<br/>SOC≤20% w L1<br/>CZEKAJ na L2!<br/>RETURN]

    TARIFF_SURPLUS -->|L2| CWU_WINDOW{CWU window?}
    CWU_WINDOW -->|TAK| SOC_CWU{SOC > 70%?}
    SOC_CWU -->|TAK| GRID_CWU[grid_to_home<br/>PC CWU w L2<br/>RETURN]
    SOC_CWU -->|NIE| CHARGE_CWU[charge_from_grid<br/>PC w L2<br/>doładuj<br/>RETURN]
    CWU_WINDOW -->|NIE| CHARGE_PV_L2[charge_from_pv<br/>Magazynuj<br/>RETURN]

    HANDLE_DEFICIT --> CHARGE_CHECK{should_charge<br/>_from_grid?}

    CHARGE_CHECK -->|TAK| CHARGE_DEFICIT[charge_from_grid<br/>RETURN]
    CHARGE_CHECK -->|NIE| CHECK_HEATING_DEFICIT{Sezon<br/>grzewczy?}

    CHECK_HEATING_DEFICIT -->|NIE| DISCHARGE_DEFICIT[discharge_to_home<br/>RETURN]

    CHECK_HEATING_DEFICIT -->|TAK| TARIFF_DEFICIT{Taryfa?}

    TARIFF_DEFICIT -->|L1| SOC_DEFICIT_L1{SOC > 20%?}
    SOC_DEFICIT_L1 -->|TAK| DISCHARGE_L1_DEF[discharge_to_home<br/>PC w L1<br/>RETURN]
    SOC_DEFICIT_L1 -->|NIE| IDLE_L1_DEF[idle<br/>SOC≤20% w L1<br/>CZEKAJ na L2!<br/>RETURN]

    TARIFF_DEFICIT -->|L2| CWU_DEF{CWU window?}
    CWU_DEF -->|TAK| SOC_CWU_DEF{SOC > 70%?}
    SOC_CWU_DEF -->|TAK| GRID_CWU_DEF[grid_to_home<br/>RETURN]
    SOC_CWU_DEF -->|NIE| CHARGE_CWU_DEF[charge_from_grid<br/>RETURN]
    CWU_DEF -->|NIE| DISCHARGE_L2_DEF[discharge_to_home<br/>RETURN]

    style EMERGENCY fill:#ff0000,color:#fff
    style URGENT fill:#ff9900,color:#fff
    style TEMP_UNSAFE fill:#ff0000,color:#fff
    style CHARGE_PV_ONLY fill:#00ff00,color:#000
    style CHARGE_PV fill:#00ff00,color:#000
    style CHARGE_GRID_L2 fill:#ffff00,color:#000
    style L2_NIGHT_CHARGE fill:#ffff00,color:#000
    style IDLE_L1 fill:#00ffff,color:#000
    style IDLE_L1_DEF fill:#00ffff,color:#000
```

## Kluczowe Priorytety (od najwyższego):

1. **🚨 BEZPIECZEŃSTWO** (temperatura, SOC krytyczne)
2. **⚡ L2 ŁADOWANIE** (tanie 0.72 zł - niezależnie od PV)
3. **🌞 PV MAGAZYNOWANIE** (darmowe - priorytet!)
4. **💰 ARBITRAŻ** (sprzedaż gdy opłacalna)
5. **🏠 AUTOCONSUMPTION** (reszta przypadków)

## Źródła Energii - Priorytet Kosztowy:

```
PV (darmowe) > L2 sieć (0.72 zł) > Bateria > L1 sieć (1.11 zł)
```

## Kluczowe Progi:

- **SOC < 5%**: KRYTYCZNE - ładuj 24/7 do 35%
- **SOC < 20%**: PILNE - ładuj w L2 do 20%
- **SOC ≤ 20% w L1**: CZEKAJ na L2 (NIE ładuj!)
- **SOC > 20% w L1**: Rozładowuj (oszczędzaj L1)
- **SOC ≥ 80%**: Pełna - różne strategie zależnie od taryfy
- **Target SOC**: Cel ładowania (zwykle 70-80%)

## Okna Czasowe:

- **L2 NOC**: 22:00-06:00 (ładuj do Target)
- **L2 POŁUDNIE**: 13:00-15:00 (inteligentne: PV > sieć)
- **L1**: 06:00-13:00, 15:00-22:00 (NIE ładuj, rozładowuj!)

## Tryby Pracy:

1. **charge_from_grid** → TOU mode + grid charging ON
2. **charge_from_pv** → maximise_self_consumption
3. **discharge_to_home** → maximise_self_consumption
4. **discharge_to_grid** → maximise_self_consumption + settings
5. **grid_to_home** → TOU mode + discharge 0W
6. **idle** → maximise_self_consumption + charge OFF
