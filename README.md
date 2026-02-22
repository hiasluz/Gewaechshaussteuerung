# Greenhouse Control System

Steuerungssystem für Gewächshaustore und Bewässerung, basierend auf Raspberry Pi und einer Cloud-API. Das System ermöglicht sowohl manuelle Steuerung als auch eine intelligente Temperaturregelung.

## Funktionen

*   **Smart Polling**: Dynamische Intervalle (3s bis 30s) je nach Aktivität und Temperaturabweichung.
*   **Intelligente Automatik**: Stufenlose Regelung der Tore (5-15% Schritte) basierend auf Innen- und Außentemperatur.
*   **LTE Failover**: Unterstützung für SIM7600/4G Module mit automatischer VPN/Hotspot-Umschaltung.
*   **Responsive Web-Interface**: Steuerung über [gewaechshaus.luzernenhof.de](https://gewaechshaus.luzernenhof.de).

## Installation & Setup

### 1. Raspberry Pi (Client)

Das System benötigt Python 3 und die Bibliothek `python-dotenv`.

```bash
# Abhängigkeiten installieren
pip install python-dotenv requests astral pytz RPi.GPIO
```

**Konfiguration:**
Erstelle eine `.env` Datei im Hauptverzeichnis (siehe `.env` Vorlage):
```env
API_URL=https://deine-domain.de/api
API_KEY=dein_geheimer_key
LATITUDE=47.8655
LONGITUDE=7.6145
# ... weitere Einstellungen für WiFi/SIM
```

### 2. Server (REST API)

*   Lade den Inhalt des `api/` Ordners auf deinen Webserver.
*   Kopiere `api/config.sample.php` nach `api/config.php`.
*   Trage deine Datenbank-Daten und denselben `API_KEY` ein, den du am Pi verwendest.
*   Importiere die `complete_schema.sql` in deine MySQL-Datenbank.

## Entwicklung & Wartung

### Verzeichnis-Struktur
*   `greenhouse_api_client.py`: Hauptdienst (Polling & Logik).
*   `greenhouse_web.py`: Hardware-Abstraktion & lokaler Webserver.
*   `setup/`: Skripte für LTE, Sensoren und System-Configuration.

### Dienst-Management
Das System läuft idealerweise als Systemd-Service:
```bash
sudo systemctl restart greenhouse-client.service
```

## Deployment (PowerShell/Bash)

Nutzen Sie `scp`, um geänderte Dateien auf den Pi zu übertragen:
```powershell
# Beispiel: Client-Update
scp .\greenhouse_api_client.py luz@luzPi.local:/home/luz/greenhouse/
```

## Sicherheit

*   **Credentials**: Sensible Daten werden niemals im Code gespeichert, sondern über `.env` (Pi) oder `config.php` (Server) verwaltet.
*   **Git**: Diese Dateien sind in `.gitignore` eingetragen und werden nicht nach GitHub hochgeladen.
*   **API**: Die Kommunikation ist durch `X-API-Key` Header und URL-Parameter gesichert.

---
*Ein Projekt des Luzernenhof (Gärtnerhof Belchenblick).*
