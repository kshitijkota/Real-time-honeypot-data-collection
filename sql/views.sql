CREATE VIEW AttackFrequencyHourly AS
SELECT 
    DATE_FORMAT(timestamp, '%Y-%m-%d %H:00:00') AS hour_slot,
    COUNT(*) AS total_attempts
FROM AUTH_ATTEMPT
GROUP BY hour_slot
ORDER BY hour_slot;

ALTER TABLE DOWNLOAD
ADD CONSTRAINT chk_valid_sha CHECK (filehash REGEXP '^[A-Fa-f0-9]{64}$');

CREATE VIEW TopMalware AS
SELECT filehash, COUNT(*) AS times_downloaded
FROM DOWNLOAD
GROUP BY filehash
ORDER BY times_downloaded DESC;

CREATE VIEW AvgSessionDurationByCountry AS
SELECT 
    g.country,
    AVG(TIMESTAMPDIFF(SECOND, s.start_time, s.end_time)) AS avg_duration_sec
FROM SESSION s
JOIN ATTACKER a ON s.attacker_id = a.attacker_id
JOIN GEOIP_CACHE g ON g.geoip_id = a.geoip_id
WHERE s.end_time IS NOT NULL
GROUP BY g.country;

CREATE VIEW ActiveAttackers AS
SELECT a.attacker_id, a.ip_address
FROM ATTACKER a
WHERE EXISTS (
    SELECT 1 FROM SESSION s
    WHERE s.attacker_id = a.attacker_id
      AND s.end_time IS NULL
);

CREATE VIEW AttackerRankings AS
SELECT 
    a.ip_address,
    COUNT(s.session_id) AS total_sessions,
    RANK() OVER (ORDER BY COUNT(s.session_id) DESC) AS rank_by_sessions
FROM ATTACKER a
JOIN SESSION s ON a.attacker_id = s.attacker_id
GROUP BY a.ip_address;
