/**
 * Gate Auto-Mode Toggle Functions
 * 
 * Diese Funktionen ermöglichen das individuelle Ein-/Ausschalten
 * des Auto-Modus für jedes Tor.
 * version 1.0
 */

// Gobale Objekte für Status
let gateAutoModeStatus = {};
let gateEnabledStatus = {}; // NEU: Wintermodus Status

/**
 * Toggle Auto-Mode für ein spezifisches Tor
 */
async function toggleGateAuto(motorName, enabled) {
    try {
        const response = await fetch(`${API_BASE}/gate-auto-mode`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                motor_name: motorName,
                auto_enabled: enabled
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update lokalen Status
            gateAutoModeStatus[motorName] = enabled;
            
            showFeedback(
                `✓ Auto-Modus für ${motorName.replace('_', ' ')} ${enabled ? 'aktiviert' : 'deaktiviert'}`,
                'success'
            );
        } else {
            showFeedback('❌ Fehler beim Ändern des Auto-Modus', 'error');
            // Checkbox zurücksetzen
            document.getElementById(`auto-${motorName}`).checked = !enabled;
        }
    } catch (error) {
        console.error('Toggle gate auto error:', error);
        showFeedback('❌ Verbindungsfehler', 'error');
        // Checkbox zurücksetzen
        document.getElementById(`auto-${motorName}`).checked = !enabled;
    }
}

/**
 * Toggle Enabled-Status (Wintermodus) für ein spezifisches Tor
 */
async function toggleGateEnabled(motorName, enabled) {
    try {
        const response = await fetch(`${API_BASE}/gate-enabled`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                motor_name: motorName,
                enabled: enabled
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            gateEnabledStatus[motorName] = enabled;
            setGateDisabledUI(motorName, !enabled);
            
            showFeedback(
                `✓ Tor ${motorName.replace('_', ' ')} ist jetzt ${enabled ? 'AKTIVIERT' : 'DEAKTIVIERT'}`,
                enabled ? 'success' : 'info'
            );
        } else {
            showFeedback('❌ Fehler beim Ändern des Tor-Status', 'error');
            document.getElementById(`enabled-${motorName}`).checked = !enabled;
        }
    } catch (error) {
        console.error('Toggle gate enabled error:', error);
        showFeedback('❌ Verbindungsfehler', 'error');
        document.getElementById(`enabled-${motorName}`).checked = !enabled;
    }
}

/**
 * UI-Zustand für deaktiviertes Tor setzen
 */
function setGateDisabledUI(motorName, isDisabled) {
    const cardEl = document.getElementById(`enabled-${motorName}`);
    if (!cardEl) return;
    
    const card = cardEl.closest('.motor-card');
    if (!card) return;

    if (isDisabled) {
        card.classList.add('gate-disabled');
    } else {
        card.classList.remove('gate-disabled');
    }

    // Buttons und andere Toggles in der Karte deaktivieren
    const controls = card.querySelectorAll('button, input:not([id^="enabled-"])');
    controls.forEach(c => {
        c.disabled = isDisabled;
    });
}

/**
 * Lade Auto-Mode & Enabled Status für alle Tore
 */
async function loadGateAutoStatus() {
    try {
        // 1. Auto-Mode Status laden
        const autoResp = await fetch(`${API_BASE}/gate-auto-mode`);
        const autoData = await autoResp.json();
        
        for (const [motorName, autoEnabled] of Object.entries(autoData)) {
            const checkbox = document.getElementById(`auto-${motorName}`);
            if (checkbox) {
                checkbox.checked = autoEnabled == 1 || autoEnabled === true;
                gateAutoModeStatus[motorName] = autoEnabled;
            }
        }

        // 2. Enabled Status (Wintermodus) laden
        const enabledResp = await fetch(`${API_BASE}/gate-enabled`);
        const enabledData = await enabledResp.json();
        
        for (const [motorName, enabled] of Object.entries(enabledData)) {
            const checkbox = document.getElementById(`enabled-${motorName}`);
            if (checkbox) {
                const isEnabled = enabled == 1 || enabled === true;
                checkbox.checked = isEnabled;
                gateEnabledStatus[motorName] = isEnabled;
                setGateDisabledUI(motorName, !isEnabled);
            }
        }
    } catch (error) {
        console.error('Load statuses error:', error);
    }
}

// Exportiere Funktionen für globalen Zugriff
window.toggleGateAuto = toggleGateAuto;
window.toggleGateEnabled = toggleGateEnabled;
window.loadGateAutoStatus = loadGateAutoStatus;
