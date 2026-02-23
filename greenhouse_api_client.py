#!/usr/bin/env python3
"""
Gewächshaus API Client - Polling-basiert mit Ventilation
Fragt regelmäßig die REST API ab und führt Befehle aus.

Smart Polling Intervals:
- 3s nach Befehl (Development Mode)
- 10s normal
- 30s wenn Temperatur >10° vom Sollwert
"""

import time
import requests
import json
import subprocess
import sys
import signal
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from astral import LocationInfo
from astral.sun import sun
import pytz

# Lade Umgebungsvariablen aus .env Datei
load_dotenv()

# Importiere greenhouse_web.py Komponenten
try:
    from greenhouse_web import init_global_system, SENSORS_AVAILABLE, GPIO, GPIO_SWITCHES
except ImportError:
    print("⚠️  greenhouse_web.py nicht gefunden!")
    print("   Stelle sicher, dass greenhouse_web.py im gleichen Verzeichnis ist.")
    sys.exit(1)



# ===== KONFIGURATION =====

API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")

if not API_KEY or not API_URL:
    print("❌ Fehler: API_KEY oder API_URL nicht in .env gefunden!")
    sys.exit(1)

# Polling-Intervalle (Sekunden) - Werden von API geladen
INTERVAL_FAST = 3       # Nach Befehl (schnelle Rückmeldung)
INTERVAL_NORMAL = 10    # Normal
INTERVAL_SLOW = 30      # Temperatur weit weg

# Temperatur-Schwellwert für langsames Polling
TEMP_THRESHOLD = 10.0   # Grad Celsius

# Retry-Konfiguration
MAX_RETRIES = 3
RETRY_DELAY = 30  # Sekunden

# Koordinaten für Sunrise-Berechnung (aus .env)
LAT_ENV = os.getenv("LATITUDE")
LON_ENV = os.getenv("LONGITUDE")

if not LAT_ENV or not LON_ENV:
    log('ERROR', "❌ LATITUDE oder LONGITUDE fehlt in .env!")
    sys.exit(1)

LAT = float(LAT_ENV)
LON = float(LON_ENV)
LOCATION = LocationInfo("Luzernenhof", "Germany", "Europe/Berlin", LAT, LON)

# ===== GLOBALE VARIABLEN =====

gh_system = None
last_command_time = None
running = True
ventilation_active = False
last_hotspot_state = None

# ===== SIGNAL HANDLER =====

def signal_handler(sig, frame):
    global running
    print("\n🛑 Shutdown Signal empfangen...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ===== HELPER FUNCTIONS =====

def log(level, message):
    """Formatiertes Logging"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {message}", flush=True)

def make_request(method, endpoint, data=None, retry_count=0):
    """HTTP-Request mit Retry-Logik"""
    # Query Parameter Ergänzung für bessere Kompatibilität (Hostsharing Header-Stripping)
    url = f"{API_URL}/{endpoint}"
    
    # Wir senden den Key im Header UND (für Hostsharing) als Parameter
    params = {'api_key': API_KEY}
    headers = {
        'X-API-Key': API_KEY,
        'Content-Type': 'application/json'
    }
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=10)
        elif method == 'POST':
            response = requests.post(url, headers=headers, params=params, json=data, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        if retry_count < MAX_RETRIES:
            log('WARNING', f"Request failed, retry {retry_count + 1}/{MAX_RETRIES}: {e}")
            time.sleep(RETRY_DELAY)
            return make_request(method, endpoint, data, retry_count + 1)
        else:
            log('ERROR', f"Request failed after {MAX_RETRIES} retries: {e}")
            return None

# ===== GPIO SWITCHES =====

def sync_gpio_switches():
    """Synchronisiert GPIO-Schalter und steuert den Hotspot"""
    global last_hotspot_state
    
    try:
        # Status von API holen
        switches = make_request('GET', 'gpio-switches')
        
        if not switches:
            return

        for sw in switches:
            name = sw.get('name')   # z.B. "Bewässerung 1" oder "Zusatz"
            state = sw.get('state') # True (AN) oder False (AUS)
            
          # --- SPEZIALFALL: HOTSPOT STEUERUNG ("Zusatz") ---
            if name == "Zusatz":
                # Wir prüfen, ob sich der Status geändert hat
                if state != last_hotspot_state:
                    
                    if state == True:
                        log('INFO', "📡 Schalter 'Zusatz' AN -> Starte HOTSPOT")
                        
                        # Pin 25 schalten
                        if GPIO_SWITCHES.get(name):
                            GPIO.output(GPIO_SWITCHES[name], GPIO.HIGH)
                            
                        # 1. Haus-WLAN sicherheitshalber trennen (falls noch an)
                        HOME_WLAN = os.getenv("WIFI_SSID_HOME")
                        if HOME_WLAN:
                            subprocess.run(['sudo', 'nmcli', 'connection', 'down', HOME_WLAN])
                        time.sleep(1)
                        
                        # 2. Hotspot starten
                        HOTSPOT_SSID = os.getenv("WIFI_SSID_HOTSPOT")
                        if HOTSPOT_SSID:
                            subprocess.run(['sudo', 'nmcli', 'connection', 'up', HOTSPOT_SSID])
                        
                    else:
                        log('INFO', "🏠 Schalter 'Zusatz' AUS -> Verbinde mit HAUS-WLAN")
                        
                        # Pin 25 aus
                        if GPIO_SWITCHES.get(name):
                            GPIO.output(GPIO_SWITCHES[name], GPIO.LOW)
                        
                        # 3. Zurück zum Haus-WLAN über die UUID
                        WIFI_UUID = os.getenv("WIFI_UUID")
                        if WIFI_UUID:
                            cmd = ['sudo', 'nmcli', 'connection', 'up', 'uuid', WIFI_UUID]
                        else:
                            log('ERROR', "❌ WIFI_UUID nicht in .env gefunden!")
                            continue
                        
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        
                        # Prüfen ob es geklappt hat und Fehler ins Log schreiben
                        if result.returncode == 0:
                            log('INFO', "✅ Erfolgreich mit FritzBox verbunden")
                        else:
                            log('ERROR', f"❌ Fehler beim Verbinden: {result.stderr}")

                    # Status merken
                    last_hotspot_state = state
                
                # Wir sind fertig mit "Zusatz", weiter zum nächsten Schalter
                continue

            # --- NORMALE GPIO LOGIK (für Bewässerung etc.) ---
            pin = GPIO_SWITCHES.get(name)
            
            if pin:
                target_state = GPIO.HIGH if state else GPIO.LOW 
                
                # Aktuellen Status lesen um unnötiges Schalten zu vermeiden
                current_state = GPIO.input(pin)
                
                if current_state != target_state:
                    GPIO.output(pin, target_state)
                    log('INFO', f"🔌 Schalter '{name}' (Pin {pin}) -> {'EIN' if state else 'AUS'}")
                    
    except Exception as e:
        log('ERROR', f"Fehler bei GPIO-Sync: {e}")

# ===== VENTILATION =====

def get_ventilation_phases(config):
    """Berechnet alle aktiven Lüftungsphasen für heute"""
    phases = []
    
    try:
        tz = pytz.timezone('Europe/Zurich')
        now = datetime.now(tz)
        today = now.date()
        
        # Sonnenauf-/untergang berechnen
        s = sun(LOCATION.observer, date=today, tzinfo=tz)
        sunrise = s['sunrise']
        sunset = s['sunset']
        
        # 1. Morgens: 1h nach Sonnenaufgang, 20 Min
        if config.get('enabled'):
            start = sunrise + timedelta(hours=1)
            end = start + timedelta(minutes=20)
            phases.append({'name': 'Morgens', 'start': start, 'end': end})
            
        # 2. Mittags: 12:00, 20 Min
        if config.get('midday_enabled'):
            start = datetime.combine(today, datetime.strptime("12:00", "%H:%M").time()).replace(tzinfo=tz)
            end = start + timedelta(minutes=20)
            phases.append({'name': 'Mittags', 'start': start, 'end': end})
            
        # 3. Abends: 1h vor Sonnenuntergang, 20 Min
        if config.get('evening_enabled'):
            start = sunset - timedelta(hours=1)
            end = start + timedelta(minutes=20)
            phases.append({'name': 'Abends', 'start': start, 'end': end})
            
        # 4. Individuelle Phasen
        for custom in config.get('custom_phases', []):
            if custom.get('enabled'):
                try:
                    start_time = datetime.strptime(custom['start_time'], "%H:%M:%S").time()
                    end_time = datetime.strptime(custom['end_time'], "%H:%M:%S").time()
                    
                    start = datetime.combine(today, start_time).replace(tzinfo=tz)
                    end = datetime.combine(today, end_time).replace(tzinfo=tz)
                    
                    if end < start:
                        end += timedelta(days=1)
                        
                    phases.append({'name': custom.get('name', 'Custom'), 'start': start, 'end': end})
                except Exception as e:
                    log('WARNING', f"Fehler bei Custom Phase: {e}")
                    
        return phases
        
    except Exception as e:
        log('ERROR', f"Fehler bei Phasen-Berechnung: {e}")
        return []

def check_ventilation():
    """Prüft ob Lüftung gestartet/beendet werden soll (Erweitert)"""
    global ventilation_active
    
    # Ventilation Config von API holen
    config = make_request('GET', 'ventilation')
    if not config:
        return

    phases = get_ventilation_phases(config)
    now = datetime.now(pytz.timezone('Europe/Zurich'))
    
    # Prüfen ob wir in IRGENDEINER Phase sind
    active_phase = None
    for phase in phases:
        if phase['start'] <= now < phase['end']:
            active_phase = phase['name']
            break
    
    # LOGIK:
    
    # A) Starten (In Phase, aber noch nicht aktiv)
    if active_phase and not ventilation_active:
        log('INFO', f"🌬️ Starte Lüftung: {active_phase}")
        make_request('POST', 'command', {'command': 'OPEN_ALL'})
        make_request('POST', 'ventilation/mark-run')
        ventilation_active = True
        
    # B) Beenden (Nicht mehr in Phase, aber noch aktiv)
    elif not active_phase and ventilation_active:
        log('INFO', "🛑 Beende Lüftung (Zeit abgelaufen)")
        make_request('POST', 'command', {'command': 'CLOSE_ALL'})
        make_request('POST', 'command', {'command': 'SET_MODE', 'parameters': {'mode': 'AUTO'}})
        ventilation_active = False

# ===== GATE AUTO MODE =====

# Cache für Gate Auto Settings (alle 10 Sekunden aktualisieren)
gate_auto_cache = {}
gate_auto_cache_time = None
GATE_AUTO_CACHE_DURATION = 10  # 10 Sekunden

# Cache für Gate Enabled Status (Wintermodus)
gate_enabled_cache = {}
gate_enabled_cache_time = None

def get_gate_auto_settings():
    """Holt Gate Auto-Mode Einstellungen von der API (mit Caching)"""
    global gate_auto_cache, gate_auto_cache_time
    
    # Prüfe ob Cache noch gültig ist
    now = datetime.now()
    if gate_auto_cache_time and (now - gate_auto_cache_time).total_seconds() < GATE_AUTO_CACHE_DURATION:
        return gate_auto_cache
    
    # Hole neue Einstellungen von API
    try:
        settings = make_request('GET', 'gate-auto-mode')
        if settings:
            gate_auto_cache = settings
            gate_auto_cache_time = now
            log('DEBUG', f"Gate Auto Settings aktualisiert: {settings}")
            return settings
    except Exception as e:
        log('WARNING', f"Konnte Gate Auto Settings nicht abrufen: {e}")
    
    # Fallback: Alle Tore auf AUTO
    if not gate_auto_cache:
        gate_auto_cache = {
            'GH1_VORNE': True,
            'GH1_HINTEN': True,
            'GH2_VORNE': True,
            'GH2_HINTEN': True,
            'GH3_VORNE': True,
            'GH3_HINTEN': True
        }
    
    return gate_auto_cache

def get_gate_enabled_settings():
    """Holt Gate Enabled Status (Wintermodus) von der API (mit Caching)"""
    global gate_enabled_cache, gate_enabled_cache_time
    
    now = datetime.now()
    if gate_enabled_cache_time and (now - gate_enabled_cache_time).total_seconds() < GATE_AUTO_CACHE_DURATION:
        return gate_enabled_cache
    
    try:
        settings = make_request('GET', 'gate-enabled')
        if settings:
            gate_enabled_cache = settings
            gate_enabled_cache_time = now
            log('DEBUG', f"Gate Enabled Status aktualisiert: {settings}")
            return settings
    except Exception as e:
        log('WARNING', f"Konnte Gate Enabled Status nicht abrufen: {e}")
    
    # Fallback: Alle Tore aktiv
    if not gate_enabled_cache:
        gate_enabled_cache = {
            'GH1_VORNE': True, 'GH1_HINTEN': True,
            'GH2_VORNE': True, 'GH2_HINTEN': True,
            'GH3_VORNE': True, 'GH3_HINTEN': True
        }
    
    return gate_enabled_cache

# ===== SMART POLLING =====

def calculate_poll_interval():
    """Berechnet intelligentes Polling-Intervall"""
    global last_command_time
    
    # Nach Befehl: schnell abfragen
    if last_command_time and (datetime.now() - last_command_time) < timedelta(seconds=60):
        return INTERVAL_FAST
    
    # Temperatur-basiert (nur wenn Sensoren verfügbar)
    if SENSORS_AVAILABLE and gh_system:
        temp_in = gh_system.get_temp_in()
        target = gh_system.target_temp
        
        if temp_in is not None and abs(temp_in - target) > TEMP_THRESHOLD:
            # Weit vom Sollwert entfernt -> langsamer
            return INTERVAL_SLOW
    
    # Normal
    return INTERVAL_NORMAL

def sync_settings():
    """Lädt Settings von API beim Start (einmalig)"""
    global INTERVAL_FAST, INTERVAL_NORMAL, INTERVAL_SLOW, TEMP_THRESHOLD
    global MAX_RETRIES, RETRY_DELAY, LOCATION
    
    try:
        response = make_request('GET', 'settings')
        if response:
            settings = response
            
            # Polling-Intervalle
            if 'polling' in settings:
                INTERVAL_FAST = settings['polling']['INTERVAL_FAST']['value']
                INTERVAL_NORMAL = settings['polling']['INTERVAL_NORMAL']['value']
                INTERVAL_SLOW = settings['polling']['INTERVAL_SLOW']['value']
                log('INFO', f"Polling-Intervalle: Fast={INTERVAL_FAST}s, Normal={INTERVAL_NORMAL}s, Slow={INTERVAL_SLOW}s")
            
            # Temperatur
            if 'temperature' in settings:
                TEMP_THRESHOLD = settings['temperature']['TEMP_THRESHOLD']['value']
                
                # Aktualisiere gh_system Settings
                if gh_system:
                    gh_system.target_temp = settings['temperature']['DEFAULT_TARGET_TEMP']['value']
                    gh_system.temp_hysteresis = settings['temperature']['TEMP_HYSTERESIS']['value']
                    log('INFO', f"Temperatur-Settings: Target={gh_system.target_temp}°C, Hysterese=±{gh_system.temp_hysteresis}°C")
            
            # Motor
            if 'motor' in settings and gh_system:
                gh_system.motor_runtime_open = settings['motor']['MOTOR_RUNTIME_OPEN']['value']
                gh_system.motor_runtime_close = settings['motor']['MOTOR_RUNTIME_CLOSE']['value']
                log('INFO', f"Motor-Zeiten: Öffnen={gh_system.motor_runtime_open}s, Schließen={gh_system.motor_runtime_close}s")
            
            # Netzwerk
            if 'network' in settings:
                MAX_RETRIES = settings['network']['MAX_RETRIES']['value']
                RETRY_DELAY = settings['network']['RETRY_DELAY']['value']
            
            # Standort
            if 'location' in settings:
                lat = settings['location']['LOCATION_LAT']['value']
                lon = settings['location']['LOCATION_LON']['value']
                LOCATION = LocationInfo("Luzernenhof", "Germany", "Europe/Berlin", lat, lon)
            
            log('SUCCESS', "✅ Settings beim Start geladen")
            return True
            
    except Exception as e:
        log('WARNING', f"Settings-Sync fehlgeschlagen: {e}")
        return False


# ===== COMMAND EXECUTION =====

def execute_command(cmd):
    """Führt einen Befehl aus"""
    global last_command_time
    
    command = cmd['command']
    parameters = cmd.get('parameters')
    cmd_id = cmd['id']

    # Sicherheitsprüfung: Parameter von JSON-String in Dictionary umwandeln, falls nötig
    if isinstance(parameters, str):
        try:
            parameters = json.loads(parameters)
        except json.JSONDecodeError:
            log('WARNING', f"Parameter für Befehl {command} (ID: {cmd_id}) sind kein valides JSON: {parameters}")
    
    log('INFO', f"Führe Befehl aus: {command} (ID: {cmd_id})")
    
    try:
        # Globale Befehle
        if command == 'OPEN_ALL':
            gh_system.run_sequence('OPEN', get_gate_enabled_settings())
        
        elif command == 'CLOSE_ALL':
            gh_system.run_sequence('CLOSE', get_gate_enabled_settings())
        
        elif command == 'SET_MODE':
            if parameters and 'mode' in parameters:
                gh_system.mode = parameters['mode']
                log('INFO', f"Modus geändert auf: {parameters['mode']}")

                # NEU: Prüfe, ob auch eine Temperatur mitgesendet wurde
                if 'temp' in parameters and parameters['temp'] is not None:
                    new_temp = float(parameters['temp'])
                    gh_system.target_temp = new_temp
                    log('INFO', f"Ziel-Temperatur gesetzt auf: {new_temp}°C")
            else:
                raise ValueError("SET_MODE requires 'mode' parameter")
        
        # Globale Teilöffnung: PARTIAL_20, PARTIAL_40, etc.
        elif command.startswith('PARTIAL_') and command.count('_') == 1:
            percentage = int(command.split('_')[1])
            enabled_settings = get_gate_enabled_settings()
            gh_system.run_sequence_partial('OPEN', percentage, enabled_settings)
            log('INFO', f"Alle aktiven Tore {percentage}% geöffnet")
        
        # Einzelmotor-Steuerung: OPEN_GH1_VORNE, CLOSE_GH2_HINTEN, etc.
        elif command.startswith('OPEN_GH') and command.count('_') == 2:
            motor_name = '_'.join(command.split('_')[1:])  # z.B. GH1_VORNE
            enabled = get_gate_enabled_settings().get(motor_name, True)
            if not enabled:
                raise ValueError(f"Tor {motor_name} ist deaktiviert (Wintermodus)")
            gh_system.move_motor(motor_name, 'OPEN')
            log('INFO', f"Motor {motor_name} geöffnet")
        
        elif command.startswith('CLOSE_GH') and command.count('_') == 2:
            motor_name = '_'.join(command.split('_')[1:])
            enabled = get_gate_enabled_settings().get(motor_name, True)
            if not enabled:
                raise ValueError(f"Tor {motor_name} ist deaktiviert (Wintermodus)")
            gh_system.move_motor(motor_name, 'CLOSE')
            log('INFO', f"Motor {motor_name} geschlossen")
        
        # Einzelmotor Teilöffnung: PARTIAL_GH1_VORNE_40
        # Bedeutet: Gehe zu Position 40% (Zielposition)
        elif command.startswith('PARTIAL_GH') and command.count('_') == 3:
            parts = command.split('_')
            motor_name = f"{parts[1]}_{parts[2]}"  # GH1_VORNE
            enabled = get_gate_enabled_settings().get(motor_name, True)
            if not enabled:
                raise ValueError(f"Tor {motor_name} ist deaktiviert (Wintermodus)")
            target_position = int(parts[3])  # Zielposition (0-100%)
            
            # Aktuelle Position holen
            current_position = gh_system.gate_positions.get(motor_name, 0)
            
            if target_position == current_position:
                log('INFO', f"Motor {motor_name} bereits bei {target_position}%")
                make_request('POST', f"command/{cmd_id}/complete")
                return
            
            # Die Richtung wird an move_motor_partial übergeben, dort aber für 
            # absolute Positionsanfahrt intern neu berechnet. Wir nutzen 
            # 'OPEN'/'CLOSE' hier nur als Platzhalter für das Argument.
            placeholder_direction = 'OPEN' if target_position > current_position else 'CLOSE'
            
            log('INFO', f"Motor {motor_name}: {current_position}% → {target_position}%")
            gh_system.move_motor_partial(motor_name, placeholder_direction, target_position)
            
            # WICHTIG: interne Position wird in move_motor_partial bereits aktualisiert.
            # Wir stellen nur sicher, dass der Client den neuen Wert kennt.
            gh_system.gate_positions[motor_name] = target_position
        
        elif command == 'RESTART':
            log('INFO', "🔄 Neustart-Befehl empfangen. Lade Einstellungen neu...")
            sync_settings()
            log('SUCCESS', "✅ Einstellungen neu geladen und aktiv.")
        
        else:
            raise ValueError(f"Unknown command: {command}")
        
        # Befehl als completed markieren
        make_request('POST', f"command/{cmd_id}/complete")
        log('INFO', f"Befehl abgeschlossen: {command}")
        
        last_command_time = datetime.now()
        
    except Exception as e:
        log('ERROR', f"Befehl fehlgeschlagen: {command} - {e}")
        make_request('POST', f"command/{cmd_id}/fail", {'error': str(e)})

# ===== STATUS UPDATE =====

def send_status():
    """Sendet aktuellen Status an API"""
    if not gh_system:
        return
    
    status_data = {
        'temp_indoor': gh_system.get_temp_in(),
        'temp_outdoor': gh_system.get_temp_out(),
        'mode': gh_system.mode,
        'last_action': gh_system.last_action,
        'is_busy': gh_system.is_busy,
        'gate_positions': gh_system.gate_positions  # Tor-Positionen
    }
    
    result = make_request('POST', 'status', status_data)
    
    if result:
        log('DEBUG', f"Status gesendet: {status_data['mode']}, Busy: {status_data['is_busy']}")

def fetch_remote_status():
    """Holt den letzten bekannten Status von der API"""
    try:
        data = make_request('GET', 'status')
        if data and 'gate_positions' in data:
            # Update internal state
            for motor, pos in data['gate_positions'].items():
                if motor in gh_system.gate_positions:
                    gh_system.gate_positions[motor] = int(pos)
            log('INFO', f"Status wiederhergestellt: {gh_system.gate_positions}")
    except Exception as e:
        log('WARNING', f"Konnte Status nicht wiederherstellen: {e}")

# ===== MAIN LOOP =====

def poll_commands():
    """Fragt API nach neuen Befehlen ab"""
    commands = make_request('GET', 'command')
    
    if commands is None:
        return
    
    if len(commands) == 0:
        log('DEBUG', "Keine neuen Befehle")
        return
    
    log('INFO', f"{len(commands)} neue(r) Befehl(e)")
    
    for cmd in commands:
        execute_command(cmd)

def main():
    global gh_system, running
    
    log('INFO', "🌱 Gewächshaus API Client startet...")
    log('INFO', f"API: {API_URL}")
    log('INFO', f"Koordinaten: {LOCATION.latitude}°N, {LOCATION.longitude}°E")
    
    # Greenhouse System initialisieren
    gh_system = init_global_system()
    
    # Settings von API laden
    sync_settings()
    
    # Status wiederherstellen
    fetch_remote_status()
    
    # Initial Status senden
    send_status()
    
    # Main Loop
    while running:
        try:
            # Befehle abrufen
            poll_commands()
            
            # Status senden
            send_status()
            
            # Automatik-Logik (falls aktiviert)
            # Hole Gate Auto Settings und Gate Enabled Status
            gate_settings = get_gate_auto_settings()
            gate_enabled = get_gate_enabled_settings()
            gh_system.check_auto_logic(gate_settings, gate_enabled)
            
            # Ventilation prüfen und ausführen
            check_ventilation()
            
            # GPIO-Schalter synchronisieren
            sync_gpio_switches()
            
            # Nächstes Intervall berechnen
            interval = calculate_poll_interval()
            log('DEBUG', f"Warte {interval}s bis zum nächsten Poll...")
            
            # Sleep mit Interrupt-Check
            for _ in range(interval):
                if not running:
                    break
                time.sleep(1)
        
        except Exception as e:
            log('ERROR', f"Unerwarteter Fehler: {e}")
            time.sleep(60)  # Bei Fehler 60s warten
    
    log('INFO', "🛑 Client beendet")

if __name__ == '__main__':
    main()
