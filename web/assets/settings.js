// ===== SETTINGS PANEL FUNCTIONS =====

function toggleSettings() {
    const panel = document.getElementById('settings-panel');
    const icon = document.getElementById('collapse-icon');
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        icon.classList.add('open');
        loadSettings();
    } else {
        panel.style.display = 'none';
        icon.classList.remove('open');
    }
}

function loadSettings() {
    fetch(`${API_BASE}/settings`)
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                console.error('API Fehler:', data.error);
                showFeedback('❌ Fehler beim Laden: ' + data.error, 'error');
                return;
            }
            
            if (!data.temperature || !data.motor || !data.polling) {
                console.error('Invalide Datenstruktur vom Server:', data);
                showFeedback('❌ Server liefert ungültige Einstellungs-Daten!', 'error');
                return;
            }

            // Temperatur
            document.getElementById('set-target-temp').value = data.temperature.DEFAULT_TARGET_TEMP.value;
            document.getElementById('set-hysteresis').value = data.temperature.TEMP_HYSTERESIS.value;
            document.getElementById('set-temp-threshold').value = data.temperature.TEMP_THRESHOLD.value;
            
            // Motor
            document.getElementById('set-motor-open').value = data.motor.MOTOR_RUNTIME_OPEN.value;
            document.getElementById('set-motor-close').value = data.motor.MOTOR_RUNTIME_CLOSE.value;
            
            // Polling
            document.getElementById('set-interval-fast').value = data.polling.INTERVAL_FAST.value;
            document.getElementById('set-interval-normal').value = data.polling.INTERVAL_NORMAL.value;
            document.getElementById('set-interval-slow').value = data.polling.INTERVAL_SLOW.value;
            
            // Netzwerk
            document.getElementById('set-max-retries').value = data.network.MAX_RETRIES.value;
            document.getElementById('set-retry-delay').value = data.network.RETRY_DELAY.value;
            
            // Standort (read-only)
            document.getElementById('set-location-lat').value = data.location.LOCATION_LAT.value;
            document.getElementById('set-location-lon').value = data.location.LOCATION_LON.value;
        })
        .catch(err => {
            console.error('Fehler beim Laden der Einstellungen:', err);
            showFeedback('❌ Fehler beim Laden der Einstellungen!', 'error');
        });
}

function saveSettings() {
    if (!confirm('Einstellungen speichern und Service neu starten?\nDie neuen Werte werden sofort übernommen.')) return;
    
    const settings = {
        DEFAULT_TARGET_TEMP: parseFloat(document.getElementById('set-target-temp').value),
        TEMP_HYSTERESIS: parseFloat(document.getElementById('set-hysteresis').value),
        TEMP_THRESHOLD: parseFloat(document.getElementById('set-temp-threshold').value),
        MOTOR_RUNTIME_OPEN: parseInt(document.getElementById('set-motor-open').value),
        MOTOR_RUNTIME_CLOSE: parseInt(document.getElementById('set-motor-close').value),
        INTERVAL_FAST: parseInt(document.getElementById('set-interval-fast').value),
        INTERVAL_NORMAL: parseInt(document.getElementById('set-interval-normal').value),
        INTERVAL_SLOW: parseInt(document.getElementById('set-interval-slow').value),
        MAX_RETRIES: parseInt(document.getElementById('set-max-retries').value),
        RETRY_DELAY: parseInt(document.getElementById('set-retry-delay').value)
    };
    
    fetch(`${API_BASE}/settings`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(settings)
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showFeedback('✅ Einstellungen gespeichert! Service wird neu gestartet...', 'success', 8000);
                toggleSettings();
                
                // Service neu starten, damit Pi die neuen Werte lädt
                restartService();
            } else {
                showFeedback('❌ Fehler: ' + (data.error || 'Unbekannter Fehler'), 'error');
            }
        })
        .catch(err => {
            console.error('Fehler beim Speichern:', err);
            showFeedback('❌ Fehler beim Speichern der Einstellungen!', 'error');
        });
}

function restartService() {
    fetch(`${API_BASE}/restart-service`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showFeedback('✅ Service neu gestartet — neue Einstellungen aktiv!', 'success', 6000);
                // Nach kurzer Wartezeit Status aktualisieren
                setTimeout(() => updateStatus(), 5000);
            } else {
                showFeedback('⚠️ Einstellungen gespeichert, aber Service-Neustart fehlgeschlagen: ' + (data.error || ''), 'error', 10000);
            }
        })
        .catch(err => {
            console.error('Service restart error:', err);
            showFeedback('⚠️ Einstellungen gespeichert, aber Service-Neustart fehlgeschlagen.', 'error', 10000);
        });
}

function cancelSettings() {
    if (confirm('Änderungen verwerfen?')) {
        toggleSettings();
    }
}
