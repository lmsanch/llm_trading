#!/usr/bin/env python3
"""
Test to verify peer review with exactly 4 pitches generating 12 reviews.

This test mocks 4 PM models to ensure:
- 4 PM pitches are created
- Each model reviews 3 other pitches (N-1)
- Total: 4 models × 3 reviews = 12 reviews
"""

import asyncio
import json
from unittest.mock import AsyncMock, patch
from backend.pipeline.stages.peer_review import PeerReviewStage
from backend.pipeline.context import PipelineContext
from backend.pipeline.stages.pm_pitch import PM_PITCHES


async def test_4_pitches_12_reviews():
    """Test peer review with 4 pitches expecting 12 reviews (4 models × 3 reviews each)."""

    # Create 4 mock PM pitches (one from each of 4 models)
    mock_pitches = [
        {
            "model": "chatgpt",
            "model_info": {"account": "CHATGPT"},
            "selected_instrument": "SPY",
            "direction": "LONG",
            "horizon": "1W",
            "conviction": 1.5,
            "thesis_bullets": ["SPY bullish thesis"],
            "risk_profile": "BASE",
            "entry_policy": {"mode": "limit"},
            "exit_policy": {"stop_loss_pct": 0.02, "take_profit_pct": 0.05, "time_stop_days": 7},
            "risk_notes": "Standard risk"
        },
        {
            "model": "gemini",
            "model_info": {"account": "GEMINI"},
            "selected_instrument": "TLT",
            "direction": "SHORT",
            "horizon": "1W",
            "conviction": 1.3,
            "thesis_bullets": ["TLT bearish thesis"],
            "risk_profile": "BASE",
            "entry_policy": {"mode": "limit"},
            "exit_policy": {"stop_loss_pct": 0.02, "take_profit_pct": 0.05, "time_stop_days": 7},
            "risk_notes": "Standard risk"
        },
        {
            "model": "claude",
            "model_info": {"account": "CLAUDE"},
            "selected_instrument": "GLD",
            "direction": "LONG",
            "horizon": "1W",
            "conviction": 1.2,
            "thesis_bullets": ["GLD bullish thesis"],
            "risk_profile": "BASE",
            "entry_policy": {"mode": "limit"},
            "exit_policy": {"stop_loss_pct": 0.02, "take_profit_pct": 0.05, "time_stop_days": 7},
            "risk_notes": "Standard risk"
        },
        {
            "model": "groq",
            "model_info": {"account": "GROQ"},
            "selected_instrument": "QQQ",
            "direction": "SHORT",
            "horizon": "1W",
            "conviction": 1.4,
            "thesis_bullets": ["QQQ bearish thesis"],
            "risk_profile": "BASE",
            "entry_policy": {"mode": "limit"},
            "exit_policy": {"stop_loss_pct": 0.02, "take_profit_pct": 0.05, "time_stop_days": 7},
            "risk_notes": "Standard risk"
        }
    ]

    # Mock responses - each model reviews 3 other pitches (not their own)
    # CHATGPT reviews Pitch B, C, D (not A)
    # GEMINI reviews Pitch A, C, D (not B)
    # CLAUDE reviews Pitch A, B, D (not C)
    # GROQ reviews Pitch A, B, C (not D)
    mock_responses = {
        "chatgpt": {
            "content": json.dumps([
                {
                    "pitch_label": "Pitch B",
                    "scores": {"clarity": 8, "edge_plausibility": 7, "timing_catalyst": 6,
                              "risk_definition": 8, "risk_management": 7, "originality": 6, "tradeability": 7},
                    "best_argument_against": "TLT bear case",
                    "one_flip_condition": "If yields drop"
                },
                {
                    "pitch_label": "Pitch C",
                    "scores": {"clarity": 7, "edge_plausibility": 6, "timing_catalyst": 5,
                              "risk_definition": 7, "risk_management": 6, "originality": 5, "tradeability": 6},
                    "best_argument_against": "GLD risk",
                    "one_flip_condition": "If dollar rallies"
                },
                {
                    "pitch_label": "Pitch D",
                    "scores": {"clarity": 8, "edge_plausibility": 7, "timing_catalyst": 7,
                              "risk_definition": 8, "risk_management": 7, "originality": 6, "tradeability": 8},
                    "best_argument_against": "QQQ downside",
                    "one_flip_condition": "If tech rallies"
                }
            ])
        },
        "gemini": {
            "content": json.dumps([
                {
                    "pitch_label": "Pitch A",
                    "scores": {"clarity": 9, "edge_plausibility": 8, "timing_catalyst": 7,
                              "risk_definition": 8, "risk_management": 8, "originality": 7, "tradeability": 8},
                    "best_argument_against": "SPY momentum risk",
                    "one_flip_condition": "If SPX breaks 5500"
                },
                {
                    "pitch_label": "Pitch C",
                    "scores": {"clarity": 6, "edge_plausibility": 5, "timing_catalyst": 6,
                              "risk_definition": 6, "risk_management": 5, "originality": 7, "tradeability": 5},
                    "best_argument_against": "GLD volatility",
                    "one_flip_condition": "If inflation cools"
                },
                {
                    "pitch_label": "Pitch D",
                    "scores": {"clarity": 7, "edge_plausibility": 6, "timing_catalyst": 6,
                              "risk_definition": 7, "risk_management": 6, "originality": 5, "tradeability": 6},
                    "best_argument_against": "QQQ could stabilize",
                    "one_flip_condition": "If earnings beat"
                }
            ])
        },
        "claude": {
            "content": json.dumps([
                {
                    "pitch_label": "Pitch A",
                    "scores": {"clarity": 8, "edge_plausibility": 7, "timing_catalyst": 6,
                              "risk_definition": 7, "risk_management": 7, "originality": 6, "tradeability": 7},
                    "best_argument_against": "SPY overextended",
                    "one_flip_condition": "If VIX spikes"
                },
                {
                    "pitch_label": "Pitch B",
                    "scores": {"clarity": 7, "edge_plausibility": 6, "timing_catalyst": 7,
                              "risk_definition": 7, "risk_management": 6, "originality": 6, "tradeability": 7},
                    "best_argument_against": "TLT oversold",
                    "one_flip_condition": "If Fed pivots"
                },
                {
                    "pitch_label": "Pitch D",
                    "scores": {"clarity": 8, "edge_plausibility": 7, "timing_catalyst": 7,
                              "risk_definition": 8, "risk_management": 7, "originality": 7, "tradeability": 8},
                    "best_argument_against": "QQQ support levels",
                    "one_flip_condition": "If tech sector reverses"
                }
            ])
        },
        "groq": {
            "content": json.dumps([
                {
                    "pitch_label": "Pitch A",
                    "scores": {"clarity": 7, "edge_plausibility": 6, "timing_catalyst": 6,
                              "risk_definition": 6, "risk_management": 6, "originality": 5, "tradeability": 6},
                    "best_argument_against": "SPY crowded trade",
                    "one_flip_condition": "If positioning unwinds"
                },
                {
                    "pitch_label": "Pitch B",
                    "scores": {"clarity": 8, "edge_plausibility": 7, "timing_catalyst": 7,
                              "risk_definition": 7, "risk_management": 7, "originality": 6, "tradeability": 7},
                    "best_argument_against": "TLT near support",
                    "one_flip_condition": "If rate cuts priced in"
                },
                {
                    "pitch_label": "Pitch C",
                    "scores": {"clarity": 6, "edge_plausibility": 5, "timing_catalyst": 5,
                              "risk_definition": 6, "risk_management": 5, "originality": 6, "tradeability": 5},
                    "best_argument_against": "GLD lacks catalyst",
                    "one_flip_condition": "If real yields rise"
                }
            ])
        }
    }

    # Create pipeline context
    context = PipelineContext()
    context = context.set(PM_PITCHES, mock_pitches)

    print("=" * 80)
    print("PEER REVIEW TEST: 4 PITCHES → 12 REVIEWS")
    print("=" * 80)
    print(f"\n📊 Input: {len(mock_pitches)} PM pitches from 4 models")
    print("   - CHATGPT: SPY LONG")
    print("   - GEMINI: TLT SHORT")
    print("   - CLAUDE: GLD LONG")
    print("   - GROQ: QQQ SHORT")

    print("\n🎯 Expected behavior:")
    print("   - Each model reviews 3 other pitches (N-1 where N=4)")
    print("   - Total reviews: 4 models × 3 reviews = 12 reviews")

    # Run peer review stage with mocked query_pm_models
    with patch('backend.pipeline.stages.peer_review.query_pm_models', new_callable=AsyncMock) as mock_query:
        mock_query.return_value = mock_responses

        print("\n" + "=" * 80)
        print("RUNNING PEER REVIEW STAGE...")
        print("=" * 80)

        stage = PeerReviewStage()
        result_context = await stage.execute(context)

        # Get peer reviews from context
        from backend.pipeline.stages.peer_review import PEER_REVIEWS
        peer_reviews = result_context.get(PEER_REVIEWS)

        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        print(f"\n📈 Total reviews generated: {len(peer_reviews)}")

        # Analyze reviews by reviewer
        reviews_by_reviewer = {}
        for review in peer_reviews:
            reviewer = review.get("reviewer_model", "unknown")
            if reviewer not in reviews_by_reviewer:
                reviews_by_reviewer[reviewer] = []
            reviews_by_reviewer[reviewer].append(review)

        print(f"\n📋 Reviews by model:")
        for reviewer, reviews in sorted(reviews_by_reviewer.items()):
            print(f"   - {reviewer}: {len(reviews)} review(s)")
            for review in reviews:
                pitch_label = review.get("pitch_label", "unknown")
                avg_score = review.get("average_score", 0)
                print(f"     → {pitch_label} (avg score: {avg_score:.1f}/10)")

        # Verify results
        print("\n🎯 Verification:")
        success = True

        if len(peer_reviews) == 12:
            print("   ✅ PASS: 12 reviews generated (expected)")
        else:
            print(f"   ❌ FAIL: {len(peer_reviews)} reviews generated (expected 12)")
            success = False

        if len(reviews_by_reviewer) == 4:
            print("   ✅ PASS: 4 reviewer models (expected)")
        else:
            print(f"   ❌ FAIL: {len(reviews_by_reviewer)} reviewer models (expected 4)")
            success = False

        # Check that each model reviewed exactly 3 pitches
        for reviewer, reviews in reviews_by_reviewer.items():
            if len(reviews) == 3:
                print(f"   ✅ PASS: {reviewer} reviewed 3 pitches (expected)")
            else:
                print(f"   ❌ FAIL: {reviewer} reviewed {len(reviews)} pitches (expected 3)")
                success = False

        print("\n" + "=" * 80)
        if success:
            print("✅ TEST PASSED: Generated 12 peer reviews from 4 pitches")
        else:
            print("❌ TEST FAILED: Did not generate expected number of reviews")
        print("=" * 80)

        return len(peer_reviews) == 12


if __name__ == "__main__":
    success = asyncio.run(test_4_pitches_12_reviews())
    exit(0 if success else 1)
