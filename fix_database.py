#!/usr/bin/env python3
"""
Script to fix the views and procedures in the database
"""
import mysql.connector
from mysql.connector import Error
import os


def get_db_config():
    """Get database configuration"""
    # Try multiple users with their passwords
    configs = [
        {
            "host": "localhost",
            "port": 3306,
            "user": "honeypot_admin",
            "password": "adminpass",
            "database": "honeypot_data",
        },
        {
            "host": "localhost",
            "port": 3306,
            "user": "etl_service",
            "password": "etlpass",
            "database": "honeypot_data",
        },
        {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "",  # Will try empty password first
            "database": "honeypot_data",
        },
    ]
    return configs


def fix_database(config):
    """Apply the fixes to views and procedures"""
    try:
        # Connect to the local honeypot database
        conn = mysql.connector.connect(**config)

        if not conn.is_connected():
            print("Failed to connect to database")
            return False

        print(f"✓ Connected to database as {config['user']}")
        cursor = conn.cursor()

        # Drop existing views
        print("\n1. Dropping existing views...")
        cursor.execute("DROP VIEW IF EXISTS COUNTRY_STATS_VIEW")
        print("  - Dropped COUNTRY_STATS_VIEW")

        cursor.execute("DROP VIEW IF EXISTS AUTH_STATS_VIEW")
        print("  - Dropped AUTH_STATS_VIEW")

        # Drop existing procedure
        print("\n2. Dropping existing procedures...")
        cursor.execute("DROP PROCEDURE IF EXISTS GetDailyTrends")
        print("  - Dropped GetDailyTrends")

        # Create COUNTRY_STATS_VIEW
        print("\n3. Creating new views...")
        cursor.execute(
            """
            CREATE VIEW COUNTRY_STATS_VIEW AS
            SELECT
                g.country,
                COUNT(DISTINCT s.session_id) AS total_sessions
            FROM SESSION s
            JOIN ATTACKER a ON s.attacker_id = a.attacker_id
            JOIN GEOIP_CACHE g ON a.geoip_id = g.geoip_id
            GROUP BY g.country
        """
        )
        print("  - Created COUNTRY_STATS_VIEW")

        # Create AUTH_STATS_VIEW
        cursor.execute(
            """
            CREATE VIEW AUTH_STATS_VIEW AS
            SELECT
                status,
                COUNT(*) AS total
            FROM AUTH_ATTEMPT
            GROUP BY status
        """
        )
        print("  - Created AUTH_STATS_VIEW")

        # Create GetDailyTrends procedure
        print("\n4. Creating new procedures...")
        cursor.execute("DROP PROCEDURE IF EXISTS GetDailyTrends")  # Just to be safe
        cursor.execute(
            """
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
            END
        """
        )
        print("  - Created GetDailyTrends procedure")

        conn.commit()
        print("\n✓ All fixes applied successfully!")

        # Test the views
        print("\n5. Testing views...")
        cursor.execute("SELECT * FROM COUNTRY_STATS_VIEW LIMIT 5")
        results = cursor.fetchall()
        print(f"  - COUNTRY_STATS_VIEW: {len(results)} countries found (showing top 5)")
        for row in results:
            print(f"    {row[0]}: {row[1]} sessions")

        cursor.execute("SELECT * FROM AUTH_STATS_VIEW")
        results = cursor.fetchall()
        print(f"\n  - AUTH_STATS_VIEW:")
        for row in results:
            print(f"    {row[0]}: {row[1]} attempts")

        # Test the procedure
        print(f"\n  - Testing GetDailyTrends procedure...")
        cursor.callproc("GetDailyTrends")
        for result in cursor.stored_results():
            rows = result.fetchall()
            print(f"    Found {len(rows)} days of data")
            if rows:
                print(f"    Sample: {rows[0]}")

        cursor.close()
        conn.close()
        print("\n✓ Database connection closed")
        return True

    except Error as e:
        print(f"\n✗ Error with config {config['user']}: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Database Fix Script - Views and Procedures")
    print("=" * 60)
    print("\nThis script will fix the graph data issues:")
    print("  1. Attack frequency showing incorrect values")
    print("  2. Auth attempts being squared of sessions")
    print("  3. Top countries showing inflated counts")
    print()

    configs = get_db_config()
    success = False

    for config in configs:
        print(f"\nTrying to connect as '{config['user']}'...")
        if fix_database(config):
            success = True
            break

    if not success:
        print("\n" + "=" * 60)
        print("✗ Could not connect with any configuration")
        print("=" * 60)
        print("\nPlease make sure:")
        print("  1. MySQL server is running on localhost:3306")
        print("  2. The 'honeypot_data' database exists")
        print("  3. User credentials are correct in roles.sql")
        print("\nYou can also run the SQL file manually:")
        print("  mysql -u root -p honeypot_data < sql/fix_views_and_procedures.sql")
    else:
        print("\n" + "=" * 60)
        print("✓ SUCCESS - All fixes applied!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Restart your Flask app if it's running")
        print("  2. Refresh your browser dashboard")
        print("  3. All graphs should now show correct data")
