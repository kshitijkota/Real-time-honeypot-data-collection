DELIMITER //
CREATE FUNCTION GetCountryFromAttackerID(attackerId INT)
RETURNS VARCHAR(100)
DETERMINISTIC
BEGIN
    DECLARE country_name VARCHAR(100);

    SELECT g.country INTO country_name
    FROM GEOIP_CACHE g
    JOIN ATTACKER a ON a.geoip_id = g.geoip_id
    WHERE a.attacker_id = attackerId
    LIMIT 1;

    RETURN country_name;
END;
//
DELIMITER ;
