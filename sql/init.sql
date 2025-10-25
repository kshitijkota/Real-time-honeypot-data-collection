CREATE DATABASE IF NOT EXISTS cowrie CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE cowrie;

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id VARCHAR(50) PRIMARY KEY,
    starttime DATETIME NOT NULL,
    endtime DATETIME DEFAULT NULL,
    sensor VARCHAR(255) DEFAULT NULL,
    ip VARCHAR(45) DEFAULT NULL,
    termsize VARCHAR(20) DEFAULT NULL,
    client VARCHAR(255) DEFAULT NULL,
    INDEX idx_starttime (starttime),
    INDEX idx_ip (ip),
    INDEX idx_sensor (sensor)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Authentication attempts table
CREATE TABLE IF NOT EXISTS auth (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session VARCHAR(50) NOT NULL,
    success TINYINT(1) NOT NULL DEFAULT 0,
    username VARCHAR(255) DEFAULT NULL,
    password VARCHAR(255) DEFAULT NULL,
    timestamp DATETIME NOT NULL,
    INDEX idx_session (session),
    INDEX idx_timestamp (timestamp),
    INDEX idx_username (username),
    FOREIGN KEY (session) REFERENCES sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Commands/Input table
CREATE TABLE IF NOT EXISTS input (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session VARCHAR(50) NOT NULL,
    timestamp DATETIME NOT NULL,
    success TINYINT(1) DEFAULT NULL,
    input TEXT,
    INDEX idx_session (session),
    INDEX idx_timestamp (timestamp),
    FOREIGN KEY (session) REFERENCES sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Downloads table (FIXED: outfile is a reserved word, changed to output_file)
CREATE TABLE IF NOT EXISTS downloads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session VARCHAR(50) NOT NULL,
    timestamp DATETIME NOT NULL,
    url TEXT,
    output_file VARCHAR(255) DEFAULT NULL,
    shasum VARCHAR(64) DEFAULT NULL,
    INDEX idx_session (session),
    INDEX idx_timestamp (timestamp),
    INDEX idx_shasum (shasum),
    FOREIGN KEY (session) REFERENCES sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Clients table
CREATE TABLE IF NOT EXISTS clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    version VARCHAR(255) NOT NULL,
    UNIQUE KEY unique_version (version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Sensors table
CREATE TABLE IF NOT EXISTS sensors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ip VARCHAR(45) NOT NULL,
    UNIQUE KEY unique_ip (ip)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- TTY logs table
CREATE TABLE IF NOT EXISTS ttylog (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session VARCHAR(50) NOT NULL,
    ttylog VARCHAR(255) DEFAULT NULL,
    size INT DEFAULT NULL,
    INDEX idx_session (session),
    FOREIGN KEY (session) REFERENCES sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create indexes for better query performance
CREATE INDEX idx_sessions_ip_time ON sessions(ip, starttime);
CREATE INDEX idx_auth_username_time ON auth(username, timestamp);
CREATE INDEX idx_input_time ON input(timestamp);
CREATE INDEX idx_downloads_time ON downloads(timestamp);
