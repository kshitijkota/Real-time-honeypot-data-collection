# Real-time Honeypot Data Collection

A comprehensive honeypot system that collects SSH/Telnet attack data using [Cowrie](https://github.com/cowrie/cowrie), stores it in MySQL, and visualizes it through an interactive web dashboard with role-based access control.

## 📋 Project Overview

This project demonstrates advanced DBMS concepts including:
- **ETL Pipeline**: Real-time data extraction from Cowrie honeypot to analytical database
- **Complex SQL Queries**: Window functions, CTEs, stored procedures, views, and triggers
- **Role-Based Access Control**: Multi-user system with different permission levels
- **Interactive Dashboard**: Real-time analytics with Chart.js visualizations
- **Data Integrity**: Foreign keys, constraints, and cascading deletes

### Key Features

✅ SSH/Telnet honeypot on ports 2222/2223  
✅ Real-time attack monitoring and data collection  
✅ Multi-role authentication (Analyst, Admin, ETL Service)  
✅ 9 interactive analytics dashboards  
✅ Admin panel with DELETE privileges demo  
✅ GeoIP geolocation for attackers  
✅ Window functions for attacker rankings  
✅ Docker containerization  

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Attacker Connections (SSH/Telnet)                      │
│ localhost:2222 / localhost:2223                         │
└────────────────┬────────────────────────────────────────┘
                 │
         ┌───────▼────────┐
         │ Cowrie Honeypot│ (Docker Container)
         │ MySQL: :3307   │
         └───────┬────────┘
                 │
    ┌────────────┴────────────┐
    │ ETL Adapter             │
    │ (cowrie_etl_adapter.py) │
    └────────────┬────────────┘
                 │
         ┌───────▼──────────────────┐
         │ Analytical DB            │
         │ honeypot_data            │
         │ MySQL: localhost:3306    │
         └───────┬──────────────────┘
                 │
    ┌────────────┴────────────────┐
    │ Flask Web Server (port 5000)│
    │ - Auth/Login               │
    │ - API Endpoints            │
    │ - Static Assets            │
    └────────────┬────────────────┘
                 │
         ┌───────▼──────────┐
         │ Web Dashboard    │
         │ (index.html)     │
         │ Charts.js        │
         └──────────────────┘
```

---

## 🗄️ Database Schema

### Main Tables

| Table | Purpose |
|-------|---------|
| **GEOIP_CACHE** | Geographical IP information (country, city, ASN) |
| **ATTACKER** | Attack sources with IP and GeoIP reference |
| **SESSION** | Individual attack sessions |
| **AUTH_ATTEMPT** | Login attempts (username:password pairs) |
| **COMMAND** | Commands executed during sessions |
| **DOWNLOAD** | Malware files downloaded by attackers |

### Views & Procedures

| Name | Type | Purpose |
|------|------|---------|
| **COUNTRY_STATS_VIEW** | View | Real-time session counts by country |
| **AUTH_STATS_VIEW** | View | Auth success/failure statistics |
| **AttackerRankings** | View | Window function: rank attackers by session count |
| **ActiveAttackers** | View | Subquery: currently active attack sessions |
| **GetTopCredentials** | Procedure | Top 10 most-used credentials |
| **GetCommandFrequency** | Procedure | Command distribution per attacker IP |
| **GetDailyTrends** | Procedure | Daily attack frequency over time |

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.8+
- MySQL client (optional)
- Linux/macOS (or WSL on Windows)

### 1. Setup Database

```bash
# Create the honeypot_data database and schema
bash setup_db.sh
```

### 2. Start Cowrie Honeypot

```bash
# Start Cowrie and MySQL containers
docker-compose up -d

# Verify containers are running
docker-compose ps
```

### 3. Start ETL Adapter (Optional - for real-time data sync)

```bash
# Continuous ETL sync loop
bash etl.sh

# Or run once:
python3 cowrie_etl_adapter.py
```

### 4. Start Flask Dashboard

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the Flask app
python app.py
```

### 5. Access Dashboard

Open http://localhost:5000 in your browser

**Login Credentials:**

| Username | Password | Role |
|----------|----------|------|
| `analyst` | `analystpass` | Read-only analyst |
| `honeypot_admin` | `adminpass` | Full admin (can delete data) |
| `etl_service` | `etlpass` | ETL service account |

---

## 📊 Dashboard Features

### Card 1: Top Attacker Countries
Bar chart showing attack origins by country

### Card 2: Auth Success vs. Failure
Doughnut chart comparing successful vs. failed login attempts

### Card 3: Top Credentials Used
Table of the 10 most-used username:password combinations

### Card 4: Attack Frequency Over Time
Line chart with dual axes:
- Blue line: Sessions per day
- Red line: Auth attempts per day

### Card 5: Command Frequency per Attacker (Interactive)
Enter an attacker IP to see the commands they executed (Uses stored procedure with `IN` parameter)

### Card 6: Attacker Rankings (Window Function)
Table showing ranked attackers with `RANK() OVER` clause

### Card 7: Active Attackers (Subquery)
Real-time list of attackers with ongoing sessions

### Card 8: Avg Session Duration
Horizontal bar chart of average session duration by country

### Card 9: Hourly Attack Frequency
Bar chart of attacks by hour of day

### Admin Panel
**Analyst role:** Hidden  
**Admin role:** Visible - allows bulk deletion of attacker data

---

## 🔧 Configuration

### Flask App ([app.py](app.py))

```python
# Database credentials (read from session)
# Default roles assigned in login handler
```

### Cowrie Config ([config/cowrie.cfg](config/cowrie.cfg))

```ini
[ssh]
enabled = true
listen_endpoints = tcp:2222:interface=0.0.0.0

[telnet]
enabled = true
listen_endpoints = tcp:2223:interface=0.0.0.0

[output_mysql]
host = mysql
database = cowrie
username = cowrie
password = cowriepassword
port = 3306
```

### ETL Adapter ([cowrie_etl_adapter.py](cowrie_etl_adapter.py))

Source: Cowrie MySQL (Docker) on port 3307  
Destination: Local honeypot_data on port 3306

Features:
- GeoIP lookup via ip-api.com (free tier)
- Sanitizes private IPs (127.x, 10.x, 192.168.x → public IP)
- Deduplication of sessions, commands, auth attempts
- Incremental updates to existing sessions

---

## 📁 File Structure

```
.
├── app.py                          # Flask web server & API
├── cowrie_etl_adapter.py           # ETL data pipeline
├── index.html                      # Dashboard frontend
├── requirements.txt                # Python dependencies
├── docker-compose.yml              # Cowrie + MySQL containers
├── Dockerfile                      # Cowrie image definition
│
├── sql/
│   ├── init.sql                    # Cowrie schema (Docker init)
│   ├── table_creation.sql          # Analytical schema
│   ├── triggers.sql                # Auto-update triggers
│   ├── procedures.sql              # Stored procedures
│   ├── views.sql                   # Analytical views
│   ├── functions.sql               # SQL functions
│   ├── roles.sql                   # User roles & permissions
│   ├── complex_queries.sql         # Reference queries
│   ├── events.sql                  # Scheduled events
│   └── fix_views_and_procedures.sql # Bug fixes
│
├── config/
│   └── cowrie.cfg                  # Honeypot configuration
│
├── static/
│   └── index.html                  # Web dashboard
│
├── setup_db.sh                     # Database initialization
├── setup.sh                        # Full project setup
├── setup_adapter.sh                # ETL adapter setup
├── etl.sh                          # ETL restart loop
├── apply_fixes.sh                  # Apply database fixes
└── fix_database.py                 # Python fix utility
```

---

## 🔐 User Roles & Permissions

### ETL Service Role (`etl_service`)
- **Permissions**: INSERT, UPDATE, SELECT
- **Purpose**: Data collection and transformation
- **Access**: Cowrie → honeypot_data ETL pipeline

### Analyst Role (`analyst`)
- **Permissions**: SELECT, EXECUTE
- **Purpose**: Read-only data analysis
- **Access**: All views, procedures, and functions
- **Cannot**: Modify data, delete attackers

### Admin Role (`honeypot_admin`)
- **Permissions**: ALL PRIVILEGES
- **Purpose**: Full system administration
- **Access**: All operations including DELETE
- **Special Feature**: `/api/admin/delete-attacker` endpoint

---

## 🐳 Docker Containers

### MySQL Container (honeypot-mysql)

```yaml
Image: mysql:8.0
Port: 3307:3306
Database: cowrie
User: cowrie / Password: cowriepassword
Volumes: MySQL data persistence
```

### Cowrie Container (cowrie-honeypot)

```yaml
Image: cowrie/cowrie:latest
Ports: 
  - 2222:2222 (SSH)
  - 2223:2223 (Telnet)
Config: ./config/cowrie.cfg
```

### Start/Stop Commands

```bash
# Start all containers
docker-compose up -d

# Stop all containers
docker-compose down

# View logs
docker-compose logs -f cowrie

# Execute command in container
docker exec honeypot-mysql mysql -u root -prootpassword cowrie -e "SHOW TABLES;"
```

---

## 📈 API Endpoints

All endpoints require authentication (login session).

### Dashboard Queries

| Endpoint | Method | Returns | Uses |
|----------|--------|---------|------|
| `/api/query/top-countries` | GET | Top 10 countries | COUNTRY_STATS_VIEW |
| `/api/query/auth-stats` | GET | Auth success/failure counts | AUTH_STATS_VIEW |
| `/api/query/top-credentials` | GET | Top 10 credentials | GetTopCredentials() |
| `/api/query/attack-trends` | GET | Daily trends | GetDailyTrends() |
| `/api/query/top-malware` | GET | Top downloaded hashes | TopMalware view |
| `/api/query/command-frequency?ip=X.X.X.X` | GET | Commands per attacker | GetCommandFrequency() |
| `/api/query/active-attackers` | GET | Active attack sessions | ActiveAttackers view |
| `/api/query/attacker-rankings` | GET | Ranked attackers | AttackerRankings view |
| `/api/query/avg-session-duration` | GET | Avg duration by country | AvgSessionDurationByCountry |
| `/api/query/hourly-trends` | GET | Hourly attack frequency | AttackFrequencyHourly view |

### Admin Endpoints

| Endpoint | Method | Body | Returns | Auth |
|----------|--------|------|---------|------|
| `/api/admin/delete-attacker` | POST | `{"ip": "X.X.X.X"}` | Deletion status | Admin only |

### Auth Endpoints

| Endpoint | Method | Body |
|----------|--------|------|
| `/login` | POST | `{"username": "...", "password": "..."}` |
| `/logout` | POST | - |
| `/api/session` | GET | - |

---

## 🐛 Troubleshooting

### Problem: Graphs showing incorrect data

**Solution**: Run the database fix script (already included)
```bash
python3 fix_database.py
# or
bash apply_fixes.sh
```

### Problem: Can't connect to Cowrie database

**Check**: 
1. Docker containers are running: `docker-compose ps`
2. MySQL is healthy: `docker-compose logs mysql`
3. Port 3307 is available

### Problem: ETL adapter not syncing data

**Check**:
1. Both databases are running: `mysql -u root -p honeypot_data -e "SELECT COUNT(*) FROM SESSION;"`
2. Cowrie has data: `docker exec honeypot-mysql mysql -u cowrie -pcowriepassword cowrie -e "SELECT COUNT(*) FROM sessions;"`
3. ETL script output for errors: `python3 cowrie_etl_adapter.py`

### Problem: Flask app won't start

**Check**:
1. Port 5000 is available: `lsof -i :5000`
2. Python dependencies installed: `pip install -r requirements.txt`
3. honeypot_data database exists

### Problem: Can't login to dashboard

**Check**:
1. Database users created: `bash setup_db.sh` (includes roles.sql)
2. Test login: `mysql -u analyst -p analystpass -h localhost honeypot_data -e "SELECT 1;"`
---

## 🔄 Data Flow

```
Attack on SSH/Telnet
    │
    ▼
Cowrie Honeypot (Docker)
    │
    ├─→ Session data
    ├─→ Auth attempts
    ├─→ Commands executed
    └─→ File downloads
    │
    ▼ (MySQL DB: cowrie)
cowrie.sessions
cowrie.auth
cowrie.input
cowrie.downloads
    │
    ▼ (ETL Adapter polls every 1-30 seconds)
Data extraction & transformation
    │
    ├─→ GeoIP lookup (ip-api.com)
    ├─→ IP sanitization (private → public)
    ├─→ Deduplication
    └─→ Incremental upsert
    │
    ▼ (MySQL DB: honeypot_data)
SESSION, ATTACKER, AUTH_ATTEMPT
COMMAND, DOWNLOAD, GEOIP_CACHE
    │
    ▼ (Triggers & Views maintain analytics)
COUNTRY_STATS (auto-updated)
AUTH_STATS (auto-updated)
AttackerRankings (real-time view)
    │
    ▼ (Flask API queries)
/api/query/top-countries
/api/query/attack-trends
/api/query/command-frequency
    │
    ▼ (Frontend renders)
Dashboard charts & tables
Interactive analytics
```

---

## 👤 Authors

**Kshitij Koushik Kota** 
**Sampriti Saha** 

