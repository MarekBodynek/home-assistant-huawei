#!/bin/bash
# Diagnostyka algorytmu baterii - sprawdzenie stanu w HA

echo "=========================================="
echo "DIAGNOSTYKA ALGORYTMU BATERII"
echo "=========================================="
echo ""

# Token HA
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIwMDkyNTJiNmE1OGU0MmEzYTZiNjBjNWZjMWQ4MTcyZCIsImlhdCI6MTczMDkyNTA1MCwiZXhwIjoyMDQ2Mjg1MDUwfQ.Z4rvslE8wBN3rWLqnedKtZzwA_tuJCqaTD8HQE7MRlk"

# Funkcja do pobierania stanu sensora
get_state() {
    entity=$1
    curl -s -H "Authorization: Bearer $TOKEN" \
         "http://localhost:8123/api/states/$entity" | \
    python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('state', 'N/A'))"
}

# Funkcja do pobierania atrybutu
get_attr() {
    entity=$1
    attr=$2
    curl -s -H "Authorization: Bearer $TOKEN" \
         "http://localhost:8123/api/states/$entity" | \
    python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('attributes', {}).get('$attr', 'N/A'))"
}

echo "📅 CZAS I TARYFA"
echo "----------------------------------------"
echo "Aktualna godzina: $(get_state sensor.time)"
echo "Aktualna data: $(get_state sensor.date)"
echo "Strefa taryfowa: $(get_state sensor.strefa_taryfowa)"
echo "Dzień roboczy: $(get_state binary_sensor.dzien_roboczy)"
echo ""

echo "🔋 BATERIA - STAN"
echo "----------------------------------------"
echo "SOC: $(get_state sensor.akumulatory_stan_pojemnosci)%"
echo "Target SOC: $(get_state input_number.battery_target_soc)%"
echo "Temperatura baterii: $(get_state sensor.bateria_temperatura_maksymalna)°C"
echo "Moc baterii: $(get_state sensor.akumulatory_moc_ladowania_rozladowania) W"
echo ""

echo "⚙️  BATERIA - KONFIGURACJA"
echo "----------------------------------------"
echo "Tryb pracy: $(get_state select.akumulatory_tryb_pracy)"
echo "Ładowanie z sieci: $(get_state switch.akumulatory_ladowanie_z_sieci)"
echo "Limit SOC ładowania: $(get_state number.akumulatory_lmit_ladowania_z_sieci_soc)%"
echo "Moc rozładowania max: $(get_state number.akumulatory_maksymalna_moc_rozladowania) W"
echo "Moc ładowania max: $(get_state number.akumulatory_maksymalna_moc_ladowania) W"
echo ""

echo "🤖 ALGORYTM - DECYZJA"
echo "----------------------------------------"
echo "Decision reason:"
decision=$(get_state input_text.battery_decision_reason)
echo "  $decision"
echo ""
echo "Storage status:"
storage=$(get_state input_text.battery_storage_status)
echo "  $storage"
echo ""

echo "☀️  PROGNOZA PV"
echo "----------------------------------------"
echo "Dziś: $(get_state sensor.prognoza_pv_dzisiaj) kWh"
echo "Jutro: $(get_state sensor.prognoza_pv_jutro) kWh"
echo ""

echo "💡 PV I ZUŻYCIE"
echo "----------------------------------------"
echo "Moc PV: $(get_state sensor.inwerter_moc_wejsciowa) W"
echo "Pobór domu: $(get_state sensor.pomiar_mocy_moc_czynna) W"
echo ""

echo "🌡️  POGODA"
echo "----------------------------------------"
echo "Temp zewnętrzna: $(get_state sensor.temperatura_zewnetrzna)°C"
echo "Sezon grzewczy: $(get_state binary_sensor.sezon_grzewczy)"
echo ""

echo "=========================================="
echo "ANALIZA PROBLEMU"
echo "=========================================="
echo ""

# Analiza - czy algorytm powinien ładować?
soc=$(get_state sensor.akumulatory_stan_pojemnosci)
target=$(get_state input_number.battery_target_soc)
tariff=$(get_state sensor.strefa_taryfowa)
hour=$(get_state sensor.time | cut -d: -f1)
charging=$(get_state switch.akumulatory_ladowanie_z_sieci)
mode=$(get_state select.akumulatory_tryb_pracy)

echo "SOC: $soc% | Target: $target%"
echo "Strefa: $tariff | Godzina: ${hour}h"
echo "Tryb: $mode"
echo "Ładowanie z sieci: $charging"
echo ""

# Sprawdź warunki ładowania w nocy L2
if [ "$tariff" = "L2" ] && [ "$hour" -ge 22 -o "$hour" -le 5 ]; then
    echo "✅ Jest NOC L2 (22-5h)"

    if (( $(echo "$soc < $target" | bc -l) )); then
        echo "✅ SOC ($soc%) < Target ($target%)"

        if [ "$charging" = "on" ] && [ "$mode" = "time_of_use_luna2000" ]; then
            echo "✅ Algorytm DZIAŁA POPRAWNIE - ładuje z sieci"
        else
            echo "❌ PROBLEM! Algorytm powinien ładować, ale:"
            [ "$charging" != "on" ] && echo "   - Ładowanie z sieci: $charging (powinno być: on)"
            [ "$mode" != "time_of_use_luna2000" ] && echo "   - Tryb pracy: $mode (powinien być: time_of_use_luna2000)"
        fi
    else
        echo "✅ SOC ($soc%) >= Target ($target%) - bateria naładowana"

        if [ "$mode" = "time_of_use_luna2000" ] && [ "$charging" = "off" ]; then
            echo "✅ Algorytm DZIAŁA POPRAWNIE - zachowuje baterię na L1"
        else
            echo "⚠️  Tryb: $mode | Ładowanie: $charging"
        fi
    fi
else
    echo "ℹ️  Nie jest noc L2 (strefa: $tariff, godzina: ${hour}h)"
fi

echo ""
echo "=========================================="
echo "Koniec diagnostyki"
echo "=========================================="
