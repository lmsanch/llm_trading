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
