"""Test execution logic focusing on position sizing calculations.

This module tests the ExecutionStage's position sizing logic including:
- POSITION_SIZING constant mapping from conviction to position size
- calculate_position_size method
- Edge cases and invalid conviction values
- Position size rationality (0-100%)
"""

import pytest
from backend.pipeline.stages.execution import ExecutionStage


class TestPositionSizingConstants:
    """Test suite for POSITION_SIZING constant definitions."""

    def test_position_sizing_exists(self):
        """Test that POSITION_SIZING mapping is defined."""
        assert ExecutionStage.POSITION_SIZING is not None
        assert isinstance(ExecutionStage.POSITION_SIZING, dict)

    def test_position_sizing_all_conviction_levels(self):
        """Test that all standard conviction levels are defined."""
        expected_levels = [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0]
        for level in expected_levels:
            assert level in ExecutionStage.POSITION_SIZING, \
                f"Conviction level {level} missing from POSITION_SIZING"

    def test_position_sizing_strong_short(self):
        """Test that strong SHORT (-2.0) has no position."""
        assert ExecutionStage.POSITION_SIZING[-2.0] == 0.0

    def test_position_sizing_negative_1_5(self):
        """Test that conviction -1.5 maps to 25% position."""
        assert ExecutionStage.POSITION_SIZING[-1.5] == 0.25

    def test_position_sizing_negative_1_0(self):
        """Test that conviction -1.0 maps to 50% position."""
        assert ExecutionStage.POSITION_SIZING[-1.0] == 0.50

    def test_position_sizing_negative_0_5(self):
        """Test that conviction -0.5 maps to 75% position."""
        assert ExecutionStage.POSITION_SIZING[-0.5] == 0.75

    def test_position_sizing_flat(self):
        """Test that FLAT (0.0 conviction) has no position."""
        assert ExecutionStage.POSITION_SIZING[0.0] == 0.0

    def test_position_sizing_positive_0_5(self):
        """Test that conviction 0.5 maps to 75% position."""
        assert ExecutionStage.POSITION_SIZING[0.5] == 0.75

    def test_position_sizing_positive_1_0(self):
        """Test that conviction 1.0 maps to 50% position."""
        assert ExecutionStage.POSITION_SIZING[1.0] == 0.50

    def test_position_sizing_positive_1_5(self):
        """Test that conviction 1.5 maps to 25% position."""
        assert ExecutionStage.POSITION_SIZING[1.5] == 0.25

    def test_position_sizing_strong_long(self):
        """Test that strong LONG (2.0) maps to 10% position."""
        assert ExecutionStage.POSITION_SIZING[2.0] == 0.10

    def test_position_sizes_are_numeric(self):
        """Test that all position sizes are numeric (float or int)."""
        for conviction, size in ExecutionStage.POSITION_SIZING.items():
            assert isinstance(size, (int, float)), \
                f"Position size for conviction {conviction} is not numeric"

    def test_position_sizes_in_valid_range(self):
        """Test that all position sizes are between 0 and 1 (0-100%)."""
        for conviction, size in ExecutionStage.POSITION_SIZING.items():
            assert 0.0 <= size <= 1.0, \
                f"Position size {size} for conviction {conviction} is out of range [0, 1]"

    def test_conviction_symmetry(self):
        """Test that positive and negative convictions have symmetric position sizes."""
        # Convictions at same magnitude should have same position size
        assert ExecutionStage.POSITION_SIZING[-0.5] == ExecutionStage.POSITION_SIZING[0.5]
        assert ExecutionStage.POSITION_SIZING[-1.0] == ExecutionStage.POSITION_SIZING[1.0]
        assert ExecutionStage.POSITION_SIZING[-1.5] == ExecutionStage.POSITION_SIZING[1.5]

    def test_position_size_decreases_with_higher_conviction(self):
        """Test that position size decreases as conviction magnitude increases (counter-intuitive but correct)."""
        # Higher conviction = smaller position (less risky)
        assert ExecutionStage.POSITION_SIZING[0.5] > ExecutionStage.POSITION_SIZING[1.0]
        assert ExecutionStage.POSITION_SIZING[1.0] > ExecutionStage.POSITION_SIZING[1.5]
        assert ExecutionStage.POSITION_SIZING[1.5] > ExecutionStage.POSITION_SIZING[2.0]

    def test_zero_position_for_extreme_and_flat(self):
        """Test that extreme conviction and FLAT result in no position."""
        # FLAT should have 0 position
        assert ExecutionStage.POSITION_SIZING[0.0] == 0.0
        # Strong SHORT should have 0 position
        assert ExecutionStage.POSITION_SIZING[-2.0] == 0.0


class TestCalculatePositionSizeMethod:
    """Test suite for ExecutionStage.calculate_position_size method."""

    @pytest.fixture
    def execution_stage(self):
        """Create an ExecutionStage instance for testing."""
        return ExecutionStage()

    def test_calculate_position_size_conviction_negative_2(self, execution_stage):
        """Test position size calculation for conviction -2.0."""
        size = execution_stage.calculate_position_size(-2.0)
        assert size == 0.0

    def test_calculate_position_size_conviction_negative_1_5(self, execution_stage):
        """Test position size calculation for conviction -1.5."""
        size = execution_stage.calculate_position_size(-1.5)
        assert size == 0.25

    def test_calculate_position_size_conviction_negative_1_0(self, execution_stage):
        """Test position size calculation for conviction -1.0."""
        size = execution_stage.calculate_position_size(-1.0)
        assert size == 0.50

    def test_calculate_position_size_conviction_negative_0_5(self, execution_stage):
        """Test position size calculation for conviction -0.5."""
        size = execution_stage.calculate_position_size(-0.5)
        assert size == 0.75

    def test_calculate_position_size_conviction_zero(self, execution_stage):
        """Test position size calculation for conviction 0.0 (FLAT)."""
        size = execution_stage.calculate_position_size(0.0)
        assert size == 0.0

    def test_calculate_position_size_conviction_positive_0_5(self, execution_stage):
        """Test position size calculation for conviction 0.5."""
        size = execution_stage.calculate_position_size(0.5)
        assert size == 0.75

    def test_calculate_position_size_conviction_positive_1_0(self, execution_stage):
        """Test position size calculation for conviction 1.0."""
        size = execution_stage.calculate_position_size(1.0)
        assert size == 0.50

    def test_calculate_position_size_conviction_positive_1_5(self, execution_stage):
        """Test position size calculation for conviction 1.5."""
        size = execution_stage.calculate_position_size(1.5)
        assert size == 0.25

    def test_calculate_position_size_conviction_positive_2(self, execution_stage):
        """Test position size calculation for conviction 2.0."""
        size = execution_stage.calculate_position_size(2.0)
        assert size == 0.10

    def test_calculate_position_size_all_standard_convictions(self, execution_stage):
        """Test all standard conviction levels at once."""
        expected_mappings = {
            -2.0: 0.0,
            -1.5: 0.25,
            -1.0: 0.50,
            -0.5: 0.75,
            0.0: 0.0,
            0.5: 0.75,
            1.0: 0.50,
            1.5: 0.25,
            2.0: 0.10,
        }

        for conviction, expected_size in expected_mappings.items():
            actual_size = execution_stage.calculate_position_size(conviction)
            assert actual_size == expected_size, \
                f"Conviction {conviction}: expected {expected_size}, got {actual_size}"


class TestPositionSizingEdgeCases:
    """Test suite for edge cases in position sizing."""

    @pytest.fixture
    def execution_stage(self):
        """Create an ExecutionStage instance for testing."""
        return ExecutionStage()

    def test_invalid_conviction_returns_zero(self, execution_stage):
        """Test that invalid conviction values return 0.0."""
        invalid_convictions = [3.0, -3.0, 0.25, -0.25, 1.75, -1.75]
        for conviction in invalid_convictions:
            size = execution_stage.calculate_position_size(conviction)
            assert size == 0.0, \
                f"Invalid conviction {conviction} should return 0.0, got {size}"

    def test_conviction_out_of_range_positive(self, execution_stage):
        """Test that conviction > 2.0 returns 0.0."""
        size = execution_stage.calculate_position_size(3.0)
        assert size == 0.0

    def test_conviction_out_of_range_negative(self, execution_stage):
        """Test that conviction < -2.0 returns 0.0."""
        size = execution_stage.calculate_position_size(-3.0)
        assert size == 0.0

    def test_conviction_with_decimal_precision(self, execution_stage):
        """Test that conviction values must match exactly (no rounding)."""
        # 1.49999999 is not the same as 1.5
        size = execution_stage.calculate_position_size(1.49999999)
        assert size == 0.0, "Non-exact conviction values should return 0.0"

    def test_conviction_zero_with_float_precision(self, execution_stage):
        """Test that 0.0 handles floating point precision correctly."""
        size = execution_stage.calculate_position_size(0.0)
        assert size == 0.0

        # Very small values near zero should NOT match 0.0 exactly
        size_near_zero = execution_stage.calculate_position_size(0.0000001)
        assert size_near_zero == 0.0, "Values near zero but not exactly 0.0 should return 0.0"

    def test_position_size_rationality(self, execution_stage):
        """Test that all returned position sizes are rational (0-100%)."""
        all_convictions = [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0]
        for conviction in all_convictions:
            size = execution_stage.calculate_position_size(conviction)
            assert 0.0 <= size <= 1.0, \
                f"Position size {size} for conviction {conviction} is not in range [0, 1]"

    def test_portfolio_value_parameter_ignored(self, execution_stage):
        """Test that portfolio_value parameter doesn't affect position size percentage."""
        conviction = 1.0
        size_default = execution_stage.calculate_position_size(conviction)
        size_custom = execution_stage.calculate_position_size(conviction, portfolio_value=50000.0)

        # Position size percentage should be the same regardless of portfolio value
        assert size_default == size_custom

    def test_position_size_is_percentage_not_dollars(self, execution_stage):
        """Test that position size is returned as a percentage (0.0-1.0), not dollar amount."""
        size = execution_stage.calculate_position_size(1.0)
        # Should be 0.5 (50%), not 50000 (50% of $100k)
        assert size == 0.5
        assert size < 100, "Position size should be a percentage, not dollar amount"


class TestPositionSizingBusinessLogic:
    """Test suite for business logic rules in position sizing."""

    @pytest.fixture
    def execution_stage(self):
        """Create an ExecutionStage instance for testing."""
        return ExecutionStage()

    def test_flat_means_no_position(self, execution_stage):
        """Test that FLAT conviction (0.0) always results in no position."""
        size = execution_stage.calculate_position_size(0.0)
        assert size == 0.0, "FLAT trades should have 0 position size"

    def test_strong_short_means_no_position(self, execution_stage):
        """Test that strong SHORT (-2.0) results in no position."""
        size = execution_stage.calculate_position_size(-2.0)
        assert size == 0.0, "Strong SHORT should have 0 position size"

    def test_weak_conviction_means_larger_position(self, execution_stage):
        """Test that weaker conviction results in larger position size."""
        # 0.5 conviction (weak) should have larger position than 2.0 (strong)
        weak_size = execution_stage.calculate_position_size(0.5)
        strong_size = execution_stage.calculate_position_size(2.0)
        assert weak_size > strong_size, "Weaker conviction should have larger position"

    def test_long_short_symmetry(self, execution_stage):
        """Test that LONG and SHORT convictions are symmetric in position sizing."""
        # Positive and negative convictions of same magnitude should have same position size
        pairs = [
            (0.5, -0.5),
            (1.0, -1.0),
            (1.5, -1.5),
        ]
        for long_conv, short_conv in pairs:
            long_size = execution_stage.calculate_position_size(long_conv)
            short_size = execution_stage.calculate_position_size(short_conv)
            assert long_size == short_size, \
                f"LONG ({long_conv}) and SHORT ({short_conv}) should have same position size"

    def test_extreme_conviction_cautious_sizing(self, execution_stage):
        """Test that extreme convictions result in cautious (small or zero) positions."""
        # Very strong conviction (2.0) should have small position
        very_strong = execution_stage.calculate_position_size(2.0)
        assert very_strong <= 0.10, "Very strong conviction should have small position"

        # Extreme SHORT (-2.0) should have no position
        extreme_short = execution_stage.calculate_position_size(-2.0)
        assert extreme_short == 0.0, "Extreme SHORT should have no position"

    def test_moderate_conviction_largest_position(self, execution_stage):
        """Test that moderate conviction results in largest positions."""
        # 0.5 and -0.5 should have largest positions (75%)
        size_pos = execution_stage.calculate_position_size(0.5)
        size_neg = execution_stage.calculate_position_size(-0.5)

        assert size_pos == 0.75, "Moderate positive conviction should have 75% position"
        assert size_neg == 0.75, "Moderate negative conviction should have 75% position"


class TestPositionSizingIntegration:
    """Test suite for integration scenarios with position sizing."""

    @pytest.fixture
    def execution_stage(self):
        """Create an ExecutionStage instance for testing."""
        return ExecutionStage()

    def test_position_sizing_with_chairman_decision(self, execution_stage):
        """Test position sizing with a typical chairman decision."""
        chairman_decision = {
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        size = execution_stage.calculate_position_size(chairman_decision["conviction"])
        assert size == 0.50

    def test_position_sizing_with_pm_pitches(self, execution_stage):
        """Test position sizing with multiple PM pitches."""
        pitches = [
            {"model": "gpt-4", "conviction": 1.5},
            {"model": "claude", "conviction": 0.5},
            {"model": "gemini", "conviction": 0.0},
        ]

        expected_sizes = [0.25, 0.75, 0.0]

        for pitch, expected in zip(pitches, expected_sizes):
            size = execution_stage.calculate_position_size(pitch["conviction"])
            assert size == expected

    def test_position_sizing_for_all_accounts(self, execution_stage):
        """Test position sizing for all 6 trading accounts."""
        # Simulate all 6 accounts with different convictions
        accounts = [
            {"name": "gpt5", "conviction": 1.5},
            {"name": "gemini", "conviction": 1.0},
            {"name": "sonnet", "conviction": 0.5},
            {"name": "grok", "conviction": 2.0},
            {"name": "council", "conviction": 1.0},
            {"name": "baseline", "conviction": 0.0},
        ]

        expected_sizes = [0.25, 0.50, 0.75, 0.10, 0.50, 0.0]

        for account, expected in zip(accounts, expected_sizes):
            size = execution_stage.calculate_position_size(account["conviction"])
            assert size == expected, \
                f"Account {account['name']} with conviction {account['conviction']} should have size {expected}"

    def test_position_sizing_handles_missing_conviction(self, execution_stage):
        """Test that missing conviction values are handled gracefully."""
        # If conviction is not in the mapping, should return 0.0
        size = execution_stage.calculate_position_size(None)
        assert size == 0.0, "None conviction should return 0.0"


# ==================== TRADE PREPARATION TESTS ====================


class TestPrepareTradeFromChairmanDecision:
    """Test suite for _prepare_trade method with chairman decisions."""

    @pytest.fixture
    def execution_stage(self):
        """Create an ExecutionStage instance for testing."""
        return ExecutionStage()

    def test_prepare_trade_from_chairman_decision_long(self, execution_stage):
        """Test preparing trade from chairman decision for LONG position."""
        chairman_decision = {
            "account": "Council",
            "alpaca_id": "council_alpaca_id",
            "model": "anthropic/claude-opus",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.5,
        }

        trade = execution_stage._prepare_trade(chairman_decision, "council")

        assert trade is not None
        assert trade["instrument"] == "SPY"
        assert trade["direction"] == "LONG"
        assert trade["side"] == "buy"
        assert trade["conviction"] == 1.5
        assert trade["position_size"] == 0.25
        assert trade["account"] == "Council"
        assert trade["alpaca_id"] == "council_alpaca_id"
        assert trade["model"] == "anthropic/claude-opus"
        assert trade["source"] == "council"
        assert trade["approved"] is False
        assert trade["order_status"] == "pending"
        assert "trade_id" in trade
        assert "timestamp" in trade

    def test_prepare_trade_from_chairman_decision_short(self, execution_stage):
        """Test preparing trade from chairman decision for SHORT position."""
        chairman_decision = {
            "account": "Council",
            "alpaca_id": "council_alpaca_id",
            "model": "anthropic/claude-opus",
            "instrument": "TLT",
            "direction": "SHORT",
            "conviction": -1.0,
        }

        trade = execution_stage._prepare_trade(chairman_decision, "council")

        assert trade is not None
        assert trade["instrument"] == "TLT"
        assert trade["direction"] == "SHORT"
        assert trade["side"] == "sell"
        assert trade["conviction"] == -1.0
        assert trade["position_size"] == 0.50

    def test_prepare_trade_chairman_flat_returns_none(self, execution_stage):
        """Test that chairman FLAT decision returns None (no execution)."""
        chairman_decision = {
            "account": "Council",
            "alpaca_id": "council_alpaca_id",
            "model": "anthropic/claude-opus",
            "instrument": "NONE",
            "direction": "FLAT",
            "conviction": 0.0,
        }

        trade = execution_stage._prepare_trade(chairman_decision, "council")

        assert trade is None, "FLAT decisions should not generate trades"

    def test_prepare_trade_chairman_high_conviction(self, execution_stage):
        """Test chairman decision with very high conviction (2.0)."""
        chairman_decision = {
            "account": "Council",
            "alpaca_id": "council_alpaca_id",
            "model": "anthropic/claude-opus",
            "instrument": "GLD",
            "direction": "LONG",
            "conviction": 2.0,
        }

        trade = execution_stage._prepare_trade(chairman_decision, "council")

        assert trade is not None
        assert trade["conviction"] == 2.0
        assert trade["position_size"] == 0.10  # Very high conviction = small position


class TestPrepareTradeFromPMPitch:
    """Test suite for _prepare_trade method with PM pitches."""

    @pytest.fixture
    def execution_stage(self):
        """Create an ExecutionStage instance for testing."""
        return ExecutionStage()

    def test_prepare_trade_from_pm_pitch_long(self, execution_stage, valid_long_pitch):
        """Test preparing trade from PM pitch for LONG position."""
        # Add required account and alpaca_id fields
        valid_long_pitch["account"] = "GPT-5.1"
        valid_long_pitch["alpaca_id"] = "gpt51_alpaca_id"
        valid_long_pitch["conviction"] = 1.0

        trade = execution_stage._prepare_trade(valid_long_pitch, valid_long_pitch["model"])

        assert trade is not None
        assert trade["instrument"] == valid_long_pitch["instrument"]
        assert trade["direction"] == "LONG"
        assert trade["side"] == "buy"
        assert trade["conviction"] == 1.0
        assert trade["position_size"] == 0.50
        assert trade["account"] == "GPT-5.1"
        assert trade["model"] == valid_long_pitch["model"]
        assert trade["source"] == valid_long_pitch["model"]

    def test_prepare_trade_from_pm_pitch_short(self, execution_stage, valid_short_pitch):
        """Test preparing trade from PM pitch for SHORT position."""
        # Add required account and alpaca_id fields
        valid_short_pitch["account"] = "Sonnet-4.5"
        valid_short_pitch["alpaca_id"] = "sonnet45_alpaca_id"
        valid_short_pitch["conviction"] = -1.5

        trade = execution_stage._prepare_trade(valid_short_pitch, valid_short_pitch["model"])

        assert trade is not None
        assert trade["instrument"] == valid_short_pitch["instrument"]
        assert trade["direction"] == "SHORT"
        assert trade["side"] == "sell"
        assert trade["conviction"] == -1.5
        assert trade["position_size"] == 0.25

    def test_prepare_trade_pm_flat_returns_none(self, execution_stage, valid_flat_pitch):
        """Test that PM FLAT pitch returns None (no execution)."""
        valid_flat_pitch["account"] = "Gemini-3"
        valid_flat_pitch["alpaca_id"] = "gemini3_alpaca_id"

        trade = execution_stage._prepare_trade(valid_flat_pitch, valid_flat_pitch["model"])

        assert trade is None, "FLAT pitches should not generate trades"

    def test_prepare_trade_pm_low_conviction(self, execution_stage):
        """Test PM pitch with low conviction (0.5)."""
        pm_pitch = {
            "account": "Grok",
            "alpaca_id": "grok_alpaca_id",
            "model": "x-ai/grok-beta",
            "instrument": "IWM",
            "direction": "LONG",
            "conviction": 0.5,
        }

        trade = execution_stage._prepare_trade(pm_pitch, pm_pitch["model"])

        assert trade is not None
        assert trade["conviction"] == 0.5
        assert trade["position_size"] == 0.75  # Low conviction = large position


class TestPrepareTradeQuantityCalculation:
    """Test suite for quantity calculation in _prepare_trade."""

    @pytest.fixture
    def execution_stage(self):
        """Create an ExecutionStage instance for testing."""
        return ExecutionStage()

    def test_qty_calculation_50_percent_position(self, execution_stage):
        """Test qty calculation for 50% position size."""
        decision = {
            "account": "Test",
            "alpaca_id": "test_id",
            "model": "test/model",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,  # 50% position
        }

        trade = execution_stage._prepare_trade(decision, "test")

        # $100,000 * 0.50 = $50,000
        assert trade["qty"] == 50000

    def test_qty_calculation_75_percent_position(self, execution_stage):
        """Test qty calculation for 75% position size."""
        decision = {
            "account": "Test",
            "alpaca_id": "test_id",
            "model": "test/model",
            "instrument": "QQQ",
            "direction": "LONG",
            "conviction": 0.5,  # 75% position
        }

        trade = execution_stage._prepare_trade(decision, "test")

        # $100,000 * 0.75 = $75,000
        assert trade["qty"] == 75000

    def test_qty_calculation_25_percent_position(self, execution_stage):
        """Test qty calculation for 25% position size."""
        decision = {
            "account": "Test",
            "alpaca_id": "test_id",
            "model": "test/model",
            "instrument": "GLD",
            "direction": "LONG",
            "conviction": 1.5,  # 25% position
        }

        trade = execution_stage._prepare_trade(decision, "test")

        # $100,000 * 0.25 = $25,000
        assert trade["qty"] == 25000

    def test_qty_calculation_10_percent_position(self, execution_stage):
        """Test qty calculation for 10% position size (very high conviction)."""
        decision = {
            "account": "Test",
            "alpaca_id": "test_id",
            "model": "test/model",
            "instrument": "USO",
            "direction": "LONG",
            "conviction": 2.0,  # 10% position
        }

        trade = execution_stage._prepare_trade(decision, "test")

        # $100,000 * 0.10 = $10,000
        assert trade["qty"] == 10000

    def test_qty_minimum_one_share(self, execution_stage):
        """Test that qty is at least 1 share even for very small positions."""
        decision = {
            "account": "Test",
            "alpaca_id": "test_id",
            "model": "test/model",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 2.0,  # 10% position = $10,000
        }

        trade = execution_stage._prepare_trade(decision, "test")

        # Even if position is small, qty should be >= 1
        assert trade["qty"] >= 1


class TestPrepareTradeFieldValidation:
    """Test suite for field validation in _prepare_trade."""

    @pytest.fixture
    def execution_stage(self):
        """Create an ExecutionStage instance for testing."""
        return ExecutionStage()

    def test_prepare_trade_includes_all_required_fields(self, execution_stage):
        """Test that prepared trade includes all required fields."""
        decision = {
            "account": "Test Account",
            "alpaca_id": "test_alpaca_id",
            "model": "test/model",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        trade = execution_stage._prepare_trade(decision, "council")

        required_fields = [
            "trade_id",
            "account",
            "alpaca_id",
            "model",
            "source",
            "instrument",
            "direction",
            "side",
            "qty",
            "position_size",
            "conviction",
            "approved",
            "order_id",
            "order_status",
            "timestamp",
        ]

        for field in required_fields:
            assert field in trade, f"Missing required field: {field}"

    def test_prepare_trade_side_buy_for_long(self, execution_stage):
        """Test that LONG direction maps to 'buy' side."""
        decision = {
            "account": "Test",
            "alpaca_id": "test_id",
            "model": "test/model",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        trade = execution_stage._prepare_trade(decision, "test")

        assert trade["side"] == "buy"

    def test_prepare_trade_side_sell_for_short(self, execution_stage):
        """Test that SHORT direction maps to 'sell' side."""
        decision = {
            "account": "Test",
            "alpaca_id": "test_id",
            "model": "test/model",
            "instrument": "TLT",
            "direction": "SHORT",
            "conviction": -1.0,
        }

        trade = execution_stage._prepare_trade(decision, "test")

        assert trade["side"] == "sell"

    def test_prepare_trade_approved_defaults_false(self, execution_stage):
        """Test that approved field defaults to False."""
        decision = {
            "account": "Test",
            "alpaca_id": "test_id",
            "model": "test/model",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        trade = execution_stage._prepare_trade(decision, "test")

        assert trade["approved"] is False

    def test_prepare_trade_order_id_null(self, execution_stage):
        """Test that order_id is None before execution."""
        decision = {
            "account": "Test",
            "alpaca_id": "test_id",
            "model": "test/model",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        trade = execution_stage._prepare_trade(decision, "test")

        assert trade["order_id"] is None

    def test_prepare_trade_order_status_pending(self, execution_stage):
        """Test that order_status defaults to 'pending'."""
        decision = {
            "account": "Test",
            "alpaca_id": "test_id",
            "model": "test/model",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        trade = execution_stage._prepare_trade(decision, "test")

        assert trade["order_status"] == "pending"

    def test_prepare_trade_timestamp_is_iso_format(self, execution_stage):
        """Test that timestamp is in ISO 8601 format."""
        decision = {
            "account": "Test",
            "alpaca_id": "test_id",
            "model": "test/model",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        trade = execution_stage._prepare_trade(decision, "test")

        # Should be able to parse as ISO 8601
        from datetime import datetime
        timestamp = datetime.fromisoformat(trade["timestamp"].replace("Z", "+00:00"))
        assert timestamp is not None


class TestPrepareTradeEdgeCases:
    """Test suite for edge cases in _prepare_trade."""

    @pytest.fixture
    def execution_stage(self):
        """Create an ExecutionStage instance for testing."""
        return ExecutionStage()

    def test_prepare_trade_invalid_conviction_returns_none(self, execution_stage):
        """Test that invalid conviction (not in POSITION_SIZING) returns None."""
        decision = {
            "account": "Test",
            "alpaca_id": "test_id",
            "model": "test/model",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 0.75,  # Invalid: not in POSITION_SIZING
        }

        trade = execution_stage._prepare_trade(decision, "test")

        assert trade is None, "Invalid conviction should return None"

    def test_prepare_trade_zero_position_size_returns_none(self, execution_stage):
        """Test that conviction with 0.0 position size returns None."""
        decision = {
            "account": "Test",
            "alpaca_id": "test_id",
            "model": "test/model",
            "instrument": "SPY",
            "direction": "SHORT",
            "conviction": -2.0,  # Maps to 0.0 position size
        }

        trade = execution_stage._prepare_trade(decision, "test")

        assert trade is None, "Zero position size should return None"

    def test_prepare_trade_missing_account_uses_unknown(self, execution_stage):
        """Test that missing account field defaults to 'Unknown'."""
        decision = {
            "alpaca_id": "test_id",
            "model": "test/model",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        trade = execution_stage._prepare_trade(decision, "test")

        assert trade["account"] == "Unknown"

    def test_prepare_trade_missing_alpaca_id_uses_unknown(self, execution_stage):
        """Test that missing alpaca_id field defaults to 'Unknown'."""
        decision = {
            "account": "Test",
            "model": "test/model",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        trade = execution_stage._prepare_trade(decision, "test")

        assert trade["alpaca_id"] == "Unknown"

    def test_prepare_trade_missing_model_uses_unknown(self, execution_stage):
        """Test that missing model field defaults to 'unknown'."""
        decision = {
            "account": "Test",
            "alpaca_id": "test_id",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        trade = execution_stage._prepare_trade(decision, "test")

        assert trade["model"] == "unknown"

    def test_prepare_trade_missing_conviction_defaults_zero(self, execution_stage):
        """Test that missing conviction defaults to 0 (returns None)."""
        decision = {
            "account": "Test",
            "alpaca_id": "test_id",
            "model": "test/model",
            "instrument": "SPY",
            "direction": "LONG",
            # conviction missing
        }

        trade = execution_stage._prepare_trade(decision, "test")

        assert trade is None, "Missing conviction should default to 0 (no trade)"

    def test_prepare_trade_missing_direction_returns_none(self, execution_stage):
        """Test that missing direction defaults to FLAT (returns None)."""
        decision = {
            "account": "Test",
            "alpaca_id": "test_id",
            "model": "test/model",
            "instrument": "SPY",
            "conviction": 1.0,
            # direction missing
        }

        trade = execution_stage._prepare_trade(decision, "test")

        assert trade is None, "Missing direction should return None"

    def test_prepare_trade_invalid_direction_returns_none(self, execution_stage):
        """Test that invalid direction (not LONG/SHORT) returns None."""
        decision = {
            "account": "Test",
            "alpaca_id": "test_id",
            "model": "test/model",
            "instrument": "SPY",
            "direction": "SIDEWAYS",  # Invalid
            "conviction": 1.0,
        }

        trade = execution_stage._prepare_trade(decision, "test")

        assert trade is None, "Invalid direction should return None"


class TestPrepareTradeWithDifferentSources:
    """Test suite for _prepare_trade with different sources."""

    @pytest.fixture
    def execution_stage(self):
        """Create an ExecutionStage instance for testing."""
        return ExecutionStage()

    def test_prepare_trade_source_council(self, execution_stage):
        """Test that source is correctly set to 'council'."""
        decision = {
            "account": "Council",
            "alpaca_id": "council_id",
            "model": "anthropic/claude-opus",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.5,
        }

        trade = execution_stage._prepare_trade(decision, "council")

        assert trade["source"] == "council"

    def test_prepare_trade_source_pm_model(self, execution_stage):
        """Test that source is correctly set to PM model key."""
        decision = {
            "account": "GPT-5.1",
            "alpaca_id": "gpt51_id",
            "model": "openai/gpt-5.1",
            "instrument": "QQQ",
            "direction": "LONG",
            "conviction": 1.0,
        }

        trade = execution_stage._prepare_trade(decision, "openai/gpt-5.1")

        assert trade["source"] == "openai/gpt-5.1"

    def test_prepare_trade_multiple_sources_different_ids(self, execution_stage):
        """Test that trades from different sources have unique trade_ids."""
        decision1 = {
            "account": "Council",
            "alpaca_id": "council_id",
            "model": "anthropic/claude-opus",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.5,
        }

        decision2 = {
            "account": "GPT-5.1",
            "alpaca_id": "gpt51_id",
            "model": "openai/gpt-5.1",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        trade1 = execution_stage._prepare_trade(decision1, "council")
        trade2 = execution_stage._prepare_trade(decision2, "openai/gpt-5.1")

        assert trade1["trade_id"] != trade2["trade_id"]


class TestPrepareTradeIntegrationScenarios:
    """Test suite for integration scenarios with _prepare_trade."""

    @pytest.fixture
    def execution_stage(self):
        """Create an ExecutionStage instance for testing."""
        return ExecutionStage()

    def test_prepare_all_pm_trades(self, execution_stage, all_pm_pitches):
        """Test preparing trades for all PM pitches."""
        # Add account and alpaca_id to all pitches
        accounts = ["GPT-5.1", "Sonnet-4.5", "Gemini-3", "Grok", "Command-R"]
        alpaca_ids = ["gpt51_id", "sonnet45_id", "gemini3_id", "grok_id", "command_id"]

        for pitch, account, alpaca_id in zip(all_pm_pitches, accounts, alpaca_ids):
            pitch["account"] = account
            pitch["alpaca_id"] = alpaca_id

        trades = []
        for pitch in all_pm_pitches:
            trade = execution_stage._prepare_trade(pitch, pitch["model"])
            if trade:  # Only include non-FLAT trades
                trades.append(trade)

        # Should have at least some trades (not all FLAT)
        assert len(trades) > 0

        # All trades should have unique trade_ids
        trade_ids = [t["trade_id"] for t in trades]
        assert len(trade_ids) == len(set(trade_ids))

    def test_prepare_trade_conflicting_directions_different_accounts(self, execution_stage):
        """Test that conflicting directions result in different sides."""
        long_decision = {
            "account": "Account1",
            "alpaca_id": "account1_id",
            "model": "model1",
            "instrument": "SPY",
            "direction": "LONG",
            "conviction": 1.0,
        }

        short_decision = {
            "account": "Account2",
            "alpaca_id": "account2_id",
            "model": "model2",
            "instrument": "SPY",
            "direction": "SHORT",
            "conviction": -1.0,
        }

        long_trade = execution_stage._prepare_trade(long_decision, "model1")
        short_trade = execution_stage._prepare_trade(short_decision, "model2")

        assert long_trade["side"] == "buy"
        assert short_trade["side"] == "sell"

    def test_prepare_trade_same_instrument_different_convictions(self, execution_stage):
        """Test preparing trades for same instrument with different conviction levels."""
        convictions = [0.5, 1.0, 1.5, 2.0]
        expected_sizes = [0.75, 0.50, 0.25, 0.10]

        trades = []
        for conv, expected_size in zip(convictions, expected_sizes):
            decision = {
                "account": f"Account_{conv}",
                "alpaca_id": f"account_{conv}_id",
                "model": f"model_{conv}",
                "instrument": "SPY",
                "direction": "LONG",
                "conviction": conv,
            }

            trade = execution_stage._prepare_trade(decision, f"model_{conv}")
            trades.append(trade)

            assert trade["position_size"] == expected_size
            assert trade["qty"] == int(100000 * expected_size)
