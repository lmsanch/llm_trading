
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def migrate():
    """Add research_date column to pm_pitches table if it doesn't exist."""
    db_name = os.getenv("DATABASE_NAME", "llm_trading")
    db_user = os.getenv("DATABASE_USER", "luis")
    
    print(f"Connecting to database {db_name} as {db_user}...")
    
    try:
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
                print("Column 'research_date' already exists in 'pm_pitches'.")
            else:
                print("Adding 'research_date' column to 'pm_pitches'...")
                cur.execute("ALTER TABLE pm_pitches ADD COLUMN research_date TEXT;")
                cur.execute("CREATE INDEX idx_pm_pitches_research_date ON pm_pitches(research_date);")
                print("Column added successfully.")
                
        conn.close()
        print("Migration complete.")
        
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    migrate()
