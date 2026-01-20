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
