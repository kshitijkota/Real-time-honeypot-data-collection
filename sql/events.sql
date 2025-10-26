SET GLOBAL event_scheduler = ON;

CREATE EVENT daily_attack_trend_update
ON SCHEDULE EVERY 1 DAY
STARTS CURRENT_TIMESTAMP + INTERVAL 1 DAY
DO
    CALL UpdateDailyTrends();