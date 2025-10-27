-- 1️⃣ Top Attacker Countries (uses trigger-updated COUNTRY_STATS)
SELECT country, total_sessions
FROM COUNTRY_STATS
ORDER BY total_sessions DESC
LIMIT 10;

-- 2️⃣ Most Common Usernames/Passwords (uses stored procedure GetTopCredentials)
CALL GetTopCredentials(10);

-- 3️⃣ Attack Frequency Over Time (relies on event-triggered ATTACK_TRENDS table)
SELECT day, total_sessions, total_auth_attempts
FROM ATTACK_TRENDS
ORDER BY day DESC;

-- 4️⃣ Success vs Failed Authentication Attempts (uses trigger-updated AUTH_STATS)
SELECT status, total
FROM AUTH_STATS
ORDER BY total DESC;

-- 5️⃣ Top Downloaded Malware Hashes (uses TopMalware view)
SELECT *
FROM TopMalware
LIMIT 10;

-- 6️⃣ Command Frequency per Attacker (uses stored procedure GetCommandFrequency)
CALL GetCommandFrequency('192.168.0.45');  -- replace with target IP

-- 7️⃣ Average Session Duration per Country (uses AvgSessionDurationByCountry view)
SELECT country, ROUND(avg_duration_sec / 60, 2) AS avg_duration_mins
FROM AvgSessionDurationByCountry
ORDER BY avg_duration_mins DESC;

-- 8️⃣ Correlated Subquery for Active Attackers (uses ActiveAttackers view + function)
SELECT a.ip_address, GetCountryFromAttackerID(a.attacker_id) AS country
FROM ActiveAttackers a
WHERE (SELECT COUNT(*) FROM SESSION s WHERE s.attacker_id = a.attacker_id) > 5
ORDER BY (SELECT COUNT(*) FROM SESSION s WHERE s.attacker_id = a.attacker_id) DESC;

-- 9️⃣ Window Function Analysis (uses AttackerRankings view)
SELECT *
FROM AttackerRankings
WHERE rank_by_sessions <= 5;

-- 🔟 Time-Based Analysis (uses AttackFrequencyHourly view)
SELECT *
FROM AttackFrequencyHourly
ORDER BY hour_slot DESC;
