# Graph Data Issues - Fixed

## Problems Identified

1. **Attack Frequency Graph (GetDailyTrends)**: The procedure was counting ALL auth attempts from a given day regardless of which sessions they belonged to, causing inflated numbers.

2. **Auth Attempts vs Sessions**: Auth attempts were being counted multiple times for each session due to a correlated subquery that wasn't properly filtering by session.

3. **Top Attacker Countries**: The trigger-based COUNTRY_STATS table might have accumulated incorrect data over time. Creating a view ensures real-time accurate counts.

## Fixes Applied

### 1. Created COUNTRY_STATS_VIEW
**File**: `sql/views.sql`

```sql
CREATE VIEW COUNTRY_STATS_VIEW AS
SELECT
    g.country,
    COUNT(DISTINCT s.session_id) AS total_sessions
FROM SESSION s
JOIN ATTACKER a ON s.attacker_id = a.attacker_id
JOIN GEOIP_CACHE g ON a.geoip_id = g.geoip_id
GROUP BY g.country;
```

This view directly calculates session counts per country by joining the tables, ensuring accurate real-time data.

### 2. Created AUTH_STATS_VIEW
**File**: `sql/views.sql`

```sql
CREATE VIEW AUTH_STATS_VIEW AS
SELECT
    status,
    COUNT(*) AS total
FROM AUTH_ATTEMPT
GROUP BY status;
```

This view directly counts auth attempts by status, replacing the trigger-based table.

### 3. Fixed GetDailyTrends Procedure
**File**: `sql/procedures.sql`

**BEFORE** (Incorrect):
```sql
SELECT
    day,
    COUNT(DISTINCT session_id) AS total_sessions,
    SUM(total_auth_attempts) AS total_auth_attempts
FROM (
    SELECT
        DATE(s.start_time) AS day,
        s.session_id,
        (SELECT COUNT(*)
         FROM AUTH_ATTEMPT
         WHERE DATE(timestamp) = DATE(s.start_time)) AS total_auth_attempts
    FROM SESSION s
) AS trends
GROUP BY day
```

**AFTER** (Correct):
```sql
SELECT
    DATE(s.start_time) AS day,
    COUNT(DISTINCT s.session_id) AS total_sessions,
    COUNT(a.auth_id) AS total_auth_attempts
FROM SESSION s
LEFT JOIN AUTH_ATTEMPT a ON s.session_id = a.session_id
    AND DATE(a.timestamp) = DATE(s.start_time)
GROUP BY DATE(s.start_time)
ORDER BY day ASC;
```

The key fix: Using a LEFT JOIN with proper filtering ensures we only count auth attempts that belong to sessions on that specific day.

### 4. Updated Flask App Endpoints
**File**: `app.py`

Changed endpoints to use the new views:
- `/api/query/top-countries` now queries `COUNTRY_STATS_VIEW` instead of `COUNTRY_STATS`
- `/api/query/auth-stats` now queries `AUTH_STATS_VIEW` instead of `AUTH_STATS`

## How to Apply These Fixes

### Option 1: Run the automated fix script (Easiest)
```bash
./apply_fixes.sh
```

### Option 2: Run the Python fix script
```bash
python3 fix_database.py
```

### Option 3: Run SQL manually
```bash
# If you have MySQL CLI
mysql -u root -p honeypot_data < sql/fix_views_and_procedures.sql

# If using Docker
docker exec -i honeypot-mysql mysql -u root -prootpassword honeypot_data < sql/fix_views_and_procedures.sql
```

### Option 4: Use MySQL Workbench
1. Open MySQL Workbench
2. Connect to the `honeypot_data` database
3. Open and execute `sql/fix_views_and_procedures.sql`

## After Applying Fixes

1. Restart your Flask application:
   ```bash
   python3 app.py
   ```

2. Refresh your browser dashboard

3. The graphs should now show:
   - **Top Countries**: Accurate session counts per country
   - **Auth Success vs Failure**: Correct total auth attempt counts
   - **Attack Frequency Over Time**:
     - Total Sessions line: Number of sessions that started on each day
     - Total Auth Attempts line: Number of auth attempts made during those sessions on that day
   - **Hourly Attack Frequency**: Auth attempts grouped by hour

## Verification

After applying the fixes, verify the data:

```sql
-- Check country stats
SELECT * FROM COUNTRY_STATS_VIEW ORDER BY total_sessions DESC LIMIT 5;

-- Check auth stats
SELECT * FROM AUTH_STATS_VIEW;

-- Check daily trends
CALL GetDailyTrends();
```

All values should now be realistic and proportional.
