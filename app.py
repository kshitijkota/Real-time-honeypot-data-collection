import os
import functools
from flask import Flask, jsonify, request, session, redirect, url_for, send_from_directory
import mysql.connector
from mysql.connector import Error

app = Flask(__name__, static_folder='static', static_url_path='')

# Secret key is required for Flask sessions
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_very_secret_key_fallback')

# --- Database Connection Logic ---

def get_db_connection(username, password):
    """
    Attempts to connect to the DB with specific credentials.
    Returns (connection, error)
    """
    try:
        conn = mysql.connector.connect(
            host='localhost',
            port=3306,
            user=username,
            password=password,
            database='honeypot_data'
        )
        return conn, None
    except Error as e:
        return None, str(e)

def get_db_connection_for_session():
    """
    Gets a DB connection using credentials stored in the user's session.
    """
    if 'username' not in session or 'password' not in session:
        return None
    
    conn, err = get_db_connection(session['username'], session['password'])
    if err:
        print(f"Failed to reconnect for user {session['username']}: {err}")
        return None
    return conn

# --- Decorators for Role-Based Access Control ---

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return jsonify({"error": "Unauthorized. Please log in."}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            return jsonify({"error": "Forbidden. Admin access required."}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- User Session & Root ---

@app.route('/')
def index():
    """Serves the main index.html file from the static folder."""
    return app.send_static_file('index.html')

@app.route('/login', methods=['POST'])
def login():
    """
    Handles user login.
    Tries to connect to the DB with provided credentials to validate them.
    """
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400

    conn, err = get_db_connection(username, password)
    if err:
        return jsonify({"success": False, "error": f"Login failed: {err}"}), 401

    conn.close()

    # Login success! Store credentials in session.
    session['username'] = username
    session['password'] = password
    
    # Determine role based on username (as defined in roles.sql)
    role = "unknown"
    if username == 'analyst':
        role = 'analyst'
    elif username == 'honeypot_admin':
        role = 'admin'
    
    session['role'] = role
    
    return jsonify({"success": True, "role": role})

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out"})

@app.route('/api/session')
def get_session():
    """Checks if a user is currently logged in."""
    if 'username' in session:
        return jsonify({
            "loggedIn": True,
            "username": session['username'],
            "role": session.get('role', 'unknown')
        })
    return jsonify({"loggedIn": False})

# --- API Endpoints for Dashboard ---

def execute_query(query, params=None):
    """Helper function to run a SELECT query and return results."""
    conn = get_db_connection_for_session()
    if not conn:
        return jsonify({"error": "Database session error"}), 500
    
    try:
        cursor = conn.cursor(dictionary=True)
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        results = cursor.fetchall()
        return jsonify(results)
    
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route('/api/query/top-countries')
@login_required
def get_top_countries():
    # 1. Top Attacker Countries
    query = "SELECT country, total_sessions FROM COUNTRY_STATS ORDER BY total_sessions DESC LIMIT 10;"
    return execute_query(query)

@app.route('/api/query/top-credentials')
@login_required
def get_top_credentials():
    # 2. Most Common Credentials (Stored Procedure)
    conn = get_db_connection_for_session()
    if not conn: return jsonify({"error": "Database session error"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('GetTopCredentials', (10,))
        results = []
        for result in cursor.stored_results():
            results = result.fetchall()
        return jsonify(results)
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@app.route('/api/query/attack-trends')
@login_required
def get_attack_trends():
    # 3. Attack Frequency Over Time
    query = "SELECT day, total_sessions, total_auth_attempts FROM ATTACK_TRENDS ORDER BY day ASC;"
    return execute_query(query)

@app.route('/api/query/auth-stats')
@login_required
def get_auth_stats():
    # 4. Success vs Failed Attempts
    query = "SELECT status, total FROM AUTH_STATS ORDER BY total DESC;"
    return execute_query(query)

@app.route('/api/query/top-malware')
@login_required
def get_top_malware():
    # 5. Top Downloaded Malware Hashes (View)
    query = "SELECT * FROM TopMalware LIMIT 10;"
    return execute_query(query)

@app.route('/api/query/command-frequency')
@login_required
def get_command_frequency():
    # 6. Command Frequency per Attacker (Stored Procedure - INTERACTIVE)
    ip_address = request.args.get('ip')
    if not ip_address:
        return jsonify({"error": "ip parameter is required"}), 400
        
    conn = get_db_connection_for_session()
    if not conn: return jsonify({"error": "Database session error"}), 500
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.callproc('GetCommandFrequency', (ip_address,))
        results = []
        for result in cursor.stored_results():
            results = result.fetchall()
        return jsonify(results)
    except Error as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

@app.route('/api/query/avg-session-duration')
@login_required
def get_avg_session_duration():
    # 7. Average Session Duration per Country (View)
    query = "SELECT country, ROUND(avg_duration_sec / 60, 2) AS avg_duration_mins FROM AvgSessionDurationByCountry ORDER BY avg_duration_mins DESC LIMIT 10;"
    return execute_query(query)

@app.route('/api/query/active-attackers')
@login_required
def get_active_attackers():
    # 8. Active Attackers (View + Function)
    query = """
        SELECT a.ip_address, GetCountryFromAttackerID(a.attacker_id) AS country
        FROM ActiveAttackers a
        WHERE (SELECT COUNT(*) FROM SESSION s WHERE s.attacker_id = a.attacker_id) > 1
        ORDER BY (SELECT COUNT(*) FROM SESSION s WHERE s.attacker_id = a.attacker_id) DESC;
    """
    return execute_query(query)

@app.route('/api/query/attacker-rankings')
@login_required
def get_attacker_rankings():
    # 9. Window Function Analysis (View)
    query = "SELECT * FROM AttackerRankings WHERE rank_by_sessions <= 10;"
    return execute_query(query)

@app.route('/api/query/hourly-trends')
@login_required
def get_hourly_trends():
    # 10. Time-Based Hourly Trends (View)
    query = "SELECT * FROM AttackFrequencyHourly ORDER BY hour_slot ASC;"
    return execute_query(query)

# --- ADMIN-ONLY ENDPOINT ---

@app.route('/api/admin/delete-attacker', methods=['POST'])
@login_required
@admin_required
def delete_attacker():
    """
    Deletes all records associated with an attacker IP.
    This demonstrates the ADMIN role's CUD privileges.
    """
    ip_address = request.json.get('ip')
    if not ip_address:
        return jsonify({"error": "IP address is required"}), 400
    
    conn = get_db_connection_for_session()
    if not conn:
        return jsonify({"error": "Database session error"}), 500
    
    try:
        cursor = conn.cursor()
        # The admin role (granted in roles.sql) has DELETE privileges
        # The analyst role does not, so this would fail for them.
        cursor.execute("DELETE FROM ATTACKER WHERE ip_address = %s", (ip_address,))
        conn.commit()
        deleted_count = cursor.rowcount
        cursor.close()
        conn.close()
        
        if deleted_count == 0:
            return jsonify({"success": True, "message": f"No attacker found with IP {ip_address}"})
        
        return jsonify({"success": True, "message": f"Successfully deleted attacker {ip_address} and all related data (sessions, commands, etc.)"})
    
    except Error as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
