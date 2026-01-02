"""Execution stage for placing approved trades via Alpaca."""

import uuid
from typing import Dict, Any, List
from datetime import datetime

from ...multi_alpaca_client import MultiAlpacaManager
from ...requesty_client import REQUESTY_MODELS
from ..context import PipelineContext, ContextKey
from ..base import Stage
from .chairman import CHAIRMAN_DECISION, PM_PITCHES


# Context keys for execution
EXECUTION_RESULT = ContextKey("execution_result")


class ExecutionStage(Stage):
    """
    Execution stage that places approved trades via Alpaca.
    
    This stage:
    1. Checks if trades are approved
    2. Calculates position size based on conviction
    3. Places orders in parallel across all accounts
    4. Records order events in database
    """
    
    # Position sizing based on conviction
    POSITION_SIZING = {
        -2.0: 0.0,      # Strong SHORT - no position
        -1.5: 0.25,    # Strong SHORT - small position
        -1.0: 0.50,     # SHORT - medium position
        -0.5: 0.75,     # Weak SHORT - large position
        0.0: 0.0,       # FLAT - no position
        0.5: 0.75,      # Weak LONG - large position
        1.0: 0.50,      # LONG - medium position
        1.5: 0.25,     # Strong LONG - small position
        2.0: 0.10      # Very strong LONG - very small position
    }
    
    @property
    def name(self) -> str:
        return "ExecutionStage"
    
    async def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute trading stage.
        
        Args:
            context: Pipeline context with chairman decision and PM pitches
            
        Returns:
            New context with execution results
        """
        print("\n" + "=" * 60)
        print("💰 EXECUTION STAGE")
        print("=" * 60)
        
        # Get chairman decision and PM pitches from context
        chairman_decision = context.get(CHAIRMAN_DECISION)
        pm_pitches = context.get(PM_PITCHES, [])
        
        if not chairman_decision:
            print("  ❌ Error: Chairman decision not found in context")
            return context
        
        # Collect all trades to execute (council + individual PMs)
        trades_to_execute = []
        
        # Add council trade
        council_trade = self._prepare_trade(
            chairman_decision,
            "council"
        )
        if council_trade:
            trades_to_execute.append(council_trade)
            print(f"\n✅ Council trade: {council_trade['instrument']} {council_trade['direction']} (conviction: {council_trade['conviction']})")
        
        # Add individual PM trades (if they want to execute their own trades)
        for pitch in pm_pitches:
            # Only execute PM trades if they have conviction > 0 (LONG/SHORT)
            # FLAT trades (conviction = 0) don't need execution
            if pitch.get("conviction", 0) != 0:
                pm_trade = self._prepare_trade(pitch, pitch["model"])
                if pm_trade:
                    trades_to_execute.append(pm_trade)
                    account = pitch.get("model_info", {}).get("account", "Unknown")
                    print(f"✅ {account} trade: {pm_trade['instrument']} {pm_trade['direction']} (conviction: {pm_trade['conviction']})")
        
        if not trades_to_execute:
            print("\n  ⚠️  No trades to execute (all FLAT)")
            return context.set(EXECUTION_RESULT, {
                "executed": False,
                "trades": [],
                "message": "No trades to execute"
            })
        
        print(f"\n📋 Total trades to execute: {len(trades_to_execute)}")
        
        # Step 1: Check approval status
        print("\n🔍 Checking approval status...")
        approved_trades = [t for t in trades_to_execute if t.get("approved", False)]
        
        if not approved_trades:
            print("  ⚠️  No approved trades found")
            print("  ℹ️  Note: Trades must be approved via GUI before execution")
            return context.set(EXECUTION_RESULT, {
                "executed": False,
                "trades": [],
                "message": "Trades not approved yet"
            })
        
        print(f"  ✅ {len(approved_trades)} trades approved for execution")
        
        # Step 2: Place orders in parallel
        print("\n🚀 Placing orders via Alpaca...")
        execution_results = await self._place_orders_parallel(approved_trades)
        
        # Step 3: Record execution results
        print("\n📊 Execution Summary:")
        for result in execution_results:
            status = "✅" if result["success"] else "❌"
            print(f"  {status} {result['account']}: {result['message']}")
        
        return context.set(EXECUTION_RESULT, {
            "executed": True,
            "trades": execution_results,
            "message": f"Executed {len(execution_results)} trades"
        })
    
    def _prepare_trade(
        self,
        decision: Dict[str, Any],
        source: str
    ) -> Dict[str, Any] | None:
        """
        Prepare trade for execution.
        
        Args:
            decision: Chairman decision or PM pitch
            source: "council" or model key
            
        Returns:
            Trade dict or None if invalid
        """
        # Get account info
        account = decision.get("account", "Unknown")
        model_key = decision.get("model", "unknown")
        alpaca_id = decision.get("alpaca_id", "Unknown")
        
        # Get position size based on conviction
        conviction = decision.get("conviction", 0)
        position_size = self.POSITION_SIZING.get(conviction, 0.0)
        
        if position_size == 0.0:
            # FLAT trade, no execution needed
            return None
        
        # Determine side and qty
        direction = decision.get("direction", "FLAT")
        if direction == "LONG":
            side = "buy"
        elif direction == "SHORT":
            side = "sell"
        else:
            # FLAT, no execution
            return None
        
        # Calculate qty (shares) - assume $100k portfolio, position size as % of portfolio
        portfolio_value = 100000  # $100,000 paper trading account
        qty = int(portfolio_value * position_size)
        
        # Round to nearest whole share
        if qty < 1:
            qty = 1
        
        return {
            "trade_id": str(uuid.uuid4()),
            "account": account,
            "alpaca_id": alpaca_id,
            "model": model_key,
            "source": source,
            "instrument": decision.get("instrument"),
            "direction": direction,
            "side": side,
            "qty": qty,
            "position_size": position_size,
            "conviction": conviction,
            "approved": False,  # Will be set by GUI
            "order_id": None,
            "order_status": "pending",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _place_orders_parallel(
        self,
        trades: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Place orders for multiple accounts in parallel.
        
        Args:
            trades: List of trade dicts with 'approved': True
            
        Returns:
            List of execution result dicts
        """
        # Prepare orders for Alpaca
        orders = []
        for trade in trades:
            orders.append({
                "account_name": trade["account"],
                "symbol": trade["instrument"],
                "qty": trade["qty"],
                "side": trade["side"],
                "order_type": "market",
                "time_in_force": "day"
            })
        
        # Place orders in parallel
        manager = MultiAlpacaManager()
        order_responses = await manager.place_orders_parallel(orders)
        
        # Process results
        results = []
        for trade, order_response in zip(trades, order_responses.values()):
            success = "order_id" in order_response
            results.append({
                "trade_id": trade["trade_id"],
                "account": trade["account"],
                "alpaca_id": trade["alpaca_id"],
                "model": trade["model"],
                "source": trade["source"],
                "instrument": trade["instrument"],
                "direction": trade["direction"],
                "qty": trade["qty"],
                "position_size": trade["position_size"],
                "conviction": trade["conviction"],
                "success": success,
                "order_id": order_response.get("id") if success else None,
                "message": order_response.get("message", "Order placed") if success else str(order_response),
                "timestamp": datetime.utcnow().isoformat()
            })
        
        return results
    
    def calculate_position_size(
        self,
        conviction: float,
        portfolio_value: float = 100000.0
    ) -> float:
        """
        Calculate position size based on conviction.
        
        Args:
            conviction: Conviction score (-2 to +2)
            portfolio_value: Total portfolio value
            
        Returns:
            Position size as percentage (0.0 to 1.0)
        """
        return self.POSITION_SIZING.get(conviction, 0.0)
