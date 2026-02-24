-- =====================================================
-- Gewächshaus Steuerung - Complete Database Schema
-- =====================================================
-- Erstellt alle benötigten Tabellen für die Gewächshaus-Steuerung
-- Verwendung: mysql -u USERNAME -p DATABASE_NAME < complete_schema.sql

-- =====================================================
-- 1. STATUS - Aktueller System-Status
-- =====================================================
CREATE TABLE IF NOT EXISTS status (
    id INT PRIMARY KEY AUTO_INCREMENT,
    temp_indoor DECIMAL(4,1) DEFAULT NULL COMMENT 'Innentemperatur in °C',
    temp_outdoor DECIMAL(4,1) DEFAULT NULL COMMENT 'Außentemperatur in °C',
    mode VARCHAR(20) DEFAULT 'MANUAL' COMMENT 'Betriebsmodus: MANUAL, AUTO',
    last_action VARCHAR(255) DEFAULT NULL COMMENT 'Letzte ausgeführte Aktion',
    is_busy TINYINT(1) DEFAULT 0 COMMENT '1 = Motor läuft gerade',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Initialer Status-Eintrag
INSERT INTO status (id, mode, is_busy) VALUES (1, 'MANUAL', 0)
ON DUPLICATE KEY UPDATE id=id;

-- =====================================================
-- 2. COMMANDS - Befehlswarteschlange
-- =====================================================
CREATE TABLE IF NOT EXISTS commands (
    id INT PRIMARY KEY AUTO_INCREMENT,
    command VARCHAR(50) NOT NULL COMMENT 'Befehlsname (z.B. OPEN_ALL, CLOSE_ALL)',
    parameters LONGTEXT DEFAULT NULL COMMENT 'JSON-Parameter',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    executed_at TIMESTAMP NULL DEFAULT NULL,
    status ENUM('pending', 'executing', 'completed', 'failed') DEFAULT 'pending',
    error_message TEXT DEFAULT NULL,
    INDEX idx_status (status),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 3. GATE_STATUS - Tor-Positionen
-- =====================================================
CREATE TABLE IF NOT EXISTS gate_status (
    id INT PRIMARY KEY AUTO_INCREMENT,
    motor_name VARCHAR(50) NOT NULL UNIQUE COMMENT 'Motor-Bezeichnung (z.B. GH1_VORNE)',
    position INT DEFAULT 0 COMMENT 'Aktuelle Position in % (0-100)',
    enabled TINYINT(1) DEFAULT 1 COMMENT '1 = aktiviert, 0 = Wintermodus',
    last_command VARCHAR(50) DEFAULT NULL COMMENT 'Letzter Befehl',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY motor_name (motor_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Initiale Tor-Positionen
INSERT INTO gate_status (motor_name, position) VALUES
    ('GH1_VORNE', 0),
    ('GH1_HINTEN', 0),
    ('GH2_VORNE', 0),
    ('GH2_HINTEN', 0),
    ('GH3_VORNE', 0),
    ('GH3_HINTEN', 0)
ON DUPLICATE KEY UPDATE motor_name=motor_name;

-- =====================================================
-- 4. GATE_AUTO_MODE - Auto-Modus Einstellungen
-- =====================================================
CREATE TABLE IF NOT EXISTS gate_auto_mode (
    motor_name VARCHAR(20) PRIMARY KEY COMMENT 'Motor-Bezeichnung',
    auto_enabled TINYINT(1) DEFAULT 1 COMMENT '1 = Auto-Modus aktiviert, 0 = manuell',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Initiale Auto-Modus Einstellungen
INSERT INTO gate_auto_mode (motor_name, auto_enabled) VALUES
    ('GH1_VORNE', 1),
    ('GH1_HINTEN', 1),
    ('GH2_VORNE', 1),
    ('GH2_HINTEN', 1),
    ('GH3_VORNE', 1),
    ('GH3_HINTEN', 1)
ON DUPLICATE KEY UPDATE motor_name=motor_name;

-- =====================================================
-- 5. VENTILATION_CONFIG - Lüftungs-Konfiguration
-- =====================================================
CREATE TABLE IF NOT EXISTS ventilation_config (
    id INT PRIMARY KEY AUTO_INCREMENT,
    enabled TINYINT(1) DEFAULT 0 COMMENT 'Morgen-Lüftung aktiviert (Sonnenaufgang)',
    latitude DECIMAL(10,8) DEFAULT 47.86559995 COMMENT 'Breitengrad für Sonnenberechnung',
    longitude DECIMAL(11,8) DEFAULT 7.61452259 COMMENT 'Längengrad für Sonnenberechnung',
    offset_minutes INT DEFAULT 30 COMMENT 'Minuten nach Sonnenaufgang',
    duration_minutes INT DEFAULT 20 COMMENT 'Lüftungsdauer in Minuten',
    last_run DATE DEFAULT NULL COMMENT 'Letzter Lüftungslauf (Datum)',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    midday_enabled TINYINT(1) DEFAULT 1 COMMENT 'Mittags-Lüftung aktiviert (12:00)',
    evening_enabled TINYINT(1) DEFAULT 1 COMMENT 'Abend-Lüftung aktiviert (vor Sonnenuntergang)'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Initiale Ventilation Config
INSERT INTO ventilation_config (id, enabled, midday_enabled, evening_enabled) VALUES (1, 1, 1, 1)
ON DUPLICATE KEY UPDATE id=id;

-- =====================================================
-- 6. CUSTOM_VENTILATION_PHASES - Benutzerdefinierte Lüftungszeiten
-- =====================================================
CREATE TABLE IF NOT EXISTS custom_ventilation_phases (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) DEFAULT NULL COMMENT 'Optionaler Name (z.B. "Nachmittags")',
    start_time TIME NOT NULL COMMENT 'Startzeit (HH:MM:SS)',
    end_time TIME NOT NULL COMMENT 'Endzeit (HH:MM:SS)',
    enabled TINYINT(1) DEFAULT 1 COMMENT '1 = aktiv, 0 = deaktiviert',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_time_range (start_time, end_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 7. GPIO_SWITCHES - Zusätzliche GPIO-Schalter
-- =====================================================
CREATE TABLE IF NOT EXISTS gpio_switches (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE COMMENT 'Schalter-Name (z.B. "Bewässerung 1")',
    gpio_pin INT NOT NULL COMMENT 'GPIO-Pin-Nummer (BCM)',
    state TINYINT(1) DEFAULT 0 COMMENT 'Schaltzustand (Active-Low): 0 = EIN/aktiv (GPIO LOW), 1 = AUS/inaktiv (GPIO HIGH)',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Initiale GPIO-Schalter
INSERT INTO gpio_switches (name, gpio_pin, state) VALUES
    ('Bewässerung 1', 20, 0),
    ('Bewässerung 2', 16, 0),
    ('Bewässerung 3', 12, 0),
    ('Zusatz', 25, 0)
ON DUPLICATE KEY UPDATE name=name;

-- =====================================================
-- 8. LOGS - System-Logs
-- =====================================================
CREATE TABLE IF NOT EXISTS logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    level VARCHAR(20) DEFAULT 'INFO' COMMENT 'Log-Level: INFO, WARNING, ERROR',
    message TEXT NOT NULL COMMENT 'Log-Nachricht',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created (created_at),
    INDEX idx_level (level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- FERTIG!
-- =====================================================
-- Alle Tabellen wurden erstellt und mit Standardwerten gefüllt.
