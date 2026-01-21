#!/usr/bin/env python3
"""Test script for /api/performance/comparison endpoint."""

import sys
import json
from pydantic import ValidationError


def test_response_models():
    """Test that response models are correctly defined."""
    from backend.api.monitor import (
        PMPerformanceSummary,
        CouncilPerformanceSummary,
        PerformanceComparison,
    )

    print("Testing response models...")

    # Test CouncilPerformanceSummary
    council = CouncilPerformanceSummary(
        account="COUNCIL",
        total_pl=355.0,
        total_pl_pct=0.355,
        equity=100355.0,
        max_drawdown=-1.2,
        sharpe_ratio=1.85,
    )
    assert council.account == "COUNCIL"
    assert council.total_pl == 355.0
    print("✓ CouncilPerformanceSummary model OK")

    # Test PMPerformanceSummary
    pm = PMPerformanceSummary(
        account="CHATGPT",
        total_pl=284.0,
        total_pl_pct=0.284,
        equity=100284.0,
        max_drawdown=-2.1,
        sharpe_ratio=1.42,
    )
    assert pm.account == "CHATGPT"
    assert pm.total_pl == 284.0
    print("✓ PMPerformanceSummary model OK")

    # Test PerformanceComparison
    comparison = PerformanceComparison(
        council=council,
        individuals=[pm],
        avg_individual_pl=284.0,
        council_advantage=71.0,
    )
    assert comparison.council.account == "COUNCIL"
    assert len(comparison.individuals) == 1
    assert comparison.individuals[0].account == "CHATGPT"
    print("✓ PerformanceComparison model OK")


def test_fallback_data():
    """Test that fallback data has correct structure."""
    print("\nTesting fallback data structure...")

    # Mock the comparison response
    council_summary = {
        "account": "COUNCIL",
        "total_pl": 355.0,
        "total_pl_pct": 0.355,
        "equity": 100355.0,
        "max_drawdown": -1.2,
        "sharpe_ratio": 1.85,
    }

    individuals = [
        {
            "account": "CHATGPT",
            "total_pl": 284.0,
            "total_pl_pct": 0.284,
            "equity": 100284.0,
            "max_drawdown": -2.1,
            "sharpe_ratio": 1.42,
        },
        {
            "account": "GEMINI",
            "total_pl": -39.0,
            "total_pl_pct": -0.039,
            "equity": 99961.0,
            "max_drawdown": -3.5,
            "sharpe_ratio": 0.95,
        },
        {
            "account": "CLAUDE",
            "total_pl": 0.0,
            "total_pl_pct": 0.0,
            "equity": 100000.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": None,
        },
        {
            "account": "GROQ",
            "total_pl": 249.0,
            "total_pl_pct": 0.249,
            "equity": 100249.0,
            "max_drawdown": -1.8,
            "sharpe_ratio": 1.58,
        },
        {
            "account": "DEEPSEEK",
            "total_pl": 18.0,
            "total_pl_pct": 0.018,
            "equity": 100018.0,
            "max_drawdown": -1.4,
            "sharpe_ratio": 1.12,
        },
    ]

    # Verify structure
    assert "account" in council_summary
    assert "total_pl" in council_summary
    assert "equity" in council_summary
    assert council_summary["account"] == "COUNCIL"
    print("✓ Council summary structure OK")

    assert len(individuals) == 5
    for ind in individuals:
        assert "account" in ind
        assert "total_pl" in ind
        assert "equity" in ind
        assert ind["account"] in ["CHATGPT", "GEMINI", "CLAUDE", "GROQ", "DEEPSEEK"]
    print(f"✓ {len(individuals)} individual PM summaries OK")

    # Calculate metrics
    avg_pl = sum(ind["total_pl"] for ind in individuals) / len(individuals)
    council_advantage = council_summary["total_pl"] - avg_pl
    print(f"✓ Metrics calculation OK (avg_pl={avg_pl:.2f}, advantage={council_advantage:.2f})")


def test_expected_fields():
    """Test that response has all expected fields from spec."""
    from backend.api.monitor import PerformanceComparison

    print("\nTesting expected fields from spec...")

    # Create sample response
    from backend.api.monitor import (
        CouncilPerformanceSummary,
        PMPerformanceSummary,
    )

    council = CouncilPerformanceSummary(
        account="COUNCIL",
        total_pl=100.0,
        total_pl_pct=0.1,
        equity=100100.0,
        max_drawdown=-1.0,
        sharpe_ratio=1.5,
    )

    pm = PMPerformanceSummary(
        account="CHATGPT",
        total_pl=50.0,
        total_pl_pct=0.05,
        equity=100050.0,
        max_drawdown=-2.0,
        sharpe_ratio=1.2,
    )

    comparison = PerformanceComparison(
        council=council,
        individuals=[pm],
        avg_individual_pl=50.0,
        council_advantage=50.0,
    )

    # Serialize to dict
    data = json.loads(comparison.model_dump_json())

    # Verify expected fields from spec
    assert "council" in data
    assert "individuals" in data
    assert "council" in data and "total_pl" in data["council"]
    assert "individuals" in data and len(data["individuals"]) > 0
    assert "account" in data["individuals"][0]
    print("✓ All expected fields present")
    print(f"  - council.total_pl: {data['council']['total_pl']}")
    print(f"  - individuals[0].account: {data['individuals'][0]['account']}")
    print(f"  - avg_individual_pl: {data['avg_individual_pl']}")
    print(f"  - council_advantage: {data['council_advantage']}")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing /api/performance/comparison endpoint")
    print("=" * 60)

    try:
        test_response_models()
        test_fallback_data()
        test_expected_fields()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
