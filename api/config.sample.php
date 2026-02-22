<?php
/**
 * Gewächshaus REST API - Konfiguration (SAMPLE)
 * 
 * Kopiere diese Datei nach config.php und trage deine Daten ein.
 */

// Fehlerbehandlung
error_reporting(E_ALL);
ini_set('display_errors', 0);
ini_set('log_errors', 1);

// Datenbank-Konfiguration
define('DB_HOST', 'localhost');
define('DB_NAME', 'DEINE_DATENBANK');
define('DB_USER', 'DEIN_USER');
define('DB_PASS', 'DEIN_PASSWORT');

// API-Sicherheit
define('API_KEY', 'DEIN_GERAET_API_KEY');

// Web-Interface Passwort (SHA-256 Hash)
define('WEB_PASSWORD_HASH', 'DEIN_PASSWORD_HASH');

// CORS-Einstellungen
define('ALLOW_CORS', false);

// Timezone
date_default_timezone_set('Europe/Berlin');

// Session-Konfiguration
ini_set('session.cookie_httponly', 1);
ini_set('session.cookie_secure', 1); // Nur über HTTPS
ini_set('session.cookie_samesite', 'Strict');

/**
 * Datenbank-Verbindung herstellen
 */
function getDB() {
    static $pdo = null;
    
    if ($pdo === null) {
        try {
            $pdo = new PDO(
                'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4',
                DB_USER,
                DB_PASS,
                [
                    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                    PDO::ATTR_EMULATE_PREPARES => false,
                ]
            );
        } catch (PDOException $e) {
            error_log('DB Connection Error: ' . $e->getMessage());
            http_response_code(500);
            echo json_encode(['error' => 'Database connection failed']);
            exit;
        }
    }
    
    return $pdo;
}

/**
 * API-Key validieren
 */
function validateApiKey() {
    // Versuche getallheaders() (funktioniert nicht immer bei FastCGI)
    $apiKey = '';
    
    if (function_exists('getallheaders')) {
        $headers = getallheaders();
        $apiKey = $headers['X-API-Key'] ?? $headers['x-api-key'] ?? '';
    }
    
    // Fallback: $_SERVER (für FastCGI/nginx)
    if (empty($apiKey)) {
        $apiKey = $_SERVER['HTTP_X_API_KEY'] ?? '';
    }
    
    // Fallback: Query Parameter (falls Header gestrippt werden)
    if (empty($apiKey)) {
        $apiKey = $_REQUEST['api_key'] ?? '';
    }
    
    if ($apiKey !== API_KEY) {
        http_response_code(401);
        echo json_encode(['error' => 'Unauthorized']);
        exit;
    }
}

/**
 * JSON-Response senden
 */
function sendJSON($data, $code = 200) {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    
    if (ALLOW_CORS) {
        header('Access-Control-Allow-Origin: *');
        header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
        header('Access-Control-Allow-Headers: Content-Type, X-API-Key');
    }
    
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

/**
 * Log-Eintrag erstellen
 */
function logMessage($level, $message) {
    try {
        $db = getDB();
        $stmt = $db->prepare('INSERT INTO logs (level, message) VALUES (?, ?)');
        $stmt->execute([$level, $message]);
    } catch (Exception $e) {
        error_log('Log Error: ' . $e->getMessage());
    }
}

/**
 * Session starten
 */
function startSession() {
    if (session_status() === PHP_SESSION_NONE) {
        session_start();
    }
}

/**
 * Login prüfen
 */
function isLoggedIn() {
    startSession();
    return isset($_SESSION['logged_in']) && $_SESSION['logged_in'] === true;
}

/**
 * Login durchführen
 */
function doLogin($password) {
    if (hash('sha256', $password) === WEB_PASSWORD_HASH) {
        startSession();
        $_SESSION['logged_in'] = true;
        $_SESSION['login_time'] = time();
        return true;
    }
    return false;
}

/**
 * Logout durchführen
 */
function doLogout() {
    startSession();
    session_destroy();
}
