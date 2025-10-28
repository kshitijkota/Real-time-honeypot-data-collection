#!/bin/bash
# Simple ETL Restart Loop - No frills version

ETL_SCRIPT="cowrie_etl_adapter.py"
RUN_DURATION=15  # Run for 30 seconds
WAIT_TIME=1      # Wait 2 seconds between restarts

echo "🔄 Starting ETL restart loop"
echo "   Running $ETL_SCRIPT for ${RUN_DURATION}s cycles"
echo "   Press Ctrl+C to stop"
echo ""

CYCLE=0

# Trap Ctrl+C
trap 'echo -e "\n🛑 Stopped"; exit 0' SIGINT

while true; do
    CYCLE=$((CYCLE + 1))
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔄 Cycle $CYCLE - $(date '+%H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Run ETL script with timeout
    timeout ${RUN_DURATION}s python3 "$ETL_SCRIPT" || true

    echo "✅ Cycle complete, waiting ${WAIT_TIME}s..."
    sleep $WAIT_TIME
    echo ""
done