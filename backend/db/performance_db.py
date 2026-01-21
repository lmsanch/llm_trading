"""Performance metrics database operations.

ASYNC PATTERNS USED:
    This module demonstrates querying performance metrics with asyncpg.
    See backend/db/ASYNC_PATTERNS.md for complete documentation.

    Key patterns:
    - Complete async chain: API → Service → DB → Pool
    - All functions are async and use await
    - Parameter placeholders use $1, $2, $3 (not %s)
    - Row access uses dict keys (not numeric indices)
    - Uses views for common queries (v_leaderboard_all_time, v_leaderboard_4w, v_leaderboard_8w)
"""

import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal

# Import async database helpers
from backend.db_helpers import fetch_one, fetch_all, fetch_val

logger = logging.getLogger(__name__)


async def get_leaderboard(weeks_filter: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get performance leaderboard ranked by total return.

    Retrieves performance metrics for all accounts, ranked by total return.
    Uses pre-built views for common time periods (all-time, 4w, 8w) for optimal performance.

    Args:
        weeks_filter: Number of weeks to look back (None = all time, 4 = last 4 weeks, 8 = last 8 weeks)
                     Only None, 4, and 8 have optimized views. Other values query the table directly.

    Returns:
        List of performance dictionaries, each containing:
            - rank: Ranking by total return (1 = best)
            - account: Account name (e.g., 'CHATGPT', 'COUNCIL', 'DEEPSEEK')
            - total_return: Cumulative return as decimal (e.g., 0.1523 = 15.23%)
            - sharpe_ratio: Risk-adjusted return metric
            - max_drawdown: Worst peak-to-trough decline
            - volatility: Standard deviation of returns
            - win_rate: Percentage of profitable weeks (e.g., 0.6667 = 66.67%)
            - weeks_traded: Number of weeks with positions
            - profitable_weeks: Number of weeks with positive returns
            - calculated_at: Timestamp when metrics were last calculated
        Returns empty list if no performance data exists.

    Database Tables/Views:
        - v_leaderboard_all_time: Pre-ranked view for all-time performance
        - v_leaderboard_4w: Pre-ranked view for 4-week performance
        - v_leaderboard_8w: Pre-ranked view for 8-week performance
        - account_performance: Base table for custom lookback periods

    Example:
        # Get all-time leaderboard
        leaderboard = await get_leaderboard()

        # Get 4-week leaderboard
        recent = await get_leaderboard(weeks_filter=4)

        # Access results
        for entry in leaderboard:
            print(f"#{entry['rank']} {entry['account']}: {entry['total_return']:.2%}")
    """
    try:
        # Use optimized views for common time periods
        if weeks_filter is None:
            # All-time performance
            query = """
                SELECT
                    rank,
                    account,
                    total_return,
                    sharpe_ratio,
                    max_drawdown,
                    volatility,
                    win_rate,
                    weeks_traded,
                    profitable_weeks,
                    calculated_at
                FROM v_leaderboard_all_time
                ORDER BY rank
            """
            rows = await fetch_all(query)
            logger.info(f"Retrieved all-time leaderboard: {len(rows)} accounts")

        elif weeks_filter == 4:
            # 4-week performance
            query = """
                SELECT
                    rank,
                    account,
                    total_return,
                    sharpe_ratio,
                    max_drawdown,
                    volatility,
                    win_rate,
                    weeks_traded,
                    profitable_weeks,
                    calculated_at
                FROM v_leaderboard_4w
                ORDER BY rank
            """
            rows = await fetch_all(query)
            logger.info(f"Retrieved 4-week leaderboard: {len(rows)} accounts")

        elif weeks_filter == 8:
            # 8-week performance
            query = """
                SELECT
                    rank,
                    account,
                    total_return,
                    sharpe_ratio,
                    max_drawdown,
                    volatility,
                    win_rate,
                    weeks_traded,
                    profitable_weeks,
                    calculated_at
                FROM v_leaderboard_8w
                ORDER BY rank
            """
            rows = await fetch_all(query)
            logger.info(f"Retrieved 8-week leaderboard: {len(rows)} accounts")

        else:
            # Custom lookback period - query table directly and calculate rank
            # ASYNC PATTERN: Use $1 parameter placeholder (not %s)
            query = """
                SELECT
                    ROW_NUMBER() OVER (ORDER BY total_return DESC) AS rank,
                    account,
                    total_return,
                    sharpe_ratio,
                    max_drawdown,
                    volatility,
                    win_rate,
                    weeks_traded,
                    profitable_weeks,
                    calculated_at
                FROM account_performance
                WHERE weeks_lookback = $1
                ORDER BY total_return DESC
            """
            rows = await fetch_all(query, weeks_filter)
            logger.info(f"Retrieved {weeks_filter}-week leaderboard: {len(rows)} accounts")

        return rows

    except Exception as e:
        logger.error(f"Error retrieving leaderboard (weeks_filter={weeks_filter}): {e}", exc_info=True)
        raise


async def get_account_performance(
    account: str,
    weeks_filter: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    """
    Get performance metrics for a specific account.

    Retrieves cumulative performance metrics for a single account over a specified time period.

    Args:
        account: Account name (e.g., 'CHATGPT', 'COUNCIL', 'DEEPSEEK', 'BASELINE')
        weeks_filter: Number of weeks to look back (None = all time)

    Returns:
        Performance dictionary containing:
            - account: Account name
            - total_return: Cumulative return as decimal
            - sharpe_ratio: Risk-adjusted return
            - max_drawdown: Worst decline from peak
            - volatility: Standard deviation of returns
            - win_rate: Percentage of profitable weeks
            - weeks_traded: Number of weeks with positions
            - profitable_weeks: Number of profitable weeks
            - avg_conviction: Average conviction level used
            - max_conviction: Maximum conviction level used
            - calculated_at: When metrics were last calculated
        Returns None if account not found or no data available.

    Database Tables:
        - account_performance: Cumulative metrics table

    Example:
        # Get all-time performance for COUNCIL account
        perf = await get_account_performance("COUNCIL")
        if perf:
            print(f"Total Return: {perf['total_return']:.2%}")
            print(f"Sharpe Ratio: {perf['sharpe_ratio']:.2f}")

        # Get 4-week performance
        recent_perf = await get_account_performance("CHATGPT", weeks_filter=4)
    """
    try:
        # ASYNC PATTERN: fetch_one returns single dict or None
        # Use $1, $2 for parameter placeholders
        query = """
            SELECT
                account,
                total_return,
                sharpe_ratio,
                max_drawdown,
                volatility,
                win_rate,
                weeks_traded,
                profitable_weeks,
                avg_conviction,
                max_conviction,
                calculated_at
            FROM account_performance
            WHERE account = $1
              AND (weeks_lookback = $2 OR (weeks_lookback IS NULL AND $2 IS NULL))
        """
        row = await fetch_one(query, account, weeks_filter)

        if row:
            logger.info(
                f"Retrieved performance for {account} "
                f"(weeks_filter={weeks_filter}): total_return={row['total_return']}"
            )
        else:
            logger.warning(
                f"No performance data found for account={account}, weeks_filter={weeks_filter}"
            )

        return row

    except Exception as e:
        logger.error(
            f"Error retrieving performance for account={account}, weeks_filter={weeks_filter}: {e}",
            exc_info=True
        )
        raise


async def get_weekly_breakdown(
    account: str,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get week-by-week performance breakdown for an account.

    Retrieves detailed weekly performance data showing individual trades, returns,
    and execution details for a specific account.

    Args:
        account: Account name (e.g., 'CHATGPT', 'COUNCIL', 'DEEPSEEK')
        limit: Maximum number of weeks to return (default: None = all weeks)
               Most recent weeks are returned first.

    Returns:
        List of weekly performance dictionaries, each containing:
            - account: Account name
            - week_id: Week identifier (YYYY-MM-DD format)
            - week_start: Start date of week
            - week_end: End date of week
            - weekly_return: Return for this specific week
            - weekly_volatility: Intraweek volatility
            - instrument: Instrument traded (None if flat)
            - direction: Trade direction (LONG, SHORT, FLAT)
            - entry_conviction: Initial conviction level
            - exit_conviction: Final conviction level
            - entry_price: Entry price
            - exit_price: Exit price
            - position_size: Number of shares/units
            - realized_pnl: Realized P&L in USD
            - fees: Trading fees
            - net_pnl: Net P&L after fees
            - entry_reason: Why trade was entered
            - exit_reason: Why trade was exited
            - panic_exit: Whether exit was unjustified panic
            - market_regime: Market condition during week
            - calculated_at: When metrics were calculated
        Returns empty list if no weekly data exists.

    Database Tables:
        - weekly_performance: Week-by-week breakdown table

    Example:
        # Get all weekly performance for COUNCIL
        weeks = await get_weekly_breakdown("COUNCIL")

        # Get last 4 weeks only
        recent_weeks = await get_weekly_breakdown("CHATGPT", limit=4)

        # Analyze weekly results
        for week in weeks:
            print(f"{week['week_id']}: {week['weekly_return']:.2%} on {week['instrument']}")
    """
    try:
        # Build query with optional limit
        query = """
            SELECT
                account,
                week_id,
                week_start,
                week_end,
                weekly_return,
                weekly_volatility,
                instrument,
                direction,
                entry_conviction,
                exit_conviction,
                entry_price,
                exit_price,
                position_size,
                realized_pnl,
                fees,
                net_pnl,
                entry_reason,
                exit_reason,
                panic_exit,
                market_regime,
                calculated_at
            FROM weekly_performance
            WHERE account = $1
            ORDER BY week_start DESC
        """

        # Add limit clause if specified
        if limit:
            query += " LIMIT $2"
            rows = await fetch_all(query, account, limit)
        else:
            rows = await fetch_all(query, account)

        logger.info(
            f"Retrieved {len(rows)} weekly performance records for account={account}"
            + (f" (limit={limit})" if limit else "")
        )

        return rows

    except Exception as e:
        logger.error(
            f"Error retrieving weekly breakdown for account={account}: {e}",
            exc_info=True
        )
        raise


async def get_market_condition_performance(
    condition_type: str,
    condition_value: str,
    weeks_filter: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get performance metrics grouped by market condition.

    Retrieves how each account performs under specific market conditions,
    enabling analysis of which models perform best in different regimes.

    Args:
        condition_type: Type of condition (e.g., 'macro_regime', 'volatility_regime')
        condition_value: Specific condition (e.g., 'RISK_ON', 'HIGH_VOLATILITY')
        weeks_filter: Number of weeks to look back (None = all time)

    Returns:
        List of performance dictionaries, one per account, each containing:
            - account: Account name
            - condition_type: Type of market condition
            - condition_value: Specific condition value
            - weeks_in_condition: Number of weeks in this condition
            - avg_return: Average return in this condition
            - avg_sharpe: Average Sharpe ratio
            - win_rate: Win rate in this condition
            - calculated_at: When metrics were calculated
        Returns empty list if no data exists for this condition.

    Database Tables:
        - market_condition_performance: Condition-based performance metrics

    Example:
        # Get performance in RISK_ON regime
        risk_on_perf = await get_market_condition_performance(
            condition_type="macro_regime",
            condition_value="RISK_ON"
        )

        # Compare which models do best
        for perf in risk_on_perf:
            print(f"{perf['account']}: {perf['avg_return']:.2%} avg return")
    """
    try:
        # ASYNC PATTERN: Use $1, $2, $3 for parameters
        query = """
            SELECT
                account,
                condition_type,
                condition_value,
                weeks_in_condition,
                avg_return,
                avg_sharpe,
                win_rate,
                calculated_at
            FROM market_condition_performance
            WHERE condition_type = $1
              AND condition_value = $2
              AND (weeks_lookback = $3 OR (weeks_lookback IS NULL AND $3 IS NULL))
            ORDER BY avg_return DESC
        """
        rows = await fetch_all(query, condition_type, condition_value, weeks_filter)

        logger.info(
            f"Retrieved market condition performance: {condition_type}={condition_value}, "
            f"weeks_filter={weeks_filter}, {len(rows)} accounts"
        )

        return rows

    except Exception as e:
        logger.error(
            f"Error retrieving market condition performance "
            f"(type={condition_type}, value={condition_value}): {e}",
            exc_info=True
        )
        raise


async def get_council_vs_individuals(weeks_filter: Optional[int] = None) -> Dict[str, Any]:
    """
    Compare council performance against individual PM models.

    Retrieves performance comparison between the council approach and individual models,
    answering the key research question: does multi-model synthesis beat single models?

    Args:
        weeks_filter: Number of weeks to look back (None = all time)

    Returns:
        Dictionary containing:
            - council: Performance dict for COUNCIL account
            - individuals: List of performance dicts for individual PM accounts
            - baseline: Performance dict for BASELINE account
            - council_vs_best_individual: Comparison metrics
        Returns empty structure if no data available.

    Database Views:
        - v_council_vs_individuals: Comparison view

    Example:
        comparison = await get_council_vs_individuals()
        print(f"Council: {comparison['council']['total_return']:.2%}")
        print(f"Best Individual: {comparison['individuals'][0]['total_return']:.2%}")
    """
    try:
        if weeks_filter is None:
            # Use the optimized view for all-time comparison
            query = """
                SELECT
                    strategy_type,
                    account,
                    total_return,
                    sharpe_ratio,
                    max_drawdown,
                    win_rate,
                    weeks_traded
                FROM v_council_vs_individuals
            """
            rows = await fetch_all(query)
        else:
            # Query table directly with weeks filter
            query = """
                SELECT
                    CASE
                        WHEN account = 'COUNCIL' THEN 'Council'
                        WHEN account = 'BASELINE' THEN 'Baseline'
                        ELSE 'Individual PM'
                    END AS strategy_type,
                    account,
                    total_return,
                    sharpe_ratio,
                    max_drawdown,
                    win_rate,
                    weeks_traded
                FROM account_performance
                WHERE weeks_lookback = $1
                ORDER BY
                    CASE
                        WHEN account = 'COUNCIL' THEN 1
                        WHEN account = 'BASELINE' THEN 3
                        ELSE 2
                    END,
                    total_return DESC
            """
            rows = await fetch_all(query, weeks_filter)

        # Organize results by strategy type
        result = {
            "council": None,
            "individuals": [],
            "baseline": None
        }

        for row in rows:
            if row["strategy_type"] == "Council":
                result["council"] = row
            elif row["strategy_type"] == "Baseline":
                result["baseline"] = row
            else:
                result["individuals"].append(row)

        # Calculate comparison metrics
        if result["council"] and result["individuals"]:
            best_individual = result["individuals"][0]  # Already sorted by total_return
            result["council_vs_best_individual"] = {
                "council_return": result["council"]["total_return"],
                "best_individual_return": best_individual["total_return"],
                "best_individual_account": best_individual["account"],
                "return_difference": (
                    result["council"]["total_return"] - best_individual["total_return"]
                ),
                "council_wins": (
                    result["council"]["total_return"] > best_individual["total_return"]
                )
            }

        logger.info(
            f"Retrieved council vs individuals comparison (weeks_filter={weeks_filter}): "
            f"council={result['council'] is not None}, "
            f"individuals={len(result['individuals'])}, "
            f"baseline={result['baseline'] is not None}"
        )

        return result

    except Exception as e:
        logger.error(
            f"Error retrieving council vs individuals comparison "
            f"(weeks_filter={weeks_filter}): {e}",
            exc_info=True
        )
        raise
