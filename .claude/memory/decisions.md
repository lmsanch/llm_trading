# Architectural Decision Records

This file documents key technical and design decisions.

---

## ADR-001: Multi-Layered Prompt Reinforcement for Critical Constraints

**Date**: 2026-01-04  
**Status**: Accepted

### Context
LLM Trading system has hard constraint: PM pitches must be based on macro/fundamental reasoning only, with technical indicators (RSI, MACD, etc.) strictly forbidden. Initial prompt mentioned this constraint once, buried in a long rules list. ChatGPT model still generated RSI-based pitch, which was correctly rejected by validation logic but created poor UX.

**Problem**: How do we ensure LLMs respect critical constraints without:
1. Post-generation filtering (wasteful, creates latency)
2. Complex retry logic (expensive, unreliable)
3. Overly restrictive validation (might reject valid pitches)

### Decision
Implement **multi-layered prompt reinforcement** pattern:

1. **System message header**: Place constraint FIRST with visual markers
2. **User prompt header**: Repeat constraint before any task instructions
3. **Rules section**: Reinforce constraint in structured rules list
4. **Visual markers**: Use emojis (⚠️🚫) and ALL CAPS for salience
5. **Explicit lists**: Name ALL banned terms, don't use "etc."
6. **Positive examples**: Show what TO do, not just what NOT to do
7. **Clear consequences**: State exactly what happens if violated

### Rationale

**Why this approach?**
- **Attention mechanism**: LLMs pay more attention to content at START of prompts
- **Repetition**: Saying something 3 times in different contexts increases compliance
- **Visual salience**: Emojis and formatting help models identify critical constraints
- **Cognitive load**: Explicit lists reduce ambiguity vs. "e.g., RSI, MACD, etc."

**Alternatives considered:**
1. **Post-generation filtering**: Wasteful, adds latency, doesn't prevent generation
2. **JSON schema constraints**: Can't express semantic constraints like "no technical terms"
3. **Few-shot examples**: Helpful but not sufficient for hard constraints
4. **Fine-tuning**: Too expensive, not flexible enough for rapid iteration

### Consequences

**Positive**:
- Significant reduction in constraint violations (testing required to quantify)
- Better UX (fewer rejection errors, faster generation)
- Cleaner training data (compliant outputs can be used for fine-tuning later)
- Maintainable (easy to add new constraints using same pattern)

**Negative**:
- Longer prompts (adds ~200 tokens to system message)
- Slightly higher API costs (~$0.0001 per generation at GPT-4 pricing)
- Risk of "over-prompting" causing model confusion (monitor carefully)

### Implementation Notes

**Location**: `backend/pipeline/stages/pm_pitch.py`

**Key sections**:
1. Lines 148-175: System message with constraint header
2. Lines 236-260: User prompt with constraint banner
3. Lines 312-325: Rules section with reinforcement

**How to verify**:
```bash
# Generate PM pitches
curl -X POST http://localhost:8200/api/pitches/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "chatgpt", "research_report_id": "..."}'

# Check for banned keywords in response
grep -i "rsi\|macd\|bollinger\|stochastic" response.json
# Should return no matches
```

**Validation logic**: `pm_pitch.py` lines 540-575
- Scans pitch content for banned keywords
- Rejects pitch if any found
- Returns error with specific keyword mentioned

### Monitoring Plan

Track metrics over next 100 pitch generations:
- Rejection rate for technical indicators
- Average prompt tokens used
- Time to first token (check for latency impact)
- User satisfaction (manual feedback)

**Success criteria**: <5% rejection rate for technical indicators (vs. current ~25%)

### Related ADRs
- ADR-002: (Future) PM Pitch Schema v2 - Risk Normalization
- ADR-003: (Future) Research-to-PM Linking via Timestamps

---


