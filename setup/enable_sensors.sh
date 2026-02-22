#!/bin/bash
# 1-Wire Kernel-Module laden und aktivieren

echo "🔧 Aktiviere 1-Wire Temperatursensoren..."

# Module laden
sudo modprobe w1-gpio
sudo modprobe w1-therm

# Prüfen ob erfolgreich
if lsmod | grep -q w1_gpio; then
    echo "✅ w1-gpio Modul geladen"
else
    echo "❌ w1-gpio Modul konnte nicht geladen werden"
fi

if lsmod | grep -q w1_therm; then
    echo "✅ w1-therm Modul geladen"
else
    echo "❌ w1-therm Modul konnte nicht geladen werden"
fi

# Sensoren anzeigen
echo ""
echo "🌡️ Verfügbare Sensoren:"
if [ -d "/sys/bus/w1/devices/" ]; then
    ls -1 /sys/bus/w1/devices/ | grep -v "w1_bus_master"
    
    # Mit w1thermsensor testen (falls installiert)
    if command -v w1thermsensor &> /dev/null; then
        echo ""
        echo "📊 Sensor-Details:"
        w1thermsensor ls
    fi
else
    echo "⚠️  /sys/bus/w1/devices/ nicht gefunden"
    echo "   Prüfe ob 1-Wire in /boot/config.txt aktiviert ist"
fi

echo ""
echo "✅ Fertig! Starte jetzt das Programm mit: ./start.sh"
