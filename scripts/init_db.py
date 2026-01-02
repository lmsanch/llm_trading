#!/usr/bin/env python
"""Initialize PostgreSQL database for LLM Trading system."""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage.schema import (
    create_engine_with_url,
    create_tables,
    get_sessionmaker,
    Base,
    ResearchPackEvent,
    PMPitchEvent,
    PeerReviewEvent,
    ChairmanDecisionEvent,
    CheckpointUpdateEvent,
    OrderEvent,
    PositionEvent,
    WeeklyPostmortemEvent,
    WeekMetadata
)


def main():
    """Initialize database and create all tables."""
    
    print("🔍 LLM Trading - Database Initialization")
    print("=" * 60)
    
    # Get database URL from environment
    from dotenv import load_dotenv
    load_dotenv()
    
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/llm_trading"
    )
    
    print(f"\n📊 Database URL: {database_url}")
    
    # Create engine
    print("\n⚙️  Creating database engine...")
    try:
        engine = create_engine_with_url(database_url)
        print("✅ Engine created successfully")
    except Exception as e:
        print(f"❌ Error creating engine: {e}")
        return 1
    
    # Create all tables
    print("\n📋 Creating tables...")
    try:
        create_tables(engine)
        print("✅ All tables created successfully")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return 1
    
    # List all created tables
    print("\n📚 Created tables:")
    for table_name in Base.metadata.tables.keys():
        print(f"   - {table_name}")
    
    # Test connection
    print("\n🔌 Testing database connection...")
    try:
        SessionLocal = get_sessionmaker(engine)
        session = SessionLocal()
        
        # Simple query to test connection
        result = session.execute("SELECT 1")
        session.close()
        
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Error connecting to database: {e}")
        return 1
    
    print("\n" + "=" * 60)
    print("✅ Database initialization complete!")
    print("\nNext steps:")
    print("  1. Run weekly pipeline: python cli.py run_weekly")
    print("  2. Start GUI: cd frontend && npm run dev")
    print("  3. Check status: python cli.py status")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
