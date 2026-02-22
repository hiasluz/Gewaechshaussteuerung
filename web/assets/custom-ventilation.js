/*
 * Custom Ventilation JavaScript
 * Verwaltet individuelle Lüftungsphasen und erweiterte Lüftungssteuerung
 * version 1.1
 */

window.API_BASE = window.API_BASE || window.location.origin + '/api';
const MAX_CUSTOM_PHASES = 5;

let customPhases = [];

// Ventilation Config laden
async function loadVentilationConfig() {
    try {
        const response = await fetch(`${window.API_BASE}/ventilation`);
        if (!response.ok) return;
        
        const config = await response.json();
        
        // Feste Zeiten setzen
        document.getElementById('morning-vent-enabled').checked = config.enabled || false;
        document.getElementById('midday-vent-enabled').checked = config.midday_enabled || false;
        document.getElementById('evening-vent-enabled').checked = config.evening_enabled || false;
        
        // Custom Phases laden
        customPhases = config.custom_phases || [];
        renderCustomPhases();
    } catch (error) {
        console.error('Error loading ventilation config:', error);
    }
}

// Morgens-Lüftung umschalten
async function toggleMorningVent(enabled) {
    await updateVentilationConfig({ enabled });
}

// Mittags-Lüftung umschalten
async function toggleMiddayVent(enabled) {
    await updateVentilationConfig({ midday_enabled: enabled });
}

// Abends-Lüftung umschalten
async function toggleEveningVent(enabled) {
    await updateVentilationConfig({ evening_enabled: enabled });
}

// Ventilation Config aktualisieren
async function updateVentilationConfig(updates) {
    try {
        const response = await fetch(`${window.API_BASE}/ventilation`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });
        
        if (!response.ok) {
            throw new Error('Failed to update ventilation config');
        }
        
        console.log('Ventilation config updated:', updates);
    } catch (error) {
        console.error('Error updating ventilation:', error);
        alert('Fehler beim Aktualisieren: ' + error.message);
    }
}

// Custom Phases rendern
function renderCustomPhases() {
    const container = document.getElementById('custom-phases-list');
    const addBtn = document.getElementById('add-phase-btn');
    
    if (!container) return;
    
    container.innerHTML = '';
    
    if (customPhases.length === 0) {
        container.innerHTML = '<p style="color: #999; font-style: italic;">Keine individuellen Lüftungszeiten definiert</p>';
    } else {
        customPhases.forEach((phase, index) => {
            const phaseDiv = document.createElement('div');
            phaseDiv.className = 'custom-phase-item';
            phaseDiv.style.cssText = `
                background: #f9f9f9;
                padding: 12px;
                margin-bottom: 10px;
                border-radius: 5px;
                border-left: 4px solid ${phase.enabled ? '#4CAF50' : '#999'};
                display: flex;
                justify-content: space-between;
                align-items: center;
            `;
            
            phaseDiv.innerHTML = `
                <div style="flex: 1;">
                    <strong>${phase.name || `Phase ${index + 1}`}</strong><br>
                    <span style="color: #666; font-size: 0.9em;">
                        ${phase.start_time.substring(0, 5)} - ${phase.end_time.substring(0, 5)}
                    </span>
                </div>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <label class="switch">
                        <input type="checkbox" 
                               ${phase.enabled ? 'checked' : ''}
                               onchange="toggleCustomPhase(${phase.id}, this.checked)">
                        <span class="slider"></span>
                    </label>
                    <button onclick="deleteCustomPhase(${phase.id})" 
                            style="background: #f44336; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">
                        🗑️
                    </button>
                </div>
            `;
            
            container.appendChild(phaseDiv);
        });
    }
    
    // Add-Button aktivieren/deaktivieren
    if (addBtn) {
        addBtn.disabled = customPhases.length >= MAX_CUSTOM_PHASES;
        addBtn.style.opacity = customPhases.length >= MAX_CUSTOM_PHASES ? '0.5' : '1';
    }
}

// Neue Custom Phase hinzufügen - öffnet Modal
function addCustomPhase() {
    if (customPhases.length >= MAX_CUSTOM_PHASES) {
        showModalError(`Maximal ${MAX_CUSTOM_PHASES} individuelle Lüftungszeiten erlaubt`);
        return;
    }
    
    // Modal öffnen
    const modal = document.getElementById('ventilation-modal');
    if (modal) {
        modal.style.display = 'block';
        // Formular zurücksetzen
        document.getElementById('phase-name').value = '';
        document.getElementById('phase-start').value = '14:00';
        document.getElementById('phase-end').value = '14:30';
        hideModalError();
    }
}

// Modal schließen
function closeVentilationModal() {
    const modal = document.getElementById('ventilation-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Formular absenden
function saveVentilationPhase(event) {
    event.preventDefault();
    
    const name = document.getElementById('phase-name').value || null;
    const startTime = document.getElementById('phase-start').value;
    const endTime = document.getElementById('phase-end').value;
    
    // Validierung
    if (!startTime || !endTime) {
        showModalError('Bitte beide Zeiten eingeben');
        return;
    }
    
    if (startTime >= endTime) {
        showModalError('Endzeit muss nach Startzeit liegen');
        return;
    }
    
    // Phase speichern
    saveCustomPhase({ name, start_time: startTime, end_time: endTime, enabled: true });
    closeVentilationModal();
}

// Modal-Fehler anzeigen
function showModalError(message) {
    const errorDiv = document.getElementById('modal-error');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    } else {
        // Fallback wenn Modal nicht existiert
        alert(message);
    }
}

// Modal-Fehler ausblenden
function hideModalError() {
    const errorDiv = document.getElementById('modal-error');
    if (errorDiv) {
        errorDiv.style.display = 'none';
    }
}

// Custom Phase speichern
async function saveCustomPhase(phase) {
    try {
        const response = await fetch(`${window.API_BASE}/ventilation/custom-phases`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(phase)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to save phase');
        }
        
        await loadVentilationConfig();
        console.log('Custom phase saved');
    } catch (error) {
        console.error('Error saving custom phase:', error);
        alert('Fehler beim Speichern: ' + error.message);
    }
}

// Custom Phase umschalten
async function toggleCustomPhase(id, enabled) {
    const phase = customPhases.find(p => p.id === id);
    if (!phase) return;
    
    await saveCustomPhase({ ...phase, enabled });
}

// Custom Phase löschen
async function deleteCustomPhase(id) {
    if (!confirm('Lüftungszeit wirklich löschen?')) return;
    
    try {
        const response = await fetch(`${window.API_BASE}/ventilation/custom-phases/${id}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete phase');
        }
        
        await loadVentilationConfig();
        console.log('Custom phase deleted');
    } catch (error) {
        console.error('Error deleting custom phase:', error);
        alert('Fehler beim Löschen: ' + error.message);
    }
}

// Beim Laden initialisieren
document.addEventListener('DOMContentLoaded', () => {
    loadVentilationConfig();
    
    // Alle 10 Sekunden aktualisieren
    setInterval(loadVentilationConfig, 10000);
});
