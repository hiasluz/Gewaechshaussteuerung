# Greenhouse Control System

Steuerungssystem für Gewächshaustore und Bewässerung, basierend auf Raspberry Pi und einer Cloud-API. Das System besteht aus einer zentralen Web-Oberfläche, einer REST-API und einem Polling-Client auf dem Raspberry Pi.

## Architektur

Das System ist in drei Hauptkomponenten unterteilt:
1. **Frontend (`web/`)**: Die Weboberfläche (HTML, JS, CSS) für den Browser (z.B. auf `gewaechshaus.luzernenhof.de`). Spricht ausschließlich mit der PHP-API.
2. **Backend / API (`api/`)**: Zentrale PHP REST-API mit MySQL-Datenbank (`complete_schema.sql`). Speichert alle Befehle, Zustände und Einstellungen.
3. **Raspberry Pi (Hardware-Client)**: Führt als `greenhouse-api.service` den Polling-Client aus.
   - `greenhouse_api_client.py`: Holt zyklisch neue Befehle von der API ab und meldet den aktuellen Sensoren- und Tor-Status.
   - `greenhouse_web.py`: Modul für Hardware-Abstraktion (GPIOs, I2C, Sensoren) und Automatik-Logik (enthält **keinen** lokalen Webserver mehr).

## Funktionen

*   **Smart Polling**: Dynamische Polling-Intervalle (3s bis 30s) je nach Aktivität und Temperaturabweichung.
*   **Intelligente Automatik**: Stufenlose Regelung der Tore (5-15% Schritte) basierend auf Innen- und Außentemperatur, komplett über das Web konfigurierbar.
*   **LTE Failover**: Unterstützung für SIM7600/4G Module mit automatischer VPN/Hotspot-Umschaltung.
*   **Zentrale Einstellungen**: Sämtliche Konfigurationen (Zieltemperatur, Hysterese, Polling-Zeiten, Motorlaufzeiten) werden in der Datenbank gespeichert und über das Web-Interface (`/api/settings`) angepasst.

## Installation & Setup

### 1. Webserver (API & Frontend)

*   Lade den Inhalt des `api/` Ordners auf deinen Webserver unter dem Pfad `/api/`.
*   Lade den Inhalt des `web/` Ordners in das öffentliche Hauptverzeichnis (Root) deines Webservers.
*   Kopiere `api/config.sample.php` nach `api/config.php` und trage die Datenbank-Zugangsdaten sowie einen sicheren `API_KEY` ein.
*   Importiere die `api/complete_schema.sql` (bzw. `api/insert_initial_settings.sql`) in deine MySQL-Datenbank.

### 2. Raspberry Pi (Client)

Das System benötigt Python 3 und die passenden Hardware-Bibliotheken (z.B. RPi.GPIO).

```bash
# Abhängigkeiten installieren
pip install python-dotenv requests astral pytz RPi.GPIO
```

**Konfiguration (`.env`):**
Erstelle eine `.env` Datei im Hauptverzeichnis des Pi (siehe `.env` Vorlage):
```env
API_URL=https://deine-domain.de/api
API_KEY=dein_geheimer_key
LATITUDE=47.8655
LONGITUDE=7.6145
# ... weitere Einstellungen für WiFi/SIM
```

**Systemd-Service einrichten:**
Der Client läuft dauerhaft als Hintergrunddienst:
```bash
sudo systemctl enable greenhouse-api.service
sudo systemctl start greenhouse-api.service
```
*(Hinweis: Es darf kein separater Service für `greenhouse_web.py` laufen!)*

## Entwicklung & Wartung

### Dienst-Management (Pi)

```bash
# Status des API-Clients prüfen
sudo systemctl status greenhouse-api.service

# Live-Logs ansehen
journalctl -u greenhouse-api.service -f

# Dienst neu starten (z.B. nach Code-Update oder Pi-Neustart)
sudo systemctl restart greenhouse-api.service
```

### Deployment (Beispiel)

Nutze `scp`, um geänderte Dateien auf den Pi zu übertragen:
```powershell
# Beispiel: Python-Client Update
scp .\greenhouse_api_client.py luz@luzPi.local:/home/luz/greenhouse/
```

## Sicherheit

*   **Credentials**: Sensible Daten werden niemals im Code gespeichert, sondern über `.env` (Pi) oder `config.php` (Server) verwaltet.
*   **Git**: Konfigurationsdateien sind in `.gitignore` eingetragen.
*   **API-Absicherung**: Die Kommunikation zwischen Pi und Server ist durch den `X-API-Key` Header gesichert. Das Web-Frontend nutzt eine Session-basierte Anmeldung (`/api/login`).

---
*Ein Projekt des Luzernenhof (die beste Solawi der Welt).*  
Kontakt: [info@luzernenhof.de](mailto:info@luzernenhof.de)
