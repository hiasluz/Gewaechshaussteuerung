<?php
/**
 * Greenhouse REST API
 * 
 * Endpoints:
 * - GET  /api/status            -> Aktuellen Status abrufen
 * - POST /api/status            -> Status aktualisieren (vom Pi)
 * - POST /api/command           -> Neuen Befehl senden (vom Web)
 * - GET  /api/command           -> Offene Befehle abrufen (vom Pi)
 * - POST /api/command/{id}/complete -> Befehl als erledigt markieren
 * - POST /api/command/{id}/fail     -> Befehl als fehlgeschlagen markieren
 * - POST /api/login             -> Einloggen
 * - POST /api/logout            -> Ausloggen
 * - GET  /api/auth-check        -> Prüfen ob eingeloggt
 * - GET  /api/ventilation       -> Ventilation Config abrufen
 * - POST /api/ventilation       -> Ventilation Config aktualisieren
 * - POST /api/ventilation/mark-run -> Ventilation als ausgeführt markieren
 */

require_once 'config.php';

// Error Reporting
error_reporting(E_ALL);
ini_set('display_errors', 0);
ini_set('log_errors', 1);
ini_set('error_log', 'php_errors.log');

// CORS Header
header("Access-Control-Allow-Origin: *");
header("Content-Type: application/json; charset=UTF-8");
header("Access-Control-Allow-Methods: GET, POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With, X-API-Key");

// Handle OPTIONS request
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// Router
$request_uri = $_SERVER['REQUEST_URI'];
$script_name = $_SERVER['SCRIPT_NAME'];
$path = str_replace(dirname($script_name), '', $request_uri);
$path = trim($path, '/');
$path = explode('?', $path)[0]; // Remove query string

// API Prefix entfernen falls vorhanden
if (strpos($path, 'api/') === 0) {
    $path = substr($path, 4);
}

$method = $_SERVER['REQUEST_METHOD'];

try {
    switch ($path) {
        case 'status':
            if ($method === 'GET') {
                getStatus();
            } elseif ($method === 'POST') {
                validateApiKey();
                updateStatus();
            } else {
                sendJSON(['error' => 'Method not allowed'], 405);
            }
            break;
            
        case 'command':
            if ($method === 'GET') {
                validateApiKey();
                getPendingCommands();
            } elseif ($method === 'POST') {
                if (!isLoggedIn()) validateApiKey(); // Web needs login, Pi needs API Key
                addCommand();
            } else {
                sendJSON(['error' => 'Method not allowed'], 405);
            }
            break;
            
        case 'login':
            if ($method === 'POST') {
                handleLogin();
            } else {
                sendJSON(['error' => 'Method not allowed'], 405);
            }
            break;
            
        case 'logout':
            if ($method === 'POST') {
                doLogout();
                sendJSON(['success' => true]);
            } else {
                sendJSON(['error' => 'Method not allowed'], 405);
            }
            break;
        
        case 'auth-check':
            if ($method === 'GET') {
                sendJSON(['logged_in' => isLoggedIn()]);
            } else {
                sendJSON(['error' => 'Method not allowed'], 405);
            }
            break;
        
        // ===== VENTILATION =====
        
        case 'ventilation':
            if ($method === 'GET') {
                getVentilationConfig();
            } elseif ($method === 'POST') {
                if (!isLoggedIn()) validateApiKey();
                updateVentilationConfig();
            } else {
                sendJSON(['error' => 'Method not allowed'], 405);
            }
            break;
        
        case 'ventilation/mark-run':
            if ($method === 'POST') {
                validateApiKey();
                markVentilationRun();
            } else {
                sendJSON(['error' => 'Method not allowed'], 405);
            }
            break;
        
        // ===== GATE AUTO MODE =====
        
        case 'gate-auto-mode':
            if ($method === 'GET') {
                getGateAutoMode();
            } elseif ($method === 'POST') {
                if (!isLoggedIn()) validateApiKey();
                updateGateAutoMode();
            } else {
                sendJSON(['error' => 'Method not allowed'], 405);
            }
            break;
        
        // ===== GATE ENABLED (Wintermodus) =====
        
        case 'gate-enabled':
            if ($method === 'GET') {
                getGateEnabled();
            } elseif ($method === 'POST') {
                if (!isLoggedIn()) validateApiKey();
                updateGateEnabled();
            } else {
                sendJSON(['error' => 'Method not allowed'], 405);
            }
            break;
        
        // ===== GPIO SWITCHES =====
        
        case 'gate-status':
            if ($method === 'GET') {
                getGateStatus();
            } elseif ($method === 'POST') {
                validateApiKey();
                updateGateStatus();
            } else {
                sendJSON(['error' => 'Method not allowed'], 405);
            }
            break;
        
        case 'gpio-switches':
            if ($method === 'GET') {
                getGpioSwitches();
            } elseif ($method === 'POST') {
                if (!isLoggedIn()) validateApiKey();
                toggleGpioSwitch();
            } else {
                sendJSON(['error' => 'Method not allowed'], 405);
            }
            break;
        
        // ===== CUSTOM VENTILATION PHASES =====
        
        case 'ventilation/custom-phases':
            if ($method === 'GET') {
                getCustomVentilationPhases();
            } elseif ($method === 'POST') {
                if (!isLoggedIn()) validateApiKey();
                createCustomVentilationPhase();
            } else {
                sendJSON(['error' => 'Method not allowed'], 405);
            }
            break;
        
        // ===== SYSTEM SETTINGS =====
        
        case 'settings':
            if ($method === 'GET') {
                if (!isLoggedIn()) validateApiKey();
                getSystemSettings();
            } elseif ($method === 'POST') {
                if (!isLoggedIn()) validateApiKey();
                updateSystemSettings();
            } else {
                sendJSON(['error' => 'Method not allowed'], 405);
            }
            break;
        
        case 'restart-service':
            if ($method === 'POST') {
                if (!isLoggedIn()) validateApiKey();
                restartService();
            } else {
                sendJSON(['error' => 'Method not allowed'], 405);
            }
            break;
        
        // ===== COMMAND STATUS UPDATES =====
        
        default:
            // Prüfe auf /command/{id}/complete oder /command/{id}/fail
            if (preg_match('/^command\/(\d+)\/(complete|fail)$/', $path, $matches)) {
                validateApiKey();
                $commandId = (int)$matches[1];
                $action = $matches[2];
                
                if ($method === 'POST') {
                    if ($action === 'complete') {
                        completeCommand($commandId);
                    } else {
                        failCommand($commandId);
                    }
                } else {
                    sendJSON(['error' => 'Method not allowed'], 405);
                }
            }
            // Prüfe auf /ventilation/custom-phases/{id} DELETE
            elseif (preg_match('/^ventilation\/custom-phases\/(\d+)$/', $path, $matches)) {
                if ($method === 'DELETE') {
                    if (!isLoggedIn()) validateApiKey();
                    deleteCustomVentilationPhase((int)$matches[1]);
                } else {
                    sendJSON(['error' => 'Method not allowed'], 405);
                }
            }
            else {
                sendJSON(['error' => 'Endpoint not found: ' . $path], 404);
            }
            break;
    }
} catch (Exception $e) {
    error_log('API Error: ' . $e->getMessage());
    logMessage('ERROR', 'API Error: ' . $e->getMessage());
    sendJSON(['error' => 'Internal server error'], 500);
}

// ===== HANDLER-FUNKTIONEN =====

/**
 * GET /api/status - Status abrufen
 */
function getStatus() {
    $db = getDB();
    $stmt = $db->query('SELECT * FROM status ORDER BY id DESC LIMIT 1');
    $status = $stmt->fetch();
    
    if (!$status) {
        $status = [
            'temp_indoor' => null,
            'temp_outdoor' => null,
            'mode' => 'MANUAL',
            'last_action' => 'Keine Daten',
            'is_busy' => false,
            'updated_at' => date('Y-m-d H:i:s')
        ];
    }
    
    // Gate Positions holen
    $stmt = $db->query('SELECT motor_name, position FROM gate_status');
    $gates = $stmt->fetchAll(PDO::FETCH_KEY_PAIR);
    $status['gate_positions'] = $gates ?: [];
    
    // Gate Auto Mode holen
    $stmt = $db->query('SELECT motor_name, auto_enabled FROM gate_auto_mode');
    $autoModeRows = $stmt->fetchAll(PDO::FETCH_ASSOC);
    $autoMode = [];
    foreach ($autoModeRows as $row) {
        $autoMode[$row['motor_name']] = (bool)(int)$row['auto_enabled'];
    }
    $status['gate_auto_mode'] = $autoMode ?: [];
    
    // Gate Enabled (Wintermodus) holen
    $stmt = $db->query('SELECT motor_name, enabled FROM gate_status');
    $enabledRows = $stmt->fetchAll(PDO::FETCH_ASSOC);
    $gateEnabled = [];
    foreach ($enabledRows as $row) {
        $gateEnabled[$row['motor_name']] = (bool)(int)$row['enabled'];
    }
    $status['gate_enabled'] = $gateEnabled;
    
    sendJSON($status);
}

/**
 * POST /api/status - Status aktualisieren (vom Pi)
 */
function updateStatus() {
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!$input) {
        sendJSON(['error' => 'Invalid JSON'], 400);
    }
    
    $db = getDB();
    
    // === LOGGING OPTIMIERUNG ===
    // Aktuellen Status für Vergleich laden
    $stmt = $db->query('SELECT last_action FROM status ORDER BY id DESC LIMIT 1');
    $currentStatus = $stmt->fetch();
    $oldAction = $currentStatus['last_action'] ?? '';
    $newAction = $input['last_action'] ?? '';
    
    // Logge nur wenn Action sich geändert hat und nicht leer ist
    if ($newAction && $newAction !== $oldAction) {
        logMessage('INFO', $newAction);
    }
    
    // Aktuelle Tor-Positionen für Vergleich laden
    $stmt = $db->query('SELECT motor_name, position FROM gate_status');
    $oldGates = $stmt->fetchAll(PDO::FETCH_KEY_PAIR);
    
    // === STATUS UPDATE ===
    // Prüfe ob Status-Eintrag existiert
    $stmt = $db->query('SELECT COUNT(*) as count FROM status');
    $count = $stmt->fetch()['count'];
    
    if ($count == 0) {
        $stmt = $db->prepare('
            INSERT INTO status (temp_indoor, temp_outdoor, mode, last_action, is_busy)
            VALUES (?, ?, ?, ?, ?)
        ');
    } else {
        $stmt = $db->prepare('
            UPDATE status SET
                temp_indoor = ?,
                temp_outdoor = ?,
                mode = ?,
                last_action = ?,
                is_busy = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = (SELECT id FROM (SELECT id FROM status ORDER BY id DESC LIMIT 1) as t)
        ');
    }
    
    $stmt->execute([
        $input['temp_indoor'] ?? null,
        $input['temp_outdoor'] ?? null,
        $input['mode'] ?? 'MANUAL',
        $input['last_action'] ?? null,
        isset($input['is_busy']) ? (int)$input['is_busy'] : 0
    ]);
    
    // Gate Positions speichern
    if (isset($input['gate_positions']) && is_array($input['gate_positions'])) {
        foreach ($input['gate_positions'] as $motor => $position) {
            $newPos = (int)$position;
            $oldPos = isset($oldGates[$motor]) ? (int)$oldGates[$motor] : null;

            // Logge nur wenn Position sich tatsächlich geändert hat
            if ($oldPos !== null && $oldPos !== $newPos) {
                logMessage('INFO', "Tor $motor: $oldPos% -> $newPos%");
            }

            $stmt = $db->prepare('
                INSERT INTO gate_status (motor_name, position, last_command)
                VALUES (?, ?, ?)
                ON DUPLICATE KEY UPDATE position = ?, updated_at = CURRENT_TIMESTAMP
            ');
            $stmt->execute([$motor, $newPos, 'UPDATE', $newPos]);
        }
    }
    
    sendJSON(['success' => true]);
}

/**
 * GET /api/command - Offene Befehle abrufen
 */
function getPendingCommands() {
    $db = getDB();
    $stmt = $db->query("SELECT * FROM commands WHERE status = 'pending' ORDER BY created_at ASC");
    $commands = $stmt->fetchAll();
    
    // Mark as executing
    if ($commands) {
        $ids = array_column($commands, 'id');
        $inQuery = implode(',', array_fill(0, count($ids), '?'));
        $stmt = $db->prepare("UPDATE commands SET status = 'executing' WHERE id IN ($inQuery)");
        $stmt->execute($ids);
    }
    
    sendJSON($commands);
}

/**
 * POST /api/command - Neuen Befehl hinzufügen
 */
function addCommand() {
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!isset($input['command'])) {
        sendJSON(['error' => 'Command required'], 400);
    }
    
    $db = getDB();
    $stmt = $db->prepare('INSERT INTO commands (command, parameters) VALUES (?, ?)');
    $stmt->execute([
        $input['command'],
        isset($input['parameters']) ? json_encode($input['parameters']) : null
    ]);
    
    $id = $db->lastInsertId();
    logMessage('INFO', "Neuer Befehl: {$input['command']} (ID: $id)");
    
    sendJSON(['success' => true, 'id' => $id]);
}

/**
 * POST /api/command/{id}/complete
 */
function completeCommand($id) {
    $db = getDB();
    $stmt = $db->prepare('
        UPDATE commands SET
            status = ?,
            executed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ');
    $stmt->execute(['completed', $id]);
    
    logMessage('INFO', "Befehl ausgeführt: ID $id");
    sendJSON(['success' => true]);
}

/**
 * POST /api/command/{id}/fail
 */
function failCommand($id) {
    $input = json_decode(file_get_contents('php://input'), true);
    $error = $input['error'] ?? 'Unknown error';
    
    $db = getDB();
    $stmt = $db->prepare('
        UPDATE commands SET
            status = ?,
            error_message = ?,
            executed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ');
    $stmt->execute(['failed', $error, $id]);
    
    logMessage('ERROR', "Befehl fehlgeschlagen: ID $id - $error");
    sendJSON(['success' => true]);
}

/**
 * POST /api/login - Login
 */
function handleLogin() {
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!isset($input['password'])) {
        sendJSON(['error' => 'Password required'], 400);
    }

    
    if (doLogin($input['password'])) {
        logMessage('INFO', 'Web-Interface Login erfolgreich');
        sendJSON(['success' => true, 'logged_in' => true]);
    } else {
        logMessage('WARNING', 'Web-Interface Login fehlgeschlagen');
        sendJSON(['error' => 'Invalid password'], 401);
    }
}

/**
 * GET /api/ventilation - Ventilation Config abrufen
 */
function getVentilationConfig() {
    $db = getDB();
    $stmt = $db->query('SELECT * FROM ventilation_config LIMIT 1');
    $config = $stmt->fetch();
    
    if (!$config) {
        $config = [
            'enabled' => false,
            'midday_enabled' => true,
            'evening_enabled' => true,
            'latitude' => 47.86559995,
            'longitude' => 7.61452259,
            'offset_minutes' => 30,
            'duration_minutes' => 20,
            'last_run' => null
        ];
    }
    
    // Hole custom phases
    $stmt = $db->query('
        SELECT id, name, start_time, end_time, enabled 
        FROM custom_ventilation_phases 
        ORDER BY start_time
    ');
    $config['custom_phases'] = $stmt->fetchAll();
    
    sendJSON($config);
}

/**
 * POST /api/ventilation - Ventilation Config aktualisieren
 */
function updateVentilationConfig() {
    $input = json_decode(file_get_contents('php://input'), true);
    $db = getDB();
    
    // Aktuelle Config laden
    $stmt = $db->query('SELECT * FROM ventilation_config LIMIT 1');
    $current = $stmt->fetch();
    
    if (!$current) {
        // Fallback falls noch kein Eintrag existiert
        $current = [
            'enabled' => 0,
            'midday_enabled' => 1,
            'evening_enabled' => 1,
            'offset_minutes' => 30,
            'duration_minutes' => 20
        ];
    }
    
    // Werte mergen (Input überschreibt Current)
    $enabled = isset($input['enabled']) ? (int)$input['enabled'] : $current['enabled'];
    $midday = isset($input['midday_enabled']) ? (int)$input['midday_enabled'] : $current['midday_enabled'];
    $evening = isset($input['evening_enabled']) ? (int)$input['evening_enabled'] : $current['evening_enabled'];
    $offset = isset($input['offset_minutes']) ? (int)$input['offset_minutes'] : $current['offset_minutes'];
    $duration = isset($input['duration_minutes']) ? (int)$input['duration_minutes'] : $current['duration_minutes'];
    
    $stmt = $db->prepare('
        UPDATE ventilation_config SET
            enabled = ?,
            midday_enabled = ?,
            evening_enabled = ?,
            offset_minutes = ?,
            duration_minutes = ?
        WHERE id = 1
    ');
    
    $stmt->execute([$enabled, $midday, $evening, $offset, $duration]);
    
    logMessage('INFO', 'Ventilation config updated: ' . json_encode($input));
    sendJSON(['success' => true]);
}

/**
 * POST /api/ventilation/mark-run - Markiere Lüftung als ausgeführt
 */
function markVentilationRun() {
    $db = getDB();
    $stmt = $db->prepare('UPDATE ventilation_config SET last_run = CURDATE() WHERE id = 1');
    $stmt->execute();
    
    logMessage('INFO', 'Ventilation marked as run today');
    sendJSON(['success' => true]);
}

/**
 * GET /api/gate-auto-mode - Gate Auto Mode Einstellungen abrufen
 */
function getGateAutoMode() {
    $db = getDB();
    $stmt = $db->query('SELECT motor_name, auto_enabled FROM gate_auto_mode');
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    // Falls Tabelle leer, Defaults zurückgeben
    if (empty($rows)) {
        $settings = [
            'GH1_VORNE' => true,
            'GH1_HINTEN' => true,
            'GH2_VORNE' => true,
            'GH2_HINTEN' => true,
            'GH3_VORNE' => true,
            'GH3_HINTEN' => true
        ];
    } else {
        // WICHTIG: auto_enabled als echten Boolean casten!
        // PDO::FETCH_KEY_PAIR gibt Strings zurück ("0"/"1").
        // In Python ist der String "0" truthy → Tor würde fälschlicherweise als AUTO erkannt.
        $settings = [];
        foreach ($rows as $row) {
            $settings[$row['motor_name']] = (bool)(int)$row['auto_enabled'];
        }
    }
    
    sendJSON($settings);
}

/**
 * GET /api/gate-enabled - Gate Enabled Status abrufen (Wintermodus)
 */
function getGateEnabled() {
    $db = getDB();
    $stmt = $db->query('SELECT motor_name, enabled FROM gate_status ORDER BY motor_name');
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
    
    $settings = [];
    foreach ($rows as $row) {
        $settings[$row['motor_name']] = (bool)(int)$row['enabled'];
    }
    
    // Defaults falls Tabelle leer
    if (empty($settings)) {
        $settings = [
            'GH1_VORNE'  => true, 'GH1_HINTEN' => true,
            'GH2_VORNE'  => true, 'GH2_HINTEN' => true,
            'GH3_VORNE'  => true, 'GH3_HINTEN' => true
        ];
    }
    
    sendJSON($settings);
}

/**
 * POST /api/gate-enabled - Tor aktivieren/deaktivieren (Wintermodus)
 */
function updateGateEnabled() {
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!isset($input['motor_name'])) {
        sendJSON(['error' => 'motor_name required'], 400);
    }
    
    $db = getDB();
    $enabled = isset($input['enabled']) ? (int)(bool)$input['enabled'] : 1;
    
    $stmt = $db->prepare('
        UPDATE gate_status
        SET enabled = ?, updated_at = CURRENT_TIMESTAMP
        WHERE motor_name = ?
    ');
    $stmt->execute([$enabled, $input['motor_name']]);
    
    if ($stmt->rowCount() === 0) {
        sendJSON(['error' => 'Motor not found'], 404);
    }
    
    $label = $enabled ? 'aktiviert' : 'deaktiviert (Wintermodus)';
    logMessage('INFO', "Tor {$input['motor_name']} $label");
    sendJSON(['success' => true]);
}

/**
 * POST /api/gate-auto-mode - Gate Auto Mode Einstellung aktualisieren
 */
function updateGateAutoMode() {
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!isset($input['motor_name'])) {
        sendJSON(['error' => 'motor_name required'], 400);
    }
    
    $db = getDB();
    $stmt = $db->prepare('
        INSERT INTO gate_auto_mode (motor_name, auto_enabled)
        VALUES (?, ?)
        ON DUPLICATE KEY UPDATE auto_enabled = ?, updated_at = CURRENT_TIMESTAMP
    ');
    
    $autoEnabled = isset($input['auto_enabled']) ? (int)$input['auto_enabled'] : 1;
    $stmt->execute([
        $input['motor_name'],
        $autoEnabled,
        $autoEnabled
    ]);
    
    logMessage('INFO', "Gate auto mode updated: {$input['motor_name']} = " . ($autoEnabled ? 'ON' : 'OFF'));
    sendJSON(['success' => true]);
}

/**
 * GET /api/gpio-switches - GPIO Switches Status abrufen
 */
function getGpioSwitches() {
    $db = getDB();
    $stmt = $db->query('SELECT name, gpio_pin, state FROM gpio_switches ORDER BY id');
    $switches = $stmt->fetchAll();
    
    sendJSON($switches);
}

/**
 * POST /api/gpio-switches - GPIO Switch umschalten
 */
function toggleGpioSwitch() {
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!isset($input['name']) || !isset($input['state'])) {
        sendJSON(['error' => 'name and state required'], 400);
    }
    
    $db = getDB();
    $stmt = $db->prepare('
        UPDATE gpio_switches 
        SET state = ?, updated_at = CURRENT_TIMESTAMP
        WHERE name = ?
    ');
    $stmt->execute([(int)$input['state'], $input['name']]);
    
    if ($stmt->rowCount() === 0) {
        sendJSON(['error' => 'Switch not found'], 404);
    }
    
    logMessage('INFO', "GPIO Switch toggled: {$input['name']} = " . ($input['state'] ? 'ON' : 'OFF'));
    sendJSON(['success' => true]);
}

/**
 * GET /api/ventilation/custom-phases - Custom Ventilation Phases abrufen
 */
function getCustomVentilationPhases() {
    $db = getDB();
    $stmt = $db->query('
        SELECT id, name, start_time, end_time, enabled 
        FROM custom_ventilation_phases 
        ORDER BY start_time
    ');
    $phases = $stmt->fetchAll();
    
    sendJSON($phases);
}

/**
 * POST /api/ventilation/custom-phases - Custom Ventilation Phase erstellen
 */
function createCustomVentilationPhase() {
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!isset($input['start_time']) || !isset($input['end_time'])) {
        sendJSON(['error' => 'start_time and end_time required'], 400);
    }
    
    // Validiere Zeitformat
    if (!preg_match('/^\d{2}:\d{2}(:\d{2})?$/', $input['start_time']) || 
        !preg_match('/^\d{2}:\d{2}(:\d{2})?$/', $input['end_time'])) {
        sendJSON(['error' => 'Invalid time format. Use HH:MM'], 400);
    }
    
    // Prüfe auf Überschneidungen
    $overlap = checkVentilationOverlap($input['start_time'], $input['end_time'], $input['id'] ?? null);
    if ($overlap) {
        sendJSON(['error' => 'Time window overlaps with: ' . $overlap], 409);
    }
    
    $db = getDB();
    
    // Update oder Insert
    if (isset($input['id'])) {
        $stmt = $db->prepare('
            UPDATE custom_ventilation_phases 
            SET name = ?, start_time = ?, end_time = ?, enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ');
        $stmt->execute([
            $input['name'] ?? null,
            $input['start_time'],
            $input['end_time'],
            isset($input['enabled']) ? (int)$input['enabled'] : 1,
            $input['id']
        ]);
    } else {
        $stmt = $db->prepare('
            INSERT INTO custom_ventilation_phases (name, start_time, end_time, enabled)
            VALUES (?, ?, ?, ?)
        ');
        $stmt->execute([
            $input['name'] ?? null,
            $input['start_time'],
            $input['end_time'],
            isset($input['enabled']) ? (int)$input['enabled'] : 1
        ]);
    }
    
    logMessage('INFO', "Custom ventilation phase created/updated: {$input['start_time']} - {$input['end_time']}");
    sendJSON(['success' => true, 'id' => $input['id'] ?? $db->lastInsertId()]);
}

/**
 * DELETE /api/ventilation/custom-phases/{id} - Custom Phase löschen
 */
function deleteCustomVentilationPhase($id) {
    $db = getDB();
    $stmt = $db->prepare('DELETE FROM custom_ventilation_phases WHERE id = ?');
    $stmt->execute([$id]);
    
    if ($stmt->rowCount() === 0) {
        sendJSON(['error' => 'Phase not found'], 404);
    }
    
    logMessage('INFO', "Custom ventilation phase deleted: ID $id");
    sendJSON(['success' => true]);
}

/**
 * Prüft ob ein Zeitfenster mit festen oder anderen custom Phasen überlappt
 */
function checkVentilationOverlap($start_time, $end_time, $exclude_id = null) {
    $db = getDB();
    
    // Hole Ventilation Config für feste Zeiten
    $stmt = $db->query('SELECT * FROM ventilation_config LIMIT 1');
    $config = $stmt->fetch();
    
    if (!$config) {
        return false; // Keine Config, keine Überschneidung
    }
    
    // Berechne feste Zeitfenster (vereinfacht - echte Berechnung erfolgt im Pi-Client)
    $fixed_windows = [];
    
    // Morgens: ca. 5:00-5:20 (Platzhalter, echte Zeit variiert)
    if ($config['enabled']) {
        $fixed_windows[] = ['name' => 'Morgens (Sonnenaufgang)', 'start' => '05:00:00', 'end' => '05:20:00'];
    }
    
    // Mittags: 12:00-12:20
    if ($config['midday_enabled']) {
        $fixed_windows[] = ['name' => 'Mittags', 'start' => '12:00:00', 'end' => '12:20:00'];
    }
    
    // Abends: ca. 18:00-18:20 (Platzhalter, echte Zeit variiert)
    if ($config['evening_enabled']) {
        $fixed_windows[] = ['name' => 'Abends (Sonnenuntergang)', 'start' => '18:00:00', 'end' => '18:20:00'];
    }
    
    // Prüfe Überschneidung mit festen Zeiten
    foreach ($fixed_windows as $window) {
        if (timeRangesOverlap($start_time, $end_time, $window['start'], $window['end'])) {
            return $window['name'];
        }
    }
    
    // Prüfe Überschneidung mit anderen custom Phasen
    $stmt = $db->prepare('
        SELECT id, name, start_time, end_time 
        FROM custom_ventilation_phases
        WHERE enabled = 1
        ' . ($exclude_id ? 'AND id != ?' : '')
    );
    $stmt->execute($exclude_id ? [$exclude_id] : []);
    $phases = $stmt->fetchAll();
    
    foreach ($phases as $phase) {
        if (timeRangesOverlap($start_time, $end_time, $phase['start_time'], $phase['end_time'])) {
            return $phase['name'] ?: "Phase #{$phase['id']}";
        }
    }
    
    return false;
}

/**
 * Prüft ob zwei Zeitbereiche sich überschneiden
 */
function timeRangesOverlap($start1, $end1, $start2, $end2) {
    // Konvertiere zu Timestamps für Vergleich
    $s1 = strtotime($start1);
    $e1 = strtotime($end1);
    $s2 = strtotime($start2);
    $e2 = strtotime($end2);
    
    // Überschneidung wenn: start1 < end2 UND end1 > start2
    return $s1 < $e2 && $e1 > $s2;
}

// Helper functions (getDB, sendJSON, etc.) are now in config.php to avoid duplication

/**
 * GET /api/gate-status - Alle Tor-Positionen abrufen
 */
function getGateStatus() {
    $db = getDB();
    $stmt = $db->query('SELECT motor_name, position, last_command, updated_at FROM gate_status ORDER BY motor_name');
    $gates = $stmt->fetchAll();
    sendJSON($gates);
}

/**
 * POST /api/gate-status - Tor-Position aktualisieren
 */
function updateGateStatus() {
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!isset($input['motor_name']) || !isset($input['position'])) {
        sendJSON(['error' => 'Missing motor_name or position'], 400);
    }
    
    $db = getDB();
    
    // Update Position
    $stmt = $db->prepare('
        UPDATE gate_status 
        SET position = ?, updated_at = CURRENT_TIMESTAMP 
        WHERE motor_name = ?
    ');
    
    $stmt->execute([(int)$input['position'], $input['motor_name']]);
    
    if ($stmt->rowCount() === 0) {
        sendJSON(['error' => 'Motor not found'], 404);
    }
    
    logMessage('INFO', "Gate {$input['motor_name']} position updated to {$input['position']}%");
    
    sendJSON(['success' => true]);
}

/**
 * GET /api/settings - System Settings abrufen
 */
function getSystemSettings() {
    $db = getDB();
    $stmt = $db->query('SELECT setting_key, setting_value, setting_type, description, category FROM system_settings ORDER BY category, setting_key');
    $settings = $stmt->fetchAll();
    
    // Gruppiere nach Kategorie
    $grouped = [];
    foreach ($settings as $setting) {
        $category = $setting['category'];
        $key = $setting['setting_key'];
        
        if (!isset($grouped[$category])) {
            $grouped[$category] = [];
        }
        
        // Wert in korrekten Typ umwandeln
        $value = $setting['setting_value'];
        if ($setting['setting_type'] === 'int') {
            $value = (int)$value;
        } elseif ($setting['setting_type'] === 'float') {
            $value = (float)$value;
        }
        
        $grouped[$category][$key] = [
            'value' => $value,
            'type' => $setting['setting_type'],
            'description' => $setting['description']
        ];
    }
    
    sendJSON($grouped);
}

/**
 * POST /api/settings - System Settings aktualisieren
 */
function updateSystemSettings() {
    $input = json_decode(file_get_contents('php://input'), true);
    
    if (!$input || !is_array($input)) {
        sendJSON(['error' => 'Invalid input'], 400);
    }
    
    $db = getDB();
    $updated = [];
    
    foreach ($input as $key => $value) {
        // Validierung
        if (!validateSettingValue($key, $value)) {
            sendJSON(['error' => "Invalid value for setting: $key"], 400);
        }
        
        // Update
        $stmt = $db->prepare('
            UPDATE system_settings 
            SET setting_value = ?, updated_at = CURRENT_TIMESTAMP
            WHERE setting_key = ?
        ');
        $stmt->execute([strval($value), $key]);
        
        if ($stmt->rowCount() > 0) {
            $updated[] = $key;
        }
    }
    
    if (!empty($updated)) {
        logMessage('INFO', 'Settings updated: ' . implode(', ', $updated));
    }
    
    sendJSON(['success' => true, 'updated' => $updated]);
}

/**
 * POST /api/restart-service - Fugt einen RESTART-Befehl für den Pi hinzu
 */
function restartService() {
    $db = getDB();
    $stmt = $db->prepare("INSERT INTO commands (command) VALUES ('RESTART')");
    $stmt->execute();
    
    logMessage('INFO', 'System-Neustart angefordert (RESTART-Befehl)');
    sendJSON(['success' => true]);
}

/**
 * Validiert Setting-Werte
 */
function validateSettingValue($key, $value) {
    // Temperatur-Validierung
    if ($key === 'DEFAULT_TARGET_TEMP') {
        return is_numeric($value) && $value >= 5 && $value <= 45;
    }
    if ($key === 'TEMP_HYSTERESIS') {
        return is_numeric($value) && $value >= 0.5 && $value <= 10;
    }
    if ($key === 'TEMP_THRESHOLD') {
        return is_numeric($value) && $value >= 1 && $value <= 30;
    }
    
    // Motor-Validierung
    if ($key === 'MOTOR_RUNTIME_OPEN' || $key === 'MOTOR_RUNTIME_CLOSE') {
        return is_numeric($value) && $value >= 60 && $value <= 300;
    }
    
    // Intervall-Validierung
    if ($key === 'INTERVAL_FAST') {
        return is_numeric($value) && $value >= 1 && $value <= 30;
    }
    if ($key === 'INTERVAL_NORMAL') {
        return is_numeric($value) && $value >= 5 && $value <= 120;
    }
    if ($key === 'INTERVAL_SLOW') {
        return is_numeric($value) && $value >= 10 && $value <= 600;
    }
    
    // Standort-Validierung
    if ($key === 'LOCATION_LAT') {
        return is_numeric($value) && $value >= -90 && $value <= 90;
    }
    if ($key === 'LOCATION_LON') {
        return is_numeric($value) && $value >= -180 && $value <= 180;
    }
    
    // Netzwerk-Validierung
    if ($key === 'MAX_RETRIES') {
        return is_numeric($value) && $value >= 1 && $value <= 10;
    }
    if ($key === 'RETRY_DELAY') {
        return is_numeric($value) && $value >= 5 && $value <= 120;
    }
    
    // Unbekannter Key
    return false;
}
