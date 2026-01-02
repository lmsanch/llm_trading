#!/usr/bin/env python3
"""
Migrate market data from SQLite to PostgreSQL.
"""

import sqlite3
import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# SQLite path
SQLITE_DB = "/research/llm_trading/backend/storage/market_data.db"

# PostgreSQL connection
PG_HOST = "localhost"
PG_PORT = 5432
PG_DB = "llm_trading"
PG_USER = "luis"

def migrate_daily_bars():
    """Migrate daily_bars from SQLite to PostgreSQL."""

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    # Connect to PostgreSQL (uses peer auth via Unix socket)
    pg_conn = psycopg2.connect(
        dbname=PG_DB,
        user=PG_USER
    )
    pg_cur = pg_conn.cursor()

    # Fetch from SQLite
    sqlite_cur.execute("SELECT * FROM daily_bars")
    rows = sqlite_cur.fetchall()

    print(f"Found {len(rows)} bars in SQLite")

    # Insert into PostgreSQL
    for row in rows:
        pg_cur.execute("""
            INSERT INTO daily_bars (symbol, date, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (symbol, date) DO NOTHING
        """, (
            row['symbol'],
            row['date'],
            float(row['open']),
            float(row['high']),
            float(row['low']),
            float(row['close']),
            int(row['volume'])
        ))

    pg_conn.commit()
    print(f"✅ Migrated {len(rows)} daily bars to PostgreSQL")

    # Verify
    pg_cur.execute("SELECT COUNT(*) FROM daily_bars")
    count = pg_cur.fetchone()[0]
    print(f"   PostgreSQL now has {count} bars")

    # Close connections
    sqlite_conn.close()
    pg_conn.close()

if __name__ == "__main__":
    migrate_daily_bars()
