DELIMITER //
CREATE PROCEDURE GetTopCredentials(IN limit_n INT)
BEGIN
    SELECT
        SUBSTRING_INDEX(creds, ':', 1) AS username,
        SUBSTRING_INDEX(creds, ':', -1) AS password,
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
CREATE PROCEDURE GetDailyTrends()
BEGIN
    SELECT
        DATE(s.start_time) AS day,
        COUNT(DISTINCT s.session_id) AS total_sessions,
        COUNT(a.auth_id) AS total_auth_attempts
    FROM SESSION s
    LEFT JOIN AUTH_ATTEMPT a ON s.session_id = a.session_id AND DATE(a.timestamp) = DATE(s.start_time)
    GROUP BY DATE(s.start_time)
    ORDER BY day ASC;
END;
//
DELIMITER ;