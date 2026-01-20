"""
Database migration script - Add research_date column to pm_pitches table.

NOTE: This migration script intentionally uses psycopg2 instead of asyncpg.
Migration scripts are one-off operations that don't benefit from connection pooling
and don't need to be async. Keeping psycopg2 for migrations is an acceptable use case.
"""

import os
import psycopg2

def migrate():
    try:
        db_name = os.getenv("DATABASE_NAME", "llm_trading")
        db_user = os.getenv("DATABASE_USER", "luis")
        
        print(f"Connecting to {db_name} as {db_user}...")
        conn = psycopg2.connect(dbname=db_name, user=db_user)
        conn.autocommit = True
        
        with conn.cursor() as cur:
            # Check if column exists
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='pm_pitches' AND column_name='research_date';
            """)
            if cur.fetchone():
                print("Column 'research_date' already exists.")
            else:
                print("Adding 'research_date' column...")
                cur.execute("ALTER TABLE pm_pitches ADD COLUMN research_date TEXT;")
                cur.execute("CREATE INDEX idx_pm_pitches_research_date ON pm_pitches(research_date);")
                print("Column added successfully.")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    migrate()
