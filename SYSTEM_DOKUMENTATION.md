# 📗 System-Dokumentation: Greenhouse Control

Dieses Dokument beschreibt die technische Architektur, die Hardware-Belegung und die Konfiguration des Gewächshaus-Steuerungssystems.

## 🏗 Architektur

Das System besteht aus zwei Hauptkomponenten auf dem Raspberry Pi:

1.  **Hardware-Layer (`greenhouse_web.py`)**:
    *   Verwaltet den direkten Zugriff auf die GPIO-Pins.
    *   Bietet eine lokale API (Flask) zur Steuerung der Motoren und Auslesen der Sensoren.
    *   Speichert den aktuellen Zustand (Tor-Positionen) in einer lokalen Variable und synchronisiert diesen mit der Remote-Datenbank.
    *   **Positions-Tracking**: Berechnet die Laufzeiten der Motoren basierend auf der gewünschten Prozent-Änderung (0-100%).

2.  **API-Client (`greenhouse_api_client.py`)**:
    *   Der "Vermittler" zwischen dem Pi und dem Web-Server im Internet.
    *   Pollt alle 10 Sekunden neue Befehle vom Server.
    *   Sendet alle 10-30 Sekunden Temperaturdaten und Status-Updates an den Server.
    *   Führt die Automatik-Logik aus (falls aktiviert).

---

## 🔌 Hardware-Belegung (GPIO)

Das System nutzt die BCM-Nummerierung der Pins. Alle Schaltungen sind **Active Low** (Relais schalten bei `GPIO.LOW`).

### Motoren (Tore)
Jeder Motor hat zwei Pins: einen für AUF und einen für ZU.

| Motor | Pin AUF (BCM) | Pin ZU (BCM) |
|-------|---------------|--------------|
| GH1_VORNE | 17 | 27 |
| GH1_HINTEN | 22 | 10 |
| GH2_VORNE | 9 | 11 |
| GH2_HINTEN | 18 | 23 |
| GH3_VORNE | 13 | 19 |
| GH3_HINTEN | 26 | 21 |

### Zusatz-Schalter (Relais)
| Gerät | Pin (BCM) |
|-------|-----------|
| Bewässerung 1 | 20 |
| Bewässerung 2 | 16 |
| Bewässerung 3 | 12 |
| Zusatz (Hotspot/Licht) | 25 |

### Sensoren (1-Wire)
*   Temperatursensoren (DS18B20) sind am Standard 1-Wire Pin (GPIO 4) angeschlossen.
*   Die Identifizierung erfolgt über die Hardware-ID (UID).

---

## ⚙️ Konfiguration

Alle wichtigen Einstellungen befinden sich am Anfang der Skripte:

### `greenhouse_web.py`
*   `MOTOR_RUNTIME_OPEN / CLOSE`: Kalibrierte Zeit für den kompletten Weg (Standard: 135s / 128s).
*   `API_URL` & `API_KEY`: Zugangsdaten für den Remote-Server.

### `greenhouse_api_client.py`
*   `POLL_INTERVAL`: Zeit zwischen den Befehls-Abfragen (Standard: 10s).
*   `AUTO-Logik`: Steuert die Tore in 5%, 10% oder 15% Schritten basierend auf der Differenz zwischen Innen- und Außentemperatur.

### Einrichtung & Hilfsskripte (`setup/`)
*   `setup_ppp.py`: Richtet die LTE-Verbindung ein (SIM7600).
*   `unlock_sim.py`: Entsperrt die SIM-Karte mit dem PIN.
*   `enable_sensors.sh`: Aktiviert das 1-Wire Interface auf dem Pi.

---

## 🛠 Fehlerbehebung

### Dienste neu starten
```bash
sudo systemctl restart greenhouse-client.service
```

### Logs einsehen
```bash
# Aktuelle Befehle und Status-Updates
journalctl -u greenhouse-client -f

# Nur Motor-Bewegungen sehen
journalctl -u greenhouse-client -f | grep "Motor"
```

### Tore synchronisieren
Falls die Anzeige im Web-Interface nicht mit der echten Position übereinstimmt:
1.  Tore über das Interface einmal komplett SCHLIESSEN oder ÖFFNEN. 
2.  Das System kalibriert sich beim Erreichen der 0% oder 100% Marke automatisch neu.
