/**
 * Gate Auto-Mode Toggle Functions
 * 
 * Diese Funktionen ermöglichen das individuelle Ein-/Ausschalten
 * des Auto-Modus für jedes Tor.
 * version 1.0
 */

// Globales Objekt für Auto-Mode Status
let gateAutoModeStatus = {};

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
 * Lade Auto-Mode Status für alle Tore
 */
async function loadGateAutoStatus() {
    try {
        const response = await fetch(`${API_BASE}/gate-auto-mode`);
        const data = await response.json();
        
        // Update UI für jedes Tor
        for (const [motorName, autoEnabled] of Object.entries(data)) {
            const checkbox = document.getElementById(`auto-${motorName}`);
            if (checkbox) {
                checkbox.checked = autoEnabled == 1 || autoEnabled === true;
                gateAutoModeStatus[motorName] = autoEnabled;
            }
        }
    } catch (error) {
        console.error('Load gate auto status error:', error);
    }
}

// Exportiere Funktionen für globalen Zugriff
window.toggleGateAuto = toggleGateAuto;
window.loadGateAutoStatus = loadGateAutoStatus;
