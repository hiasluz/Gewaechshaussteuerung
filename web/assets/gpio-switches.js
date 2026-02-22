/*
 * GPIO Switches JavaScript
 * Lädt und steuert die 4 zusätzlichen GPIO-Schalter (Bewässerung 1-3, Zusatz)
 * version 1.1
 */

window.API_BASE = window.API_BASE || window.location.origin + '/api';

// GPIO Switches laden und anzeigen
async function loadGpioSwitches() {
    try {
        const response = await fetch(`${window.API_BASE}/gpio-switches`);
        if (!response.ok) {
            console.error('Failed to load GPIO switches');
            return;
        }
        
        const switches = await response.json();
        renderGpioSwitches(switches);
    } catch (error) {
        console.error('Error loading GPIO switches:', error);
    }
}

// GPIO Switches UI rendern
function renderGpioSwitches(switches) {
    const container = document.getElementById('gpio-switches');
    if (!container) return;
    
    container.innerHTML = '';
    container.style.display = 'grid';
    container.style.gridTemplateColumns = 'repeat(auto-fit, minmax(200px, 1fr))';
    container.style.gap = '15px';
    
    switches.forEach(sw => {
        const card = document.createElement('div');
        card.className = 'gpio-switch-card';
        card.style.cssText = `
            background: #f9f9f9;
            padding: 15px;
            border-radius: 8px;
            border: 2px solid ${sw.state ? '#4CAF50' : '#ddd'};
            transition: all 0.3s;
        `;
        
        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: bold; font-size: 1.1em;">${sw.name}</span>
                <label class="switch">
                    <input type="checkbox" 
                           id="gpio-${sw.name.replace(/\s+/g, '_')}" 
                           ${!sw.state ? 'checked' : ''}
                           onchange="toggleGpioSwitch('${sw.name}', !this.checked)">
                    <span class="slider"></span>
                </label>
            </div>
            <div style="margin-top: 10px; font-size: 0.9em; color: #666;">
                GPIO Pin: ${sw.gpio_pin}
            </div>
            <div style="margin-top: 5px; font-size: 0.9em; font-weight: bold; color: ${!sw.state ? '#4CAF50' : '#999'};">
                ${!sw.state ? '🟢 Aktiv' : '⚪ Inaktiv'}
            </div>
        `;
        
        container.appendChild(card);
    });
}

// GPIO Switch umschalten
async function toggleGpioSwitch(name, state) {
    try {
        const response = await fetch(`${window.API_BASE}/gpio-switches`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, state })
        });
        
        if (!response.ok) {
            throw new Error('Failed to toggle switch');
        }
        
        // UI aktualisieren
        await loadGpioSwitches();
        
        console.log(`GPIO Switch "${name}" ${state ? 'aktiviert' : 'deaktiviert'}`);
    } catch (error) {
        console.error('Error toggling GPIO switch:', error);
        alert('Fehler beim Schalten: ' + error.message);
        // Checkbox zurücksetzen
        const checkbox = document.getElementById(`gpio-${name.replace(/\s+/g, '_')}`);
        if (checkbox) checkbox.checked = !state;
    }
}

// Beim Laden der App initialisieren
document.addEventListener('DOMContentLoaded', () => {
    loadGpioSwitches();
    
    // Alle 5 Sekunden aktualisieren
    setInterval(loadGpioSwitches, 5000);
});
