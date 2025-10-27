#!/usr/bin/env python3
"""
Cowrie to Custom Schema ETL Adapter
Transfers data from Cowrie's MySQL database to your custom schema

Modifications:
- Added get_public_ip() and sanitize_ip() helpers.
- sanitize_ip() replaces private/local IPs (127.*, 10.*, 172.*, 192.168.*)
  with the machine's public IP (via https://api.ipify.org). If public IP
  lookup fails, a mock external IP is generated so GeoIP lookups return
  non-private results for visualization.
- Minimal logging added when IPs are sanitized.
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
            logger.debug(f"Fetched public IP: {ip}")
            return ip
    except Exception as e:
        logger.warning(f"Could not fetch public IP: {e}")
    return None


def random_external_ip():
    """
    Generate a random (likely public) IPv4 address.
    Avoids RFC1918 private ranges and common reserved addresses.
    """
    # choose first octet from common public ranges (11-223 excluding 127, 169, 172, 192)
    first_octet = random.choice([i for i in range(11, 224) if i not in (127, 169, 172, 192)])
    return f"{first_octet}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}"


def sanitize_ip(ip):
    """
    Replace private/local ips with a public or mock external ip.

    Private ranges handled:
      - 127.0.0.0/8
      - 10.0.0.0/8
      - 172.16.0.0/12  (we check prefix 172.)
      - 192.168.0.0/16
    """
    if not ip:
        return ip

    private_prefixes = ("127.", "10.", "172.", "192.168.")
    if ip.startswith(private_prefixes):
        public_ip = get_public_ip()
        if public_ip:
            logger.info(f"Sanitizing private IP {ip} -> using public IP {public_ip}")
            return public_ip
        mock_ip = random_external_ip()
        logger.info(f"Sanitizing private IP {ip} -> using mock external IP {mock_ip}")
        return mock_ip
    return ip


class CowrieETLAdapter:
    def __init__(self, source_config, dest_config):
        """
        Initialize ETL adapter with source (Cowrie) and destination configs

        Args:
            source_config: dict with Cowrie DB connection details
            dest_config: dict with destination DB connection details
        """
        self.source_config = source_config
        self.dest_config = dest_config
        self.source_conn = None
        self.dest_conn = None
        self.processed_sessions = set()

    def connect_databases(self):
        """Establish connections to both databases"""
        try:
            # Connect to Cowrie database
            self.source_conn = mysql.connector.connect(**self.source_config)
            logger.info("✅ Connected to Cowrie database")

            # Connect to destination database
            self.dest_conn = mysql.connector.connect(**self.dest_config)
            logger.info("✅ Connected to destination database")

            return True
        except Error as e:
            logger.error(f"❌ Database connection error: {e}")
            return False

    def get_geoip_info(self, ip_address):
        """
        Fetch geolocation info for an IP address using free API

        Args:
            ip_address: IP address string

        Returns:
            dict with country, region, city, asn
        """
        try:
            # Using free ip-api.com service (no key needed)
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
        """
        Insert or retrieve GeoIP info

        Returns:
            geoip_id (int)
        """
        cursor = self.dest_conn.cursor()

        # Get GeoIP info
        geo_info = self.get_geoip_info(ip_address)

        # Insert into GEOIP_CACHE
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
        """
        Insert or retrieve attacker by IP

        Returns:
            attacker_id (int)
        """
        cursor = self.dest_conn.cursor()

        # Check if attacker exists
        cursor.execute(
            "SELECT attacker_id FROM ATTACKER WHERE ip_address = %s", (ip_address,)
        )
        result = cursor.fetchone()

        if result:
            cursor.close()
            return result[0]

        # Get or create GeoIP entry
        geoip_id = self.insert_or_get_geoip(ip_address)

        # Insert new attacker
        query = """
        INSERT INTO ATTACKER (ip_address, geoip_id)
        VALUES (%s, %s)
        """
        cursor.execute(query, (ip_address, geoip_id))
        attacker_id = cursor.lastrowid

        cursor.close()
        logger.info(f"📍 New attacker: {ip_address} from {geoip_id}")

        return attacker_id

    def transfer_sessions(self):
        """Transfer sessions from Cowrie to custom schema"""
        source_cursor = self.source_conn.cursor(dictionary=True)
        dest_cursor = self.dest_conn.cursor()

        # Get new sessions from Cowrie
        query = """
        SELECT id, ip, starttime, endtime
        FROM sessions
        ORDER BY starttime DESC
        """
        source_cursor.execute(query)
        sessions = source_cursor.fetchall()

        transferred = 0

        for session in sessions:
            cowrie_session_id = session["id"]

            # Skip if already processed
            if cowrie_session_id in self.processed_sessions:
                continue

            raw_ip = session.get("ip")
            ip_address = sanitize_ip(raw_ip) if raw_ip is not None else None
            start_time = session["starttime"]
            end_time = session["endtime"]

            # Get or create attacker
            attacker_id = self.insert_or_get_attacker(ip_address)

            # Insert session
            query = """
            INSERT INTO SESSION (attacker_id, start_time, end_time)
            VALUES (%s, %s, %s)
            """
            dest_cursor.execute(query, (attacker_id, start_time, end_time))
            new_session_id = dest_cursor.lastrowid

            # Transfer auth attempts for this session
            self.transfer_auth_attempts(cowrie_session_id, new_session_id)

            # Transfer commands for this session
            self.transfer_commands(cowrie_session_id, new_session_id)

            # Transfer downloads for this session
            self.transfer_downloads(cowrie_session_id, new_session_id)

            self.processed_sessions.add(cowrie_session_id)
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

        for cmd in commands:
            query = """
            INSERT INTO COMMAND (session_id, timestamp, command_text)
            VALUES (%s, %s, %s)
            """
            dest_cursor.execute(query, (new_session_id, cmd["timestamp"], cmd["input"]))

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

        source_cursor.close()
        dest_cursor.close()

    def run_continuous(self, interval=30):
        """
        Run ETL continuously at specified interval

        Args:
            interval: seconds between runs
        """
        logger.info(f"🔄 Starting continuous ETL (interval: {interval}s)")

        while True:
            try:
                if not self.source_conn or not self.source_conn.is_connected():
                    logger.warning("⚠️  Reconnecting to databases...")
                    self.connect_databases()

                transferred = self.transfer_sessions()

                if transferred > 0:
                    logger.info(f"✅ Transfer complete: {transferred} sessions")

            except Exception as e:
                logger.error(f"❌ Error during transfer: {e}")

            time.sleep(interval)

    def run_once(self):
        """Run ETL once"""
        logger.info("🔄 Running one-time ETL transfer")
        try:
            transferred = self.transfer_sessions()
            logger.info(f"✅ Transfer complete: {transferred} sessions")
            return transferred
        except Exception as e:
            logger.error(f"❌ Error during transfer: {e}")
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
        "port": 3307,
        "user": "cowrie",
        "password": "cowriepassword",
        "database": "cowrie",
    }

    # Your local database configuration
    dest_config = {
        "host": "localhost",
        "port": 3306,  # Change if different
        "user": "root",
        "password": "root123",
        "database": "honeypot_data",
    }

    # Create ETL adapter
    adapter = CowrieETLAdapter(source_config, dest_config)

    # Connect to databases
    if not adapter.connect_databases():
        logger.error("Failed to connect to databases")
        return

    try:
        # Option 1: Run once
        #adapter.run_once()

        # Option 2: Run continuously (uncomment to use)
        adapter.run_continuous(interval=30)

    except KeyboardInterrupt:
        logger.info("\n⏸️  Stopping ETL adapter...")
    finally:
        adapter.close()


if __name__ == "__main__":
    main()
