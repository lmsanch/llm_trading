"""Backfill knowledge graphs for existing research reports."""

import os
import sys
import psycopg2
from pathlib import Path
from psycopg2.extras import Json

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.pipeline.graph_extractor import extract_graph

def backfill_graphs():
    """Iterate over research reports and generate graphs if missing."""
    print("🚀 Starting graph backfill...")
    
    db_name = os.getenv("DATABASE_NAME", "llm_trading")
    db_user = os.getenv("DATABASE_USER", "luis")
    
    try:
        conn = psycopg2.connect(dbname=db_name, user=db_user)
        cur = conn.cursor()
        
        # Fetch reports
        cur.execute("""
            SELECT id, week_id, provider, model, natural_language, structured_json, generated_at
            FROM research_reports
            ORDER BY created_at DESC
        """)
        
        rows = cur.fetchall()
        print(f"📊 Found {len(rows)} reports to check.")
        
        updated_count = 0
        
        for row in rows:
            report_id = row[0]
            week_id = row[1]
            provider = row[2]
            structured_json = row[5] or {}
            
            # Check if graph already exists
            if structured_json.get("weekly_graph"):
                print(f"  ✅ Report {report_id} ({provider}) already has graph.")
                continue
                
            print(f"  📝 Generating graph for report {report_id} ({provider})...")
            
            # Reconstruct research object for extractor
            research_data = {
                "week_id": week_id,
                "model": row[3],
                "natural_language": row[4],
                "structured_json": structured_json,
                "generated_at": row[6].isoformat() if row[6] else None
            }
            
            try:
                # Generate graph
                graph = extract_graph(research_data)
                
                # Update DB
                structured_json["weekly_graph"] = graph
                
                cur.execute("""
                    UPDATE research_reports
                    SET structured_json = %s
                    WHERE id = %s
                """, (Json(structured_json), report_id))
                
                updated_count += 1
                
            except Exception as e:
                print(f"  ⚠️  Failed to generate graph for {report_id}: {e}")
        
        conn.commit()
        print(f"\n🎉 Backfill complete. Updated {updated_count} reports.")
        
    except Exception as e:
        print(f"❌ Error during backfill: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    backfill_graphs()
