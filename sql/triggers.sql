DELIMITER //
CREATE TRIGGER trg_update_country_stats
AFTER INSERT ON SESSION
FOR EACH ROW
BEGIN
    DECLARE country_name VARCHAR(100);
    SELECT g.country INTO country_name
    FROM GEOIP_CACHE g
    JOIN ATTACKER a ON a.geoip_id = g.geoip_id
    WHERE a.attacker_id = NEW.attacker_id;

    INSERT INTO COUNTRY_STATS (country, total_sessions)
    VALUES (country_name, 1)
    ON DUPLICATE KEY UPDATE total_sessions = total_sessions + 1;
END;
//
DELIMITER ;

DELIMITER //
CREATE TRIGGER trg_auth_stats_update
AFTER INSERT ON AUTH_ATTEMPT
FOR EACH ROW
BEGIN
    INSERT INTO AUTH_STATS(status, total)
    VALUES (NEW.status, 1)
    ON DUPLICATE KEY UPDATE total = total + 1;
END;
//
DELIMITER ;
