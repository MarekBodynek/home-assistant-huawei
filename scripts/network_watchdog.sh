#!/bin/bash
# Network Watchdog - monitoruje połączenie z inwerterem Huawei
# Automatycznie przełącza na wlan0 jeśli eth0 nie działa

DONGLE_IP="192.168.0.78"
LOG_FILE="/var/log/network_watchdog.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Test połączenia przez eth0
if ip link show eth0 | grep -q "state UP"; then
    # eth0 jest UP - sprawdź czy działa
    if ! ping -c 2 -W 2 -I eth0 "$DONGLE_IP" > /dev/null 2>&1; then
        log "WARNING: eth0 UP but cannot reach dongle $DONGLE_IP"

        # Test przez wlan0
        if ping -c 2 -W 2 -I wlan0 "$DONGLE_IP" > /dev/null 2>&1; then
            log "INFO: wlan0 can reach dongle - disabling eth0"
            ip link set eth0 down
            log "INFO: eth0 disabled, wlan0 is now primary"
        else
            log "ERROR: Neither eth0 nor wlan0 can reach dongle!"
        fi
    else
        log "INFO: eth0 OK - dongle reachable"
    fi
else
    # eth0 jest DOWN - sprawdź czy wlan0 działa
    if ping -c 2 -W 2 -I wlan0 "$DONGLE_IP" > /dev/null 2>&1; then
        log "INFO: eth0 DOWN, wlan0 OK - dongle reachable"
    else
        log "ERROR: eth0 DOWN, wlan0 cannot reach dongle - trying to restore eth0"
        ip link set eth0 up
        sleep 5
        if ping -c 2 -W 2 "$DONGLE_IP" > /dev/null 2>&1; then
            log "INFO: eth0 restored and working"
        else
            log "ERROR: eth0 restored but still cannot reach dongle"
        fi
    fi
fi
