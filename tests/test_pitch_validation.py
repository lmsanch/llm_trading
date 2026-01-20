"""Test PM pitch validation logic focusing on risk profiles.

This module tests risk profile constants, validation logic, and business rules
for pitch validation including:
- RISK_PROFILES constants correctness
- Risk profile validation (TIGHT, BASE, WIDE)
- Stop loss and take profit percentage validation
- Risk profile consistency checks
"""

import pytest
from unittest.mock import patch
from backend.pipeline.stages.pm_pitch import (
    RISK_PROFILES,
    PMPitchStage,
    IndicatorError,
    ENTRY_MODES,
    EXIT_EVENTS,
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


class TestRiskProfileConstants:
    """Test suite for RISK_PROFILES constant definitions."""

    def test_risk_profiles_exist(self):
        """Test that all three risk profiles are defined."""
        assert "TIGHT" in RISK_PROFILES
        assert "BASE" in RISK_PROFILES
        assert "WIDE" in RISK_PROFILES

    def test_risk_profiles_count(self):
        """Test that exactly three risk profiles are defined."""
        assert len(RISK_PROFILES) == 3

    def test_tight_profile_values(self):
        """Test TIGHT risk profile has correct stop loss and take profit percentages."""
        tight = RISK_PROFILES["TIGHT"]
        assert tight["stop_loss_pct"] == 0.010  # 1.0%
        assert tight["take_profit_pct"] == 0.015  # 1.5%

    def test_base_profile_values(self):
        """Test BASE risk profile has correct stop loss and take profit percentages."""
        base = RISK_PROFILES["BASE"]
        assert base["stop_loss_pct"] == 0.015  # 1.5%
        assert base["take_profit_pct"] == 0.025  # 2.5%

    def test_wide_profile_values(self):
        """Test WIDE risk profile has correct stop loss and take profit percentages."""
        wide = RISK_PROFILES["WIDE"]
        assert wide["stop_loss_pct"] == 0.020  # 2.0%
        assert wide["take_profit_pct"] == 0.035  # 3.5%

    def test_risk_profile_structure(self):
        """Test that each risk profile has required fields."""
        for profile_name, profile in RISK_PROFILES.items():
            assert "stop_loss_pct" in profile, f"{profile_name} missing stop_loss_pct"
            assert "take_profit_pct" in profile, f"{profile_name} missing take_profit_pct"

    def test_risk_profile_types(self):
        """Test that risk profile values are numeric."""
        for profile_name, profile in RISK_PROFILES.items():
            assert isinstance(profile["stop_loss_pct"], (int, float)), \
                f"{profile_name} stop_loss_pct is not numeric"
            assert isinstance(profile["take_profit_pct"], (int, float)), \
                f"{profile_name} take_profit_pct is not numeric"

    def test_risk_profile_positive_values(self):
        """Test that all risk profile percentages are positive."""
        for profile_name, profile in RISK_PROFILES.items():
            assert profile["stop_loss_pct"] > 0, \
                f"{profile_name} stop_loss_pct must be positive"
            assert profile["take_profit_pct"] > 0, \
                f"{profile_name} take_profit_pct must be positive"

    def test_take_profit_greater_than_stop_loss(self):
        """Test that take profit is greater than stop loss for each profile."""
        for profile_name, profile in RISK_PROFILES.items():
            assert profile["take_profit_pct"] > profile["stop_loss_pct"], \
                f"{profile_name} take_profit must be greater than stop_loss"

    def test_risk_profiles_ordered_correctly(self):
        """Test that risk profiles are ordered from TIGHT to WIDE."""
        tight_stop = RISK_PROFILES["TIGHT"]["stop_loss_pct"]
        base_stop = RISK_PROFILES["BASE"]["stop_loss_pct"]
        wide_stop = RISK_PROFILES["WIDE"]["stop_loss_pct"]

        assert tight_stop < base_stop < wide_stop, \
            "Risk profiles should be ordered: TIGHT < BASE < WIDE"

        tight_tp = RISK_PROFILES["TIGHT"]["take_profit_pct"]
        base_tp = RISK_PROFILES["BASE"]["take_profit_pct"]
        wide_tp = RISK_PROFILES["WIDE"]["take_profit_pct"]

        assert tight_tp < base_tp < wide_tp, \
            "Take profit should be ordered: TIGHT < BASE < WIDE"

    def test_risk_profiles_reasonable_ranges(self):
        """Test that risk profile percentages are within reasonable ranges (0-10%)."""
        for profile_name, profile in RISK_PROFILES.items():
            assert 0 < profile["stop_loss_pct"] <= 0.10, \
                f"{profile_name} stop_loss_pct should be between 0% and 10%"
            assert 0 < profile["take_profit_pct"] <= 0.10, \
                f"{profile_name} take_profit_pct should be between 0% and 10%"


class TestRiskProfileValidation:
    """Test suite for risk profile validation logic in PMPitchStage._parse_pm_pitch."""

    def setup_method(self):
        """Set up test fixtures."""
        self.stage = PMPitchStage()

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_valid_tight_risk_profile(self):
        """Test that TIGHT risk profile is accepted."""
        pitch_json = self._create_valid_pitch_json(
            risk_profile="TIGHT",
            stop_loss_pct=0.010,
            take_profit_pct=0.015
        )

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        assert result is not None
        assert result["risk_profile"] == "TIGHT"

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_valid_base_risk_profile(self):
        """Test that BASE risk profile is accepted."""
        pitch_json = self._create_valid_pitch_json(
            risk_profile="BASE",
            stop_loss_pct=0.015,
            take_profit_pct=0.025
        )

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        assert result is not None
        assert result["risk_profile"] == "BASE"

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_valid_wide_risk_profile(self):
        """Test that WIDE risk profile is accepted."""
        pitch_json = self._create_valid_pitch_json(
            risk_profile="WIDE",
            stop_loss_pct=0.020,
            take_profit_pct=0.035
        )

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        assert result is not None
        assert result["risk_profile"] == "WIDE"

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_invalid_risk_profile_name(self):
        """Test that invalid risk profile names are rejected."""
        pitch_json = self._create_valid_pitch_json(
            risk_profile="CUSTOM",
            stop_loss_pct=0.015,
            take_profit_pct=0.025
        )

        with pytest.raises(ValueError, match="Invalid risk_profile"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_risk_profile_case_sensitive(self):
        """Test that risk profile names are case-sensitive (must be uppercase)."""
        pitch_json = self._create_valid_pitch_json(
            risk_profile="tight",  # lowercase should fail
            stop_loss_pct=0.010,
            take_profit_pct=0.015
        )

        with pytest.raises(ValueError, match=r"Invalid risk_profile"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_stop_loss_mismatch_rejected(self):
        """Test that mismatched stop loss percentage is rejected."""
        pitch_json = self._create_valid_pitch_json(
            risk_profile="BASE",
            stop_loss_pct=0.020,  # Wrong: BASE should be 0.015
            take_profit_pct=0.025
        )

        with pytest.raises(ValueError, match=r"stop_loss_pct .* does not match"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_take_profit_mismatch_rejected(self):
        """Test that mismatched take profit percentage is rejected."""
        pitch_json = self._create_valid_pitch_json(
            risk_profile="TIGHT",
            stop_loss_pct=0.010,
            take_profit_pct=0.025  # Wrong: TIGHT should be 0.015
        )

        with pytest.raises(ValueError, match=r"take_profit_pct .* does not match"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_both_percentages_mismatch_rejected(self):
        """Test that both percentages mismatched is rejected."""
        pitch_json = self._create_valid_pitch_json(
            risk_profile="WIDE",
            stop_loss_pct=0.010,  # Wrong: should be 0.020
            take_profit_pct=0.015  # Wrong: should be 0.035
        )

        with pytest.raises(ValueError, match=r"stop_loss_pct .* does not match"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_flat_trade_no_risk_profile(self):
        """Test that FLAT trades should not have risk profiles."""
        pitch_json = self._create_flat_pitch_json(risk_profile=None)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        assert result is not None
        assert result["direction"] == "FLAT"
        # FLAT trades should have None or no risk_profile

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_flat_trade_with_risk_profile_rejected(self):
        """Test that FLAT trades with risk profiles are rejected."""
        pitch_json = self._create_flat_pitch_json(risk_profile="BASE")

        with pytest.raises(ValueError, match=r"FLAT trades must not have risk_profile"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_risk_profile_none_for_flat(self):
        """Test that risk_profile=None is accepted for FLAT trades."""
        pitch_json = self._create_flat_pitch_json(risk_profile=None)

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        assert result is not None

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_missing_risk_profile_for_long_rejected(self):
        """Test that LONG trades without risk_profile are rejected."""
        pitch_json = self._create_valid_pitch_json(
            risk_profile=None,  # Missing!
            stop_loss_pct=0.015,
            take_profit_pct=0.025
        )

        with pytest.raises(ValueError, match=r"Invalid risk_profile"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_missing_risk_profile_for_short_rejected(self):
        """Test that SHORT trades without risk_profile are rejected."""
        pitch_json = self._create_valid_pitch_json(
            risk_profile=None,  # Missing!
            stop_loss_pct=0.015,
            take_profit_pct=0.025,
            direction="SHORT",
            conviction=-1.5
        )

        with pytest.raises(ValueError, match=r"Invalid risk_profile"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_stop_loss_percentage_tolerance(self):
        """Test that small floating point differences are tolerated."""
        pitch_json = self._create_valid_pitch_json(
            risk_profile="BASE",
            stop_loss_pct=0.0150001,  # Very close to 0.015
            take_profit_pct=0.025
        )

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        # Should be accepted due to tolerance of 0.0001
        assert result is not None

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_take_profit_percentage_tolerance(self):
        """Test that small floating point differences are tolerated."""
        pitch_json = self._create_valid_pitch_json(
            risk_profile="WIDE",
            stop_loss_pct=0.020,
            take_profit_pct=0.0349999  # Very close to 0.035
        )

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        # Should be accepted due to tolerance of 0.0001
        assert result is not None

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_zero_stop_loss_rejected(self):
        """Test that zero stop loss is rejected."""
        pitch_json = self._create_valid_pitch_json(
            risk_profile="BASE",
            stop_loss_pct=0.0,  # Invalid!
            take_profit_pct=0.025
        )

        with pytest.raises(ValueError, match=r"stop_loss_pct .* does not match"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_negative_stop_loss_rejected(self):
        """Test that negative stop loss is rejected."""
        pitch_json = self._create_valid_pitch_json(
            risk_profile="BASE",
            stop_loss_pct=-0.015,  # Invalid!
            take_profit_pct=0.025
        )

        with pytest.raises(ValueError, match=r"stop_loss_pct .* does not match"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_missing_exit_policy_for_long_rejected(self):
        """Test that LONG trades without exit_policy are rejected."""
        pitch_json = """
        {
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "SPY",
            "direction": "LONG",
            "horizon": "1W",
            "conviction": 1.5,
            "risk_profile": "BASE",
            "thesis_bullets": ["Rates: Fed supportive", "Growth: Strong data"],
            "entry_policy": {"mode": "limit", "limit_price": null},
            "risk_notes": "Monitor Fed signals",
            "timestamp": "2025-01-20T16:00:00Z"
        }
        """

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        # Should be rejected because exit_policy is required for LONG/SHORT
        assert result is None

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_flat_trade_with_exit_policy_rejected(self):
        """Test that FLAT trades with exit_policy are rejected."""
        pitch_json = """
        {
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "FLAT",
            "direction": "FLAT",
            "horizon": "1W",
            "conviction": 0,
            "risk_profile": null,
            "thesis_bullets": ["Policy: Insufficient clarity"],
            "entry_policy": {"mode": "NONE", "limit_price": null},
            "exit_policy": {
                "time_stop_days": 7,
                "stop_loss_pct": 0.015,
                "take_profit_pct": 0.025
            },
            "risk_notes": "Neutral positioning",
            "timestamp": "2025-01-20T16:00:00Z"
        }
        """

        # Should be rejected because FLAT trades shouldn't have exit_policy
        with pytest.raises(ValueError, match=r"FLAT trades must not have exit_policy"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    # ==================== Helper Methods ====================

    def _create_valid_pitch_json(
        self,
        risk_profile: str = "BASE",
        stop_loss_pct: float = 0.015,
        take_profit_pct: float = 0.025,
        direction: str = "LONG",
        conviction: float = 1.5
    ) -> str:
        """Create a valid pitch JSON string for testing.

        Args:
            risk_profile: Risk profile name (TIGHT, BASE, WIDE, or None)
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
            direction: Trade direction (LONG, SHORT, FLAT)
            conviction: Conviction value

        Returns:
            JSON string representing a pitch
        """
        risk_profile_str = f'"{risk_profile}"' if risk_profile else "null"

        return f"""
        {{
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "SPY",
            "direction": "{direction}",
            "horizon": "1W",
            "conviction": {conviction},
            "risk_profile": {risk_profile_str},
            "thesis_bullets": [
                "Rates: Fed policy supportive",
                "Growth: Strong economic data"
            ],
            "entry_policy": {{
                "mode": "limit",
                "limit_price": null
            }},
            "exit_policy": {{
                "time_stop_days": 7,
                "stop_loss_pct": {stop_loss_pct},
                "take_profit_pct": {take_profit_pct},
                "exit_before_events": []
            }},
            "risk_notes": "Monitor Fed signals and economic data",
            "timestamp": "2025-01-20T16:00:00Z"
        }}
        """

    def _create_flat_pitch_json(self, risk_profile=None) -> str:
        """Create a FLAT pitch JSON string for testing.

        Args:
            risk_profile: Risk profile (should be None for FLAT trades)

        Returns:
            JSON string representing a FLAT pitch
        """
        risk_profile_str = f'"{risk_profile}"' if risk_profile else "null"

        return f"""
        {{
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "FLAT",
            "direction": "FLAT",
            "horizon": "1W",
            "conviction": 0,
            "risk_profile": {risk_profile_str},
            "thesis_bullets": [
                "Policy: Insufficient macro clarity for directional trade",
                "Risk: Market conditions require neutral stance"
            ],
            "entry_policy": {{
                "mode": "NONE",
                "limit_price": null
            }},
            "exit_policy": null,
            "risk_notes": "Macro uncertainty requires neutral positioning",
            "timestamp": "2025-01-20T16:00:00Z"
        }}
        """


class TestConvictionValidation:
    """Test suite for conviction value validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.stage = PMPitchStage()

    def test_conviction_constants(self):
        """Test that conviction min/max constants are defined correctly."""
        assert self.stage.CONVICTION_MIN == -2
        assert self.stage.CONVICTION_MAX == 2

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_valid_conviction_positive_boundary(self):
        """Test that conviction of +2 (max) is accepted."""
        pitch_json = self._create_pitch_with_conviction(2.0, "LONG")
        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is not None
        assert result["conviction"] == 2.0

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_valid_conviction_negative_boundary(self):
        """Test that conviction of -2 (min) is accepted."""
        pitch_json = self._create_pitch_with_conviction(-2.0, "SHORT")
        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is not None
        assert result["conviction"] == -2.0

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_valid_conviction_zero(self):
        """Test that conviction of 0 is accepted for FLAT."""
        pitch_json = self._create_flat_pitch_with_conviction(0)
        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is not None
        assert result["conviction"] == 0

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_valid_conviction_positive_mid_range(self):
        """Test that positive mid-range convictions are accepted."""
        for conviction in [0.5, 1.0, 1.5]:
            pitch_json = self._create_pitch_with_conviction(conviction, "LONG")
            result = self.stage._parse_pm_pitch(pitch_json, "test_model")
            assert result is not None
            assert result["conviction"] == conviction

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_valid_conviction_negative_mid_range(self):
        """Test that negative mid-range convictions are accepted."""
        for conviction in [-0.5, -1.0, -1.5]:
            pitch_json = self._create_pitch_with_conviction(conviction, "SHORT")
            result = self.stage._parse_pm_pitch(pitch_json, "test_model")
            assert result is not None
            assert result["conviction"] == conviction

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_conviction_above_max_rejected(self):
        """Test that conviction above +2 is rejected."""
        pitch_json = self._create_pitch_with_conviction(2.1, "LONG")
        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None  # Rejected

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_conviction_below_min_rejected(self):
        """Test that conviction below -2 is rejected."""
        pitch_json = self._create_pitch_with_conviction(-2.1, "SHORT")
        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None  # Rejected

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_conviction_way_above_max_rejected(self):
        """Test that conviction way above range is rejected."""
        pitch_json = self._create_pitch_with_conviction(10.0, "LONG")
        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None  # Rejected

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_conviction_way_below_min_rejected(self):
        """Test that conviction way below range is rejected."""
        pitch_json = self._create_pitch_with_conviction(-10.0, "SHORT")
        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None  # Rejected

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_conviction_decimal_precision(self):
        """Test that decimal conviction values are handled correctly."""
        for conviction in [1.234, 1.9999, -1.567, -1.001]:
            direction = "LONG" if conviction > 0 else "SHORT"
            pitch_json = self._create_pitch_with_conviction(conviction, direction)
            result = self.stage._parse_pm_pitch(pitch_json, "test_model")
            assert result is not None
            assert result["conviction"] == conviction

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_conviction_integer_values(self):
        """Test that integer conviction values are accepted."""
        for conviction in [-2, -1, 1, 2]:
            direction = "LONG" if conviction > 0 else "SHORT"
            pitch_json = self._create_pitch_with_conviction(conviction, direction)
            result = self.stage._parse_pm_pitch(pitch_json, "test_model")
            assert result is not None
            assert result["conviction"] == conviction

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_flat_with_non_zero_conviction_rejected(self):
        """Test that FLAT direction with non-zero conviction is rejected."""
        for conviction in [0.1, -0.1, 1.0, -1.0]:
            pitch_json = self._create_flat_pitch_with_conviction(conviction)
            result = self.stage._parse_pm_pitch(pitch_json, "test_model")
            assert result is None  # Rejected

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_long_with_negative_conviction_rejected(self):
        """Test that LONG direction with negative conviction is rejected."""
        for conviction in [-0.5, -1.0, -2.0]:
            pitch_json = self._create_pitch_with_conviction(conviction, "LONG")
            result = self.stage._parse_pm_pitch(pitch_json, "test_model")
            assert result is None  # Rejected

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_long_with_zero_conviction_rejected(self):
        """Test that LONG direction with zero conviction is rejected."""
        pitch_json = self._create_pitch_with_conviction(0, "LONG")
        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None  # Rejected

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_short_with_positive_conviction_rejected(self):
        """Test that SHORT direction with positive conviction is rejected."""
        for conviction in [0.5, 1.0, 2.0]:
            pitch_json = self._create_pitch_with_conviction(conviction, "SHORT")
            result = self.stage._parse_pm_pitch(pitch_json, "test_model")
            assert result is None  # Rejected

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_short_with_zero_conviction_rejected(self):
        """Test that SHORT direction with zero conviction is rejected."""
        pitch_json = self._create_pitch_with_conviction(0, "SHORT")
        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None  # Rejected

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_conviction_string_rejected(self):
        """Test that string conviction values are rejected."""
        pitch_json = """
        {
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "SPY",
            "direction": "LONG",
            "horizon": "1W",
            "conviction": "1.5",
            "risk_profile": "BASE",
            "thesis_bullets": ["Rates: Fed supportive"],
            "entry_policy": {"mode": "limit", "limit_price": null},
            "exit_policy": {
                "time_stop_days": 7,
                "stop_loss_pct": 0.015,
                "take_profit_pct": 0.025
            },
            "risk_notes": "Monitor Fed signals",
            "timestamp": "2025-01-20T16:00:00Z"
        }
        """
        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None  # Rejected

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_conviction_null_rejected(self):
        """Test that null conviction values are rejected."""
        pitch_json = """
        {
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "SPY",
            "direction": "LONG",
            "horizon": "1W",
            "conviction": null,
            "risk_profile": "BASE",
            "thesis_bullets": ["Rates: Fed supportive"],
            "entry_policy": {"mode": "limit", "limit_price": null},
            "exit_policy": {
                "time_stop_days": 7,
                "stop_loss_pct": 0.015,
                "take_profit_pct": 0.025
            },
            "risk_notes": "Monitor Fed signals",
            "timestamp": "2025-01-20T16:00:00Z"
        }
        """
        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None  # Rejected

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_conviction_missing_rejected(self):
        """Test that missing conviction field is rejected."""
        pitch_json = """
        {
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "FLAT",
            "direction": "FLAT",
            "horizon": "1W",
            "risk_profile": null,
            "thesis_bullets": ["Policy: Insufficient clarity"],
            "entry_policy": {"mode": "NONE", "limit_price": null},
            "exit_policy": null,
            "risk_notes": "Neutral positioning",
            "timestamp": "2025-01-20T16:00:00Z"
        }
        """
        result = self.stage._parse_pm_pitch(pitch_json, "test_model")
        assert result is None  # Rejected because conviction is required

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_conviction_exact_boundary_edge_cases(self):
        """Test exact boundary values with floating point edge cases."""
        # Test exactly at boundaries
        for conviction in [2.0, -2.0, 2, -2]:
            direction = "LONG" if conviction > 0 else "SHORT"
            pitch_json = self._create_pitch_with_conviction(conviction, direction)
            result = self.stage._parse_pm_pitch(pitch_json, "test_model")
            assert result is not None

        # Test just outside boundaries
        for conviction in [2.00001, -2.00001]:
            direction = "LONG" if conviction > 0 else "SHORT"
            pitch_json = self._create_pitch_with_conviction(conviction, direction)
            result = self.stage._parse_pm_pitch(pitch_json, "test_model")
            assert result is None  # Rejected

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_conviction_small_positive_values(self):
        """Test small positive conviction values near zero."""
        for conviction in [0.001, 0.01, 0.1]:
            pitch_json = self._create_pitch_with_conviction(conviction, "LONG")
            result = self.stage._parse_pm_pitch(pitch_json, "test_model")
            assert result is not None
            assert result["conviction"] == conviction

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_conviction_small_negative_values(self):
        """Test small negative conviction values near zero."""
        for conviction in [-0.001, -0.01, -0.1]:
            pitch_json = self._create_pitch_with_conviction(conviction, "SHORT")
            result = self.stage._parse_pm_pitch(pitch_json, "test_model")
            assert result is not None
            assert result["conviction"] == conviction

    # ==================== Helper Methods ====================

    def _create_pitch_with_conviction(
        self,
        conviction: float,
        direction: str = "LONG"
    ) -> str:
        """Create a pitch JSON with specified conviction and direction.

        Args:
            conviction: Conviction value to use
            direction: Trade direction (LONG or SHORT)

        Returns:
            JSON string representing a pitch
        """
        return f"""
        {{
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "SPY",
            "direction": "{direction}",
            "horizon": "1W",
            "conviction": {conviction},
            "risk_profile": "BASE",
            "thesis_bullets": [
                "Rates: Fed policy supportive",
                "Growth: Strong economic data"
            ],
            "entry_policy": {{
                "mode": "limit",
                "limit_price": null
            }},
            "exit_policy": {{
                "time_stop_days": 7,
                "stop_loss_pct": 0.015,
                "take_profit_pct": 0.025,
                "exit_before_events": []
            }},
            "risk_notes": "Monitor Fed signals and economic data",
            "timestamp": "2025-01-20T16:00:00Z"
        }}
        """

    def _create_flat_pitch_with_conviction(self, conviction: float) -> str:
        """Create a FLAT pitch JSON with specified conviction.

        Args:
            conviction: Conviction value to use

        Returns:
            JSON string representing a FLAT pitch
        """
        return f"""
        {{
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "FLAT",
            "direction": "FLAT",
            "horizon": "1W",
            "conviction": {conviction},
            "risk_profile": null,
            "thesis_bullets": [
                "Policy: Insufficient macro clarity for directional trade"
            ],
            "entry_policy": {{
                "mode": "NONE",
                "limit_price": null
            }},
            "exit_policy": null,
            "risk_notes": "Macro uncertainty requires neutral positioning",
            "timestamp": "2025-01-20T16:00:00Z"
        }}
        """


class TestEntryAndExitValidation:
    """Test suite for entry mode and exit event validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.stage = PMPitchStage()

    def test_entry_modes_constant(self):
        """Test that ENTRY_MODES constant is defined correctly."""
        assert ENTRY_MODES == ["limit"]

    def test_exit_events_constant(self):
        """Test that EXIT_EVENTS constant is defined correctly."""
        assert set(EXIT_EVENTS) == {"NFP", "CPI", "FOMC"}

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_valid_limit_entry_mode(self):
        """Test that 'limit' entry mode is accepted."""
        pitch_json = """
        {
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "SPY",
            "direction": "LONG",
            "horizon": "1W",
            "conviction": 1.5,
            "risk_profile": "BASE",
            "thesis_bullets": ["Rates: Fed supportive"],
            "entry_policy": {"mode": "limit", "limit_price": null},
            "exit_policy": {
                "time_stop_days": 7,
                "stop_loss_pct": 0.015,
                "take_profit_pct": 0.025
            },
            "risk_notes": "Monitor Fed signals",
            "timestamp": "2025-01-20T16:00:00Z"
        }
        """

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        assert result is not None
        assert result["entry_policy"]["mode"] == "limit"

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_none_entry_mode_for_flat(self):
        """Test that 'NONE' entry mode is accepted for FLAT trades."""
        pitch_json = """
        {
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "FLAT",
            "direction": "FLAT",
            "horizon": "1W",
            "conviction": 0,
            "risk_profile": null,
            "thesis_bullets": ["Policy: Insufficient clarity"],
            "entry_policy": {"mode": "NONE", "limit_price": null},
            "exit_policy": null,
            "risk_notes": "Neutral positioning",
            "timestamp": "2025-01-20T16:00:00Z"
        }
        """

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        assert result is not None
        assert result["entry_policy"]["mode"] == "NONE"

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_invalid_entry_mode_rejected(self):
        """Test that invalid entry modes are rejected."""
        pitch_json = """
        {
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "SPY",
            "direction": "LONG",
            "horizon": "1W",
            "conviction": 1.5,
            "risk_profile": "BASE",
            "thesis_bullets": ["Rates: Fed supportive"],
            "entry_policy": {"mode": "market", "limit_price": null},
            "exit_policy": {
                "time_stop_days": 7,
                "stop_loss_pct": 0.015,
                "take_profit_pct": 0.025
            },
            "risk_notes": "Monitor Fed signals",
            "timestamp": "2025-01-20T16:00:00Z"
        }
        """

        # Should be rejected because 'market' is not in ENTRY_MODES
        with pytest.raises(ValueError, match=r"Invalid entry_policy.mode"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_flat_with_limit_entry_rejected(self):
        """Test that FLAT trades with 'limit' entry mode are rejected."""
        pitch_json = """
        {
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "FLAT",
            "direction": "FLAT",
            "horizon": "1W",
            "conviction": 0,
            "risk_profile": null,
            "thesis_bullets": ["Policy: Insufficient clarity"],
            "entry_policy": {"mode": "limit", "limit_price": null},
            "exit_policy": null,
            "risk_notes": "Neutral positioning",
            "timestamp": "2025-01-20T16:00:00Z"
        }
        """

        # Should be rejected because FLAT must use 'NONE' mode
        with pytest.raises(ValueError, match=r"FLAT trades must have entry_policy.mode='NONE'"):
            self.stage._parse_pm_pitch(pitch_json, "test_model")

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_valid_nfp_exit_event(self):
        """Test that NFP exit event is accepted."""
        pitch_json = """
        {
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "SPY",
            "direction": "LONG",
            "horizon": "1W",
            "conviction": 1.5,
            "risk_profile": "BASE",
            "thesis_bullets": ["Rates: Fed supportive"],
            "entry_policy": {"mode": "limit", "limit_price": null},
            "exit_policy": {
                "time_stop_days": 7,
                "stop_loss_pct": 0.015,
                "take_profit_pct": 0.025,
                "exit_before_events": ["NFP"]
            },
            "risk_notes": "Exit before NFP",
            "timestamp": "2025-01-20T16:00:00Z"
        }
        """

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        assert result is not None

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_valid_cpi_exit_event(self):
        """Test that CPI exit event is accepted."""
        pitch_json = """
        {
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "SPY",
            "direction": "LONG",
            "horizon": "1W",
            "conviction": 1.5,
            "risk_profile": "BASE",
            "thesis_bullets": ["Rates: Fed supportive"],
            "entry_policy": {"mode": "limit", "limit_price": null},
            "exit_policy": {
                "time_stop_days": 7,
                "stop_loss_pct": 0.015,
                "take_profit_pct": 0.025,
                "exit_before_events": ["CPI"]
            },
            "risk_notes": "Exit before CPI",
            "timestamp": "2025-01-20T16:00:00Z"
        }
        """

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        assert result is not None

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_valid_fomc_exit_event(self):
        """Test that FOMC exit event is accepted."""
        pitch_json = """
        {
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "SPY",
            "direction": "LONG",
            "horizon": "1W",
            "conviction": 1.5,
            "risk_profile": "BASE",
            "thesis_bullets": ["Rates: Fed supportive"],
            "entry_policy": {"mode": "limit", "limit_price": null},
            "exit_policy": {
                "time_stop_days": 7,
                "stop_loss_pct": 0.015,
                "take_profit_pct": 0.025,
                "exit_before_events": ["FOMC"]
            },
            "risk_notes": "Exit before FOMC",
            "timestamp": "2025-01-20T16:00:00Z"
        }
        """

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        assert result is not None

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_multiple_exit_events(self):
        """Test that multiple exit events can be specified."""
        pitch_json = """
        {
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "SPY",
            "direction": "LONG",
            "horizon": "1W",
            "conviction": 1.5,
            "risk_profile": "BASE",
            "thesis_bullets": ["Rates: Fed supportive"],
            "entry_policy": {"mode": "limit", "limit_price": null},
            "exit_policy": {
                "time_stop_days": 7,
                "stop_loss_pct": 0.015,
                "take_profit_pct": 0.025,
                "exit_before_events": ["NFP", "CPI", "FOMC"]
            },
            "risk_notes": "Exit before major events",
            "timestamp": "2025-01-20T16:00:00Z"
        }
        """

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        assert result is not None

    @patch('backend.pipeline.stages.pm_pitch.REQUESTY_MODELS', MOCK_REQUESTY_MODELS)
    def test_empty_exit_events_accepted(self):
        """Test that empty exit events array is accepted."""
        pitch_json = """
        {
            "idea_id": "test-123",
            "week_id": "2025-01-20",
            "asof_et": "2025-01-20T16:00:00-05:00",
            "pm_model": "test_model",
            "selected_instrument": "SPY",
            "direction": "LONG",
            "horizon": "1W",
            "conviction": 1.5,
            "risk_profile": "BASE",
            "thesis_bullets": ["Rates: Fed supportive"],
            "entry_policy": {"mode": "limit", "limit_price": null},
            "exit_policy": {
                "time_stop_days": 7,
                "stop_loss_pct": 0.015,
                "take_profit_pct": 0.025,
                "exit_before_events": []
            },
            "risk_notes": "No early exits planned",
            "timestamp": "2025-01-20T16:00:00Z"
        }
        """

        result = self.stage._parse_pm_pitch(pitch_json, "test_model")

        assert result is not None
