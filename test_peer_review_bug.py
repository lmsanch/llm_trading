#!/usr/bin/env python3
"""Test script to reproduce peer review bug: only one review extracted per model."""

import asyncio
import json
from backend.pipeline.stages.peer_review import PeerReviewStage
from backend.pipeline.context import PipelineContext
from backend.pipeline.stages.pm_pitch import PM_PITCHES


async def test_peer_review_with_mock_pitches():
    """Test peer review with 4 mock pitches to verify bug."""

    # Create 4 mock PM pitches (simulating output from 4 PM models)
    mock_pitches = [
        {
            "model": "openai/gpt-5.1",
            "model_info": {"account": "Acct 1 (GPT-5.1)"},
            "selected_instrument": "SPY",
            "direction": "LONG",
            "horizon": "1W",
            "conviction": 1.5,
            "thesis_bullets": [
                "Strong momentum in equities",
                "Technical breakout above 500",
                "Fed pause likely"
            ],
            "risk_profile": "BASE",
            "entry_policy": {"mode": "limit"},
            "exit_policy": {
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.05,
                "time_stop_days": 7
            },
            "risk_notes": "Watch for Fed hawkish surprise"
        },
        {
            "model": "google/gemini-3-pro",
            "model_info": {"account": "Acct 2 (Gemini)"},
            "selected_instrument": "TLT",
            "direction": "SHORT",
            "horizon": "1W",
            "conviction": 1.8,
            "thesis_bullets": [
                "Rising yields as inflation persists",
                "Fed hiking cycle not done",
                "Technical breakdown"
            ],
            "risk_profile": "BASE",
            "entry_policy": {"mode": "limit"},
            "exit_policy": {
                "stop_loss_pct": 0.025,
                "take_profit_pct": 0.04,
                "time_stop_days": 7
            },
            "risk_notes": "Risk if CPI comes in soft"
        },
        {
            "model": "anthropic/claude-3.5-sonnet",
            "model_info": {"account": "Acct 3 (Sonnet)"},
            "selected_instrument": "GLD",
            "direction": "LONG",
            "horizon": "1W",
            "conviction": 1.2,
            "thesis_bullets": [
                "Safe haven demand rising",
                "Dollar weakness",
                "Geopolitical tensions"
            ],
            "risk_profile": "BASE",
            "entry_policy": {"mode": "limit"},
            "exit_policy": {
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.06,
                "time_stop_days": 7
            },
            "risk_notes": "Risk if dollar strengthens"
        },
        {
            "model": "x-ai/grok",
            "model_info": {"account": "Acct 4 (Grok)"},
            "selected_instrument": "FLAT",
            "direction": "FLAT",
            "horizon": "1W",
            "conviction": 0,
            "thesis_bullets": [
                "Too much uncertainty",
                "Wait for clearer signals"
            ],
            "risk_profile": "BASE",
            "entry_policy": {"mode": "limit"},
            "exit_policy": {
                "stop_loss_pct": 0.0,
                "take_profit_pct": 0.0,
                "time_stop_days": 7
            },
            "risk_notes": "N/A"
        }
    ]

    # Create pipeline context with mock pitches
    context = PipelineContext()
    context = context.set(PM_PITCHES, mock_pitches)

    print("=" * 70)
    print("PEER REVIEW BUG REPRODUCTION TEST")
    print("=" * 70)
    print(f"\n📊 Input: {len(mock_pitches)} PM pitches")
    print("   - Acct 1 (GPT-5.1): SPY LONG")
    print("   - Acct 2 (Gemini): TLT SHORT")
    print("   - Acct 3 (Sonnet): GLD LONG")
    print("   - Acct 4 (Grok): FLAT")

    print("\n🔍 Expected behavior:")
    print("   - Each of 4 models should review 3 other pitches (N-1)")
    print("   - Total reviews: 4 models × 3 reviews = 12 reviews")

    print("\n🐛 Bug hypothesis:")
    print("   - Parser only extracts FIRST review from each model's response")
    print("   - Total reviews: 4 models × 1 review = 4 reviews (WRONG!)")

    # Run peer review stage
    print("\n" + "=" * 70)
    print("RUNNING PEER REVIEW STAGE...")
    print("=" * 70)

    stage = PeerReviewStage()
    result_context = await stage.execute(context)

    # Get peer reviews from context
    from backend.pipeline.stages.peer_review import PEER_REVIEWS
    peer_reviews = result_context.get(PEER_REVIEWS)

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"\n📈 Actual reviews generated: {len(peer_reviews)}")

    # Analyze reviews
    reviews_by_reviewer = {}
    for review in peer_reviews:
        reviewer = review.get("reviewer_model", "unknown")
        if reviewer not in reviews_by_reviewer:
            reviews_by_reviewer[reviewer] = []
        reviews_by_reviewer[reviewer].append(review)

    print("\n📋 Reviews per model:")
    for reviewer, reviews in reviews_by_reviewer.items():
        print(f"   - {reviewer}: {len(reviews)} review(s)")
        for review in reviews:
            pitch_label = review.get("pitch_label", "unknown")
            avg_score = review.get("average_score", 0)
            print(f"     → {pitch_label} (avg score: {avg_score:.1f}/10)")

    print("\n🎯 Verdict:")
    if len(peer_reviews) == 12:
        print("   ✅ EXPECTED: 12 reviews generated (bug is FIXED)")
    elif len(peer_reviews) == 4:
        print("   ❌ BUG CONFIRMED: Only 4 reviews generated (should be 12)")
        print("   ⚠️  Each model only generated 1 review instead of 3")
    else:
        print(f"   ⚠️  UNEXPECTED: {len(peer_reviews)} reviews generated")

    # Save detailed output
    output = {
        "total_reviews": len(peer_reviews),
        "expected_reviews": 12,
        "bug_confirmed": len(peer_reviews) < 12,
        "reviews_by_reviewer": {
            reviewer: len(reviews)
            for reviewer, reviews in reviews_by_reviewer.items()
        },
        "reviews": peer_reviews
    }

    output_file = "./.auto-claude/specs/014-anonymized-peer-review-system/peer_review_output.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n💾 Detailed output saved to: {output_file}")

    return len(peer_reviews), peer_reviews


if __name__ == "__main__":
    count, reviews = asyncio.run(test_peer_review_with_mock_pitches())
    print(f"\n✅ Test completed: {count} reviews generated")
