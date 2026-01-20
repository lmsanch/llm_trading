"""Test that all fixtures are working correctly."""

import pytest


def test_valid_long_pitch_fixture(valid_long_pitch):
    """Test that valid_long_pitch fixture works."""
    assert valid_long_pitch is not None
    assert valid_long_pitch["direction"] == "LONG"
    assert "thesis_bullets" in valid_long_pitch
    assert isinstance(valid_long_pitch["conviction"], (int, float))


def test_valid_short_pitch_fixture(valid_short_pitch):
    """Test that valid_short_pitch fixture works."""
    assert valid_short_pitch is not None
    assert valid_short_pitch["direction"] == "SHORT"
    assert valid_short_pitch["conviction"] < 0


def test_valid_flat_pitch_fixture(valid_flat_pitch):
    """Test that valid_flat_pitch fixture works."""
    assert valid_flat_pitch is not None
    assert valid_flat_pitch["direction"] == "FLAT"
    assert valid_flat_pitch["conviction"] == 0.0


def test_all_pm_pitches_fixture(all_pm_pitches):
    """Test that all_pm_pitches fixture works."""
    assert all_pm_pitches is not None
    assert len(all_pm_pitches) == 5
    assert all(isinstance(pitch, dict) for pitch in all_pm_pitches)


def test_mock_stage1_responses_fixture(mock_stage1_responses):
    """Test that mock_stage1_responses fixture works."""
    assert mock_stage1_responses is not None
    assert len(mock_stage1_responses) > 0
    assert all("model" in resp for resp in mock_stage1_responses)


def test_mock_stage2_rankings_fixture(mock_stage2_rankings):
    """Test that mock_stage2_rankings fixture works."""
    assert mock_stage2_rankings is not None
    assert len(mock_stage2_rankings) > 0
    assert all("model" in resp for resp in mock_stage2_rankings)


def test_mock_chairman_response_fixture(mock_chairman_response):
    """Test that mock_chairman_response fixture works."""
    assert mock_chairman_response is not None
    assert isinstance(mock_chairman_response, str)
    assert len(mock_chairman_response) > 0


def test_label_to_model_mapping_fixture(label_to_model_mapping):
    """Test that label_to_model_mapping fixture works."""
    assert label_to_model_mapping is not None
    assert isinstance(label_to_model_mapping, dict)
    assert all(key.startswith("Response") for key in label_to_model_mapping.keys())


def test_market_snapshot_fixture(market_snapshot):
    """Test that market_snapshot fixture works."""
    assert market_snapshot is not None
    assert hasattr(market_snapshot, "prices")
    assert hasattr(market_snapshot, "to_dict")


def test_sample_prices_fixture(sample_prices):
    """Test that sample_prices fixture works."""
    assert sample_prices is not None
    assert "SPY" in sample_prices
    assert isinstance(sample_prices["SPY"], (int, float))


@pytest.mark.asyncio
async def test_mock_alpaca_client_fixture(mock_alpaca_client):
    """Test that mock_alpaca_client fixture works."""
    assert mock_alpaca_client is not None

    # Test async methods
    account = await mock_alpaca_client.get_account()
    assert account is not None
    assert "account_number" in account

    positions = await mock_alpaca_client.get_positions()
    assert isinstance(positions, list)


def test_mock_query_model_fixture(mock_query_model):
    """Test that mock_query_model fixture works."""
    assert mock_query_model is not None
    assert callable(mock_query_model)


def test_mock_query_models_parallel_fixture(mock_query_models_parallel):
    """Test that mock_query_models_parallel fixture works."""
    assert mock_query_models_parallel is not None
    assert callable(mock_query_models_parallel)


def test_async_return_fixture(async_return):
    """Test that async_return fixture works."""
    assert async_return is not None
    assert callable(async_return)


def test_async_raise_fixture(async_raise):
    """Test that async_raise fixture works."""
    assert async_raise is not None
    assert callable(async_raise)
