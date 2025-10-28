#!/usr/bin/env python3
"""
Cowrie to Custom Schema ETL Adapter - OPTIMIZED VERSION
Only processes NEW sessions instead of all sessions every time
"""

import mysql.connector
from mysql.connector import Error
import requests
import time
import logging
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_public_ip():
    """Fetch the host's public IP address using a simple service."""
    try:
        resp = requests.get("https://api.ipify.org", timeout=5)
        if resp.status_code == 200 and resp.text:
            ip = resp.text.strip()
            return ip
    except Exception as e:
        logger.warning(f"Could not fetch public IP: {e}")
    return None


def random_external_ip():
    """Generate a random (likely public) IPv4 address."""
    first_octet = random.choice(
        [i for i in range(11, 224) if i not in (127, 169, 172, 192)]
    )
    return f"{first_octet}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"


def sanitize_ip(ip):
    """Replace private/local ips with a public or mock external ip."""
    if not ip:
        return ip

    private_prefixes = ("127.", "10.", "172.", "192.168.")
    if ip.startswith(private_prefixes):
        public_ip = get_public_ip()
        if public_ip:
            return public_ip
        mock_ip = random_external_ip()
        return mock_ip
    return ip


class CowrieETLAdapter:
    def __init__(self, source_config, dest_config):
        self.source_config = source_config
        self.dest_config = dest_config
        self.source_conn = None
        self.dest_conn = None

    def connect_databases(self):
        """Establish connections to both databases"""
        try:
            self.source_conn = mysql.connector.connect(**self.source_config)
            logger.info("✅ Connected to Cowrie database")

            self.dest_conn = mysql.connector.connect(**self.dest_config)
            logger.info("✅ Connected to destination database")

            return True
        except Error as e:
            logger.error(f"❌ Database connection error: {e}")
            return False

    def get_geoip_info(self, ip_address):
        """Fetch geolocation info for an IP address using free API"""
        try:
            response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return {
                        "country": data.get("country", "Unknown"),
                        "region": data.get("regionName", None),
                        "city": data.get("city", None),
                        "asn": (
                            str(data.get("as", "").split()[0].replace("AS", ""))
                            if data.get("as")
                            else None
                        ),
                    }
        except Exception as e:
            logger.warning(f"⚠️  GeoIP lookup failed for {ip_address}: {e}")

        return {"country": "Unknown", "region": None, "city": None, "asn": None}

    def insert_or_get_geoip(self, ip_address):
        """Insert or retrieve GeoIP info"""
        cursor = self.dest_conn.cursor()
        geo_info = self.get_geoip_info(ip_address)

        query = """
        INSERT INTO GEOIP_CACHE (country, region, city, asn)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(
            query,
            (
                geo_info["country"],
                geo_info["region"],
                geo_info["city"],
                geo_info["asn"],
            ),
        )

        geoip_id = cursor.lastrowid
        cursor.close()
        return geoip_id

    def insert_or_get_attacker(self, ip_address):
        """Insert or retrieve attacker by IP"""
        cursor = self.dest_conn.cursor()

        cursor.execute(
            "SELECT attacker_id FROM ATTACKER WHERE ip_address = %s", (ip_address,)
        )
        result = cursor.fetchone()

        if result:
            cursor.close()
            return result[0]

        geoip_id = self.insert_or_get_geoip(ip_address)

        query = """
        INSERT INTO ATTACKER (ip_address, geoip_id)
        VALUES (%s, %s)
        """
        cursor.execute(query, (ip_address, geoip_id))
        attacker_id = cursor.lastrowid

        cursor.close()
        logger.info(f"📍 New attacker: {ip_address} (ID: {attacker_id})")

        return attacker_id

    def transfer_sessions(self):
        """Transfer ONLY NEW sessions from Cowrie to custom schema"""
        source_cursor = self.source_conn.cursor(dictionary=True)
        dest_cursor = self.dest_conn.cursor()

        # Check if cowrie_session_id column exists
        dest_cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = 'honeypot_data'
            AND TABLE_NAME = 'SESSION'
            AND COLUMN_NAME = 'cowrie_session_id'
        """
        )

        has_cowrie_id_column = dest_cursor.fetchone()[0] > 0

        if not has_cowrie_id_column:
            logger.warning("⚠️  cowrie_session_id column doesn't exist.")
            logger.warning(
                "⚠️  Run: ALTER TABLE SESSION ADD COLUMN cowrie_session_id VARCHAR(50) UNIQUE;"
            )
            dest_cursor.close()
            source_cursor.close()
            return 0

        # Get list of Cowrie session IDs we've already processed
        dest_cursor.execute(
            "SELECT cowrie_session_id FROM SESSION WHERE cowrie_session_id IS NOT NULL"
        )
        existing_cowrie_ids = {row[0] for row in dest_cursor.fetchall()}
        logger.info(f"🔍 Already processed {len(existing_cowrie_ids)} sessions")

        # Get ONLY NEW sessions from Cowrie (ones we haven't seen before)
        if existing_cowrie_ids:
            placeholders = ",".join(["%s"] * len(existing_cowrie_ids))
            query = f"""
            SELECT id, ip, starttime, endtime
            FROM sessions
            WHERE id NOT IN ({placeholders})
            ORDER BY starttime ASC
            """
            source_cursor.execute(query, tuple(existing_cowrie_ids))
        else:
            # First run - get all sessions
            query = """
            SELECT id, ip, starttime, endtime
            FROM sessions
            ORDER BY starttime ASC
            """
            source_cursor.execute(query)

        sessions = source_cursor.fetchall()
        logger.info(f"📥 Found {len(sessions)} NEW sessions to process")

        transferred = 0

        # Process only NEW sessions
        for session in sessions:
            cowrie_session_id = session["id"]
            raw_ip = session.get("ip")
            ip_address = sanitize_ip(raw_ip) if raw_ip is not None else None
            start_time = session["starttime"]
            end_time = session["endtime"]

            # Get or create attacker
            attacker_id = self.insert_or_get_attacker(ip_address)

            # Insert NEW session
            logger.info(f"✨ New session: {cowrie_session_id}")

            query = """
            INSERT INTO SESSION (attacker_id, start_time, end_time, cowrie_session_id)
            VALUES (%s, %s, %s, %s)
            """
            dest_cursor.execute(
                query, (attacker_id, start_time, end_time, cowrie_session_id)
            )

            new_session_id = dest_cursor.lastrowid
            logger.info(f"✅ Created session as ID {new_session_id}")

            # Transfer related data
            self.transfer_auth_attempts(cowrie_session_id, new_session_id)
            self.transfer_commands(cowrie_session_id, new_session_id)
            self.transfer_downloads(cowrie_session_id, new_session_id)

            transferred += 1

        self.dest_conn.commit()
        source_cursor.close()
        dest_cursor.close()

        logger.info(f"✅ Transferred {transferred} new sessions")
        return transferred

    def transfer_auth_attempts(self, cowrie_session_id, new_session_id):
        """Transfer authentication attempts for a session"""
        source_cursor = self.source_conn.cursor(dictionary=True)
        dest_cursor = self.dest_conn.cursor()

        query = """
        SELECT timestamp, success, username, password
        FROM auth
        WHERE session = %s
        ORDER BY timestamp
        """
        source_cursor.execute(query, (cowrie_session_id,))
        auth_attempts = source_cursor.fetchall()

        inserted = 0
        for auth in auth_attempts:
            status = "SUCCESS" if auth["success"] == 1 else "FAILURE"
            creds = f"{auth['username']}:{auth['password']}"

            query = """
            INSERT INTO AUTH_ATTEMPT (session_id, timestamp, status, creds)
            VALUES (%s, %s, %s, %s)
            """
            dest_cursor.execute(
                query, (new_session_id, auth["timestamp"], status, creds)
            )
            inserted += 1

        if inserted > 0:
            logger.info(f"  ➕ Added {inserted} auth attempts")

        source_cursor.close()
        dest_cursor.close()

    def transfer_commands(self, cowrie_session_id, new_session_id):
        """Transfer commands executed in a session"""
        source_cursor = self.source_conn.cursor(dictionary=True)
        dest_cursor = self.dest_conn.cursor()

        query = """
        SELECT timestamp, input
        FROM input
        WHERE session = %s
        ORDER BY timestamp
        """
        source_cursor.execute(query, (cowrie_session_id,))
        commands = source_cursor.fetchall()

        inserted = 0
        for cmd in commands:
            query = """
            INSERT INTO COMMAND (session_id, timestamp, command_text)
            VALUES (%s, %s, %s)
            """
            dest_cursor.execute(query, (new_session_id, cmd["timestamp"], cmd["input"]))
            inserted += 1

        if inserted > 0:
            logger.info(f"  ➕ Added {inserted} commands")

        source_cursor.close()
        dest_cursor.close()

    def transfer_downloads(self, cowrie_session_id, new_session_id):
        """Transfer file downloads for a session"""
        source_cursor = self.source_conn.cursor(dictionary=True)
        dest_cursor = self.dest_conn.cursor()

        query = """
        SELECT timestamp, shasum, output_file
        FROM downloads
        WHERE session = %s
        ORDER BY timestamp
        """
        source_cursor.execute(query, (cowrie_session_id,))
        downloads = source_cursor.fetchall()

        inserted = 0
        for download in downloads:
            query = """
            INSERT INTO DOWNLOAD (session_id, timestamp, filehash, file_name)
            VALUES (%s, %s, %s, %s)
            """
            dest_cursor.execute(
                query,
                (
                    new_session_id,
                    download["timestamp"],
                    download["shasum"],
                    download["output_file"],
                ),
            )
            inserted += 1

        if inserted > 0:
            logger.info(f"  ➕ Added {inserted} downloads")

        source_cursor.close()
        dest_cursor.close()

    def run_continuous(self, interval=30):
        """Run ETL continuously at specified interval"""
        logger.info(f"🔄 Starting continuous ETL (interval: {interval}s)")

        while True:
            try:
                if not self.source_conn or not self.source_conn.is_connected():
                    logger.warning("⚠️  Reconnecting to databases...")
                    self.connect_databases()

                transferred = self.transfer_sessions()

                if transferred > 0:
                    logger.info(f"🎉 Transfer cycle complete!")
                else:
                    logger.info(f"😴 No new sessions")

            except Exception as e:
                logger.error(f"❌ Error during transfer: {e}", exc_info=True)

            time.sleep(interval)

    def run_once(self):
        """Run ETL once"""
        logger.info("🔄 Running one-time ETL transfer")
        try:
            transferred = self.transfer_sessions()
            logger.info(f"✅ Transfer complete: {transferred} sessions")
            return transferred
        except Exception as e:
            logger.error(f"❌ Error during transfer: {e}", exc_info=True)
            return 0

    def close(self):
        """Close database connections"""
        if self.source_conn and self.source_conn.is_connected():
            self.source_conn.close()
            logger.info("Closed source connection")

        if self.dest_conn and self.dest_conn.is_connected():
            self.dest_conn.close()
            logger.info("Closed destination connection")


def main():
    """Main function"""

    # Cowrie database configuration (Docker container)
    source_config = {
        "host": "localhost",
        "port": 3307,  # Changed port for Docker MySQL
        "user": "cowrie",
        "password": "cowriepassword",
        "database": "cowrie",
    }

    # Your local database configuration
    dest_config = {
        "host": "localhost",
        "port": 3306,
        "user": "etl_service",  # Using ETL user for proper permissions
        "password": "etlpass",
        "database": "honeypot_data",
    }

    # Create ETL adapter
    adapter = CowrieETLAdapter(source_config, dest_config)

    # Connect to databases
    if not adapter.connect_databases():
        logger.error("Failed to connect to databases")
        return

    try:
        # Run continuously - checks every 1 second
        adapter.run_continuous(interval=1)

    except KeyboardInterrupt:
        logger.info("\n⏸️  Stopping ETL adapter...")
    finally:
        adapter.close()


if __name__ == "__main__":
    main()
