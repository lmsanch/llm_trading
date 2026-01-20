"""Test complete PM pitch schema validation with all required fields.

This module tests the complete pitch schema validation logic including:
- All required fields for LONG/SHORT/FLAT trades
- Field type validation
- Field format validation
- Risk profile and exit policy validation
- Direction-conviction consistency
- Complete valid pitch examples
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.pipeline.stages.pm_pitch import (
    PMPitchStage,
    RISK_PROFILES,
    ENTRY_MODES,
    EXIT_EVENTS,
    IndicatorError,
)
from tests.fixtures.sample_pitches import (
    get_valid_long_pitch,
    get_valid_short_pitch,
    get_valid_flat_pitch,
)


# Mock REQUESTY_MODELS for testing
MOCK_REQUESTY_MODELS = {
    "test_model": {
        "model_id": "test/test-model",
        "account": "TEST_ACCOUNT",
        "alpaca_id": "TEST123",
        "role": "portfolio_manager",
    }
}


class TestPitchSchemaValidation:
    """Test suite for complete pitch schema validation."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.stage = PMPitchStage()

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_valid_long_pitch_all_required_fields(self):
        """Test valid LONG pitch with all required fields passes validation."""
        pitch = get_valid_long_pitch()

        # Convert to v2 schema format expected by _parse_pm_pitch
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Serialize to JSON string to simulate LLM response
        import json
        pitch_json = json.dumps(v2_pitch)

        # Parse and validate
        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        # Assertions
        assert result is not None
        assert result["direction"] == "LONG"
        assert result["selected_instrument"] in self.stage.INSTRUMENTS
        assert result["conviction"] > 0
        assert result["risk_profile"] in ["TIGHT", "BASE", "WIDE"]
        assert "exit_policy" in result
        assert result["model"] == "test_model"

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_valid_short_pitch_all_required_fields(self):
        """Test valid SHORT pitch with all required fields passes validation."""
        # Create pitch directly to avoid banned keywords in fixtures
        v2_pitch = self._create_test_pitch(direction="SHORT", conviction=-1.5)

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        assert result is not None
        assert result["direction"] == "SHORT"
        assert result["conviction"] < 0
        assert result["risk_profile"] in ["TIGHT", "BASE", "WIDE"]
        assert "exit_policy" in result

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_valid_flat_pitch_all_required_fields(self):
        """Test valid FLAT pitch with all required fields passes validation."""
        v2_pitch = self._create_test_pitch(direction="FLAT", conviction=0.0)

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        assert result is not None
        assert result["direction"] == "FLAT"
        assert result["conviction"] == 0
        assert result["selected_instrument"] == "FLAT"
        assert result.get("risk_profile") in [None, "NONE"]
        assert result.get("exit_policy") in [None, {}]

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_missing_required_field_week_id(self):
        """Test pitch missing week_id is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Remove required field
        del v2_pitch["week_id"]

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_missing_required_field_direction(self):
        """Test pitch missing direction is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Remove required field
        del v2_pitch["direction"]

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_missing_required_field_conviction(self):
        """Test pitch missing conviction is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Remove required field
        del v2_pitch["conviction"]

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_missing_required_field_thesis_bullets(self):
        """Test pitch missing thesis_bullets is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Remove required field
        del v2_pitch["thesis_bullets"]

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_missing_required_field_entry_policy(self):
        """Test pitch missing entry_policy is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Remove required field
        del v2_pitch["entry_policy"]

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_missing_risk_profile_for_long(self):
        """Test LONG pitch missing risk_profile is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Remove risk_profile (required for LONG/SHORT)
        del v2_pitch["risk_profile"]

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_missing_exit_policy_for_short(self):
        """Test SHORT pitch missing exit_policy is rejected."""
        v2_pitch = self._create_test_pitch(direction="SHORT", conviction=-1.5)

        # Remove exit_policy (required for LONG/SHORT)
        del v2_pitch["exit_policy"]

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_invalid_direction(self):
        """Test pitch with invalid direction is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Set invalid direction
        v2_pitch["direction"] = "SIDEWAYS"

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_invalid_conviction_type(self):
        """Test pitch with invalid conviction type is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Set invalid conviction type
        v2_pitch["conviction"] = "high"

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_invalid_conviction_out_of_range_high(self):
        """Test pitch with conviction > 2 is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Set out-of-range conviction
        v2_pitch["conviction"] = 3.0

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_invalid_conviction_out_of_range_low(self):
        """Test pitch with conviction < -2 is rejected."""
        v2_pitch = self._create_test_pitch(direction="SHORT", conviction=-3.0)

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_flat_with_nonzero_conviction(self):
        """Test FLAT pitch with non-zero conviction is rejected."""
        pitch = get_valid_flat_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="FLAT")

        # Set invalid conviction for FLAT
        v2_pitch["conviction"] = 1.0

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_long_with_negative_conviction(self):
        """Test LONG pitch with negative conviction is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Set invalid conviction for LONG
        v2_pitch["conviction"] = -1.0

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_short_with_positive_conviction(self):
        """Test SHORT pitch with positive conviction is rejected."""
        v2_pitch = self._create_test_pitch(direction="SHORT", conviction=1.0)

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_invalid_risk_profile(self):
        """Test pitch with invalid risk_profile is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Set invalid risk_profile
        v2_pitch["risk_profile"] = "EXTREME"

        import json
        pitch_json = json.dumps(v2_pitch)

        with pytest.raises(ValueError, match="Invalid risk_profile"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_flat_with_risk_profile(self):
        """Test FLAT pitch with risk_profile is rejected."""
        pitch = get_valid_flat_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="FLAT")

        # Add risk_profile to FLAT (not allowed)
        v2_pitch["risk_profile"] = "BASE"

        import json
        pitch_json = json.dumps(v2_pitch)

        with pytest.raises(ValueError, match="FLAT trades must not have risk_profile"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_flat_with_exit_policy(self):
        """Test FLAT pitch with exit_policy is rejected."""
        pitch = get_valid_flat_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="FLAT")

        # Add exit_policy to FLAT (not allowed)
        v2_pitch["exit_policy"] = {
            "time_stop_days": 7,
            "stop_loss_pct": 0.015,
            "take_profit_pct": 0.025
        }

        import json
        pitch_json = json.dumps(v2_pitch)

        with pytest.raises(ValueError, match="FLAT trades must not have exit_policy"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_entry_policy_missing_mode(self):
        """Test pitch with entry_policy missing mode is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Remove mode from entry_policy
        v2_pitch["entry_policy"] = {}

        import json
        pitch_json = json.dumps(v2_pitch)

        with pytest.raises(ValueError, match="entry_policy missing required field: mode"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_invalid_entry_mode_for_long(self):
        """Test LONG pitch with invalid entry mode is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Set invalid entry mode
        v2_pitch["entry_policy"]["mode"] = "market"

        import json
        pitch_json = json.dumps(v2_pitch)

        with pytest.raises(ValueError, match="Invalid entry_policy.mode"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_flat_with_non_none_entry_mode(self):
        """Test FLAT pitch with entry mode other than NONE is rejected."""
        pitch = get_valid_flat_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="FLAT")

        # Set invalid entry mode for FLAT
        v2_pitch["entry_policy"]["mode"] = "limit"

        import json
        pitch_json = json.dumps(v2_pitch)

        with pytest.raises(ValueError, match="FLAT trades must have entry_policy.mode='NONE'"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_exit_policy_missing_time_stop_days(self):
        """Test pitch with exit_policy missing time_stop_days is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Remove time_stop_days
        del v2_pitch["exit_policy"]["time_stop_days"]

        import json
        pitch_json = json.dumps(v2_pitch)

        with pytest.raises(ValueError, match="exit_policy missing required field: time_stop_days"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_exit_policy_missing_stop_loss_pct(self):
        """Test pitch with exit_policy missing stop_loss_pct is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Remove stop_loss_pct
        del v2_pitch["exit_policy"]["stop_loss_pct"]

        import json
        pitch_json = json.dumps(v2_pitch)

        with pytest.raises(ValueError, match="exit_policy missing required field: stop_loss_pct"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_stop_loss_does_not_match_risk_profile(self):
        """Test pitch with stop_loss_pct not matching risk_profile is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Set risk_profile to BASE but use TIGHT stop_loss
        v2_pitch["risk_profile"] = "BASE"
        v2_pitch["exit_policy"]["stop_loss_pct"] = 0.010  # TIGHT value

        import json
        pitch_json = json.dumps(v2_pitch)

        with pytest.raises(ValueError, match="stop_loss_pct.*does not match.*risk_profile"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_take_profit_does_not_match_risk_profile(self):
        """Test pitch with take_profit_pct not matching risk_profile is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Set risk_profile to BASE but use WIDE take_profit
        v2_pitch["risk_profile"] = "BASE"
        v2_pitch["exit_policy"]["take_profit_pct"] = 0.035  # WIDE value

        import json
        pitch_json = json.dumps(v2_pitch)

        with pytest.raises(ValueError, match="take_profit_pct.*does not match.*risk_profile"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_invalid_instrument(self):
        """Test pitch with invalid instrument is rejected."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        # Set invalid instrument
        v2_pitch["selected_instrument"] = "INVALID"

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_all_valid_instruments(self):
        """Test pitch with each valid instrument is accepted."""
        for instrument in self.stage.INSTRUMENTS:
            pitch = get_valid_long_pitch(instrument=instrument)
            v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

            import json
            pitch_json = json.dumps(v2_pitch)

            result = self.stage._parse_pm_pitch(pitch_json, "test_model")
            assert result is not None
            assert result["selected_instrument"] == instrument

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_all_risk_profiles(self):
        """Test pitch with each risk profile is accepted and validated correctly."""
        for risk_profile in ["TIGHT", "BASE", "WIDE"]:
            pitch = get_valid_long_pitch()
            v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

            # Set risk profile and matching stop/take profit
            v2_pitch["risk_profile"] = risk_profile
            v2_pitch["exit_policy"]["stop_loss_pct"] = RISK_PROFILES[risk_profile]["stop_loss_pct"]
            v2_pitch["exit_policy"]["take_profit_pct"] = RISK_PROFILES[risk_profile]["take_profit_pct"]

            import json
            pitch_json = json.dumps(v2_pitch)

            result = self.stage._parse_pm_pitch(pitch_json, "test_model")
            assert result is not None
            assert result["risk_profile"] == risk_profile

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_conviction_boundary_values(self):
        """Test pitch with boundary conviction values is accepted."""
        # Test max positive conviction
        v2_pitch = self._create_test_pitch(direction="LONG", conviction=2.0)

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is not None
        assert result["conviction"] == 2.0

        # Test max negative conviction
        v2_pitch = self._create_test_pitch(direction="SHORT", conviction=-2.0)
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is not None
        assert result["conviction"] == -2.0

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_complete_pitch_structure(self):
        """Test that parsed pitch contains all expected fields."""
        pitch = get_valid_long_pitch()
        v2_pitch = self._convert_to_v2_schema(pitch, direction="LONG")

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        # Verify all required fields are present
        required_fields = [
            "week_id",
            "asof_et",
            "pm_model",
            "selected_instrument",
            "direction",
            "conviction",
            "horizon",
            "thesis_bullets",
            "entry_policy",
            "risk_notes",
            "risk_profile",
            "exit_policy",
            "model",
            "model_info",
            "timestamp"
        ]

        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_no_json_in_response(self):
        """Test that response with no JSON is rejected."""
        result = self.stage._parse_pm_pitch("This is just text without JSON", "test_model")
        assert result is None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_malformed_json(self):
        """Test that malformed JSON is rejected."""
        malformed_json = '{"direction": "LONG", "conviction": 1.5'  # Missing closing brace
        result = self.stage._parse_pm_pitch(malformed_json, "test_model")
        assert result is None

    # Helper methods

    def _create_test_pitch(self, direction: str, conviction: float, instrument: str = "SPY", risk_profile: str = "BASE") -> dict:
        """Create a test pitch without banned keywords.

        Args:
            direction: Trade direction (LONG, SHORT, FLAT)
            conviction: Conviction value
            instrument: Trading instrument
            risk_profile: Risk profile (TIGHT, BASE, WIDE)

        Returns:
            v2 schema formatted pitch
        """
        from datetime import datetime, timezone, timedelta
        import uuid

        et_tz = timezone(timedelta(hours=-5))
        asof_et = datetime.now(et_tz).isoformat()

        v2_pitch = {
            "idea_id": str(uuid.uuid4()),
            "week_id": "2026-01-19",
            "asof_et": asof_et,
            "pm_model": "test_model",
            "selected_instrument": "FLAT" if direction == "FLAT" else instrument,
            "direction": direction,
            "horizon": "1W",
            "conviction": conviction,
            "thesis_bullets": [
                "Rates: Fed policy shift expected",
                "Policy: Central bank action likely",
                "Growth: Economic data shows strength"
            ],
            "entry_policy": {
                "mode": "NONE" if direction == "FLAT" else "limit",
                "limit_price": 450.0 if direction != "FLAT" else None,
            },
            "risk_notes": "Exit if support breaks",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Add risk_profile and exit_policy for LONG/SHORT
        if direction != "FLAT":
            v2_pitch["risk_profile"] = risk_profile
            v2_pitch["exit_policy"] = {
                "time_stop_days": 7,
                "stop_loss_pct": RISK_PROFILES[risk_profile]["stop_loss_pct"],
                "take_profit_pct": RISK_PROFILES[risk_profile]["take_profit_pct"],
                "exit_before_events": ["NFP"]
            }
        else:
            v2_pitch["risk_profile"] = None
            v2_pitch["exit_policy"] = None

        return v2_pitch

    def _convert_to_v2_schema(self, pitch: dict, direction: str) -> dict:
        """Convert sample pitch to v2 schema format.

        Args:
            pitch: Sample pitch from fixtures
            direction: Trade direction (LONG, SHORT, FLAT)

        Returns:
            v2 schema formatted pitch
        """
        from datetime import datetime, timezone, timedelta
        import uuid

        et_tz = timezone(timedelta(hours=-5))
        asof_et = datetime.now(et_tz).isoformat()

        v2_pitch = {
            "idea_id": pitch.get("idea_id", str(uuid.uuid4())),
            "week_id": pitch.get("week_id"),
            "asof_et": asof_et,
            "pm_model": pitch.get("model", "test_model"),
            "selected_instrument": pitch.get("instrument"),
            "direction": direction,
            "horizon": pitch.get("horizon", "1W"),
            "conviction": pitch.get("conviction"),
            "thesis_bullets": pitch.get("thesis_bullets", []),
            "entry_policy": {
                "mode": pitch.get("entry_mode", "limit").lower() if direction != "FLAT" else "NONE",
                "limit_price": pitch.get("entry_price"),
            },
            "risk_notes": pitch.get("invalidation", "Risk notes"),
            "timestamp": pitch.get("timestamp", datetime.utcnow().isoformat()),
        }

        # Add risk_profile and exit_policy for LONG/SHORT
        if direction != "FLAT":
            risk_profile = pitch.get("risk_profile", "BASE")
            v2_pitch["risk_profile"] = risk_profile
            v2_pitch["exit_policy"] = {
                "time_stop_days": 7,
                "stop_loss_pct": RISK_PROFILES[risk_profile]["stop_loss_pct"],
                "take_profit_pct": RISK_PROFILES[risk_profile]["take_profit_pct"],
                "exit_before_events": [pitch.get("exit_event", "NFP")] if pitch.get("exit_event") else []
            }
        else:
            v2_pitch["risk_profile"] = None
            v2_pitch["exit_policy"] = None

        return v2_pitch


class TestPitchSchemaEdgeCases:
    """Test suite for edge cases in pitch schema validation."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.stage = PMPitchStage()

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_json_with_trailing_commas(self):
        """Test that JSON with trailing commas is repaired and parsed."""
        pitch = get_valid_long_pitch()
        v2_pitch = TestPitchSchemaValidation()._convert_to_v2_schema(pitch, direction="LONG")

        import json
        pitch_json = json.dumps(v2_pitch)

        # Add trailing commas
        pitch_json_with_commas = pitch_json.replace('"1W"', '"1W",')

        result = self.stage._parse_pm_pitch(pitch_json_with_commas, "test_model")
        assert result is not None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_json_with_comments(self):
        """Test that JSON with comments is repaired and parsed."""
        v2_pitch = TestPitchSchemaValidation()._create_test_pitch(direction="LONG", conviction=1.5)

        import json
        pitch_json = json.dumps(v2_pitch, indent=2)

        # Add comments on separate lines
        pitch_json_with_comments = pitch_json.replace(
            '"direction": "LONG"',
            '"direction": "LONG" // Trade direction\n'
        )

        result = self.stage._parse_pm_pitch(pitch_json_with_comments, "test_model")
        assert result is not None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_empty_thesis_bullets(self):
        """Test pitch with empty thesis_bullets array."""
        pitch = get_valid_long_pitch()
        v2_pitch = TestPitchSchemaValidation()._convert_to_v2_schema(pitch, direction="LONG")

        # Empty thesis bullets (still present, just empty)
        v2_pitch["thesis_bullets"] = []

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is not None
        assert result["thesis_bullets"] == []

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_very_long_pitch(self):
        """Test pitch with very long content is handled."""
        pitch = get_valid_long_pitch()
        v2_pitch = TestPitchSchemaValidation()._convert_to_v2_schema(pitch, direction="LONG")

        # Add very long thesis bullets
        v2_pitch["thesis_bullets"] = ["Policy: " + "x" * 10000 for _ in range(10)]

        import json
        pitch_json = json.dumps(v2_pitch)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is not None

    @patch("backend.pipeline.stages.pm_pitch.REQUESTY_MODELS", MOCK_REQUESTY_MODELS)
    def test_unicode_in_thesis_bullets(self):
        """Test pitch with unicode characters in thesis bullets."""
        pitch = get_valid_long_pitch()
        v2_pitch = TestPitchSchemaValidation()._convert_to_v2_schema(pitch, direction="LONG")

        # Add unicode characters
        v2_pitch["thesis_bullets"] = [
            "Rates: 中国经济增长放缓",
            "Policy: Événements géopolitiques en Europe",
            "Growth: Потенциал роста в развивающихся странах"
        ]

        import json
        pitch_json = json.dumps(v2_pitch, ensure_ascii=False)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is not None
