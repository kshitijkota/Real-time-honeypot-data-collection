#!/bin/bash
# Quick setup script for Cowrie ETL Adapter

echo "🚀 Cowrie ETL Adapter Setup"
echo "============================"
echo ""

# Step 1: Check Python
echo "1️⃣  Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ $PYTHON_VERSION found"
else
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi

# Step 2: Install requirements
echo ""
echo "2️⃣  Installing Python dependencies..."
pip3 install mysql-connector-python requests
if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Step 3: Create local database
echo ""
echo "3️⃣  Setting up local database..."
read -p "Enter your MySQL root password: " -s MYSQL_PASSWORD
echo ""
read -p "Enter database name (default: honeypot_data): " DB_NAME
DB_NAME=${DB_NAME:-honeypot_data}

# Create database
mysql -u root -p"$MYSQL_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS $DB_NAME;" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Database '$DB_NAME' created"
else
    echo "❌ Failed to create database"
    exit 1
fi

# Import schema
if [ -f "table_creation.sql" ]; then
    mysql -u root -p"$MYSQL_PASSWORD" "$DB_NAME" < table_creation.sql
    echo "✅ Schema imported"
else
    echo "⚠️  table_creation.sql not found. Please import manually."
fi

# Step 4: Test Cowrie database connection
echo ""
echo "4️⃣  Testing Cowrie database connection..."
mysql -h localhost -P 3306 -u cowrie -pcowriepassword cowrie -e "SELECT COUNT(*) FROM sessions;" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ Cowrie database accessible"
else
    echo "❌ Cannot connect to Cowrie database. Is Docker running?"
    exit 1
fi

# Step 5: Create config file
echo ""
echo "5️⃣  Creating configuration..."
cat > etl_config.py << EOF
# ETL Configuration
SOURCE_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'cowrie',
    'password': 'cowriepassword',
    'database': 'cowrie'
}

DEST_CONFIG = {
    'host': 'localhost',
    'port': 3306,  # Change if your local MySQL is on different port
    'user': 'root',
    'password': '$MYSQL_PASSWORD',
    'database': '$DB_NAME'
}
EOF
echo "✅ Configuration saved to etl_config.py"

# Step 6: Run test transfer
echo ""
echo "6️⃣  Ready to run ETL adapter!"
echo ""
echo "To run the adapter:"
echo "  python3 cowrie_etl_adapter.py"
echo ""
echo "To verify data:"
echo "  mysql -u root -p $DB_NAME"
echo "  > SELECT * FROM SESSION;"
echo ""