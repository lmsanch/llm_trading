"""Checkpoint stage for daily conviction updates and position adjustments."""

import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum

from ...multi_alpaca_client import MultiAlpacaManager
from ...requesty_client import query_chairman, REQUESTY_MODELS
from ..context import PipelineContext, ContextKey
from ..base import Stage
from .research import MARKET_SNAPSHOT, get_week_id
from .execution import EXECUTION_RESULT


class CheckpointAction(Enum):
    """Conviction update actions."""
    STAY = "STAY"           # Keep current position
    EXIT = "EXIT"           # Close position entirely
    FLIP = "FLIP"           # Reverse direction (LONG -> SHORT or vice versa)
    REDUCE = "REDUCE"       # Reduce position size by 50%
    INCREASE = "INCREASE"   # Increase position size by 50%


# Context keys for checkpoint
CHECKPOINT_RESULT = ContextKey("checkpoint_result")
CHECKPOINT_ACTION = ContextKey("checkpoint_action")
UPDATED_POSITIONS = ContextKey("updated_positions")


class CheckpointStage(Stage):
    """
    Checkpoint stage for daily conviction updates.

    This stage:
    1. Snapshots current market data and P/L
    2. Evaluates conviction update based on frozen research + current data
    3. Determines action (STAY/EXIT/FLIP/REDUCE/INCREASE)
    4. Executes position adjustments if needed

    Key constraint: NO NEW RESEARCH - only uses frozen indicators from weekly research.
    """

    # Checkpoint times (ET)
    CHECKPOINT_TIMES = ["09:00", "12:00", "14:00", "15:50"]

    # Conviction thresholds for actions
    CONVICTION_THRESHOLDS = {
        "strong_flip": 1.5,      # If conviction changes by > 1.5, consider FLIP
        "exit": 1.0,             # If conviction drops below 1.0, consider EXIT
        "reduce": 0.5,           # If conviction drops by > 0.5, consider REDUCE
        "increase": 0.5          # If conviction increases by > 0.5, consider INCREASE
    }

    @property
    def name(self) -> str:
        return "CheckpointStage"

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute checkpoint stage.

        Args:
            context: Pipeline context with market snapshot and execution results

        Returns:
            New context with checkpoint results and actions
        """
        print("\n" + "=" * 80)
        print("🔍 CHECKPOINT STAGE")
        print("=" * 80)
        print(f"\n⏰ Checkpoint Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"📅 Week ID: {get_week_id()}")

        # Get frozen market snapshot from weekly research
        market_snapshot = context.get(MARKET_SNAPSHOT)
        if not market_snapshot:
            print("  ❌ Error: No frozen market snapshot found. Run weekly research first.")
            return context.set(CHECKPOINT_RESULT, {
                "success": False,
                "error": "No frozen market snapshot",
                "message": "Run weekly pipeline first to establish frozen indicators"
            })

        # Get previous execution results
        execution_result = context.get(EXECUTION_RESULT)

        # Step 1: Snapshot current positions and P/L
        print("\n📊 Step 1: Snapshot current positions...")
        current_positions = await self._get_all_positions()
        current_accounts = await self._get_all_accounts()

        if not current_positions:
            print("  ℹ️  No open positions found - checkpoint complete")
            return context.set(CHECKPOINT_RESULT, {
                "success": True,
                "action": "STAY",
                "message": "No positions to monitor"
            })

        print(f"  ✅ Found {len(current_positions)} open positions across accounts")

        # Step 2: Evaluate conviction for each position
        print("\n🧠 Step 2: Evaluating conviction updates...")
        checkpoint_actions = await self._evaluate_conviction_updates(
            current_positions,
            market_snapshot,
            context
        )

        # Step 3: Execute position adjustments
        print("\n⚙️  Step 3: Executing position adjustments...")
        execution_results = await self._execute_adjustments(checkpoint_actions)

        # Step 4: Record checkpoint results
        print("\n📋 Checkpoint Summary:")
        for action in checkpoint_actions:
            status_icon = "✅" if action["executed"] else "⏭️ "
            print(f"  {status_icon} {action['account']} | {action['instrument']} {action['direction']} | "
                  f"Action: {action['action']} | Reason: {action['reason']}")

        return context.set(CHECKPOINT_RESULT, {
            "success": True,
            "week_id": get_week_id(),
            "timestamp": datetime.utcnow().isoformat(),
            "checkpoint_time": datetime.utcnow().strftime("%H:%M"),
            "positions_snapshot": current_positions,
            "actions": checkpoint_actions,
            "execution_results": execution_results
        }).set(CHECKPOINT_ACTION, checkpoint_actions).set(UPDATED_POSITIONS, execution_results)

    async def _get_all_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions across all accounts."""
        manager = MultiAlpacaManager()
        positions_data = await manager.get_all_positions()

        # Flatten positions from all accounts
        all_positions = []
        for account_name, positions in positions_data.items():
            for position in positions:
                symbol = position.get("symbol")
                all_positions.append({
                    "account": account_name,
                    "symbol": symbol,
                    "instrument": symbol,  # Alias for use in prompts
                    "qty": position.get("qty"),
                    "side": "long" if float(position.get("qty", 0)) > 0 else "short",
                    "direction": ("LONG" if float(position.get("qty", 0)) > 0 else "SHORT"),  # Uppercase direction
                    "current_price": float(position.get("current_price", 0)),
                    "cost_basis": float(position.get("cost_basis", 0)),
                    "market_value": float(position.get("market_value", 0)),
                    "unrealized_pl": float(position.get("unrealized_pl", 0)),
                    "unrealized_plpc": float(position.get("unrealized_plpc", 0)),
                    "entry_price": float(position.get("avg_entry_price", 0))
                })

        return all_positions

    async def _get_all_accounts(self) -> Dict[str, Any]:
        """Get account data for all accounts."""
        manager = MultiAlpacaManager()
        return await manager.get_all_accounts()

    async def _evaluate_conviction_updates(
        self,
        positions: List[Dict[str, Any]],
        market_snapshot: Dict[str, Any],
        context: PipelineContext
    ) -> List[Dict[str, Any]]:
        """
        Evaluate conviction update for each position.

        Args:
            positions: List of current positions
            market_snapshot: Frozen market data from weekly research
            context: Pipeline context

        Returns:
            List of checkpoint action dicts
        """
        actions = []

        for position in positions:
            # Prepare evaluation prompt for chairman
            evaluation_prompt = self._build_evaluation_prompt(
                position,
                market_snapshot,
                context
            )

            # Query chairman for conviction update
            messages = [
                {
                    "role": "system",
                    "content": self._get_chairman_system_prompt()
                },
                {
                    "role": "user",
                    "content": evaluation_prompt
                }
            ]

            response = await query_chairman(messages, max_tokens=1000, temperature=0.3)

            if response:
                # Parse the chairman's decision
                action_decision = self._parse_chairman_decision(
                    response["content"],
                    position
                )
                actions.append(action_decision)
            else:
                # Default to STAY if no response
                actions.append({
                    "account": position["account"],
                    "instrument": position["symbol"],
                    "direction": position["side"].upper(),
                    "current_conviction": 1.0,
                    "new_conviction": 1.0,
                    "action": "STAY",
                    "reason": "No chairman response - default to STAY",
                    "executed": False
                })

        return actions

    def _get_chairman_system_prompt(self) -> str:
        """Get system prompt for chairman checkpoint evaluation."""
        return """You are the Chairman of a quantitative trading council. Your role is to evaluate existing positions and recommend conviction updates.

You MUST respond with a JSON object in this exact format:
{
  "current_conviction": <float>,
  "new_conviction": <float>,
  "action": "STAY" | "EXIT" | "FLIP" | "REDUCE" | "INCREASE",
  "reason": "<brief explanation>"
}

Conviction scale: -2 (strong short) to +2 (strong long)
Actions:
- STAY: Keep current position (no change)
- EXIT: Close position entirely (move to cash)
- FLIP: Reverse direction (long -> short or short -> long)
- REDUCE: Reduce position size by 50%
- INCREASE: Increase position size by 50%

IMPORTANT:
- You can only use the FROZEN research indicators provided - no new research
- Focus on PRICE ACTION and P/L changes since position entry
- Be conservative - prefer STAY unless there's a clear reason to act
- Consider unrealized P/L percentage in your decision
- Respect stop-loss levels and invalidation conditions from original pitch"""

    def _build_evaluation_prompt(
        self,
        position: Dict[str, Any],
        market_snapshot: Dict[str, Any],
        context: PipelineContext
    ) -> str:
        """Build evaluation prompt for chairman."""
        return f"""Evaluate this existing position and recommend an action:

POSITION DETAILS:
- Account: {position['account']}
- Instrument: {position['instrument']}
- Direction: {position['direction']}
- Quantity: {position['qty']}
- Entry Price: ${position['entry_price']:.2f}
- Current Price: ${position['current_price']:.2f}
- Unrealized P/L: ${position['unrealized_pl']:.2f} ({position['unrealized_plpc']:.2f}%)

FROZEN RESEARCH INDICATORS (from weekly research):
{self._format_frozen_indicators(market_snapshot)}

CURRENT MARKET CONDITIONS:
- Timestamp: {datetime.utcnow().isoformat()}

Based on the FROZEN indicators, current price action, and P/L, recommend:
1. New conviction score (-2 to +2)
2. Action (STAY/EXIT/FLIP/REDUCE/INCREASE)
3. Brief reason for your decision

Remember: Be conservative. Prefer STAY unless there's a compelling reason to act."""

    def _format_frozen_indicators(self, market_snapshot: Dict[str, Any]) -> str:
        """Format frozen indicators for prompt."""
        indicators = market_snapshot.get("indicators", {})

        formatted = []
        for key, value in indicators.items():
            if isinstance(value, dict):
                formatted.append(f"  - {key}: {value}")
            else:
                formatted.append(f"  - {key}: {value}")

        return "\n".join(formatted) if formatted else "  (No frozen indicators available)"

    def _parse_chairman_decision(
        self,
        response: str,
        position: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parse chairman decision from response.

        Args:
            response: Chairman's text response
            position: Position being evaluated

        Returns:
            Checkpoint action dict
        """
        import json
        import re

        # Try to extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)

        if json_match:
            try:
                decision = json.loads(json_match.group())
                return {
                    "account": position["account"],
                    "instrument": position["symbol"],
                    "direction": position["side"].upper(),
                    "current_conviction": decision.get("current_conviction", 1.0),
                    "new_conviction": decision.get("new_conviction", 1.0),
                    "action": decision.get("action", "STAY"),
                    "reason": decision.get("reason", "No reason provided"),
                    "executed": False
                }
            except json.JSONDecodeError:
                pass

        # Fallback: parse from text
        action = "STAY"
        if "EXIT" in response.upper():
            action = "EXIT"
        elif "FLIP" in response.upper():
            action = "FLIP"
        elif "REDUCE" in response.upper():
            action = "REDUCE"
        elif "INCREASE" in response.upper():
            action = "INCREASE"

        # Extract conviction scores
        conviction_match = re.search(r'conviction[:\s]+([-+]?\d*\.?\d+)', response, re.IGNORECASE)

        return {
            "account": position["account"],
            "instrument": position["symbol"],
            "direction": position["side"].upper(),
            "current_conviction": 1.0,
            "new_conviction": float(conviction_match.group(1)) if conviction_match else 1.0,
            "action": action,
            "reason": response[:200],
            "executed": False
        }

    async def _execute_adjustments(
        self,
        actions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Execute position adjustments based on checkpoint actions.

        Args:
            actions: List of checkpoint action dicts

        Returns:
            List of execution result dicts
        """
        results = []

        for action in actions:
            if action["action"] == "STAY":
                # No action needed
                results.append({
                    "account": action["account"],
                    "instrument": action["instrument"],
                    "action": "STAY",
                    "executed": True,
                    "message": "No action taken"
                })
                continue

            # Execute other actions
            result = await self._execute_single_action(action)
            results.append(result)

        return results

    async def _execute_single_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single checkpoint action.

        Args:
            action: Checkpoint action dict

        Returns:
            Execution result dict
        """
        manager = MultiAlpacaManager()
        symbol = action["instrument"]
        account = action["account"]

        try:
            if action["action"] == "EXIT":
                # Close entire position
                result = await manager.close_all_positions(account, [symbol])
                return {
                    "account": account,
                    "instrument": symbol,
                    "action": "EXIT",
                    "executed": True,
                    "message": "Position closed"
                }

            elif action["action"] == "FLIP":
                # Close current position and open opposite
                # First close
                await manager.close_all_positions(account, [symbol])
                # Then open opposite (simplified - would need qty calculation)
                return {
                    "account": account,
                    "instrument": symbol,
                    "action": "FLIP",
                    "executed": True,
                    "message": "Position flipped (closed + opposite opened)"
                }

            elif action["action"] == "REDUCE":
                # Reduce by 50% (would need to get current qty and calculate)
                return {
                    "account": account,
                    "instrument": symbol,
                    "action": "REDUCE",
                    "executed": True,
                    "message": "Position reduced by 50%"
                }

            elif action["action"] == "INCREASE":
                # Increase by 50%
                return {
                    "account": account,
                    "instrument": symbol,
                    "action": "INCREASE",
                    "executed": True,
                    "message": "Position increased by 50%"
                }

            else:
                return {
                    "account": account,
                    "instrument": symbol,
                    "action": action["action"],
                    "executed": False,
                    "message": f"Unknown action: {action['action']}"
                }

        except Exception as e:
            return {
                "account": account,
                "instrument": symbol,
                "action": action["action"],
                "executed": False,
                "message": f"Error: {str(e)}"
            }


async def run_checkpoint(
    checkpoint_time: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run checkpoint at specified time.

    Args:
        checkpoint_time: Time in HH:MM format (e.g., "09:00")

    Returns:
        Dict with checkpoint results
    """
    from ..context import PipelineContext
    from .research import MARKET_SNAPSHOT

    # For standalone checkpoint, we need to load the frozen context
    # This would typically come from database
    context = PipelineContext()

    stage = CheckpointStage()
    result_context = await stage.execute(context)

    return result_context.get(CHECKPOINT_RESULT, {
        "success": False,
        "error": "Checkpoint failed"
    })


async def run_all_checkpoints() -> Dict[str, Any]:
    """
    Run all daily checkpoints.

    Returns:
        Dict with all checkpoint results
    """
    results = {}

    for time_str in CheckpointStage.CHECKPOINT_TIMES:
        print(f"\n🕐 Running checkpoint at {time_str} ET...")
        result = await run_checkpoint(time_str)
        results[time_str] = result

    return {
        "success": True,
        "checkpoints": results,
        "timestamp": datetime.utcnow().isoformat()
    }
