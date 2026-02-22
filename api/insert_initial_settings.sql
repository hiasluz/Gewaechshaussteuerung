-- =====================================================
-- Initial Settings für system_settings Tabelle
-- =====================================================
-- Verwendung: mysql -u USERNAME -p DATABASE_NAME < insert_initial_settings.sql

INSERT INTO system_settings (setting_key, setting_value, setting_type, description, category) VALUES
-- Temperatur-Einstellungen
('DEFAULT_TARGET_TEMP', '24.0', 'float', 'Wunschtemperatur für Automatik-Modus in °C', 'temperature'),
('TEMP_HYSTERESIS', '2.0', 'float', 'Toleranzbereich (± Grad) für Temperatur-Regelung', 'temperature'),
('TEMP_THRESHOLD', '10.0', 'float', 'Schwellwert für langsames Polling in °C', 'temperature'),

-- Motor-Laufzeiten
('MOTOR_RUNTIME_OPEN', '135', 'int', 'Sekunden für vollständiges Öffnen (0% → 100%)', 'motor'),
('MOTOR_RUNTIME_CLOSE', '128', 'int', 'Sekunden für vollständiges Schließen (100% → 0%)', 'motor'),

-- Polling-Intervalle
('INTERVAL_FAST', '3', 'int', 'Polling-Intervall nach Befehl (Sekunden)', 'polling'),
('INTERVAL_NORMAL', '10', 'int', 'Normales Polling-Intervall (Sekunden)', 'polling'),
('INTERVAL_SLOW', '30', 'int', 'Langsames Polling bei großer Temp-Abweichung (Sekunden)', 'polling'),

-- Standort (für Sonnenauf-/-untergang Berechnung)
('LOCATION_LAT', '47.86559995', 'float', 'Breitengrad Luzernenhof', 'location'),
('LOCATION_LON', '7.61452259', 'float', 'Längengrad Luzernenhof', 'location'),

-- Netzwerk/Retry
('MAX_RETRIES', '3', 'int', 'Maximale Anzahl Wiederholungen bei API-Fehlern', 'network'),
('RETRY_DELAY', '30', 'int', 'Wartezeit zwischen Wiederholungen (Sekunden)', 'network')

ON DUPLICATE KEY UPDATE 
    setting_value = VALUES(setting_value),
    description = VALUES(description);
