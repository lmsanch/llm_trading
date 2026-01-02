
import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from backend.research.gemini_client import query_gemini_research

async def main():
    print("🚀 Testing Gemini Deep Research API...")
    
    mock_market_data = {
        "asof_et": "2026-01-01 10:00:00",
        "account_info": {
            "portfolio_value": 100000,
            "cash": 50000,
            "buying_power": 200000
        },
        "instruments": {
            "SPY": {"current": {"price": 475.20, "change_pct": 0.5}}
        }
    }
    
    prompt = "Analyze the market and provide a recommendation. Primary objective: Beat SPY."
    
    try:
        result = await query_gemini_research(prompt, mock_market_data)
        print("\n🏆 Research Result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
