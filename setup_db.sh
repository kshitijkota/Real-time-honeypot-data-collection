#!/bin/bash
# ==========================================================
# Honeypot Data Database Setup Script
# Author: Sampriti Saha
# Description:
#   Runs all SQL files in the correct dependency order to
#   initialize the honeypot_data database.
# ==========================================================

DB_NAME="honeypot_data"
DB_USER="root"
DB_PASS="root123"
DB_HOST="localhost"
DB_PORT="3306"

echo "🧠 Starting database setup for $DB_NAME..."

# Function to execute SQL files safely
run_sql() {
  local file=$1
  echo "⚙️  Executing $file..."
  mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASS $DB_NAME < "$file"
  if [ $? -eq 0 ]; then
    echo "✅ Successfully executed $file"
  else
    echo "❌ Error executing $file"
    exit 1
  fi
}

# 1️⃣ Create database if not exists
echo "📦 Creating database (if not exists)..."
mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASS -e "CREATE DATABASE IF NOT EXISTS $DB_NAME;"
echo "✅ Database ready."

# 2️⃣ Execute all SQL scripts in proper order
run_sql "sql/table_creation.sql"
run_sql "sql/triggers.sql"
run_sql "sql/functions.sql"
run_sql "sql/procedures.sql"
run_sql "sql/events.sql"
run_sql "sql/views.sql"
run_sql "sql/roles.sql"

# 3️⃣ Optional: preload sample data or test queries
if [ -f "sql/complex_queries.sql" ]; then
  echo "🧩 Running analytical views and test queries..."
  run_sql "sql/complex_queries.sql"
fi

echo "🎯 Database setup complete!"
echo "--------------------------------------------------"
echo "To verify setup, you can log in with:"
echo "mysql -u $DB_USER -p$DB_PASS -h $DB_HOST -P $DB_PORT $DB_NAME"
echo "--------------------------------------------------"
