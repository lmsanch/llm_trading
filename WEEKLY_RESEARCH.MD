
## A) Weekly Research Prompt (Gemini Deep Research + Perplexity Deep Research)

Use the **same prompt** for both; they output `research_pack.json`.

**System / Instruction (pasteable)**

**Goal:** Produce a “Research Pack” for a **single-week macro trade** from a fixed ETF universe.

**Constraints**

* Allowed instruments: `SPY, QQQ, IWM, TLT, HYG, UUP, GLD, USO` (add/remove later)
* Horizon: 1 week
* Focus: macro + cross-asset drivers (rates, USD, commodities, risk appetite)
* Must be falsifiable; avoid vague narratives
* Include *only* information likely to matter within ~1 week

**Output: STRICT JSON only** (no markdown, no prose outside JSON)

```json
{
  "week_id": "YYYY-MM-DD",
  "asof_et": "YYYY-MM-DDTHH:MM:SS-05:00",
  "research_source": "gemini_deep_research | perplexity_deep_research",
  "macro_regime": {
    "risk_mode": "risk_on | risk_off | mixed",
    "rates_impulse": "up | down | range",
    "usd_impulse": "up | down | range",
    "inflation_impulse": "up | down | range",
    "growth_impulse": "up | down | range"
  },
  "top_narratives": [
    {
      "name": "string",
      "why_it_moves_prices_this_week": ["string", "string"],
      "key_catalysts_next_7d": ["string", "string"],
      "what_would_falsify_it": ["string"]
    }
  ],
  "consensus_map": {
    "street_consensus": "string",
    "positioning_guess": "light | neutral | crowded",
    "what_market_is_priced_for": ["string", "string"],
    "what_would_surprise": ["string", "string"]
  },
  "tradable_candidates": [
    {
      "instrument": "SPY|QQQ|IWM|TLT|HYG|UUP|GLD|USO",
      "directional_bias": "bullish | bearish | neutral",
      "one_week_thesis": ["string", "string"],
      "primary_risks": ["string", "string"],
      "watch_indicators": [
        {
          "name": "string",
          "type": "price_level | return | yield | spread | event | other",
          "bullish_condition": "string",
          "bearish_condition": "string",
          "check_frequency": "intraday | daily | event"
        }
      ],
      "invalidation_rule": "string"
    }
  ],
  "event_calendar_next_7d": [
    {
      "event": "string",
      "date_et": "YYYY-MM-DD",
      "why_matters": "string",
      "expected_impact_assets": ["SPY", "TLT"]
    }
  ],
  "confidence_notes": {
    "known_unknowns": ["string", "string"],
    "data_quality_flags": ["string"]
  }
}
```

That’s it. Two packs per week: A (Gemini) and B (Perplexity).

---

## B) How to “incorporate PM Pitch + Peer Review” using llm-council (instructions for OpenCode)

Tell OpenCode:

1. **Stage 1 = PM Pitch generation**

* Input to each council model = `Research Pack A + Research Pack B + constraints + allowed tickers`
* Replace Karpathy’s freeform prompt with a “return JSON pitch” prompt
* Save raw + parsed pitch JSON

Pitch schema (high level):

* instrument, direction, horizon
* conviction (-2..+2)
* thesis bullets
* indicators (frozen)
* invalidation rule
* entry plan (simple)

2. **Stage 2 = Peer Review**

* Use Karpathy’s anonymization as-is
* Replace ranking prompt with **rubric scoring JSON**
* Each model scores each other pitch (1–10) on:

  * clarity, edge, timing, risk definition, indicator integrity, originality, tradeability
* Output JSON per review

3. **Stage 3 = Chairman**

* Same as Karpathy, but force strict JSON output:

  * council_trade (instrument/direction/horizon)
  * conviction
  * rationale bullets
  * dissent summary
  * monitoring plan for checkpoints

**Key point:** llm-council provides the *skeleton*; you supply the *contracts*.

---

## C) Minimal message you can paste to OpenCode

* “Keep llm-council orchestration (3 stages)”
* “Swap prompts to enforce strict JSON schemas”
* “Add a new pre-stage that fetches Research Pack A/B (Gemini/Perplexity Deep Research)”
* “Stage1 outputs `pm_pitch.json` per model”
* “Stage2 outputs `peer_reviews.jsonl`”
* “Stage3 outputs `chairman_decision.json`”
* “Persist everything in per-week folders + SQLite event log”

