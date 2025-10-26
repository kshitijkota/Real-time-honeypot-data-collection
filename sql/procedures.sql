DELIMITER //
CREATE PROCEDURE GetTopCredentials(IN limit_n INT)
BEGIN
    SELECT 
        SUBSTRING_INDEX(method, ':', 1) AS username,
        SUBSTRING_INDEX(method, ':', -1) AS password,
        COUNT(*) AS attempts
    FROM AUTH_ATTEMPT
    GROUP BY username, password
    ORDER BY attempts DESC
    LIMIT limit_n;
END;
//
DELIMITER ;

DELIMITER //
CREATE PROCEDURE GetCommandFrequency(IN attacker_ip VARCHAR(45))
BEGIN
    SELECT c.command_text, COUNT(*) AS frequency
    FROM COMMAND c
    JOIN SESSION s ON s.session_id = c.session_id
    JOIN ATTACKER a ON a.attacker_id = s.attacker_id
    WHERE a.ip_address = attacker_ip
    GROUP BY c.command_text
    ORDER BY frequency DESC;
END;
//
DELIMITER ;

DELIMITER //
CREATE PROCEDURE UpdateDailyTrends()
BEGIN
    INSERT INTO ATTACK_TRENDS (day, total_sessions, total_auth_attempts)
    VALUES (
        CURDATE(),
        (SELECT COUNT(*) FROM SESSION WHERE DATE(start_time) = CURDATE()),
        (SELECT COUNT(*) FROM AUTH_ATTEMPT WHERE DATE(timestamp) = CURDATE())
    )
    ON DUPLICATE KEY UPDATE
        total_sessions = VALUES(total_sessions),
        total_auth_attempts = VALUES(total_auth_attempts);
END;
//
DELIMITER ;