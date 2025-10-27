-- Drop old roles if exist
DROP ROLE IF EXISTS 'etl_user', 'analyst_user', 'admin_user';

-- 1️⃣ ETL Role - inserts and updates data
CREATE ROLE 'etl_user';
GRANT INSERT, UPDATE, SELECT ON honeypot_data.* TO 'etl_user';

-- 2️⃣ Analyst Role - read-only, can run complex queries AND execute procedures/functions
CREATE ROLE 'analyst_user';
GRANT SELECT ON honeypot_data.* TO 'analyst_user';
GRANT EXECUTE ON honeypot_data.* TO 'analyst_user';  -- ← ADD THIS LINE

-- 3️⃣ Admin Role - full privileges
CREATE ROLE 'admin_user';
GRANT ALL PRIVILEGES ON honeypot_data.* TO 'admin_user' WITH GRANT OPTION;

-- Create users and assign roles
CREATE USER IF NOT EXISTS 'etl_service'@'localhost' IDENTIFIED BY 'etlpass';
CREATE USER IF NOT EXISTS 'analyst'@'localhost' IDENTIFIED BY 'analystpass';
CREATE USER IF NOT EXISTS 'honeypot_admin'@'localhost' IDENTIFIED BY 'adminpass';

GRANT 'etl_user' TO 'etl_service'@'localhost';
GRANT 'analyst_user' TO 'analyst'@'localhost';
GRANT 'admin_user' TO 'honeypot_admin'@'localhost';

-- Default roles
SET DEFAULT ROLE ALL TO 'etl_service'@'localhost', 'analyst'@'localhost', 'honeypot_admin'@'localhost';

FLUSH PRIVILEGES;
