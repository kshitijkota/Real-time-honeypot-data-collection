-- Fix Views and Procedures Script
-- Run this to fix the graph data issues

USE honeypot_data;

-- Drop existing views and procedures
DROP VIEW IF EXISTS COUNTRY_STATS_VIEW;
DROP VIEW IF EXISTS AUTH_STATS_VIEW;
DROP PROCEDURE IF EXISTS GetDailyTrends;

-- Create corrected COUNTRY_STATS_VIEW
CREATE VIEW COUNTRY_STATS_VIEW AS
SELECT
    g.country,
    COUNT(DISTINCT s.session_id) AS total_sessions
FROM SESSION s
JOIN ATTACKER a ON s.attacker_id = a.attacker_id
JOIN GEOIP_CACHE g ON a.geoip_id = g.geoip_id
GROUP BY g.country;

-- Create corrected AUTH_STATS_VIEW
CREATE VIEW AUTH_STATS_VIEW AS
SELECT
    status,
    COUNT(*) AS total
FROM AUTH_ATTEMPT
GROUP BY status;

-- Create corrected GetDailyTrends procedure
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

-- Show results
SELECT 'Views and procedures updated successfully!' AS status;
