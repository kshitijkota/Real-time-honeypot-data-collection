#!/bin/bash

# Fix Database Views and Procedures
# This script applies fixes to resolve graph data issues

echo "========================================"
echo "Database Fix Script"
echo "========================================"
echo ""
echo "This will fix the following issues:"
echo "  - Attack frequency graph showing incorrect values"
echo "  - Auth attempts being squared of total sessions"
echo "  - Top attacker countries showing incorrect counts"
echo ""

# Check if MySQL is available via command line
if command -v mysql &> /dev/null; then
    echo "MySQL CLI found. Running fix script..."
    mysql -u root -p honeypot_data < sql/fix_views_and_procedures.sql
    echo ""
    echo "✓ Fixes applied successfully!"
elif command -v docker &> /dev/null && docker ps | grep -q honeypot-mysql; then
    echo "MySQL container found. Running fix script..."
    docker exec -i honeypot-mysql mysql -u root -prootpassword honeypot_data < sql/fix_views_and_procedures.sql
    echo ""
    echo "✓ Fixes applied successfully!"
else
    echo "Neither MySQL CLI nor Docker container found."
    echo ""
    echo "Please run the fix manually:"
    echo "  1. Open MySQL Workbench or your preferred MySQL client"
    echo "  2. Connect to the 'honeypot_data' database"
    echo "  3. Run the commands from: sql/fix_views_and_procedures.sql"
    echo ""
    echo "OR run the Python fix script:"
    echo "  python3 fix_database.py"
fi
