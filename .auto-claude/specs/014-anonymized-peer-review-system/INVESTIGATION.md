# Peer Review Bug Investigation

**Date:** 2026-01-21
**Investigator:** Claude (Auto-Claude)
**Task:** Subtask 1-1 - Run peer review stage and capture output to verify bug

---

## Executive Summary

**BUG CONFIRMED:** The peer review system only extracts **ONE review per model** instead of **N-1 reviews per model** (where N = number of pitches).

- **Expected:** 4 models × 3 reviews each = **12 total reviews**
- **Actual:** 5 models × 1 review each = **5 total reviews**
- **Root Cause:** Parser explicitly discards multiple reviews (lines 428-433 in `peer_review.py`)

---

## 1. Current Behavior (Buggy)

### Test Setup

Ran `test_peer_review_bug.py` with 4 mock PM pitches:

```
Input: 4 PM pitches
- Acct 1 (GPT-5.1): SPY LONG
- Acct 2 (Gemini): TLT SHORT
- Acct 3 (Sonnet): GLD LONG
- Acct 4 (Grok): FLAT
```

### Observed Results

```
📈 Actual reviews generated: 5

📋 Reviews per model:
   - gpt-4.1-trader: 1 review(s)
     → Pitch A (avg score: 5.7/10)
   - Expert_Trader_Bot: 1 review(s)
     → Pitch A (avg score: 4.9/10)
   - ExpertTraderAI: 1 review(s)
     → Pitch A (avg score: 6.6/10)
   - claude-3-7-sonnet-20250219: 1 review(s)
     → Pitch A (avg score: 5.1/10)
   - model_name: 1 review(s)
     → Pitch A (avg score: 7.1/10)
```

### Key Observations

1. **Only 5 reviews generated** (should be 12)
2. **Each model reviewed only "Pitch A"** (should review 3 different pitches)
3. **Parser output shows:** `"Reviewed 7 pitches"` but only 1 is actually extracted
4. **All reviews stored are for "Pitch A"**

---

## 2. Root Cause Analysis

### Location: `backend/pipeline/stages/peer_review.py`

#### Problem 1: Parser Returns Single Dict (Lines 334-469)

```python
def _parse_peer_review(
    self, content: str, reviewer_model: str
) -> Dict[str, Any] | None:  # ❌ Returns single dict or None
    """Parse peer review from LLM response."""

    # ... JSON extraction logic ...

    # If model returned a list of reviews, take the first element
    if isinstance(review, list):
        if not review:
            print(f"  ⚠️  Empty review list from {reviewer_model}")
            return None
        review = review[0]  # ❌ BUG: Only takes first element!

    # ... validation logic ...

    return review  # ❌ Returns single review dict
```

**Issues:**
- Function signature returns `Dict[str, Any] | None` (single review)
- Lines 428-433: Explicitly discards multiple reviews with `review = review[0]`
- No way to return multiple reviews

#### Problem 2: Caller Appends Single Review (Lines 177-193)

```python
async def _generate_peer_reviews(
    self, anonymized_pitches: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Generate peer reviews from all PM models."""

    # ... query models ...

    peer_reviews = []
    for model_key, response in responses.items():
        if response is not None:
            review = self._parse_peer_review(response["content"], model_key)
            if review:
                peer_reviews.append(review)  # ❌ Appends single review
                model_info = REQUESTY_MODELS[model_key]
                print(f"   Reviewed {len(review['scores'])} pitches")
                # ❌ This prints 7 but only 1 review is added!
```

**Issues:**
- `peer_reviews.append(review)` appends single review
- Should be `peer_reviews.extend(reviews)` to add all reviews
- Print statement is misleading: "Reviewed 7 pitches" but only 1 is extracted

#### Problem 3: JSON Regex Only Matches First Object (Line 387)

```python
# Try to extract JSON from response (non-greedy)
review = None
json_match = re.search(r"\{.*?\}", content_stripped, re.DOTALL)
#                                ^^^ Non-greedy match = FIRST object only
if json_match:
    try:
        review = json.loads(json_match.group(0))
```

**Issues:**
- Regex `\{.*?\}` is non-greedy and matches **first** JSON object only
- If model returns `[{review1}, {review2}, {review3}]`, regex matches `{review1}` only
- Fallback with `JSONDecoder().raw_decode()` also only decodes first object

---

## 3. Expected Behavior

### For N Pitches and N Models

Each model should generate **N-1 reviews** (reviewing all pitches except their own):

| Scenario | Models | Pitches per Model | Expected Reviews |
|----------|--------|-------------------|------------------|
| 4 models × 4 pitches | 4 | 3 reviews each | 4 × 3 = **12 reviews** |
| 5 models × 5 pitches | 5 | 4 reviews each | 5 × 4 = **20 reviews** |
| N models × N pitches | N | N-1 reviews each | N × (N-1) reviews |

### Expected Data Flow

```
1. Model generates N-1 reviews as JSON array:
   [
     {review for Pitch A, scores: {...}, ...},
     {review for Pitch B, scores: {...}, ...},
     {review for Pitch C, scores: {...}, ...}
   ]

2. Parser extracts ALL reviews:
   _parse_peer_review() -> List[Dict[str, Any]]  # List of reviews

3. Caller extends peer_reviews list:
   peer_reviews.extend(reviews)  # Add all reviews

4. Final output: N × (N-1) reviews stored
```

### Expected Output for Test Case

```
📈 Expected reviews: 12

📋 Reviews per model:
   - gpt-4.1-trader: 3 reviews (Pitch B, C, D)
   - Expert_Trader_Bot: 3 reviews (Pitch A, C, D)
   - ExpertTraderAI: 3 reviews (Pitch A, B, D)
   - claude-3-7-sonnet: 3 reviews (Pitch A, B, C)

Total: 4 models × 3 reviews = 12 reviews ✅
```

---

## 4. Evidence

### Test Output

See `peer_review_output.json`:

```json
{
  "total_reviews": 5,
  "expected_reviews": 12,
  "bug_confirmed": true,
  "reviews_by_reviewer": {
    "gpt-4.1-trader": 1,
    "Expert_Trader_Bot": 1,
    "ExpertTraderAI": 1,
    "claude-3-7-sonnet-20250219": 1,
    "model_name": 1
  }
}
```

### Code Evidence

1. **Parser signature:** `-> Dict[str, Any] | None` (single review)
2. **Explicit discard:** `review = review[0]` on line 433
3. **Single append:** `peer_reviews.append(review)` on line 182
4. **Regex limitation:** `\{.*?\}` matches first object only

### Console Output

```
✅ CHATGPT (CHATGPT)
   Reviewed 7 pitches        # ❌ Misleading: only 1 extracted
   Average score: 5.71/10

✅ GEMINI (GEMINI)
   Reviewed 7 pitches        # ❌ Misleading: only 1 extracted
   Average score: 4.86/10
```

---

## 5. Impact Assessment

### Functional Impact

- **Critical:** Council decisions are based on incomplete peer review data
- **Bias:** Only "Pitch A" reviews are captured; other pitches receive no scrutiny
- **Incomplete analysis:** Chairman sees only 4-5 reviews instead of 12
- **Undermines anonymization:** Pattern of missing reviews may reveal biases

### Data Impact

- **Database:** Only ~33% of expected peer review records are stored
- **Postmortem analysis:** Cannot analyze full peer review dynamics
- **Model comparison:** Cannot compare how different models critique different pitches

### User Stories Affected

- ❌ "As a systematic trader, I want unbiased peer review" → BROKEN (only 1 pitch reviewed)
- ❌ "As a researcher, I want to analyze how models critique each other" → BROKEN (missing 67% of reviews)

---

## 6. Proposed Fix (High-Level)

### Changes Required

1. **Update `_parse_peer_review()` signature:**
   - Change from `-> Dict[str, Any] | None`
   - To `-> List[Dict[str, Any]]`
   - Return empty list on error (not `None`)

2. **Update parser logic:**
   - Remove `review = review[0]` discard logic
   - If `isinstance(review, dict)`: wrap in list `[review]`
   - If `isinstance(review, list)`: return as-is
   - Validate each review in the list individually

3. **Update `_generate_peer_reviews()` caller:**
   - Change from `peer_reviews.append(review)`
   - To `peer_reviews.extend(reviews)`
   - Update print statement to show actual count

4. **Update prompt:**
   - Clarify expected output format: `[{review1}, {review2}, ...]`
   - Specify: "Return JSON array with one review per pitch (excluding your own)"

5. **Improve JSON extraction:**
   - Use `json.loads(content_stripped)` directly (handles arrays)
   - Keep fallback with `raw_decode()` but extract full array

---

## 7. Test Plan

### Unit Tests

- Parse single review object → returns list with 1 item
- Parse array of reviews → returns list with N items
- Parse invalid JSON → returns empty list
- Parse empty array → returns empty list

### Integration Test

- 4 PM pitches → expect 12 peer reviews (4 × 3)
- Verify each model reviews exactly N-1 pitches
- Verify no model reviews their own pitch
- Verify all pitches are reviewed by all other models

### Regression Test

- Existing council integration tests continue to pass
- Database save logic handles multiple reviews correctly
- Frontend displays all peer reviews

---

## 8. References

### Files Analyzed

- `backend/pipeline/stages/peer_review.py` (lines 334-469)
- `test_peer_review_bug.py` (reproduction script)
- `peer_review_output.json` (test results)

### Related Documents

- `spec.md` - Acceptance criteria requiring N-1 reviews per model
- `implementation_plan.json` - Phase 2 fix details

---

## Conclusion

**Bug Status:** ✅ CONFIRMED

The peer review system has a critical bug where only **one review per model** is extracted instead of **N-1 reviews**. The root cause is explicit discard logic in `_parse_peer_review()` (line 433: `review = review[0]`) combined with a function signature that returns a single dict instead of a list.

**Next Steps:** Proceed to Phase 2 (Fix Peer Review Parser) to implement the changes outlined in Section 6.

---

**Test Command:**
```bash
python test_peer_review_bug.py
```

**Artifacts:**
- `test_peer_review_bug.py` - Reproduction script
- `peer_review_output.json` - Detailed test results
- `peer_review_test_output.txt` - Console output
