# 📗 System-Dokumentation: Greenhouse Control

Dieses Dokument beschreibt die technische Architektur, die Hardware-Belegung und die Konfiguration des Gewächshaus-Steuerungssystems.

## 🏗 Architektur

Das System besteht aus drei zentralen Komponenten: dem Web-Frontend, der zentralen REST-API (PHP/MySQL) und dem Hardware-Client auf dem Raspberry Pi.

1.  **Hardware-Layer (`greenhouse_web.py`)**:
    *   Fungiert ausschließlich als Python-Modul für die Hardware-Abstraktion (enthält **keinen** lokalen Webserver mehr).
    *   Verwaltet den direkten Zugriff auf die GPIO-Pins.
    *   Speichert den aktuellen Zustand (Tor-Positionen) im RAM und übernimmt die Automatik-Logik (`check_auto_logic`).
    *   **Positions-Tracking**: Berechnet die Laufzeiten der Motoren basierend auf der gewünschten Prozent-Änderung (0-100%).

2.  **API-Client (`greenhouse_api_client.py`)**:
    *   Der einzige Dienst (`greenhouse-api.service`), der auf dem Raspberry Pi läuft.
    *   Der "Vermittler" zwischen dem Pi und der zentralen PHP-API (`api/index.php`) im Internet.
    *   Pollt zyklisch neue Befehle (Smart Polling: 3s bis 30s) von der API.
    *   Sendet Temperaturdaten, Tor-Positionen und Status-Updates an die API.
    *   Importiert `greenhouse_web.py`, um die eigentlichen Schaltvorgänge und die Automatik-Regelung auszuführen.

3.  **Zentrale API & Web-Frontend (`api/` und `web/`)**:
    *   Das Frontend im Browser kommuniziert ausschließlich mit der PHP-API.
    *   Die API speichert Befehle, Stati und alle Systemeinstellungen (inklusive Zieltemperatur) in einer MySQL-Datenbank (`system_settings`).

---

## 🔌 Hardware-Belegung (GPIO)

Das System nutzt die BCM-Nummerierung der Pins. Alle Schaltungen für Tore und Relais sind **Active Low** (Relais schalten bei `GPIO.LOW` bzw. `0`).

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

## ⚙️ Konfiguration & Automatik

Die Konfiguration wird nicht mehr hart im Code vorgenommen, sondern zentral über das Web-Frontend ("Erweiterte Einstellungen" -> `/api/settings`) verwaltet und in der Datenbank (`system_settings`) gespeichert. Der Pi lädt diese Einstellungen beim Start und regelmäßig herunter.

### Wichtige Einstellungen (via Web-Interface)
*   **Zieltemperatur (`DEFAULT_TARGET_TEMP`)**: Die Wunschtemperatur für den Automatik-Modus.
*   **Laufzeiten (`MOTOR_RUNTIME_OPEN / CLOSE`)**: Kalibrierte Zeit für den kompletten Weg (Standard: 135s / 128s).
*   **Polling-Intervalle (`INTERVAL_FAST / NORMAL / SLOW`)**: Dynamische Zeiten zwischen den Befehls-Abfragen.

### Automatik-Logik
*   Die Automatik steuert die Tore in 5%, 10% oder 15% Schritten basierend auf der Differenz zwischen Innen- und Zieltemperatur.
*   **Global vs. Tor-spezifisch**:
    *   Ein Tor wird nur automatisch bewegt, wenn sein **eigener** Auto-Schalter auf "AN" steht (und es nicht über den AN/AUS-Schalter für den Wintermodus deaktiviert wurde).
    *   Steht der **globale Modus** auf AUTO, folgen alle Tore mit aktiviertem Tor-Auto-Schalter der Regelung.
    *   Steht der **globale Modus** auf MANUAL, können einzelne Tore trotzdem automatisch geregelt werden, sofern ihr spezifischer Tor-Auto-Schalter "AN" ist.

### `.env` Datei (auf dem Pi)
*   `API_URL` & `API_KEY`: Zugangsdaten für die zentrale REST-API.
*   `LATITUDE` & `LONGITUDE`: Für die Sonnenaufgangs-/Untergangsberechnung (Lüftungsmodus).

### Einrichtung & Hilfsskripte (`setup/`)
*   `setup_ppp.py`: Richtet die LTE-Verbindung ein (SIM7600).
*   `unlock_sim.py`: Entsperrt die SIM-Karte mit dem PIN.
*   `enable_sensors.sh`: Aktiviert das 1-Wire Interface auf dem Pi.

---

## 🛠 Fehlerbehebung

### Dienste neu starten
Das System läuft auf dem Pi als einziger Hintergrunddienst:
```bash
sudo systemctl restart greenhouse-api.service
```

### Logs einsehen
```bash
# Aktuelle Befehle und Status-Updates fortlaufend anzeigen
journalctl -u greenhouse-api.service -f

# Nur Motor-Bewegungen sehen
journalctl -u greenhouse-api.service -f | grep "Motor"
```

### Tore synchronisieren
Falls die prozentuale Anzeige im Web-Interface nicht mit der echten physischen Position übereinstimmt:
1.  Tore über das Interface einmal komplett SCHLIESSEN oder komplett ÖFFNEN. 
2.  Das System kalibriert sich beim Erreichen der 0% oder 100% Marke im Code automatisch neu und setzt den Zähler zurück.
