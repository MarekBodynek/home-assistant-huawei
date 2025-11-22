#!/bin/bash

# ============================================
# 🔍 DIAGNOSTYKA SYSTEMU BATERII
# ============================================
# Sprawdza status Home Assistant, baterii, algorytmu i sensorów
# Autor: Marek Bodynek + Claude Code
# Data: 2025-11-17

set -e

# Kolory
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Konfiguracja
HA_URL="${HA_URL:-http://localhost:8123}"
HA_TOKEN="${HA_TOKEN}"

if [ -z "$HA_TOKEN" ]; then
    echo -e "${RED}❌ Błąd: Brak HA_TOKEN${NC}"
    echo "Ustaw zmienną środowiskową HA_TOKEN lub uruchom z Docker kontenera"
    exit 1
fi

# Funkcja do zapytań API
ha_api() {
    local endpoint=$1
    curl -s -H "Authorization: Bearer $HA_TOKEN" \
         -H "Content-Type: application/json" \
         "$HA_URL/api/$endpoint"
}

# Funkcja do pobierania stanu sensora
get_state() {
    local entity=$1
    local response=$(ha_api "states/$entity")
    echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('state', 'unavailable'))" 2>/dev/null || echo "unavailable"
}

# Nagłówek
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🔍 DIAGNOSTYKA SYSTEMU BATERII${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "📅 Data: $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "🌐 URL: $HA_URL"
echo ""

# ============================================
# 1. STATUS HOME ASSISTANT
# ============================================
echo -e "${BLUE}━━━ 1. HOME ASSISTANT ━━━${NC}"
HA_STATUS=$(ha_api "" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('message', 'error'))" 2>/dev/null || echo "error")

if [ "$HA_STATUS" = "API running." ]; then
    echo -e "${GREEN}✅ Home Assistant: ONLINE${NC}"
else
    echo -e "${RED}❌ Home Assistant: OFFLINE${NC}"
    exit 1
fi

# Wersja HA
HA_VERSION=$(get_state "sensor.current_version" 2>/dev/null || echo "unknown")
echo -e "   Wersja: $HA_VERSION"
echo ""

# ============================================
# 2. STATUS BATERII
# ============================================
echo -e "${BLUE}━━━ 2. BATERIA (Huawei Luna 2000) ━━━${NC}"

# SOC
SOC=$(get_state "sensor.akumulatory_stan_pojemnosci")
if [ "$SOC" != "unavailable" ]; then
    echo -e "${GREEN}✅ Stan naładowania (SOC): ${SOC}%${NC}"

    # Kolory dla SOC
    if (( $(echo "$SOC >= 80" | bc -l) )); then
        echo -e "   ${GREEN}🔋 Bardzo dobry poziom${NC}"
    elif (( $(echo "$SOC >= 50" | bc -l) )); then
        echo -e "   ${YELLOW}🔋 Dobry poziom${NC}"
    else
        echo -e "   ${RED}🔋 Niski poziom${NC}"
    fi
else
    echo -e "${RED}❌ Stan naładowania (SOC): NIEDOSTĘPNY${NC}"
fi

# Moc
POWER=$(get_state "sensor.akumulatory_moc_ladowania_rozladowania")
echo -e "   Moc: ${POWER} W"

# Status
STATUS=$(get_state "sensor.akumulatory_status")
echo -e "   Status: ${STATUS}"

# Temperatura
TEMP=$(get_state "sensor.bateria_temperatura_maksymalna")
TEMP_SAFE=$(get_state "binary_sensor.bateria_bezpieczna_temperatura")
if [ "$TEMP_SAFE" = "on" ]; then
    echo -e "${GREEN}✅ Temperatura: ${TEMP}°C (bezpieczna)${NC}"
else
    echo -e "${YELLOW}⚠️  Temperatura: ${TEMP}°C (sprawdź zakres)${NC}"
fi

# Ładowanie z sieci
CHARGING=$(get_state "switch.akumulatory_ladowanie_z_sieci")
if [ "$CHARGING" = "on" ]; then
    echo -e "${YELLOW}⚡ Ładowanie z sieci: AKTYWNE${NC}"
else
    echo -e "   Ładowanie z sieci: WYŁĄCZONE"
fi

echo ""

# ============================================
# 3. ALGORYTM ZARZĄDZANIA
# ============================================
echo -e "${BLUE}━━━ 3. ALGORYTM ZARZĄDZANIA ━━━${NC}"

# Decyzja algorytmu
DECISION=$(get_state "input_text.battery_decision_reason")
echo -e "${GREEN}🎯 Decyzja: ${DECISION}${NC}"

# Target SOC
TARGET_SOC=$(get_state "input_number.battery_target_soc")
echo -e "   Target SOC: ${TARGET_SOC}%"

# Charge SOC Limit
CHARGE_LIMIT=$(get_state "number.akumulatory_docelowy_stan_pojemnosci_ladowania")
echo -e "   Charge SOC Limit: ${CHARGE_LIMIT}%"

# Max moc ładowania
MAX_CHARGE=$(get_state "number.akumulatory_maksymalna_moc_ladowania")
echo -e "   Max moc ładowania: ${MAX_CHARGE} W"

# Max moc rozładowania
MAX_DISCHARGE=$(get_state "sensor.bateria_max_moc_rozladowania")
echo -e "   Max moc rozładowania: ${MAX_DISCHARGE} W"

echo ""

# ============================================
# 4. TARYFA I KONTEKST
# ============================================
echo -e "${BLUE}━━━ 4. TARYFA I KONTEKST ━━━${NC}"

# Taryfa
TARIFF=$(get_state "sensor.strefa_g12w")
if [ "$TARIFF" = "L1" ]; then
    echo -e "${YELLOW}⚡ Taryfa: L1 (droga - 1.11 zł/kWh)${NC}"
else
    echo -e "${GREEN}⚡ Taryfa: L2 (tania - 0.72 zł/kWh)${NC}"
fi

# Dzień roboczy
WORKDAY=$(get_state "binary_sensor.dzien_roboczy")
if [ "$WORKDAY" = "on" ]; then
    echo -e "   Dzień: ROBOCZY"
else
    echo -e "   Dzień: WEEKEND/ŚWIĘTO"
fi

# Sezon grzewczy
HEATING=$(get_state "binary_sensor.sezon_grzewczy")
if [ "$HEATING" = "on" ]; then
    echo -e "   Sezon: GRZEWCZY 🔥"
else
    echo -e "   Sezon: LETNI ☀️"
fi

# Temperatura zewnętrzna
TEMP_OUT=$(get_state "sensor.temperatura_zewnetrzna")
echo -e "   Temperatura zewnętrzna: ${TEMP_OUT}°C"

echo ""

# ============================================
# 5. PRODUKCJA PV
# ============================================
echo -e "${BLUE}━━━ 5. PRODUKCJA PV (Forecast.Solar) ━━━${NC}"

# Prognoza dziś
FORECAST_TODAY=$(get_state "sensor.energy_production_today_remaining")
echo -e "   Prognoza dziś (pozostało): ${FORECAST_TODAY} kWh"

# Prognoza jutro
FORECAST_TOMORROW=$(get_state "sensor.energy_production_tomorrow")
echo -e "   Prognoza jutro: ${FORECAST_TOMORROW} kWh"

# Aktualna produkcja
PRODUCTION=$(get_state "sensor.inwerter_moc_wejsciowa")
echo -e "   Aktualna produkcja: ${PRODUCTION} W"

# Dzienna produkcja
DAILY=$(get_state "sensor.inwerter_dzienna_produkcja")
echo -e "   Dziś wyprodukowano: ${DAILY} kWh"

echo ""

# ============================================
# 6. CENY ENERGII (RCE PSE)
# ============================================
echo -e "${BLUE}━━━ 6. CENY ENERGII (RCE PSE) ━━━${NC}"

# Aktualna cena RCE (PLN/MWh → PLN/kWh)
RCE_MWH=$(get_state "sensor.rce_pse_cena")
if [ "$RCE_MWH" != "unavailable" ] && [ "$RCE_MWH" != "unknown" ]; then
    RCE_KWH=$(echo "scale=3; $RCE_MWH / 1000" | bc)
    echo -e "   Cena RCE: ${RCE_KWH} zł/kWh (${RCE_MWH} PLN/MWh)"
else
    RCE_KWH="N/A"
    echo -e "   Cena RCE: niedostępna"
fi
BUY_PRICE=$RCE_KWH
SELL_PRICE=$RCE_KWH

# Próg arbitrażu
if [ "$HEATING" = "on" ]; then
    THRESHOLD="0.90"
else
    THRESHOLD="0.88"
fi
echo -e "   Próg arbitrażu: ${THRESHOLD} zł/kWh"

# Najtańsze godziny (z algorytmu)
CHEAPEST=$(get_state "input_text.battery_cheapest_hours" 2>/dev/null || echo "N/A")
if [ "$CHEAPEST" != "N/A" ] && [ "$CHEAPEST" != "unavailable" ] && [ "$CHEAPEST" != "Brak danych" ]; then
    echo -e "${GREEN}✅ Najtańsze godziny dziś: ${CHEAPEST}${NC}"
fi

echo ""

# ============================================
# 7. ZUŻYCIE ENERGII
# ============================================
echo -e "${BLUE}━━━ 7. ZUŻYCIE ENERGII ━━━${NC}"

# Aktualne zużycie domu
CONSUMPTION=$(get_state "sensor.aktualne_zuzycie_domu")
echo -e "   Aktualne zużycie: ${CONSUMPTION} W"

# Dzienne zużycie
DAILY_CONSUMPTION=$(get_state "sensor.dzienne_zuzycie_energii" 2>/dev/null || echo "N/A")
if [ "$DAILY_CONSUMPTION" != "N/A" ]; then
    echo -e "   Dzisiaj zużyto: ${DAILY_CONSUMPTION} kWh"
fi

echo ""

# ============================================
# 8. PODSUMOWANIE I REKOMENDACJE
# ============================================
echo -e "${BLUE}━━━ 8. PODSUMOWANIE ━━━${NC}"

# Analiza statusu
ERRORS=0
WARNINGS=0

# Sprawdź SOC
if [ "$SOC" = "unavailable" ]; then
    echo -e "${RED}❌ BŁĄD: Brak odczytu SOC baterii${NC}"
    ((ERRORS++))
elif (( $(echo "$SOC < 20" | bc -l) )); then
    echo -e "${YELLOW}⚠️  UWAGA: SOC poniżej bezpiecznego minimum (20%)${NC}"
    ((WARNINGS++))
fi

# Sprawdź temperaturę
if [ "$TEMP_SAFE" != "on" ]; then
    echo -e "${YELLOW}⚠️  UWAGA: Temperatura baterii poza bezpiecznym zakresem${NC}"
    ((WARNINGS++))
fi

# Sprawdź prognozy
if [ "$FORECAST_TODAY" = "unavailable" ] || [ "$FORECAST_TOMORROW" = "unavailable" ]; then
    echo -e "${YELLOW}⚠️  UWAGA: Brak prognoz PV (Forecast.Solar offline?)${NC}"
    ((WARNINGS++))
fi

# Sprawdź ceny RCE PSE
if [ "$BUY_PRICE" = "N/A" ] || [ "$SELL_PRICE" = "N/A" ]; then
    echo -e "${YELLOW}⚠️  UWAGA: Brak danych o cenach RCE (RCE PSE offline?)${NC}"
    ((WARNINGS++))
fi

# Sprawdź algorytm
if [ "$DECISION" = "unavailable" ] || [ "$DECISION" = "unknown" ]; then
    echo -e "${RED}❌ BŁĄD: Algorytm nie zwraca decyzji${NC}"
    ((ERRORS++))
fi

# Podsumowanie
echo ""
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ System działa poprawnie!${NC}"
    echo -e "${GREEN}   Brak błędów i ostrzeżeń.${NC}"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  System działa z ostrzeżeniami: ${WARNINGS}${NC}"
else
    echo -e "${RED}❌ System ma błędy: ${ERRORS}, ostrzeżenia: ${WARNINGS}${NC}"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}🏁 KONIEC DIAGNOSTYKI${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

exit 0
