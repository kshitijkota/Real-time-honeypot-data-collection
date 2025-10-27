-- GEOIP_CACHE stores geographical info of attacker IPs
CREATE TABLE GEOIP_CACHE (
    geoip_id INT PRIMARY KEY AUTO_INCREMENT,
    country VARCHAR(50) DEFAULT 'Unknown',
    region VARCHAR(50),
    city VARCHAR(50),
    asn VARCHAR(50) CHECK (asn REGEXP '^[0-9]+$' OR asn IS NULL)
);

-- ATTACKER table references GEOIP_CACHE
CREATE TABLE ATTACKER (
    attacker_id INT PRIMARY KEY AUTO_INCREMENT,
    ip_address VARCHAR(45) UNIQUE NOT NULL,
    geoip_id INT,
    FOREIGN KEY (geoip_id) REFERENCES GEOIP_CACHE(geoip_id)
        ON DELETE SET NULL
);

-- SESSION table links to ATTACKER
CREATE TABLE SESSION (
    session_id INT PRIMARY KEY AUTO_INCREMENT,
    attacker_id INT NOT NULL,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME,
    FOREIGN KEY (attacker_id) REFERENCES ATTACKER(attacker_id)
        ON DELETE CASCADE
);

-- AUTH_ATTEMPT table links to SESSION
CREATE TABLE AUTH_ATTEMPT (
    auth_id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('SUCCESS', 'FAILURE') DEFAULT 'FAILURE',
    creds VARCHAR(50),
    FOREIGN KEY (session_id) REFERENCES SESSION(session_id)
        ON DELETE CASCADE
);

-- COMMAND table linked to SESSION
CREATE TABLE COMMAND (
    command_id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    command_text TEXT,
    FOREIGN KEY (session_id) REFERENCES SESSION(session_id)
        ON DELETE CASCADE
);

-- DOWNLOAD table linked to SESSION
CREATE TABLE DOWNLOAD (
    download_id INT PRIMARY KEY AUTO_INCREMENT,
    session_id INT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    filehash CHAR(64),
    file_name VARCHAR(255),
    FOREIGN KEY (session_id) REFERENCES SESSION(session_id)
        ON DELETE CASCADE
);

CREATE TABLE COUNTRY_STATS (
    country VARCHAR(100) PRIMARY KEY,
    total_sessions INT DEFAULT 0
);

CREATE TABLE AUTH_STATS (
    status ENUM('SUCCESS', 'FAILURE') PRIMARY KEY,
    total INT DEFAULT 0
);

CREATE TABLE ATTACK_TRENDS (
    day DATE PRIMARY KEY,
    total_sessions INT,
    total_auth_attempts INT
);

ALTER TABLE SESSION ADD COLUMN cowrie_session_id VARCHAR(50) UNIQUE;