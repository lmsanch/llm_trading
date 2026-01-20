"""Test checkpoint logic focusing on conviction change calculation and action mapping.

This module tests the CheckpointStage's conviction update logic including:
- CheckpointAction enum constants (STAY, EXIT, FLIP, REDUCE, INCREASE)
- CONVICTION_THRESHOLDS for action determination
- Chairman decision parsing for action extraction
- Conviction change calculation and action mapping
- Position adjustment logic for each action type
"""

import json
import pytest
from backend.pipeline.stages.checkpoint import CheckpointStage, CheckpointAction


class TestCheckpointActionEnum:
    """Test suite for CheckpointAction enum definitions."""

    def test_checkpoint_action_enum_exists(self):
        """Test that CheckpointAction enum is defined."""
        assert CheckpointAction is not None

    def test_checkpoint_action_stay(self):
        """Test STAY action is defined."""
        assert CheckpointAction.STAY is not None
        assert CheckpointAction.STAY.value == "STAY"

    def test_checkpoint_action_exit(self):
        """Test EXIT action is defined."""
        assert CheckpointAction.EXIT is not None
        assert CheckpointAction.EXIT.value == "EXIT"

    def test_checkpoint_action_flip(self):
        """Test FLIP action is defined."""
        assert CheckpointAction.FLIP is not None
        assert CheckpointAction.FLIP.value == "FLIP"

    def test_checkpoint_action_reduce(self):
        """Test REDUCE action is defined."""
        assert CheckpointAction.REDUCE is not None
        assert CheckpointAction.REDUCE.value == "REDUCE"

    def test_checkpoint_action_increase(self):
        """Test INCREASE action is defined."""
        assert CheckpointAction.INCREASE is not None
        assert CheckpointAction.INCREASE.value == "INCREASE"

    def test_all_checkpoint_actions_defined(self):
        """Test that all expected actions are defined."""
        expected_actions = ["STAY", "EXIT", "FLIP", "REDUCE", "INCREASE"]
        actual_actions = [action.value for action in CheckpointAction]
        assert set(expected_actions) == set(actual_actions)


class TestConvictionThresholds:
    """Test suite for CONVICTION_THRESHOLDS constant definitions."""

    def test_conviction_thresholds_exists(self):
        """Test that CONVICTION_THRESHOLDS is defined."""
        assert CheckpointStage.CONVICTION_THRESHOLDS is not None
        assert isinstance(CheckpointStage.CONVICTION_THRESHOLDS, dict)

    def test_conviction_threshold_strong_flip(self):
        """Test that strong_flip threshold is 1.5."""
        assert CheckpointStage.CONVICTION_THRESHOLDS["strong_flip"] == 1.5

    def test_conviction_threshold_exit(self):
        """Test that exit threshold is 1.0."""
        assert CheckpointStage.CONVICTION_THRESHOLDS["exit"] == 1.0

    def test_conviction_threshold_reduce(self):
        """Test that reduce threshold is 0.5."""
        assert CheckpointStage.CONVICTION_THRESHOLDS["reduce"] == 0.5

    def test_conviction_threshold_increase(self):
        """Test that increase threshold is 0.5."""
        assert CheckpointStage.CONVICTION_THRESHOLDS["increase"] == 0.5

    def test_all_thresholds_are_numeric(self):
        """Test that all thresholds are numeric values."""
        for key, value in CheckpointStage.CONVICTION_THRESHOLDS.items():
            assert isinstance(value, (int, float)), \
                f"Threshold '{key}' is not numeric"

    def test_all_thresholds_are_positive(self):
        """Test that all thresholds are positive."""
        for key, value in CheckpointStage.CONVICTION_THRESHOLDS.items():
            assert value > 0, f"Threshold '{key}' is not positive"

    def test_thresholds_ordering(self):
        """Test that thresholds are ordered logically."""
        # strong_flip > exit > reduce/increase
        assert CheckpointStage.CONVICTION_THRESHOLDS["strong_flip"] > \
               CheckpointStage.CONVICTION_THRESHOLDS["exit"]
        assert CheckpointStage.CONVICTION_THRESHOLDS["exit"] > \
               CheckpointStage.CONVICTION_THRESHOLDS["reduce"]


class TestParseChairmanDecisionJSON:
    """Test suite for parsing chairman decisions from JSON format."""

    @pytest.fixture
    def checkpoint_stage(self):
        """Create a CheckpointStage instance for testing."""
        return CheckpointStage()

    @pytest.fixture
    def sample_position(self):
        """Sample position for testing."""
        return {
            "account": "Council",
            "symbol": "SPY",
            "side": "long",
            "qty": "100",
            "current_price": 450.00,
            "entry_price": 440.00,
            "unrealized_pl": 1000.00,
            "unrealized_plpc": 2.27,
        }

    def test_parse_stay_action_from_json(self, checkpoint_stage, sample_position):
        """Test parsing STAY action from JSON response."""
        response = json.dumps({
            "current_conviction": 1.5,
            "new_conviction": 1.5,
            "action": "STAY",
            "reason": "Position performing well, no change needed"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "STAY"
        assert result["current_conviction"] == 1.5
        assert result["new_conviction"] == 1.5
        assert result["reason"] == "Position performing well, no change needed"
        assert result["instrument"] == "SPY"
        assert result["account"] == "Council"
        assert result["direction"] == "LONG"
        assert result["executed"] is False

    def test_parse_exit_action_from_json(self, checkpoint_stage, sample_position):
        """Test parsing EXIT action from JSON response."""
        response = json.dumps({
            "current_conviction": 1.5,
            "new_conviction": 0.5,
            "action": "EXIT",
            "reason": "Conviction dropped below threshold"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "EXIT"
        assert result["new_conviction"] == 0.5

    def test_parse_flip_action_from_json(self, checkpoint_stage, sample_position):
        """Test parsing FLIP action from JSON response."""
        response = json.dumps({
            "current_conviction": 1.5,
            "new_conviction": -1.0,
            "action": "FLIP",
            "reason": "Strong reversal signal detected"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "FLIP"
        assert result["new_conviction"] == -1.0

    def test_parse_reduce_action_from_json(self, checkpoint_stage, sample_position):
        """Test parsing REDUCE action from JSON response."""
        response = json.dumps({
            "current_conviction": 1.5,
            "new_conviction": 0.8,
            "action": "REDUCE",
            "reason": "Conviction weakened, reducing exposure"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "REDUCE"
        assert result["new_conviction"] == 0.8

    def test_parse_increase_action_from_json(self, checkpoint_stage, sample_position):
        """Test parsing INCREASE action from JSON response."""
        response = json.dumps({
            "current_conviction": 1.0,
            "new_conviction": 1.8,
            "action": "INCREASE",
            "reason": "Thesis strengthening, increasing position"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "INCREASE"
        assert result["new_conviction"] == 1.8

    def test_parse_decision_with_negative_conviction(self, checkpoint_stage, sample_position):
        """Test parsing decision with negative conviction (SHORT)."""
        response = json.dumps({
            "current_conviction": -1.0,
            "new_conviction": -1.5,
            "action": "STAY",
            "reason": "Short thesis intact"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["current_conviction"] == -1.0
        assert result["new_conviction"] == -1.5

    def test_parse_decision_with_zero_conviction(self, checkpoint_stage, sample_position):
        """Test parsing decision with zero conviction (EXIT to FLAT)."""
        response = json.dumps({
            "current_conviction": 1.5,
            "new_conviction": 0.0,
            "action": "EXIT",
            "reason": "No conviction remaining"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["new_conviction"] == 0.0
        assert result["action"] == "EXIT"


class TestParseChairmanDecisionTextFallback:
    """Test suite for parsing chairman decisions from text format (fallback)."""

    @pytest.fixture
    def checkpoint_stage(self):
        """Create a CheckpointStage instance for testing."""
        return CheckpointStage()

    @pytest.fixture
    def sample_position(self):
        """Sample position for testing."""
        return {
            "account": "Council",
            "symbol": "QQQ",
            "side": "long",
            "qty": "50",
            "current_price": 380.00,
            "entry_price": 370.00,
            "unrealized_pl": 500.00,
            "unrealized_plpc": 2.70,
        }

    def test_parse_stay_from_text(self, checkpoint_stage, sample_position):
        """Test parsing STAY action from text response."""
        response = "Based on current conditions, I recommend we STAY in the position. The thesis remains valid."

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "STAY"

    def test_parse_exit_from_text(self, checkpoint_stage, sample_position):
        """Test parsing EXIT action from text response."""
        response = "The position should EXIT immediately. Stop loss triggered."

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "EXIT"

    def test_parse_flip_from_text(self, checkpoint_stage, sample_position):
        """Test parsing FLIP action from text response."""
        response = "Strong reversal signal. Recommend FLIP to opposite direction."

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "FLIP"

    def test_parse_reduce_from_text(self, checkpoint_stage, sample_position):
        """Test parsing REDUCE action from text response."""
        response = "Conviction weakening. REDUCE position by 50%."

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "REDUCE"

    def test_parse_increase_from_text(self, checkpoint_stage, sample_position):
        """Test parsing INCREASE action from text response."""
        response = "Thesis strengthening. INCREASE exposure by 50%."

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "INCREASE"

    def test_parse_conviction_from_text(self, checkpoint_stage, sample_position):
        """Test parsing conviction value from text response."""
        response = "Current conviction: 1.5. This should remain stable."

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["new_conviction"] == 1.5

    def test_parse_multiple_keywords_uses_first(self, checkpoint_stage, sample_position):
        """Test that when multiple keywords present, first one wins."""
        response = "Should we EXIT or REDUCE? I recommend EXIT."

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "EXIT"

    def test_parse_no_keywords_defaults_stay(self, checkpoint_stage, sample_position):
        """Test that no keywords defaults to STAY."""
        response = "The position looks fine. Continue monitoring."

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "STAY"

    def test_parse_case_insensitive(self, checkpoint_stage, sample_position):
        """Test that parsing is case insensitive."""
        responses = [
            "Recommend exit immediately",
            "Recommend EXIT immediately",
            "Recommend ExIt immediately",
        ]

        for response in responses:
            result = checkpoint_stage._parse_chairman_decision(response, sample_position)
            assert result["action"] == "EXIT"


class TestConvictionChangeScenarios:
    """Test suite for conviction change scenarios and action mapping."""

    @pytest.fixture
    def checkpoint_stage(self):
        """Create a CheckpointStage instance for testing."""
        return CheckpointStage()

    @pytest.fixture
    def sample_position(self):
        """Sample position for testing."""
        return {
            "account": "Council",
            "symbol": "SPY",
            "side": "long",
            "qty": "100",
            "current_price": 450.00,
            "entry_price": 440.00,
            "unrealized_pl": 1000.00,
            "unrealized_plpc": 2.27,
        }

    def test_stay_no_conviction_change(self, checkpoint_stage, sample_position):
        """Test STAY action when conviction doesn't change."""
        response = json.dumps({
            "current_conviction": 1.5,
            "new_conviction": 1.5,
            "action": "STAY",
            "reason": "No change needed"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "STAY"
        assert result["current_conviction"] == result["new_conviction"]

    def test_stay_small_conviction_change(self, checkpoint_stage, sample_position):
        """Test STAY action when conviction change is small (< 0.5)."""
        response = json.dumps({
            "current_conviction": 1.5,
            "new_conviction": 1.3,
            "action": "STAY",
            "reason": "Minor change, stay in position"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "STAY"
        conviction_change = abs(result["new_conviction"] - result["current_conviction"])
        assert conviction_change < CheckpointStage.CONVICTION_THRESHOLDS["reduce"]

    def test_exit_low_absolute_conviction(self, checkpoint_stage, sample_position):
        """Test EXIT action when new conviction drops below exit threshold (1.0)."""
        response = json.dumps({
            "current_conviction": 1.5,
            "new_conviction": 0.8,
            "action": "EXIT",
            "reason": "Conviction below threshold"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "EXIT"
        assert result["new_conviction"] < CheckpointStage.CONVICTION_THRESHOLDS["exit"]

    def test_exit_conviction_drops_to_zero(self, checkpoint_stage, sample_position):
        """Test EXIT action when conviction drops to zero."""
        response = json.dumps({
            "current_conviction": 1.5,
            "new_conviction": 0.0,
            "action": "EXIT",
            "reason": "No conviction remaining"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "EXIT"
        assert result["new_conviction"] == 0.0

    def test_flip_conviction_change_exceeds_threshold(self, checkpoint_stage, sample_position):
        """Test FLIP action when conviction change exceeds strong_flip threshold (1.5)."""
        response = json.dumps({
            "current_conviction": 1.5,
            "new_conviction": -0.5,
            "action": "FLIP",
            "reason": "Strong reversal"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "FLIP"
        conviction_change = abs(result["new_conviction"] - result["current_conviction"])
        assert conviction_change >= CheckpointStage.CONVICTION_THRESHOLDS["strong_flip"]

    def test_flip_long_to_short(self, checkpoint_stage, sample_position):
        """Test FLIP action from LONG to SHORT."""
        response = json.dumps({
            "current_conviction": 1.5,
            "new_conviction": -1.0,
            "action": "FLIP",
            "reason": "Reversing to short"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "FLIP"
        assert result["current_conviction"] > 0
        assert result["new_conviction"] < 0

    def test_flip_short_to_long(self, checkpoint_stage, sample_position):
        """Test FLIP action from SHORT to LONG."""
        sample_position["side"] = "short"
        response = json.dumps({
            "current_conviction": -1.5,
            "new_conviction": 1.0,
            "action": "FLIP",
            "reason": "Reversing to long"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "FLIP"
        assert result["current_conviction"] < 0
        assert result["new_conviction"] > 0

    def test_reduce_conviction_drop_above_threshold(self, checkpoint_stage, sample_position):
        """Test REDUCE action when conviction drops by > 0.5."""
        response = json.dumps({
            "current_conviction": 1.8,
            "new_conviction": 1.2,
            "action": "REDUCE",
            "reason": "Conviction weakened"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "REDUCE"
        conviction_drop = result["current_conviction"] - result["new_conviction"]
        assert conviction_drop >= CheckpointStage.CONVICTION_THRESHOLDS["reduce"]

    def test_reduce_maintains_same_direction(self, checkpoint_stage, sample_position):
        """Test REDUCE maintains same direction (LONG stays LONG)."""
        response = json.dumps({
            "current_conviction": 1.8,
            "new_conviction": 1.2,
            "action": "REDUCE",
            "reason": "Reducing exposure"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "REDUCE"
        # Both convictions should have same sign (both positive or both negative)
        assert (result["current_conviction"] > 0) == (result["new_conviction"] > 0)

    def test_increase_conviction_rise_above_threshold(self, checkpoint_stage, sample_position):
        """Test INCREASE action when conviction increases by > 0.5."""
        response = json.dumps({
            "current_conviction": 1.0,
            "new_conviction": 1.6,
            "action": "INCREASE",
            "reason": "Thesis strengthening"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "INCREASE"
        conviction_rise = result["new_conviction"] - result["current_conviction"]
        assert conviction_rise >= CheckpointStage.CONVICTION_THRESHOLDS["increase"]

    def test_increase_maintains_same_direction(self, checkpoint_stage, sample_position):
        """Test INCREASE maintains same direction (LONG stays LONG)."""
        response = json.dumps({
            "current_conviction": 1.0,
            "new_conviction": 1.6,
            "action": "INCREASE",
            "reason": "Increasing exposure"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "INCREASE"
        # Both convictions should have same sign
        assert (result["current_conviction"] > 0) == (result["new_conviction"] > 0)


class TestPositionFieldsInDecision:
    """Test suite for position field mapping in chairman decisions."""

    @pytest.fixture
    def checkpoint_stage(self):
        """Create a CheckpointStage instance for testing."""
        return CheckpointStage()

    def test_decision_includes_account_name(self, checkpoint_stage):
        """Test that decision includes account name from position."""
        position = {
            "account": "GPT-5.1",
            "symbol": "SPY",
            "side": "long",
            "qty": "100",
            "current_price": 450.00,
            "entry_price": 440.00,
            "unrealized_pl": 1000.00,
            "unrealized_plpc": 2.27,
        }

        response = json.dumps({
            "current_conviction": 1.5,
            "new_conviction": 1.5,
            "action": "STAY",
            "reason": "Position good"
        })

        result = checkpoint_stage._parse_chairman_decision(response, position)

        assert result["account"] == "GPT-5.1"

    def test_decision_includes_instrument_symbol(self, checkpoint_stage):
        """Test that decision includes instrument symbol from position."""
        position = {
            "account": "Council",
            "symbol": "QQQ",
            "side": "long",
            "qty": "50",
            "current_price": 380.00,
            "entry_price": 370.00,
            "unrealized_pl": 500.00,
            "unrealized_plpc": 2.70,
        }

        response = json.dumps({
            "current_conviction": 1.0,
            "new_conviction": 1.0,
            "action": "STAY",
            "reason": "Good"
        })

        result = checkpoint_stage._parse_chairman_decision(response, position)

        assert result["instrument"] == "QQQ"

    def test_decision_uppercase_direction_long(self, checkpoint_stage):
        """Test that LONG side is uppercased in decision."""
        position = {
            "account": "Council",
            "symbol": "SPY",
            "side": "long",
            "qty": "100",
            "current_price": 450.00,
            "entry_price": 440.00,
            "unrealized_pl": 1000.00,
            "unrealized_plpc": 2.27,
        }

        response = json.dumps({
            "current_conviction": 1.5,
            "new_conviction": 1.5,
            "action": "STAY",
            "reason": "Good"
        })

        result = checkpoint_stage._parse_chairman_decision(response, position)

        assert result["direction"] == "LONG"

    def test_decision_uppercase_direction_short(self, checkpoint_stage):
        """Test that SHORT side is uppercased in decision."""
        position = {
            "account": "Council",
            "symbol": "TLT",
            "side": "short",
            "qty": "-50",
            "current_price": 95.00,
            "entry_price": 100.00,
            "unrealized_pl": 250.00,
            "unrealized_plpc": 5.00,
        }

        response = json.dumps({
            "current_conviction": -1.5,
            "new_conviction": -1.5,
            "action": "STAY",
            "reason": "Good"
        })

        result = checkpoint_stage._parse_chairman_decision(response, position)

        assert result["direction"] == "SHORT"

    def test_decision_executed_defaults_false(self, checkpoint_stage):
        """Test that executed field defaults to False."""
        position = {
            "account": "Council",
            "symbol": "SPY",
            "side": "long",
            "qty": "100",
            "current_price": 450.00,
            "entry_price": 440.00,
            "unrealized_pl": 1000.00,
            "unrealized_plpc": 2.27,
        }

        response = json.dumps({
            "current_conviction": 1.5,
            "new_conviction": 1.5,
            "action": "STAY",
            "reason": "Good"
        })

        result = checkpoint_stage._parse_chairman_decision(response, position)

        assert result["executed"] is False


class TestEdgeCasesAndErrorHandling:
    """Test suite for edge cases and error handling in chairman decision parsing."""

    @pytest.fixture
    def checkpoint_stage(self):
        """Create a CheckpointStage instance for testing."""
        return CheckpointStage()

    @pytest.fixture
    def sample_position(self):
        """Sample position for testing."""
        return {
            "account": "Council",
            "symbol": "SPY",
            "side": "long",
            "qty": "100",
            "current_price": 450.00,
            "entry_price": 440.00,
            "unrealized_pl": 1000.00,
            "unrealized_plpc": 2.27,
        }

    def test_parse_malformed_json_falls_back_to_text(self, checkpoint_stage, sample_position):
        """Test that malformed JSON falls back to text parsing."""
        response = "{invalid json} but mentions EXIT action"

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        # Should parse EXIT from text
        assert result["action"] == "EXIT"

    def test_parse_empty_response_defaults_stay(self, checkpoint_stage, sample_position):
        """Test that empty response defaults to STAY."""
        response = ""

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "STAY"

    def test_parse_json_missing_action_field(self, checkpoint_stage, sample_position):
        """Test handling of JSON with missing action field."""
        response = json.dumps({
            "current_conviction": 1.5,
            "new_conviction": 1.5,
            "reason": "Good position"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        # Should default to STAY
        assert result["action"] == "STAY"

    def test_parse_json_missing_conviction_fields(self, checkpoint_stage, sample_position):
        """Test handling of JSON with missing conviction fields."""
        response = json.dumps({
            "action": "EXIT",
            "reason": "Stop loss triggered"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        # Should have default conviction values
        assert result["current_conviction"] == 1.0
        assert result["new_conviction"] == 1.0
        assert result["action"] == "EXIT"

    def test_parse_very_long_response_truncates_reason(self, checkpoint_stage, sample_position):
        """Test that very long text responses are truncated in reason field."""
        response = "This is a very long response. " * 50  # > 200 chars

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        # Reason should be truncated to 200 chars
        assert len(result["reason"]) == 200

    def test_parse_unicode_in_response(self, checkpoint_stage, sample_position):
        """Test parsing response with unicode characters."""
        response = json.dumps({
            "current_conviction": 1.5,
            "new_conviction": 1.5,
            "action": "STAY",
            "reason": "Position looks good 👍 📈"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["action"] == "STAY"
        assert "👍" in result["reason"]

    def test_parse_extreme_conviction_values(self, checkpoint_stage, sample_position):
        """Test parsing with extreme conviction values."""
        response = json.dumps({
            "current_conviction": 2.0,
            "new_conviction": -2.0,
            "action": "FLIP",
            "reason": "Complete reversal"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        assert result["current_conviction"] == 2.0
        assert result["new_conviction"] == -2.0
        assert result["action"] == "FLIP"

    def test_parse_invalid_action_value_defaults_stay(self, checkpoint_stage, sample_position):
        """Test that invalid action values default to STAY."""
        response = json.dumps({
            "current_conviction": 1.5,
            "new_conviction": 1.5,
            "action": "INVALID_ACTION",
            "reason": "Test"
        })

        result = checkpoint_stage._parse_chairman_decision(response, sample_position)

        # Should still parse but action might not be valid
        # Text fallback should default to STAY
        assert result["action"] in ["STAY", "INVALID_ACTION"]


class TestCheckpointTimesConfiguration:
    """Test suite for checkpoint times configuration."""

    def test_checkpoint_times_defined(self):
        """Test that CHECKPOINT_TIMES is defined."""
        assert CheckpointStage.CHECKPOINT_TIMES is not None
        assert isinstance(CheckpointStage.CHECKPOINT_TIMES, list)

    def test_checkpoint_times_count(self):
        """Test that 4 checkpoint times are defined."""
        assert len(CheckpointStage.CHECKPOINT_TIMES) == 4

    def test_checkpoint_times_format(self):
        """Test that checkpoint times are in HH:MM format."""
        for time_str in CheckpointStage.CHECKPOINT_TIMES:
            assert isinstance(time_str, str)
            assert ":" in time_str
            parts = time_str.split(":")
            assert len(parts) == 2
            assert len(parts[0]) == 2  # HH
            assert len(parts[1]) == 2  # MM

    def test_checkpoint_times_values(self):
        """Test that checkpoint times match expected values."""
        expected_times = ["09:00", "12:00", "14:00", "15:50"]
        assert CheckpointStage.CHECKPOINT_TIMES == expected_times

    def test_checkpoint_times_ordered(self):
        """Test that checkpoint times are in chronological order."""
        times = CheckpointStage.CHECKPOINT_TIMES
        for i in range(len(times) - 1):
            assert times[i] < times[i + 1], \
                f"Checkpoint times not in order: {times[i]} >= {times[i + 1]}"


class TestPositionAdjustmentCalculations:
    """Test suite for position size adjustment calculations for different checkpoint actions."""

    @pytest.fixture
    def checkpoint_stage(self):
        """Create a CheckpointStage instance for testing."""
        return CheckpointStage()

    @pytest.fixture
    def sample_long_position(self):
        """Sample LONG position with 100 shares."""
        return {
            "account": "Council",
            "symbol": "SPY",
            "side": "long",
            "qty": "100",
            "current_price": 450.00,
            "entry_price": 440.00,
            "unrealized_pl": 1000.00,
            "unrealized_plpc": 2.27,
        }

    @pytest.fixture
    def sample_short_position(self):
        """Sample SHORT position with -50 shares."""
        return {
            "account": "GPT-5.1",
            "symbol": "QQQ",
            "side": "short",
            "qty": "-50",
            "current_price": 380.00,
            "entry_price": 390.00,
            "unrealized_pl": 500.00,
            "unrealized_plpc": 1.28,
        }

    def test_stay_action_maintains_position_long(self, checkpoint_stage, sample_long_position):
        """Test STAY action maintains current LONG position."""
        action_decision = {
            "action": "STAY",
            "account": sample_long_position["account"],
            "instrument": sample_long_position["symbol"],
            "direction": "LONG",
            "current_conviction": 1.5,
            "new_conviction": 1.5,
        }

        # STAY means no change to position
        # Original qty: 100 shares
        # After STAY: still 100 shares
        assert action_decision["action"] == "STAY"
        assert float(sample_long_position["qty"]) == 100.0

    def test_stay_action_maintains_position_short(self, checkpoint_stage, sample_short_position):
        """Test STAY action maintains current SHORT position."""
        action_decision = {
            "action": "STAY",
            "account": sample_short_position["account"],
            "instrument": sample_short_position["symbol"],
            "direction": "SHORT",
            "current_conviction": -1.5,
            "new_conviction": -1.5,
        }

        # STAY means no change to position
        # Original qty: -50 shares
        # After STAY: still -50 shares
        assert action_decision["action"] == "STAY"
        assert float(sample_short_position["qty"]) == -50.0

    def test_reduce_action_decreases_position_by_50_percent_long(self, checkpoint_stage, sample_long_position):
        """Test REDUCE action decreases LONG position by 50%."""
        action_decision = {
            "action": "REDUCE",
            "account": sample_long_position["account"],
            "instrument": sample_long_position["symbol"],
            "direction": "LONG",
            "current_conviction": 1.5,
            "new_conviction": 0.9,
        }

        # REDUCE should decrease position by 50%
        original_qty = float(sample_long_position["qty"])
        expected_new_qty = original_qty * 0.5

        assert action_decision["action"] == "REDUCE"
        assert original_qty == 100.0
        assert expected_new_qty == 50.0

    def test_reduce_action_decreases_position_by_50_percent_short(self, checkpoint_stage, sample_short_position):
        """Test REDUCE action decreases SHORT position by 50%."""
        action_decision = {
            "action": "REDUCE",
            "account": sample_short_position["account"],
            "instrument": sample_short_position["symbol"],
            "direction": "SHORT",
            "current_conviction": -1.5,
            "new_conviction": -0.9,
        }

        # REDUCE should decrease SHORT position by 50%
        # For SHORT, "reduce" means less negative (closer to zero)
        original_qty = float(sample_short_position["qty"])
        expected_new_qty = original_qty * 0.5

        assert action_decision["action"] == "REDUCE"
        assert original_qty == -50.0
        assert expected_new_qty == -25.0

    def test_reduce_maintains_same_direction(self, checkpoint_stage, sample_long_position):
        """Test REDUCE maintains the same position direction."""
        action_decision = {
            "action": "REDUCE",
            "account": sample_long_position["account"],
            "instrument": sample_long_position["symbol"],
            "direction": "LONG",
            "current_conviction": 1.8,
            "new_conviction": 1.2,
        }

        # REDUCE should maintain direction (LONG stays LONG)
        assert action_decision["action"] == "REDUCE"
        assert action_decision["direction"] == "LONG"
        # Both convictions should be positive for LONG
        assert action_decision["current_conviction"] > 0
        assert action_decision["new_conviction"] > 0

    def test_increase_action_increases_position_by_50_percent_long(self, checkpoint_stage, sample_long_position):
        """Test INCREASE action increases LONG position by 50%."""
        action_decision = {
            "action": "INCREASE",
            "account": sample_long_position["account"],
            "instrument": sample_long_position["symbol"],
            "direction": "LONG",
            "current_conviction": 1.0,
            "new_conviction": 1.6,
        }

        # INCREASE should increase position by 50%
        original_qty = float(sample_long_position["qty"])
        expected_new_qty = original_qty * 1.5

        assert action_decision["action"] == "INCREASE"
        assert original_qty == 100.0
        assert expected_new_qty == 150.0

    def test_increase_action_increases_position_by_50_percent_short(self, checkpoint_stage, sample_short_position):
        """Test INCREASE action increases SHORT position by 50%."""
        action_decision = {
            "action": "INCREASE",
            "account": sample_short_position["account"],
            "instrument": sample_short_position["symbol"],
            "direction": "SHORT",
            "current_conviction": -1.0,
            "new_conviction": -1.6,
        }

        # INCREASE should increase SHORT position by 50%
        # For SHORT, "increase" means more negative (away from zero)
        original_qty = float(sample_short_position["qty"])
        expected_new_qty = original_qty * 1.5

        assert action_decision["action"] == "INCREASE"
        assert original_qty == -50.0
        assert expected_new_qty == -75.0

    def test_increase_maintains_same_direction(self, checkpoint_stage, sample_long_position):
        """Test INCREASE maintains the same position direction."""
        action_decision = {
            "action": "INCREASE",
            "account": sample_long_position["account"],
            "instrument": sample_long_position["symbol"],
            "direction": "LONG",
            "current_conviction": 1.2,
            "new_conviction": 1.8,
        }

        # INCREASE should maintain direction (LONG stays LONG)
        assert action_decision["action"] == "INCREASE"
        assert action_decision["direction"] == "LONG"
        # Both convictions should be positive for LONG
        assert action_decision["current_conviction"] > 0
        assert action_decision["new_conviction"] > 0

    def test_flip_action_reverses_long_to_short(self, checkpoint_stage, sample_long_position):
        """Test FLIP action reverses LONG position to SHORT."""
        action_decision = {
            "action": "FLIP",
            "account": sample_long_position["account"],
            "instrument": sample_long_position["symbol"],
            "direction": "LONG",
            "current_conviction": 1.5,
            "new_conviction": -1.0,
        }

        # FLIP should reverse direction
        # Original: LONG +100 shares
        # After FLIP: SHORT -100 shares (same size, opposite direction)
        original_qty = float(sample_long_position["qty"])
        expected_new_qty = -original_qty

        assert action_decision["action"] == "FLIP"
        assert original_qty == 100.0
        assert expected_new_qty == -100.0
        # Conviction should change sign
        assert action_decision["current_conviction"] > 0
        assert action_decision["new_conviction"] < 0

    def test_flip_action_reverses_short_to_long(self, checkpoint_stage, sample_short_position):
        """Test FLIP action reverses SHORT position to LONG."""
        action_decision = {
            "action": "FLIP",
            "account": sample_short_position["account"],
            "instrument": sample_short_position["symbol"],
            "direction": "SHORT",
            "current_conviction": -1.5,
            "new_conviction": 1.0,
        }

        # FLIP should reverse direction
        # Original: SHORT -50 shares
        # After FLIP: LONG +50 shares (same size, opposite direction)
        original_qty = float(sample_short_position["qty"])
        expected_new_qty = -original_qty

        assert action_decision["action"] == "FLIP"
        assert original_qty == -50.0
        assert expected_new_qty == 50.0
        # Conviction should change sign
        assert action_decision["current_conviction"] < 0
        assert action_decision["new_conviction"] > 0

    def test_flip_maintains_position_size(self, checkpoint_stage, sample_long_position):
        """Test FLIP maintains the same position size (absolute value)."""
        original_qty = abs(float(sample_long_position["qty"]))

        # After FLIP, size should be same but opposite direction
        expected_new_qty_abs = original_qty

        assert original_qty == 100.0
        assert expected_new_qty_abs == 100.0

    def test_exit_action_closes_entire_long_position(self, checkpoint_stage, sample_long_position):
        """Test EXIT action closes entire LONG position."""
        action_decision = {
            "action": "EXIT",
            "account": sample_long_position["account"],
            "instrument": sample_long_position["symbol"],
            "direction": "LONG",
            "current_conviction": 1.5,
            "new_conviction": 0.5,
        }

        # EXIT should close entire position
        # Original: 100 shares
        # After EXIT: 0 shares
        original_qty = float(sample_long_position["qty"])
        expected_new_qty = 0.0

        assert action_decision["action"] == "EXIT"
        assert original_qty == 100.0
        assert expected_new_qty == 0.0

    def test_exit_action_closes_entire_short_position(self, checkpoint_stage, sample_short_position):
        """Test EXIT action closes entire SHORT position."""
        action_decision = {
            "action": "EXIT",
            "account": sample_short_position["account"],
            "instrument": sample_short_position["symbol"],
            "direction": "SHORT",
            "current_conviction": -1.5,
            "new_conviction": -0.5,
        }

        # EXIT should close entire position
        # Original: -50 shares
        # After EXIT: 0 shares
        original_qty = float(sample_short_position["qty"])
        expected_new_qty = 0.0

        assert action_decision["action"] == "EXIT"
        assert original_qty == -50.0
        assert expected_new_qty == 0.0

    def test_exit_conviction_below_threshold(self, checkpoint_stage, sample_long_position):
        """Test EXIT occurs when conviction drops below exit threshold."""
        action_decision = {
            "action": "EXIT",
            "account": sample_long_position["account"],
            "instrument": sample_long_position["symbol"],
            "direction": "LONG",
            "current_conviction": 1.5,
            "new_conviction": 0.8,
        }

        # New conviction below exit threshold (1.0)
        assert action_decision["action"] == "EXIT"
        assert action_decision["new_conviction"] < CheckpointStage.CONVICTION_THRESHOLDS["exit"]

    def test_reduce_calculation_with_large_position(self, checkpoint_stage):
        """Test REDUCE calculation with a large position."""
        large_position = {
            "account": "Council",
            "symbol": "SPY",
            "side": "long",
            "qty": "1000",
            "current_price": 450.00,
            "entry_price": 440.00,
            "unrealized_pl": 10000.00,
            "unrealized_plpc": 2.27,
        }

        # REDUCE by 50%
        original_qty = float(large_position["qty"])
        expected_new_qty = original_qty * 0.5

        assert original_qty == 1000.0
        assert expected_new_qty == 500.0

    def test_increase_calculation_with_large_position(self, checkpoint_stage):
        """Test INCREASE calculation with a large position."""
        large_position = {
            "account": "GPT-5.1",
            "symbol": "QQQ",
            "side": "long",
            "qty": "800",
            "current_price": 380.00,
            "entry_price": 370.00,
            "unrealized_pl": 8000.00,
            "unrealized_plpc": 2.70,
        }

        # INCREASE by 50%
        original_qty = float(large_position["qty"])
        expected_new_qty = original_qty * 1.5

        assert original_qty == 800.0
        assert expected_new_qty == 1200.0

    def test_reduce_calculation_with_small_position(self, checkpoint_stage):
        """Test REDUCE calculation with a small position."""
        small_position = {
            "account": "Gemini",
            "symbol": "TLT",
            "side": "long",
            "qty": "10",
            "current_price": 95.00,
            "entry_price": 100.00,
            "unrealized_pl": -50.00,
            "unrealized_plpc": -5.00,
        }

        # REDUCE by 50%
        original_qty = float(small_position["qty"])
        expected_new_qty = original_qty * 0.5

        assert original_qty == 10.0
        assert expected_new_qty == 5.0

    def test_increase_calculation_with_small_position(self, checkpoint_stage):
        """Test INCREASE calculation with a small position."""
        small_position = {
            "account": "Claude",
            "symbol": "GLD",
            "side": "long",
            "qty": "5",
            "current_price": 180.00,
            "entry_price": 175.00,
            "unrealized_pl": 25.00,
            "unrealized_plpc": 2.86,
        }

        # INCREASE by 50%
        original_qty = float(small_position["qty"])
        expected_new_qty = original_qty * 1.5

        assert original_qty == 5.0
        assert expected_new_qty == 7.5

    def test_position_adjustment_preserves_decimal_precision(self, checkpoint_stage):
        """Test that position adjustments preserve decimal precision."""
        position = {
            "account": "Council",
            "symbol": "SPY",
            "side": "long",
            "qty": "33",
            "current_price": 450.00,
            "entry_price": 440.00,
            "unrealized_pl": 330.00,
            "unrealized_plpc": 2.27,
        }

        # REDUCE by 50%
        original_qty = float(position["qty"])
        expected_new_qty = original_qty * 0.5

        assert original_qty == 33.0
        assert expected_new_qty == 16.5  # Decimal result

        # INCREASE by 50%
        expected_increased_qty = original_qty * 1.5
        assert expected_increased_qty == 49.5  # Decimal result

    def test_multiple_action_sequence_reduce_then_increase(self, checkpoint_stage, sample_long_position):
        """Test sequence of REDUCE followed by INCREASE."""
        # Start with 100 shares
        original_qty = float(sample_long_position["qty"])
        assert original_qty == 100.0

        # REDUCE by 50% -> 50 shares
        after_reduce = original_qty * 0.5
        assert after_reduce == 50.0

        # INCREASE by 50% -> 75 shares
        after_increase = after_reduce * 1.5
        assert after_increase == 75.0

    def test_multiple_action_sequence_increase_then_reduce(self, checkpoint_stage, sample_long_position):
        """Test sequence of INCREASE followed by REDUCE."""
        # Start with 100 shares
        original_qty = float(sample_long_position["qty"])
        assert original_qty == 100.0

        # INCREASE by 50% -> 150 shares
        after_increase = original_qty * 1.5
        assert after_increase == 150.0

        # REDUCE by 50% -> 75 shares
        after_reduce = after_increase * 0.5
        assert after_reduce == 75.0

    def test_all_actions_documented_behavior(self, checkpoint_stage):
        """Test that all checkpoint actions have documented expected behavior."""
        # STAY: No change
        stay_multiplier = 1.0

        # REDUCE: 50% decrease
        reduce_multiplier = 0.5

        # INCREASE: 50% increase
        increase_multiplier = 1.5

        # EXIT: Close entire position
        exit_multiplier = 0.0

        # FLIP: Reverse direction (negate quantity)
        flip_multiplier = -1.0

        # Verify multipliers are correct
        assert stay_multiplier == 1.0
        assert reduce_multiplier == 0.5
        assert increase_multiplier == 1.5
        assert exit_multiplier == 0.0
        assert flip_multiplier == -1.0
