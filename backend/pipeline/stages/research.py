"""Research stage for market data and macro analysis."""

import asyncio
import os
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

import psycopg2
from psycopg2.extras import Json

from ...research import query_perplexity_research, query_gemini_research
from ...storage.data_fetcher import MarketDataManager
from ..context import PipelineContext, ContextKey
from ..base import Stage


# Context keys for research
RESEARCH_PACK_A = ContextKey("research_pack_a")
RESEARCH_PACK_B = ContextKey("research_pack_b")
MARKET_SNAPSHOT = ContextKey("market_snapshot")


class ResearchStage(Stage):
    """
    Research stage that fetches market data and generates macro analysis.

    This stage:
    1. Fetches current market data from Alpaca
    2. Loads research prompt from markdown file
    3. Queries BOTH Perplexity and Gemini in parallel
    4. Returns natural language reports + structured JSON
    """

    def __init__(self, selected_models: list = None, prompt_override: str = None):
        super().__init__()
        self.selected_models = selected_models or ["perplexity", "gemini"]
        self.prompt_override = prompt_override

    @property
    def name(self) -> str:
        return "ResearchStage"

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute research stage.

        Args:
            context: Pipeline context

        Returns:
            New context with research data added
        """
        print("\n" + "=" * 60)
        print("📊 RESEARCH STAGE")
        print("=" * 60)

        # Step 1: Fetch market data from Alpaca
        print("\n📡 Fetching market data from Alpaca...")
        market_snapshot = await self._fetch_market_data()

        # Step 2: Load research prompt
        print("📋 Loading research prompt template...")
        if self.prompt_override:
             print("  ⚠️  Using PROMPT OVERRIDE provided in request")
             research_prompt = self.prompt_override
        else:
            research_prompt = self._load_research_prompt()
            if not research_prompt:
                print("  ❌ Failed to load research prompt, using default")
                research_prompt = self._get_default_prompt()

        # Step 3: Query selected research providers in parallel
        print(f"🔍 Querying Selected Models: {self.selected_models}")
        
        tasks = []
        if "perplexity" in self.selected_models:
             tasks.append(self._run_perplexity_research(research_prompt, market_snapshot))
        
        if "gemini" in self.selected_models:
             tasks.append(self._run_gemini_research(research_prompt, market_snapshot))
             
        if not tasks:
            print("  ⚠️  No models selected!")
            return context.set(MARKET_SNAPSHOT, market_snapshot)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle results - map back to keys
        perplexity_result = None
        gemini_result = None
        
        # Unpack based on selection order
        result_idx = 0
        
        if "perplexity" in self.selected_models:
            perplexity_result = results[result_idx]
            result_idx += 1
            
            if isinstance(perplexity_result, Exception):
                print(f"  ⚠️  Perplexity research failed: {perplexity_result}")
                perplexity_result = self._error_research_pack("perplexity", str(perplexity_result))
            else:
                 print(f"  ✅ Perplexity: {perplexity_result.get('structured_json', {}).get('macro_regime', {}).get('risk_mode', 'Unknown')}")
                 # Save to database
                 self._save_research_to_db(perplexity_result, "perplexity")


        if "gemini" in self.selected_models:
            gemini_result = results[result_idx]
            result_idx += 1
            
            if isinstance(gemini_result, Exception):
                print(f"  ⚠️  Gemini research failed: {gemini_result}")
                gemini_result = self._error_research_pack("gemini", str(gemini_result))
            else:
                 print(f"  ✅ Gemini: {gemini_result.get('structured_json', {}).get('macro_regime', {}).get('risk_mode', 'Unknown')}")
                 # Save to database
                 self._save_research_to_db(gemini_result, "gemini")


        # Return context with both research packs
        ctx = context.set(MARKET_SNAPSHOT, market_snapshot)
        if perplexity_result:
            ctx = ctx.set(RESEARCH_PACK_A, perplexity_result)
        if gemini_result:
            ctx = ctx.set(RESEARCH_PACK_B, gemini_result)
            
        return ctx

    async def _fetch_market_data(self) -> Dict[str, Any]:
        """
        Fetch market data from the local database.

        The database is populated by the separate data_fetcher.py script
        running via cron job. This method simply queries the database.

        Returns:
            Dict with market snapshot including 30-day OHLCV data per instrument
        """
        try:
            from ...storage.data_fetcher import MarketDataFetcher

            fetcher = MarketDataFetcher()
            market_snapshot = fetcher.get_market_snapshot_for_research()

            # Add account info from Alpaca (optional - don't fail if unavailable)
            try:
                from ...multi_alpaca_client import MultiAlpacaManager
                manager = MultiAlpacaManager()
                client = manager.get_client("COUNCIL")
                account_info = await client.get_account()

                market_snapshot["account_info"] = {
                    "buying_power": account_info.get("buying_power"),
                    "cash": account_info.get("cash"),
                    "portfolio_value": account_info.get("portfolio_value"),
                }
                print(f"  ✅ Loaded account info from Alpaca")
            except Exception as e:
                # Account info is optional - research can work without it
                print(f"  ⚠️  Could not fetch account info (continuing without it): {e}")
                market_snapshot["account_info"] = {
                    "buying_power": "N/A",
                    "cash": "N/A",
                    "portfolio_value": "N/A",
                }

            print(f"  ✅ Loaded market data from database for {len(market_snapshot.get('instruments', {}))} instruments")
            return market_snapshot

        except Exception as e:
            print(f"  ❌ Error fetching market data: {e}")
            # Return minimal market data on error
            return {
                "asof_et": self._get_timestamp(),
                "error": str(e),
                "instruments": {}
            }

    def _calculate_rsi(self, prices: list, period: int = 14) -> float:
        """
        Calculate Relative Strength Index (RSI).

        Note: This is now handled by data_fetcher.py, kept for reference.
        """
        if len(prices) < period + 1:
            return None

        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def _load_research_prompt(self) -> str:
        """
        Load research prompt from markdown file.

        Returns:
            Prompt content as string, or None if file not found
        """
        try:
            prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts" / "research_prompt.md"

            if not prompt_path.exists():
                print(f"  ⚠️  Prompt file not found: {prompt_path}")
                return None

            with open(prompt_path, 'r') as f:
                content = f.read()
            print(f"  ✅ Loaded prompt from {prompt_path}")
            return content

        except Exception as e:
            print(f"  ❌ Error loading prompt: {e}")
            return None

    def _get_default_prompt(self) -> str:
        """Return default prompt if file loading fails."""
        return """You are a senior macro research analyst. Provide macro research with:

1. Macro Regime (risk-on/risk-off/neutral)
2. Top Narratives (what's driving markets this week)
3. Tradable Candidates (ETF recommendations with LONG/SHORT/NEUTRAL bias)
4. Event Calendar (next 7 days)

Provide BOTH a natural language report AND structured JSON.

 Tradable Universe: SPY, QQQ, IWM, TLT, HYG, UUP, GLD, USO, VIXY, SH

JSON format:
{
  "macro_regime": {"risk_mode": "RISK_ON" | "RISK_OFF" | "NEUTRAL", "description": "..."},
  "top_narratives": ["..."],
  "tradable_candidates": [{"ticker": "...", "directional_bias": "LONG|SHORT|NEUTRAL", "rationale": "..."}],
  "event_calendar": [{"date": "...", "event": "...", "impact": "HIGH|MEDIUM|LOW"}]
}"""

    async def _run_perplexity_research(
        self,
        prompt: str,
        market_snapshot: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run Perplexity Sonar Pro research."""
        print("  📊 Querying Perplexity Sonar Pro...")
        result = await query_perplexity_research(prompt, market_snapshot)
        return result

    async def _run_gemini_research(
        self,
        prompt: str,
        market_snapshot: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run Gemini Deep Research."""
        print("  🧠 Querying Gemini Deep Research...")
        result = await query_gemini_research(prompt, market_snapshot)
        return result

    def _error_research_pack(self, source: str, error: str) -> Dict[str, Any]:
        """Return error research pack."""
        return {
            "source": source,
            "model": "unknown",
            "natural_language": f"Research generation failed: {error}",
            "structured_json": {
                "macro_regime": {
                    "risk_mode": "NEUTRAL",
                    "description": "Research unavailable"
                },
                "top_narratives": [],
                "tradable_candidates": [],
                "event_calendar": [],
                "confidence_notes": {
                    "known_unknowns": f"Error: {error}",
                    "data_quality_flags": ["research_failed"]
                }
            },
            "error": error,
            "generated_at": self._get_timestamp()
        }

    def _get_timestamp(self) -> str:
        """Get current ISO timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat()

    def _save_research_to_db(self, research_result: Dict[str, Any], provider: str) -> None:
        """
        Save research result to database.
        
        Args:
            research_result: Research pack with natural_language and structured_json
            provider: 'perplexity' or 'gemini'
        """
        try:
            week_id = get_week_id()
            model = research_result.get('model', 'unknown')
            natural_language = research_result.get('natural_language', '')
            structured_json = research_result.get('structured_json', {})
            status = 'error' if research_result.get('error') else 'complete'
            error_message = research_result.get('error')
            generated_at = research_result.get('generated_at')
            
            # Connect to database
            db_name = os.getenv("DATABASE_NAME", "llm_trading")
            db_user = os.getenv("DATABASE_USER", "luis")
            
            conn = psycopg2.connect(dbname=db_name, user=db_user)
            
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO research_reports 
                        (week_id, provider, model, natural_language, structured_json, 
                         status, error_message, generated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        week_id,
                        provider,
                        model,
                        natural_language,
                        Json(structured_json),
                        status,
                        error_message,
                        generated_at
                    ))
                    
                    research_id = cur.fetchone()[0]
                    conn.commit()
                    print(f"  💾 Saved {provider} research to database (ID: {research_id})")
                    
            finally:
                conn.close()
                
        except Exception as e:
            print(f"  ⚠️  Failed to save {provider} research to database: {e}")


def get_week_id() -> str:
    """Get current week ID (Wednesday date)."""
    from datetime import datetime, timedelta

    today = datetime.utcnow()

    # Find most recent Wednesday
    days_since_wednesday = (today.weekday() - 2) % 7  # Wednesday is 2
    wednesday = today - timedelta(days=days_since_wednesday)

    return wednesday.strftime("%Y-%m-%d")
