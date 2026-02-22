#!/usr/bin/env python3

import asyncio
import threading
import time
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, redirect
import RPi.GPIO as GPIO

# Lade Umgebungsvariablen
load_dotenv()

# Sensor-Import optional (falls 1-Wire Module nicht geladen)
try:
    from w1thermsensor import W1ThermSensor
    SENSORS_AVAILABLE = True
except Exception as e:
    print(f"⚠️  Warnung: Temperatursensoren nicht verfügbar: {e}")
    print("   System läuft trotzdem, aber ohne Temperaturmessung.")
    SENSORS_AVAILABLE = False
    W1ThermSensor = None

# --- KONFIGURATION ---
WEB_PORT = 8080
DEFAULT_TARGET_TEMP = 24.0  # Wunschtemperatur
TEMP_HYSTERESIS = 2.0       # Toleranzbereich (+/- 2 Grad)
# Motor-Laufzeiten (gemessen)
MOTOR_RUNTIME_OPEN = 135     # 135 Sekunden für vollständiges Öffnen (0% → 100%)
MOTOR_RUNTIME_CLOSE = 128    # 128 Sekunden für vollständiges Schließen (100% → 0%)

# API-URL für Datenbank-Sync
API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")

# Sensor IDs (leer lassen für automatische Erkennung)
SENSOR_ID_INDOOR = ""
SENSOR_ID_OUTDOOR = ""

# --- GPIO SETUP ---
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Pin-Definitionen (Relais)
MOTORS = {
    "GH1_VORNE": [17, 27],
    "GH1_HINTEN": [22, 10],
    "GH2_VORNE": [9, 11],
    "GH2_HINTEN": [18, 23],
    "GH3_VORNE": [13, 19],
    "GH3_HINTEN": [26, 21]
}

# Zusätzliche GPIO-Schalter (Bewässerung & Zusatz)
GPIO_SWITCHES = {
    "Bewässerung 1": 20,
    "Bewässerung 2": 16,
    "Bewässerung 3": 12,
    "Zusatz": 25
}

# Setup aller Relais-Pins
for pins in MOTORS.values():
    GPIO.setup(pins[0], GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(pins[1], GPIO.OUT, initial=GPIO.HIGH)

# Setup aller GPIO-Switch Pins
for pin in GPIO_SWITCHES.values():
    GPIO.setup(pin, GPIO.OUT, initial=GPIO.HIGH)  # HIGH = Aus (Active Low)

# --- GEWÄCHSHAUS SYSTEM ---
class GreenhouseSystem:
    def __init__(self):
        self.mode = "MANUAL"  # AUTO, MANUAL
        self.target_temp = DEFAULT_TARGET_TEMP
        self.status_text = "System bereit"
        self.last_action = "Keine"
        self.last_check = datetime.now()
        self.is_busy = False
        
        # Settings (werden von API geladen, Fallback auf Konstanten)
        self.temp_hysteresis = TEMP_HYSTERESIS
        self.motor_runtime_open = MOTOR_RUNTIME_OPEN
        self.motor_runtime_close = MOTOR_RUNTIME_CLOSE
        
        # Gate Position Tracking (0-100%)
        self.gate_positions = {
            "GH1_VORNE": 0,
            "GH1_HINTEN": 0,
            "GH2_VORNE": 0,
            "GH2_HINTEN": 0,
            "GH3_VORNE": 0,
            "GH3_HINTEN": 0
        }
        
        # Sensoren initialisieren
        self.sensor_in = None
        self.sensor_out = None
        self._init_sensors()
        
        # Settings von API laden
        self._load_settings_from_api()
        
        # Gate Positionen aus DB laden
        self._load_gate_positions_from_db()
    
    def _load_settings_from_api(self):
        """Lädt Settings von der REST API"""
        try:
            response = requests.get(
                f"{API_URL}/settings",
                params={'api_key': API_KEY},
                headers={'X-API-Key': API_KEY},
                timeout=5
            )
            
            if response.status_code == 200:
                settings = response.json()
                
                # Temperatur-Settings
                if 'temperature' in settings:
                    self.target_temp = settings['temperature']['DEFAULT_TARGET_TEMP']['value']
                    self.temp_hysteresis = settings['temperature']['TEMP_HYSTERESIS']['value']
                    print(f"✅ Settings geladen: Target={self.target_temp}°C, Hysterese=±{self.temp_hysteresis}°C")
                
                # Motor-Settings
                if 'motor' in settings:
                    self.motor_runtime_open = settings['motor']['MOTOR_RUNTIME_OPEN']['value']
                    self.motor_runtime_close = settings['motor']['MOTOR_RUNTIME_CLOSE']['value']
                    print(f"✅ Motor-Zeiten: Öffnen={self.motor_runtime_open}s, Schließen={self.motor_runtime_close}s")
            else:
                print(f"⚠️  Konnte Settings nicht laden (HTTP {response.status_code}), verwende Defaults")
                
        except Exception as e:
            print(f"⚠️  Fehler beim Laden der Settings: {e}")
            print("   Verwende Default-Werte aus Konfiguration")


    def _load_gate_positions_from_db(self):
        """Lädt gespeicherte Tor-Positionen aus der Datenbank"""
        try:
            status_params = {'api_key': API_KEY}
            headers = {'X-API-Key': API_KEY}
            
            response = requests.get(
                f"{API_URL}/status",
                params=status_params,
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                # Hole Gate-Status aus der gate_status Tabelle
                gate_response = requests.get(
                    f"{API_URL}/gate-status",
                    params=status_params,
                    headers=headers,
                    timeout=5
                )
                
                if gate_response.status_code == 200:
                    gates = gate_response.json()
                    for gate in gates:
                        motor_name = gate.get('motor_name')
                        position = gate.get('position', 0)
                        if motor_name in self.gate_positions:
                            self.gate_positions[motor_name] = position
                            print(f"✅ Gate {motor_name}: {position}% (aus DB geladen)")
                else:
                    print("⚠️  Konnte Gate-Status nicht laden, verwende 0%")
            else:
                print("⚠️  API nicht erreichbar, verwende 0% für alle Tore")
                
        except Exception as e:
            print(f"⚠️  Fehler beim Laden der Gate-Positionen: {e}")
            print("   Verwende 0% für alle Tore")
    
    def _save_gate_position_to_db(self, motor_name, position):
        """Speichert Tor-Position in der Datenbank"""
        try:
            requests.post(
                f"{API_URL}/gate-status",
                params={'api_key': API_KEY},
                headers={'X-API-Key': API_KEY},
                json={'motor_name': motor_name, 'position': position},
                timeout=5
            )
        except Exception as e:
            print(f"⚠️  Fehler beim Speichern der Position für {motor_name}: {e}")
    
    def _init_sensors(self):
        if not SENSORS_AVAILABLE:
            print("⚠️  Sensoren übersprungen (1-Wire Module nicht geladen)")
            return
            
        try:
            all_sensors = W1ThermSensor.get_available_sensors()
            if len(all_sensors) >= 1:
                if SENSOR_ID_INDOOR:
                    self.sensor_in = W1ThermSensor(sensor_id=SENSOR_ID_INDOOR)
                else:
                    self.sensor_in = all_sensors[0]
            
            if len(all_sensors) >= 2:
                if SENSOR_ID_OUTDOOR:
                    self.sensor_out = W1ThermSensor(sensor_id=SENSOR_ID_OUTDOOR)
                else:
                    self.sensor_out = all_sensors[1]
                    
            print(f"✓ Sensoren: Innen={self.sensor_in}, Außen={self.sensor_out}")
        except Exception as e:
            print(f"⚠ Sensor-Fehler: {e}")

    def get_temp_in(self):
        try:
            if self.sensor_in:
                return round(self.sensor_in.get_temperature(), 1)
        except:
            pass
        return None

    def get_temp_out(self):
        try:
            if self.sensor_out:
                return round(self.sensor_out.get_temperature(), 1)
        except:
            pass
        return None

    def move_motor(self, motor_name, direction):
        """Bewegt einen Motor (blockierend) - Position-aware"""
        pins = MOTORS.get(motor_name)
        if not pins:
            return

        pin_auf = pins[0]
        pin_zu = pins[1]
        
        # Hole aktuelle Position
        current_position = self.gate_positions.get(motor_name, 0)
        
        # Berechne Zielposition und Basis-Laufzeit
        if direction == "OPEN":
            target_position = 100
            base_runtime = self.motor_runtime_open
        elif direction == "CLOSE":
            target_position = 0
            base_runtime = self.motor_runtime_close
        else:
            return
        
        # Berechne benötigte Bewegung
        movement_percentage = abs(target_position - current_position)
        
        # Wenn bereits an Zielposition, nichts tun
        if movement_percentage <= 0:
            print(f"→ Motor {motor_name}: Bereits bei {current_position}%, überspringe {direction}")
            return
        
        # Berechne tatsächliche Laufzeit basierend auf benötigter Bewegung
        runtime = int(base_runtime * (movement_percentage / 100))
        
        print(f"→ Motor {motor_name}: {direction} von {current_position}% → {target_position}% ({movement_percentage}%, {runtime}s)")
        
        # Alles aus
        GPIO.output(pin_auf, GPIO.HIGH)
        GPIO.output(pin_zu, GPIO.HIGH)
        time.sleep(0.5)

        # Schalten
        if direction == "OPEN":
            GPIO.output(pin_auf, GPIO.LOW)
        elif direction == "CLOSE":
            GPIO.output(pin_zu, GPIO.LOW)
        
        # Warten (nur so lange wie nötig!)
        time.sleep(runtime)

        # Stoppen
        GPIO.output(pin_auf, GPIO.HIGH)
        GPIO.output(pin_zu, GPIO.HIGH)
        time.sleep(0.5)
        
        # Position aktualisieren
        self.gate_positions[motor_name] = target_position
        
        # In DB speichern
        self._save_gate_position_to_db(motor_name, target_position)

    def run_sequence(self, command):
        """Führt Befehl für alle Motoren PARALLEL aus"""
        if self.is_busy:
            return "System ist beschäftigt!"
        
        self.is_busy = True
        self.status_text = f"Führe aus: ALLES {command} (parallel)..."
        
        threads = []
        errors = []
        
        def motor_wrapper(motor_name):
            """Wrapper to catch exceptions in threads"""
            try:
                self.move_motor(motor_name, command)
            except Exception as e:
                errors.append(f"{motor_name}: {e}")
        
        try:
            # Start all motors in parallel
            for name in MOTORS.keys():
                thread = threading.Thread(
                    target=motor_wrapper,
                    args=(name,),
                    name=f"Motor-{name}"
                )
                threads.append(thread)
                thread.start()
            
            # Wait for all to complete (with timeout)
            max_runtime = max(self.motor_runtime_open, self.motor_runtime_close)
            for thread in threads:
                thread.join(timeout=max_runtime + 15)
                if thread.is_alive():
                    errors.append(f"{thread.name}: Timeout")
            
            if errors:
                error_msg = "; ".join(errors)
                self.status_text = f"Fehler: {error_msg}"
                return f"Fehler: {error_msg}"
            
            self.status_text = f"Fertig: ALLES {command} (parallel)"
            self.last_action = f"ALLES {command} um {datetime.now().strftime('%H:%M:%S')}"
            return "OK"
        except Exception as e:
            self.status_text = f"Fehler: {e}"
            return f"Fehler: {e}"
        finally:
            self.is_busy = False
    
    def run_sequence_auto(self, command, gate_auto_settings=None):
        """Führt Befehl nur für Motoren mit Auto=ON PARALLEL aus"""
        if self.is_busy:
            return "System ist beschäftigt!"
        
        # Wenn keine Settings übergeben, alle Tore steuern (Fallback)
        if gate_auto_settings is None:
            gate_auto_settings = {name: True for name in MOTORS.keys()}
        
        self.is_busy = True
        
        # Filtere nur Tore mit Auto=ON
        auto_enabled_gates = [name for name in MOTORS.keys() 
                             if gate_auto_settings.get(name, True)]
        
        if not auto_enabled_gates:
            self.status_text = "Keine Tore im Auto-Modus"
            self.is_busy = False
            return "Keine Tore im Auto-Modus"
        
        self.status_text = f"Führe aus: AUTO {command} ({len(auto_enabled_gates)} Tore, parallel)..."
        
        threads = []
        errors = []
        
        def motor_wrapper(motor_name):
            """Wrapper to catch exceptions in threads"""
            try:
                self.move_motor(motor_name, command)
            except Exception as e:
                errors.append(f"{motor_name}: {e}")
        
        try:
            # Start all auto-enabled motors in parallel
            for name in auto_enabled_gates:
                thread = threading.Thread(
                    target=motor_wrapper,
                    args=(name,),
                    name=f"Motor-{name}"
                )
                threads.append(thread)
                thread.start()
            
            # Wait for all to complete (with timeout)
            max_runtime = max(self.motor_runtime_open, self.motor_runtime_close)
            for thread in threads:
                thread.join(timeout=max_runtime + 15)
                if thread.is_alive():
                    errors.append(f"{thread.name}: Timeout")
            
            if errors:
                error_msg = "; ".join(errors)
                self.status_text = f"Fehler: {error_msg}"
                return f"Fehler: {error_msg}"
            
            gates_list = ", ".join([n.replace('_', ' ') for n in auto_enabled_gates])
            self.status_text = f"Fertig: AUTO {command} ({gates_list}, parallel)"
            self.last_action = f"AUTO {command} um {datetime.now().strftime('%H:%M:%S')}"
            return "OK"
        except Exception as e:
            self.status_text = f"Fehler: {e}"
            return f"Fehler: {e}"
        finally:
            self.is_busy = False

    def move_motor_partial(self, motor_name, direction, percentage):
        """Bewegt einen Motor zu einer absoluten Zielposition (percentage = Zielposition 0-100%)"""
        pins = MOTORS.get(motor_name)
        if not pins:
            return

        pin_auf = pins[0]
        pin_zu = pins[1]
        
        # Hole aktuelle Position
        current_position = self.gate_positions.get(motor_name, 0)
        
        # Zielposition ist der percentage Parameter
        target_position = percentage
        
        # Berechne benötigte Bewegung und Richtung
        movement_needed = target_position - current_position
        
        # Wenn bereits an Zielposition, nichts tun
        if movement_needed == 0:
            print(f"→ Motor {motor_name}: Bereits bei {current_position}%, überspringe")
            return
        
        # Bestimme Richtung basierend auf Bewegung
        if movement_needed > 0:
            actual_direction = "OPEN"
            base_runtime = self.motor_runtime_open
            movement_percentage = movement_needed
        else:
            actual_direction = "CLOSE"
            base_runtime = self.motor_runtime_close
            movement_percentage = abs(movement_needed)
        
        # Berechne Laufzeit basierend auf tatsächlicher Bewegung
        runtime = int(base_runtime * (movement_percentage / 100))

        print(f"→ Motor {motor_name}: {actual_direction} von {current_position}% → {target_position}% ({movement_percentage}%, {runtime}s)")
        
        # Alles aus
        GPIO.output(pin_auf, GPIO.HIGH)
        GPIO.output(pin_zu, GPIO.HIGH)
        time.sleep(0.5)

        # Schalten basierend auf tatsächlicher Richtung
        if actual_direction == "OPEN":
            GPIO.output(pin_auf, GPIO.LOW)
        elif actual_direction == "CLOSE":
            GPIO.output(pin_zu, GPIO.LOW)
        
        # Warten (nur so lange wie nötig)
        time.sleep(runtime)

        # Stoppen
        GPIO.output(pin_auf, GPIO.HIGH)
        GPIO.output(pin_zu, GPIO.HIGH)
        time.sleep(0.5)
        
        # Position aktualisieren
        self.gate_positions[motor_name] = target_position
        
        # In DB speichern
        self._save_gate_position_to_db(motor_name, target_position)

    def run_sequence_partial(self, command, percentage):
        """Führt Befehl für alle Motoren teilweise PARALLEL aus"""
        if self.is_busy:
            return "System ist beschäftigt!"
        
        self.is_busy = True
        self.status_text = f"Führe aus: ALLES {command} {percentage}% (parallel)..."
        
        threads = []
        errors = []
        
        def motor_wrapper(motor_name):
            """Wrapper to catch exceptions in threads"""
            try:
                self.move_motor_partial(motor_name, command, percentage)
            except Exception as e:
                errors.append(f"{motor_name}: {e}")
        
        try:
            # Start all motors in parallel
            for name in MOTORS.keys():
                thread = threading.Thread(
                    target=motor_wrapper,
                    args=(name,),
                    name=f"Motor-{name}"
                )
                threads.append(thread)
                thread.start()
            
            # Wait for all to complete (with timeout)
            max_runtime = max(self.motor_runtime_open, self.motor_runtime_close)
            for thread in threads:
                thread.join(timeout=max_runtime + 15)
                if thread.is_alive():
                    errors.append(f"{thread.name}: Timeout")
            
            if errors:
                error_msg = "; ".join(errors)
                self.status_text = f"Fehler: {error_msg}"
                return f"Fehler: {error_msg}"
            
            self.status_text = f"Fertig: ALLES {command} {percentage}% (parallel)"
            self.last_action = f"ALLES {command} {percentage}% um {datetime.now().strftime('%H:%M:%S')}"
            return "OK"
        except Exception as e:
            self.status_text = f"Fehler: {e}"
            return f"Fehler: {e}"
        finally:
            self.is_busy = False

    def check_auto_logic(self, gate_auto_settings=None):
        """Automatik-Regelung mit stufenweiser Anpassung (5%-Schritte)"""
        if self.mode != "AUTO":
            return
        
        temp_in = self.get_temp_in()
        temp_out = self.get_temp_out()
        
        if temp_in is None:
            return
        
        self.last_check = datetime.now()
        
        # Berechne Temperatur-Abweichung vom Ziel
        temp_diff = temp_in - self.target_temp
        
        # Bestimme Basis-Schrittgröße (5% Standard)
        if temp_diff > self.temp_hysteresis:
            # Zu warm → ÖFFNEN
            base_step = 5
            direction = "OPEN"
        elif temp_diff < -self.temp_hysteresis:
            # Zu kalt → SCHLIESSEN
            base_step = 5
            direction = "CLOSE"
        else:
            # Im Toleranzbereich → Nichts tun
            print(f"🌡 AUTO: {temp_in}°C im Toleranzbereich ({self.target_temp - self.temp_hysteresis}°C - {self.target_temp + self.temp_hysteresis}°C)")
            return
        
        # Berechne Multiplikator basierend auf Außentemperatur-Differenz
        multiplier = 1  # Standard: 5% Schritte
        
        if temp_out is not None:
            temp_delta = abs(temp_in - temp_out)
            
            if temp_delta >= 15:
                multiplier = 3  # 15% Schritte bei großer Differenz
            elif temp_delta >= 10:
                multiplier = 2  # 10% Schritte bei mittlerer Differenz
            # else: multiplier = 1 (5% Schritte bei kleiner Differenz)
            
            print(f"🌡 AUTO: Innen {temp_in}°C, Außen {temp_out}°C, Differenz {temp_delta:.1f}°C → Multiplikator {multiplier}x")
        
        # Finale Schrittgröße
        step_size = base_step * multiplier
        
        # Hole aktuelle durchschnittliche Position aller Auto-Tore
        if gate_auto_settings is None:
            gate_auto_settings = {name: True for name in MOTORS.keys()}
        
        auto_enabled_gates = [name for name in MOTORS.keys() 
                             if gate_auto_settings.get(name, True)]
        
        if not auto_enabled_gates:
            return
        
        # Berechne durchschnittliche Position
        avg_position = sum(self.gate_positions.get(name, 0) for name in auto_enabled_gates) / len(auto_enabled_gates)
        
        # Berechne Zielposition
        if direction == "OPEN":
            target_position = min(100, avg_position + step_size)
        else:  # CLOSE
            target_position = max(0, avg_position - step_size)
        
        # Wenn bereits an Zielposition, nichts tun
        if int(avg_position) == int(target_position):
            print(f"🌡 AUTO: Tore bereits bei {avg_position:.0f}%, keine Änderung nötig")
            return
        
        # Führe Bewegung aus
        print(f"🌡 AUTO: {temp_in}°C → {direction} von {avg_position:.0f}% → {target_position:.0f}% ({step_size}% Schritt)")
        
        # Bewege alle Auto-Tore zur Zielposition
        self.is_busy = True
        self.status_text = f"AUTO: {direction} {avg_position:.0f}% → {target_position:.0f}% ({step_size}%)"
        
        threads = []
        errors = []
        
        def motor_wrapper(motor_name):
            """Wrapper to catch exceptions in threads"""
            try:
                # Verwende move_motor_partial mit absoluter Zielposition
                self.move_motor_partial(motor_name, direction, int(target_position))
            except Exception as e:
                errors.append(f"{motor_name}: {e}")
        
        try:
            # Start all auto-enabled motors in parallel
            for name in auto_enabled_gates:
                thread = threading.Thread(
                    target=motor_wrapper,
                    args=(name,),
                    name=f"Motor-{name}"
                )
                threads.append(thread)
                thread.start()
            
            # Wait for all to complete
            for thread in threads:
                thread.join(timeout=150)
                if thread.is_alive():
                    errors.append(f"{thread.name}: Timeout")
            
            if errors:
                error_msg = "; ".join(errors)
                self.status_text = f"AUTO Fehler: {error_msg}"
            else:
                self.status_text = f"AUTO: {target_position:.0f}% ({temp_in}°C)"
                self.last_action = f"AUTO {direction} {step_size}% um {datetime.now().strftime('%H:%M:%S')}"
                
        except Exception as e:
            self.status_text = f"AUTO Fehler: {e}"
        finally:
            self.is_busy = False

# System erstellen (Global für Flask-Routen, aber erst in main oder via init instanziiert)
gh = None

def init_global_system():
    global gh
    if gh is None:
        gh = GreenhouseSystem()
    return gh


# --- FLASK WEB-SERVER ---
app = Flask(__name__)

# HTML_TEMPLATE wurde entfernt - verwende stattdessen web/index.html als Frontend

@app.route('/')
def index():
    """Weiterleitung zum Frontend"""
    return redirect('/web/index.html')

@app.route('/web/<path:filename>')
def serve_web(filename):
    """Liefert statische Dateien aus dem web/ Verzeichnis"""
    import os
    web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
    return send_from_directory(web_dir, filename)

@app.route('/api/status')
def api_status():
    if gh is None: return jsonify({'error': 'System not initialized'}), 500
    return jsonify({
        'mode': gh.mode,
        'status': gh.status_text,
        'last_action': gh.last_action,
        'temp_in': gh.get_temp_in() or "---",
        'temp_out': gh.get_temp_out() or "---",
        'target_temp': gh.target_temp,
        'is_busy': gh.is_busy
    })

@app.route('/api/mode', methods=['POST'])
def api_mode():
    if gh is None: return jsonify({'error': 'System not initialized'}), 500
    data = request.json
    gh.mode = data.get('mode', 'MANUAL')
    return jsonify({'ok': True})

@app.route('/api/command', methods=['POST'])
def api_command():
    if gh is None: return jsonify({'error': 'System not initialized'}), 500
    data = request.json
    cmd = data.get('command')
    
    # Im Hintergrund ausführen
    threading.Thread(target=gh.run_sequence, args=(cmd,)).start()
    return jsonify({'ok': True})

@app.route('/api/target', methods=['POST'])
def api_target():
    if gh is None: return jsonify({'error': 'System not initialized'}), 500
    data = request.json
    gh.target_temp = float(data.get('target', DEFAULT_TARGET_TEMP))
    return jsonify({'ok': True})

@app.route('/api/settings')
def api_settings():
    """Proxy für Settings GET - lädt von REST API"""
    try:
        response = requests.get(
            f"{API_URL}/settings",
            params={'api_key': API_KEY},
            headers={'X-API-Key': API_KEY},
            timeout=5
        )
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Failed to load settings'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings', methods=['POST'])
def api_update_settings():
    """Proxy für Settings POST - speichert zur REST API"""
    try:
        data = request.json
        response = requests.post(
            f"{API_URL}/settings",
            params={'api_key': API_KEY},
            headers={'X-API-Key': API_KEY, 'Content-Type': 'application/json'},
            json=data,
            timeout=5
        )
        
        if response.status_code == 200:
            # Alle Einstellungen lokal neu laden
            if gh:
                gh._load_settings_from_api()
            
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Failed to update settings'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/restart-service', methods=['POST'])
def api_restart_service():
    """Startet den greenhouse_api_client Service neu, damit neue Settings geladen werden"""
    import subprocess
    try:
        result = subprocess.run(
            ['sudo', 'systemctl', 'restart', 'greenhouse_api_client.service'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return jsonify({'success': True, 'message': 'Service neu gestartet'})
        else:
            return jsonify({'success': False, 'error': result.stderr}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# --- AUTO-LOOP (Hintergrund) ---
def auto_loop():
    while True:
        try:
            if gh:
                gh.check_auto_logic()
        except Exception as e:
            print(f"Auto-Loop Fehler: {e}")
        time.sleep(300)  # Alle 5 Minuten

# --- MAIN ---
if __name__ == '__main__':
    print("=" * 50)
    print("🌱 GEWÄCHSHAUS-STEUERUNG")
    print("=" * 50)
    print(f"Web-Interface: http://luzPi:{WEB_PORT}")
    print(f"               http://192.168.178.132:{WEB_PORT}")
    print("=" * 50)
    
    # System initialisieren
    init_global_system()
    
    # Auto-Loop starten
    threading.Thread(target=auto_loop, daemon=True).start()
    
    # Web-Server starten
    app.run(host='0.0.0.0', port=WEB_PORT, debug=False)
