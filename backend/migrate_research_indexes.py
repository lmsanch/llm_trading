"""
Database migration script - Add composite indexes to research_reports table.

NOTE: This migration script intentionally uses psycopg2 instead of asyncpg.
Migration scripts are one-off operations that don't benefit from connection pooling
and don't need to be async. Keeping psycopg2 for migrations is an acceptable use case.
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate():
    """Add composite indexes to research_reports table for query performance optimization."""
    db_name = os.getenv("DATABASE_NAME", "llm_trading")
    db_user = os.getenv("DATABASE_USER", "luis")

    print(f"Connecting to database {db_name} as {db_user}...")

    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user)
        conn.autocommit = True

        with conn.cursor() as cur:
            # Check if idx_research_status_created_at exists
            cur.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename='research_reports' AND indexname='idx_research_status_created_at';
            """)

            if cur.fetchone():
                print("Index 'idx_research_status_created_at' already exists.")
            else:
                print("Creating index 'idx_research_status_created_at'...")
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_research_status_created_at
                    ON research_reports(status, created_at DESC);
                """)
                print("Index 'idx_research_status_created_at' created successfully.")

            # Check if idx_research_created_at exists
            cur.execute("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename='research_reports' AND indexname='idx_research_created_at';
            """)

            if cur.fetchone():
                print("Index 'idx_research_created_at' already exists.")
            else:
                print("Creating index 'idx_research_created_at'...")
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_research_created_at
                    ON research_reports(created_at DESC);
                """)
                print("Index 'idx_research_created_at' created successfully.")

        conn.close()
        print("Migration complete.")

    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate()
