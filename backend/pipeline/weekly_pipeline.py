"""Weekly pipeline orchestration for LLM trading system."""

import asyncio
from typing import Dict, Any
from datetime import datetime

from .base import Pipeline
from .context import PipelineContext
from .stages.research import ResearchStage, get_week_id
from .stages.pm_pitch import PMPitchStage
from .stages.peer_review import PeerReviewStage
from .stages.chairman import ChairmanStage
from .stages.execution import ExecutionStage
from ..requesty_client import get_pm_model_keys


class WeeklyTradingPipeline:
    """
    Weekly trading pipeline that orchestrates all stages.
    
    Pipeline flow:
    1. Research Stage (market data + macro analysis)
    2. PM Pitch Stage (5 PM models generate pitches)
    3. Peer Review Stage (anonymized evaluation)
    4. Chairman Stage (synthesis of final decision)
    5. Execution Stage (place approved trades via Alpaca)
    """
    
    def __init__(self):
        """Initialize weekly pipeline with all stages."""
        self.pipeline = Pipeline([
            ResearchStage(),
            PMPitchStage(),
            PeerReviewStage(),
            ChairmanStage(),
            ExecutionStage()
        ])
    
    async def run(self, user_query: str = None) -> Dict[str, Any]:
        """
        Run complete weekly pipeline.
        
        Args:
            user_query: Optional query for research (defaults to macro analysis)
            
        Returns:
            Dict with pipeline results and metadata
        """
        print("\n" + "=" * 80)
        print("🚀 WEEKLY TRADING PIPELINE")
        print("=" * 80)
        print(f"\n⏰ Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"📅 Week ID: {get_week_id()}")
        
        # Initialize context
        context = PipelineContext()
        
        # Add user query if provided
        if user_query:
            from .context import USER_QUERY
            context = context.set(USER_QUERY, user_query)
        
        # Execute pipeline
        try:
            result_context = await self.pipeline.execute(context)
            
            # Extract results
            results = self._extract_results(result_context)
            
            print("\n" + "=" * 80)
            print("✅ WEEKLY PIPELINE COMPLETE")
            print("=" * 80)
            print(f"\n⏰ Completed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            
            self._print_summary(results)
            
            return results
            
        except Exception as e:
            print("\n" + "=" * 80)
            print("❌ PIPELINE FAILED")
            print("=" * 80)
            print(f"\nError: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _extract_results(self, context: PipelineContext) -> Dict[str, Any]:
        """
        Extract results from pipeline context.
        
        Args:
            context: Final pipeline context
            
        Returns:
            Dict with all stage results
        """
        from .stages.research import (
            RESEARCH_PACK_A, RESEARCH_PACK_B, MARKET_SNAPSHOT
        )
        from .stages.pm_pitch import PM_PITCHES
        from .stages.peer_review import PEER_REVIEWS, LABEL_TO_MODEL
        from .stages.chairman import CHAIRMAN_DECISION
        from .stages.execution import EXECUTION_RESULT
        
        return {
            "week_id": get_week_id(),
            "timestamp": datetime.utcnow().isoformat(),
            "research_pack_a": context.get(RESEARCH_PACK_A),
            "research_pack_b": context.get(RESEARCH_PACK_B),
            "market_snapshot": context.get(MARKET_SNAPSHOT),
            "pm_pitches": context.get(PM_PITCHES, []),
            "peer_reviews": context.get(PEER_REVIEWS, []),
            "label_to_model": context.get(LABEL_TO_MODEL, {}),
            "chairman_decision": context.get(CHAIRMAN_DECISION),
            "execution_result": context.get(EXECUTION_RESULT)
        }
    
    def _print_summary(self, results: Dict[str, Any]):
        """Print pipeline summary."""
        print("\n📊 PIPELINE SUMMARY:")
        print("-" * 60)
        
        # Research
        research_a = results.get("research_pack_a", {})
        print(f"\n📊 Research:")
        print(f"   Source A: {research_a.get('research_source', 'N/A')}")
        print(f"   Macro Regime: {research_a.get('macro_regime', {}).get('risk_mode', 'N/A')}")
        
        # PM Pitches
        pm_pitches = results.get("pm_pitches", [])
        print(f"\n📈 PM Pitches ({len(pm_pitches)}):")
        for pitch in pm_pitches:
            print(f"   - {pitch.get('model_info', {}).get('account', 'Unknown')}: {pitch.get('instrument')} {pitch.get('direction')} (conviction: {pitch.get('conviction')})")
        
        # Chairman Decision
        chairman = results.get("chairman_decision", {})
        print(f"\n👑 Chairman Decision:")
        print(f"   Instrument: {chairman.get('selected_trade', {}).get('instrument', 'N/A')}")
        print(f"   Direction: {chairman.get('selected_trade', {}).get('direction', 'N/A')}")
        print(f"   Conviction: {chairman.get('conviction', 'N/A')}")
        
        # Execution
        execution = results.get("execution_result", {})
        print(f"\n💰 Execution:")
        if execution.get("executed"):
            trades = execution.get("trades", [])
            print(f"   Trades executed: {len(trades)}")
            for trade in trades:
                status = "✅" if trade.get("success") else "❌"
                print(f"   {status} {trade.get('account')}: {trade.get('message')}")
        else:
            print(f"   Status: {execution.get('message', 'Not executed')}")
        
        print("-" * 60)


async def run_weekly_pipeline(user_query: str = None) -> Dict[str, Any]:
    """
    Convenience function to run weekly pipeline.
    
    Args:
        user_query: Optional query for research
        
    Returns:
        Dict with pipeline results
    """
    pipeline = WeeklyTradingPipeline()
    return await pipeline.run(user_query)


async def run_research_only() -> Dict[str, Any]:
    """
    Run only research stage (for testing).
    
    Returns:
        Dict with research results
    """
    pipeline = Pipeline([ResearchStage()])
    context = PipelineContext()
    result_context = await pipeline.execute(context)
    
    from .stages.research import RESEARCH_PACK_A, RESEARCH_PACK_B, MARKET_SNAPSHOT
    
    return {
        "week_id": get_week_id(),
        "timestamp": datetime.utcnow().isoformat(),
        "research_pack_a": result_context.get(RESEARCH_PACK_A),
        "research_pack_b": result_context.get(RESEARCH_PACK_B),
        "market_snapshot": result_context.get(MARKET_SNAPSHOT)
    }


async def run_pm_pitches_only(research_pack_a: Dict, research_pack_b: Dict) -> Dict[str, Any]:
    """
    Run only PM pitch stage (for testing).
    
    Args:
        research_pack_a: Primary research pack
        research_pack_b: Alternative research pack
        
    Returns:
        Dict with PM pitches
    """
    from .context import PipelineContext
    from .stages.research import RESEARCH_PACK_A, RESEARCH_PACK_B
    from .stages.pm_pitch import PM_PITCHES
    
    pipeline = Pipeline([PMPitchStage()])
    context = (
        PipelineContext()
        .set(RESEARCH_PACK_A, research_pack_a)
        .set(RESEARCH_PACK_B, research_pack_b)
    )
    
    result_context = await pipeline.execute(context)
    
    return {
        "week_id": get_week_id(),
        "timestamp": datetime.utcnow().isoformat(),
        "pm_pitches": result_context.get(PM_PITCHES, [])
    }
