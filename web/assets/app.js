/**
 * Gewächshaus Web-Interface - Enhanced JavaScript
 */

const API_BASE = '/api';
let updateInterval = null;
let feedbackTimeout = null;
let isModeToggleLocked = false; // NEU: Sperre für den Modus-Schalter

// ===== INIT =====

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
});

function setupEventListeners() {
    // Login Form
    document.getElementById('login-form')?.addEventListener('submit', handleLogin);
    
    // Logout Button
    document.getElementById('logout-btn')?.addEventListener('click', handleLogout);
}

// ===== FEEDBACK SYSTEM =====

function showFeedback(message, type = 'info', duration = 5000) {
    const feedbackDiv = document.getElementById('feedback');
    
    // Clear existing timeout
    if (feedbackTimeout) {
        clearTimeout(feedbackTimeout);
    }
    
    // Set message and type
    feedbackDiv.textContent = message;
    feedbackDiv.className = `feedback-bar ${type} show`;
    
    // Auto-hide after duration
    feedbackTimeout = setTimeout(() => {
        feedbackDiv.classList.remove('show');
    }, duration);
}

// ===== AUTHENTICATION =====

async function checkAuth() {
    try {
        const response = await fetch(`${API_BASE}/auth-check`);
        
        // Check if response is ok
        if (!response.ok) {
            console.error('Auth check failed with status:', response.status);
            showLogin();
            return;
        }
        
        // Check if response has content
        const text = await response.text();
        if (!text) {
            console.error('Auth check returned empty response');
            showLogin();
            return;
        }
        
        const data = JSON.parse(text);
        
        if (data.logged_in) {
            showApp();
        } else {
            showLogin();
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        showLogin();
    }
}

async function handleLogin(e) {
    e.preventDefault();
    
    const password = document.getElementById('password').value;
    const errorDiv = document.getElementById('login-error');
    
    try {
        const response = await fetch(`${API_BASE}/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ password })
        });
        
        // Check if response is ok
        if (!response.ok) {
            errorDiv.textContent = `Server-Fehler: ${response.status}`;
            return;
        }
        
        // Check if response has content
        const text = await response.text();
        if (!text) {
            errorDiv.textContent = 'Server gab keine Antwort';
            return;
        }
        
        const data = JSON.parse(text);
        
        if (data.success) {
            showApp();
        } else {
            errorDiv.textContent = 'Falsches Passwort';
            document.getElementById('password').value = '';
        }
    } catch (error) {
        errorDiv.textContent = 'Verbindungsfehler';
        console.error('Login error:', error);
    }
}

async function handleLogout() {
    try {
        await fetch(`${API_BASE}/logout`, { method: 'POST' });
        showLogin();
    } catch (error) {
        console.error('Logout error:', error);
    }
}

function showLogin() {
    document.getElementById('login-screen').style.display = 'flex';
    document.getElementById('app').style.display = 'none';
    
    if (updateInterval) {
        clearInterval(updateInterval);
        updateInterval = null;
    }
}

function showApp() {
    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('app').style.display = 'block';
    
    // Initial load
    updateStatus();
    //loadVentilationStatus();
    loadGateAutoStatus();  // Load gate auto mode status
    
    // Auto-refresh alle 3 Sekunden
    if (!updateInterval) {
        updateInterval = setInterval(updateStatus, 3000);
    }
}

// ===== STATUS UPDATE =====

async function updateStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const data = await response.json();
        
        // Temperaturen
        document.getElementById('temp-in').textContent = 
            data.temp_indoor !== null ? `${data.temp_indoor}°C` : '---';
        document.getElementById('temp-out').textContent = 
            data.temp_outdoor !== null ? `${data.temp_outdoor}°C` : '---';
        
        // Modus
        const modeBadge = document.getElementById('mode');
        modeBadge.textContent = data.mode || 'MANUAL';
        modeBadge.className = `mode-badge ${data.mode || 'MANUAL'}`;
        
        // NEU: Temperatur-Eingabefeld nur im AUTO-Modus anzeigen
        const tempInputContainer = document.querySelector('.temp-input-container');
        if (tempInputContainer) {
            tempInputContainer.style.display = (data.mode === 'AUTO') ? 'flex' : 'none';
            // Wende die Sperre auch hier an, um ein Flackern zu verhindern
            if (!isModeToggleLocked) {
                tempInputContainer.style.display = (data.mode === 'AUTO') ? 'flex' : 'none';
            }
        }

        // Busy-State zuerst definieren
        const isBusy = data.is_busy === true || data.is_busy === 1;

        // NEU: Globalen Modus-Schalter (Checkbox) aktualisieren
        const modeCheckbox = document.getElementById('global-mode-checkbox');
        if (modeCheckbox) {
            // Überspringe die Aktualisierung, wenn der Schalter gerade erst geklickt wurde
            if (!isModeToggleLocked) {
                // Setze den Haken, wenn der Modus 'AUTO' ist
                modeCheckbox.checked = (data.mode === 'AUTO');
            }
            modeCheckbox.disabled = isBusy;
        }

        // Status
        document.getElementById('status').textContent = data.last_action || '---';
        document.getElementById('last-action').textContent = data.last_action || '---';
        
        // Andere Buttons mit dem gleichen isBusy-Status deaktivieren
        document.getElementById('btn-open').disabled = isBusy;
        document.getElementById('btn-close').disabled = isBusy;
        
        // Gate Positions aktualisieren
        if (data.gate_positions) {
            for (const [motor, position] of Object.entries(data.gate_positions)) {
                const fillEl = document.getElementById(`pos-${motor}`);
                const textEl = document.getElementById(`pos-text-${motor}`);
                if (fillEl) fillEl.style.width = `${position}%`;
                if (textEl) textEl.textContent = `${position}%`;
            }
        }
        
        // Letzte Aktualisierung
        document.getElementById('last-update').textContent = 
            new Date().toLocaleTimeString('de-DE');
        
    } catch (error) {
        console.error('Status update failed:', error);
        document.getElementById('status').textContent = 'Verbindungsfehler';
    }
}

// ===== COMMANDS =====

async function sendCommand(command, parameters = null) {
    // Bestätigung für kritische Befehle
    if (command === 'OPEN_ALL' || command === 'CLOSE_ALL') {
        const action = command === 'OPEN_ALL' ? 'ÖFFNEN' : 'SCHLIESSEN';
        if (!confirm(`Wirklich ALLE Tore ${action}?`)) {
            return;
        }
    }

    // NEU: Bei globalen Aktionen ZUERST den SET_MODE Befehl senden
    if (command === 'OPEN_ALL' || command === 'CLOSE_ALL' || command.startsWith('PARTIAL_')) {
        const modeCheckbox = document.getElementById('global-mode-checkbox');
        if (modeCheckbox && modeCheckbox.checked) {
            // 1. Visuelles Feedback: Schalter sofort auf Manuell stellen
            modeCheckbox.checked = false;
            showFeedback('ℹ️ Automatik-Modus wurde für diese manuelle Aktion deaktiviert.', 'info', 4000);

            // 1a. UI-Sperre aktivieren, um ein Zurückspringen zu verhindern
            isModeToggleLocked = true;
            setTimeout(() => {
                isModeToggleLocked = false;
                console.log("Mode toggle lock (from global command) released.");
            }, 10000); // 8 Sekunden Sperre


            // 2. Ersten Befehl senden: SET_MODE auf MANUAL
            try {
                await fetch(`${API_BASE}/command`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: 'SET_MODE', parameters: { mode: 'MANUAL' } })
                });
                console.log("Befehl 'SET_MODE: MANUAL' erfolgreich gesendet.");
            } catch (error) {
                console.error("Fehler beim Senden von 'SET_MODE: MANUAL':", error);
                showFeedback('❌ Fehler beim Umschalten in den manuellen Modus.', 'error');
                return; // Breche ab, wenn der erste Befehl fehlschlägt
            }
        }
    }
    
    // Sofortiges Feedback
    showFeedback('⏳ Befehl wird gesendet...', 'info', 2000);
    
    // 3. Zweiten (oder einzigen) Befehl senden
    try {
        const response = await fetch(`${API_BASE}/command`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ command, parameters })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showFeedback('❌ Fehler: ' + data.error, 'error');
        } else {
            // Erfolg-Feedback
            const commandName = getCommandDisplayName(command);
            showFeedback(`✓ ${commandName} an API übermittelt (wird in max. 60s ausgeführt)`, 'success');
            
            // Sofort Status aktualisieren
            updateStatus();
        }
    } catch (error) {
        console.error('Command error:', error);
        showFeedback('❌ Verbindungsfehler beim Senden des Befehls', 'error');
    }
}

function getCommandDisplayName(command) {
    const names = {
        'OPEN_ALL': 'Alle Tore ÖFFNEN',
        'CLOSE_ALL': 'Alle Tore SCHLIESSEN',
        'SET_MODE': 'Modus ändern',
        'TOGGLE_MODE': 'Modus umschalten',
        'PARTIAL_20': 'Teilöffnung 20%',
        'PARTIAL_40': 'Teilöffnung 40%',
        'PARTIAL_60': 'Teilöffnung 60%',
        'PARTIAL_80': 'Teilöffnung 80%',
        'PARTIAL_100': 'Teilöffnung 100%'
    };
    
    // Einzelmotoren
    if (command.startsWith('OPEN_GH')) {
        const motor = command.replace('OPEN_', '').replace('_', ' ');
        return `${motor} ÖFFNEN`;
    }
    if (command.startsWith('CLOSE_GH')) {
        const motor = command.replace('CLOSE_', '').replace('_', ' ');
        return `${motor} SCHLIESSEN`;
    }
    if (command.startsWith('PARTIAL_GH')) {
        const parts = command.split('_');
        const motor = `${parts[1]} ${parts[2]}`;
        const percentage = parts[3];
        return `${motor} ${percentage}% öffnen`;
    }
    
    return names[command] || command;
}

// ===== NEUE FUNKTION FÜR DEN MODUS-SCHALTER =====

function handleModeToggle(checkbox) {
    // Prüfe den neuen Zustand des Schalters
    const isChecked = checkbox.checked;
    const newMode = isChecked ? 'AUTO' : 'MANUAL';

    // NEU: Temperatur-Eingabefeld sofort ein-/ausblenden für direktes Feedback
    const tempInputContainer = document.querySelector('.temp-input-container');
    if (tempInputContainer) {
        tempInputContainer.style.display = (newMode === 'AUTO') ? 'flex' : 'none';
    }

    // Parameter-Objekt erstellen
    const parameters = { mode: newMode };

    // NEU: Wenn auf AUTO geschaltet wird, die Ziel-Temperatur mitsenden
    if (newMode === 'AUTO') {
        const targetTemp = document.getElementById('target-temp-input').value;
        parameters.temp = parseFloat(targetTemp);
    }

    // Sende den spezifischen SET_MODE Befehl
    sendCommand('SET_MODE', parameters);

    // --- OPTIMISTISCHE UI-SPERRE ---
    // Verhindere für 8 Sekunden, dass `updateStatus` den Schalter zurücksetzt.
    // Das gibt dem Pi genug Zeit, den Befehl auszuführen und den Status zu melden.
    isModeToggleLocked = true;
    setTimeout(() => {
        isModeToggleLocked = false;
        console.log("Mode toggle lock released.");
    }, 8000); // 8 Sekunden Sperre
}


// ===== VENTILATION MODE =====

async function toggleVentilation(enabled) {
    try {
        const response = await fetch(`${API_BASE}/ventilation`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ enabled })
        });
        
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('ventilation-status').textContent = 
                enabled ? 'Aktiviert' : 'Deaktiviert';
            
            if (enabled && data.next_run) {
                document.getElementById('ventilation-info').textContent = 
                    `Nächste Lüftung: ${data.next_run}`;
            } else {
                document.getElementById('ventilation-info').textContent = '';
            }
            
            showFeedback(
                enabled ? '✓ Lüftungsmodus aktiviert' : '✓ Lüftungsmodus deaktiviert',
                'success'
            );
        }
    } catch (error) {
        console.error('Ventilation toggle error:', error);
        showFeedback('❌ Fehler beim Ändern des Lüftungsmodus', 'error');
    }
}

// OLD: Ventilation status loading removed - now handled by custom-ventilation.js
// The ventilation-enabled checkbox was replaced with morning/midday/evening toggles
/*
async function loadVentilationStatus() {
    try {
        const response = await fetch(`${API_BASE}/ventilation`);
        const data = await response.json();
        
        document.getElementById('ventilation-enabled').checked = data.enabled || false;
        document.getElementById('ventilation-status').textContent = 
            data.enabled ? 'Aktiviert' : 'Deaktiviert';
        
        if (data.enabled && data.next_run) {
            document.getElementById('ventilation-info').textContent = 
                `Nächste Lüftung: ${data.next_run}`;
        }
    } catch (error) {
        console.error('Load ventilation status error:', error);
    }
}
*/

// ===== GLOBAL FUNCTIONS (für onclick) =====

window.sendCommand = sendCommand;
window.toggleVentilation = toggleVentilation;
window.handleModeToggle = handleModeToggle; // Mache die neue Funktion global verfügbar
