#!/bin/bash
#
# Daily market data update script
# Run this via cron after market close (5:00 PM ET)
#
# Usage: ./daily_update.sh

set -e  # Exit on error

# Change to project directory
cd /research/llm_trading

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Load environment variables
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run daily data fetch (includes automatic metrics calculation)
echo "==================================================="
echo "Daily Market Data Update - $(date)"
echo "==================================================="

python backend/storage/fetch_market_data.py daily

echo ""
echo "✅ Daily update complete at $(date)"
