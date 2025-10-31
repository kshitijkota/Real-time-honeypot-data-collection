import os
import functools
import threading
import time
from flask import (
    Flask,
    jsonify,
    request,
    session,
)
import mysql.connector
from mysql.connector import Error

app = Flask(__name__, static_folder="static", static_url_path="")

# Secret key is required for Flask sessions
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "a_very_secret_key_fallback")

# --- Database Connection Logic ---


def get_db_connection(username, password):
    """
    Attempts to connect to the DB with specific credentials.
    Returns (connection, error)
    """
    try:
        conn = mysql.connector.connect(
            host="localhost",
            port=3306,
            user=username,
            password=password,
            database="honeypot_data",
        )
        return conn, None
    except Error as e:
        return None, str(e)


def get_db_connection_for_session():
    """
    Gets a DB connection using credentials stored in the user's session.
    """
    if "username" not in session or "password" not in session:
        return None

    conn, err = get_db_connection(session["username"], session["password"])
    if err:
        print(f"Failed to reconnect for user {session['username']}: {err}")
        return None
    return conn


# --- Decorators for Role-Based Access Control ---


def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            return jsonify({"error": "Unauthorized. Please log in."}), 401
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("role") != "admin":
            return jsonify({"error": "Forbidden. Admin access required."}), 403
        return f(*args, **kwargs)

    return decorated_function


# --- User Session & Root ---


@app.route("/")
def index():
    """Serves the main index.html file from the static folder."""
    return app.send_static_file("index.html")


@app.route("/login", methods=["POST"])
def login():
    """
    Handles user login.
    Tries to connect to the DB with provided credentials to validate them.
    """
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return (
            jsonify({"success": False, "error": "Username and password required"}),
            400,
        )

    conn, err = get_db_connection(username, password)
    if err:
        return jsonify({"success": False, "error": f"Login failed: {err}"}), 401

    conn.close()

    # Login success! Store credentials in session.
    session["username"] = username
    session["password"] = password

    # Determine role based on username (as defined in roles.sql)
    role = "unknown"
    if username == "analyst":
        role = "analyst"
    elif username == "honeypot_admin":
        role = "admin"

    session["role"] = role

    return jsonify({"success": True, "role": role})


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out"})


@app.route("/api/session")
def get_session():
    """Checks if a user is currently logged in."""
    if "username" in session:
        return jsonify(
            {
                "loggedIn": True,
                "username": session["username"],
                "role": session.get("role", "unknown"),
            }
        )
    return jsonify({"loggedIn": False})


# --- API Query Helper ---


def execute_query(query, params=None):
    """Helper function to run a SELECT or CALL query and return results."""
    conn = get_db_connection_for_session()
    if not conn:
        return jsonify({"error": "Database session error"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if query.strip().upper().startswith("SELECT"):
            results = cursor.fetchall()
            return jsonify(results)
        else:
            conn.commit()
            return jsonify({"success": True})
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


# --- Dashboard Queries ---


@app.route("/api/query/top-countries")
@login_required
def get_top_countries():
    query = "SELECT country, total_sessions FROM COUNTRY_STATS ORDER BY total_sessions DESC LIMIT 10;"
    return execute_query(query)


@app.route("/api/query/top-credentials")
@login_required
def get_top_credentials():
    conn = get_db_connection_for_session()
    if not conn:
        return jsonify({"error": "Database session error"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.callproc("GetTopCredentials", (10,))
        results = []
        for result in cursor.stored_results():
            results = result.fetchall()
        return jsonify(results)
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@app.route("/api/query/attack-trends")
@login_required
def get_attack_trends():
    """
    Fetches daily attack trends by calling the GetDailyTrends stored procedure.
    Returns the data directly to the frontend without modifying the database.
    """
    conn = get_db_connection_for_session()
    if not conn:
        return jsonify({"error": "Database session error"}), 500

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.callproc("GetDailyTrends")
        daily_trends = []
        for result in cursor.stored_results():
            daily_trends = result.fetchall()

        # Return the trends directly to the frontend
        return jsonify(daily_trends)
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@app.route("/api/query/auth-stats")
@login_required
def get_auth_stats():
    query = "SELECT status, total FROM AUTH_STATS ORDER BY total DESC;"
    return execute_query(query)


@app.route("/api/query/top-malware")
@login_required
def get_top_malware():
    query = "SELECT * FROM TopMalware LIMIT 10;"
    return execute_query(query)


@app.route("/api/query/command-frequency")
@login_required
def get_command_frequency():
    ip_address = request.args.get("ip")
    if not ip_address:
        return jsonify({"error": "ip parameter is required"}), 400

    conn = get_db_connection_for_session()
    if not conn:
        return jsonify({"error": "Database session error"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.callproc("GetCommandFrequency", (ip_address,))
        results = []
        for result in cursor.stored_results():
            results = result.fetchall()
        return jsonify(results)
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


@app.route("/api/query/avg-session-duration")
@login_required
def get_avg_session_duration():
    query = """
    SELECT country, ROUND(avg_duration_sec / 60, 2) AS avg_duration_mins
    FROM AvgSessionDurationByCountry
    ORDER BY avg_duration_mins DESC LIMIT 10;
    """
    return execute_query(query)


@app.route('/api/query/active-attackers')
@login_required
def get_active_attackers():
    conn = get_db_connection_for_session()
    if not conn: 
        return jsonify({"error": "Database session error"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT a.ip_address, GetCountryFromAttackerID(a.attacker_id) AS country
            FROM ActiveAttackers a
            WHERE (SELECT COUNT(*) FROM SESSION s WHERE s.attacker_id = a.attacker_id) > 1
            ORDER BY (SELECT COUNT(*) FROM SESSION s WHERE s.attacker_id = a.attacker_id) DESC;
        """
        cursor.execute(query)
        results = cursor.fetchall()
        return jsonify(results)
    except Error as e:
        print(f"SQL Error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected(): 
            cursor.close()
            conn.close()


@app.route("/api/query/attacker-rankings")
@login_required
def get_attacker_rankings():
    query = "SELECT * FROM AttackerRankings WHERE rank_by_sessions <= 10;"
    return execute_query(query)


@app.route("/api/query/hourly-trends")
@login_required
def get_hourly_trends():
    query = "SELECT * FROM AttackFrequencyHourly ORDER BY hour_slot ASC;"
    return execute_query(query)


# --- ADMIN-ONLY ENDPOINT ---


@app.route("/api/admin/delete-attacker", methods=["POST"])
@login_required
@admin_required
def delete_attacker():
    ip_address = request.json.get("ip")
    if not ip_address:
        return jsonify({"error": "IP address is required"}), 400

    # --- Local MySQL Connection ---
    local_conn = get_db_connection_for_session()
    if not local_conn:
        return jsonify({"error": "Local database session error"}), 500

    # --- Cowrie Container MySQL Connection ---
    try:
        cowrie_conn = mysql.connector.connect(
            host="localhost",      # or container host name if Docker networked
            port=3307,             # <-- replace with your Cowrie container’s MySQL port
            user="cowrie",           # Cowrie MySQL user
            password="cowriepassword",  # Cowrie MySQL password
            database="cowrie"      # Cowrie DB name
        )
    except Error as e:
        print(f"[!] Cowrie DB connection error: {e}")
        cowrie_conn = None

    try:
        # --- 1 Delete from Cowrie honeypot database ---
        if cowrie_conn:
            cowrie_cursor = cowrie_conn.cursor()
            # Remove sessions and related data linked to this IP
            cowrie_cursor.execute("DELETE FROM sessions WHERE ip = %s", (ip_address,))
            cowrie_conn.commit()
            cowrie_deleted = cowrie_cursor.rowcount
            cowrie_cursor.close()
        else:
            cowrie_deleted = 0
        # --- 2 Delete from LOCAL honeypot_data database ---
        local_cursor = local_conn.cursor()
        local_cursor.execute("DELETE FROM ATTACKER WHERE ip_address = %s", (ip_address,))
        local_conn.commit()
        local_deleted = local_cursor.rowcount
        local_cursor.close()

        message = (
            f"Deleted attacker {ip_address} — "
            f"{local_deleted} local entries, {cowrie_deleted} in Cowrie DB."
        )
        print(f"[+] {message}")
        return jsonify({"success": True, "message": message})

    except Error as e:
        if local_conn and local_conn.is_connected():
            local_conn.rollback()
        if cowrie_conn and cowrie_conn.is_connected():
            cowrie_conn.rollback()
        return jsonify({"error": str(e)}), 500

    finally:
        if local_conn and local_conn.is_connected():
            local_conn.close()
        if cowrie_conn and cowrie_conn.is_connected():
            cowrie_conn.close()

# # --- Background Trend Updater Thread ---


# def update_trends_periodically():
#     """Runs the stored procedure every 5 minutes in background."""
#     while True:
#         try:
#             conn, err = get_db_connection("honeypot_admin", "your_admin_password")
#             if conn and not err:
#                 cursor = conn.cursor()
#                 cursor.execute("CALL UpdateDailyTrends();")
#                 conn.commit()
#                 cursor.close()
#                 conn.close()
#                 print("[+] Attack trends updated.")
#             else:
#                 print(f"[!] Could not connect to DB: {err}")
#         except Exception as e:
#             print(f"[!] Error updating trends: {e}")
#         time.sleep(300)  # 5 minutes


if __name__ == "__main__":
    # Start the background updater thread
    # threading.Thread(target=update_trends_periodically, daemon=True).start()
    app.run(debug=True, port=5000)
