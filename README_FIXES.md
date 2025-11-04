# Graph Issues - Fixed! ✓

## Summary of Issues Fixed

All the graph data issues have been successfully resolved:

1. ✅ **Attack frequency graph** - Now shows correct daily sessions and auth attempts
2. ✅ **Auth attempts vs sessions** - Auth attempts are no longer squared
3. ✅ **Top attacker countries** - Shows accurate session counts

## What Was Wrong

### 1. GetDailyTrends Procedure (Attack Frequency Graph)
**Problem**: The procedure was using a correlated subquery that counted ALL auth attempts from a given day, not just those belonging to sessions on that day. This caused the auth attempts to be multiplied by the number of sessions.

**Example of the bug**:
- Day 1: 10 sessions, 20 auth attempts total
- Old query would count: 10 sessions × 20 = 200 auth attempts ❌
- Fixed query counts: 10 sessions, 20 auth attempts ✓

### 2. COUNTRY_STATS Table
**Problem**: Using a trigger-updated table instead of a view meant data could become stale or incorrect over time.

**Solution**: Created `COUNTRY_STATS_VIEW` that calculates counts directly from the SESSION table with proper JOINs.

### 3. AUTH_STATS Table
**Problem**: Similar to country stats - trigger-based updates could lead to inconsistencies.

**Solution**: Created `AUTH_STATS_VIEW` that counts directly from AUTH_ATTEMPT table.

## Changes Made

### SQL Files Updated

1. **`sql/views.sql`** - Added two new views:
   ```sql
   - COUNTRY_STATS_VIEW: Real-time country session counts
   - AUTH_STATS_VIEW: Real-time auth attempt statistics
   ```

2. **`sql/procedures.sql`** - Fixed GetDailyTrends:
   ```sql
   - Now uses LEFT JOIN to properly correlate sessions with auth attempts
   - Ensures each auth attempt is counted only once per session per day
   ```

3. **`sql/fix_views_and_procedures.sql`** - Standalone fix script

### Application Files Updated

1. **`app.py`** - Updated two endpoints:
   ```python
   - /api/query/top-countries → uses COUNTRY_STATS_VIEW
   - /api/query/auth-stats → uses AUTH_STATS_VIEW
   ```

### Utility Scripts Created

1. **`fix_database.py`** - Python script to apply fixes (ALREADY RUN ✓)
2. **`apply_fixes.sh`** - Bash script alternative
3. **`FIXES_APPLIED.md`** - Detailed technical documentation

## Verification Results

The fix script ran successfully and verified:

```
✓ COUNTRY_STATS_VIEW created
  - Canada: 4 sessions
  - India: 27 sessions

✓ AUTH_STATS_VIEW created
  - SUCCESS: 50 attempts

✓ GetDailyTrends procedure created
  - Found 4 days of data
  - Sample: (2025-10-17, 4 sessions, 6 auth attempts)
```

## What You Need to Do

### 1. Restart Flask App
If your Flask app (`app.py`) is currently running, restart it:

```bash
# Press Ctrl+C in the terminal where Flask is running
# Then restart it:
cd /Users/kshitij/Personal/Academics/Clg/Studies/Sem5/DBMS/mini_proj
source .venv/bin/activate
python app.py
```

### 2. Clear Browser Cache & Refresh
1. Open your dashboard in the browser
2. Press `Cmd + Shift + R` (Mac) or `Ctrl + Shift + R` (Windows/Linux) for a hard refresh
3. Or clear your browser cache and reload

### 3. Verify the Graphs

Check that:
- **Top Attacker Countries** shows reasonable session counts (not inflated)
- **Auth Success vs. Failure** shows proportional numbers
- **Attack Frequency Over Time** shows:
  - Blue line (Total Sessions): Reasonable daily counts
  - Red line (Total Auth Attempts): Should be higher than sessions but not drastically so
  - The ratio should make sense (e.g., 2-5 attempts per session on average)

## Technical Details

### Before and After Examples

#### GetDailyTrends Query

**BEFORE (Buggy)**:
```sql
SELECT day, COUNT(DISTINCT session_id), SUM(total_auth_attempts)
FROM (
    SELECT DATE(s.start_time) AS day, s.session_id,
           (SELECT COUNT(*) FROM AUTH_ATTEMPT
            WHERE DATE(timestamp) = DATE(s.start_time)) AS total_auth_attempts
    FROM SESSION s
) AS trends
GROUP BY day
```
Problem: Subquery counts ALL auth attempts for the day, multiplied by sessions

**AFTER (Fixed)**:
```sql
SELECT DATE(s.start_time) AS day,
       COUNT(DISTINCT s.session_id) AS total_sessions,
       COUNT(a.auth_id) AS total_auth_attempts
FROM SESSION s
LEFT JOIN AUTH_ATTEMPT a ON s.session_id = a.session_id
    AND DATE(a.timestamp) = DATE(s.start_time)
GROUP BY DATE(s.start_time)
```
Solution: LEFT JOIN ensures each auth attempt is counted exactly once

## Troubleshooting

If graphs still show incorrect data:

1. **Check if Flask restarted properly**:
   ```bash
   lsof -i :5000
   ```

2. **Verify views exist**:
   ```bash
   source .venv/bin/activate
   python -c "import mysql.connector; conn = mysql.connector.connect(host='localhost', user='analyst', password='analystpass', database='honeypot_data'); cur = conn.cursor(); cur.execute('SHOW FULL TABLES WHERE Table_type = \"VIEW\"'); print(cur.fetchall())"
   ```

3. **Re-run the fix script**:
   ```bash
   python fix_database.py
   ```

4. **Check browser console** for any JavaScript errors

## Files Modified

```
✓ sql/views.sql (updated with new views)
✓ sql/procedures.sql (fixed GetDailyTrends)
✓ app.py (updated API endpoints)
✓ sql/fix_views_and_procedures.sql (new standalone fix)
✓ fix_database.py (new utility script)
✓ apply_fixes.sh (new utility script)
✓ FIXES_APPLIED.md (technical documentation)
✓ README_FIXES.md (this file - user guide)
```

## Need Help?

If you encounter any issues:
1. Check the Flask app logs in the terminal
2. Check browser developer console (F12) for errors
3. Verify database connection with: `python -c "import mysql.connector; print('OK')"`
4. Re-run: `python fix_database.py`

---

**Status**: ✅ All fixes applied successfully to database
**Next Step**: Restart Flask app and refresh browser
