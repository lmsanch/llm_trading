# Project Changelog

This file tracks all significant changes to the LLM Trading system.

## Template (Copy for New Entries)

```markdown
## [DATE]: [Brief Description]

### Added
- [New feature 1]

### Changed
- [Modified behavior 1]

### Fixed
- [Bug fix 1]

### Technical
- [Infrastructure change]

### Files Modified
- `path/to/file` - [what changed]

### Commands Run
```bash
# Important commands
```

### Impact
- [Effect on system/users]

### Lessons Learned
- [What we learned]

### Blocked/TODO
- [Still pending]
```

---

## 2026-01-04: Strengthened PM Pitch Prompt to Prevent Technical Indicator Generation

### Problem
ChatGPT PM model was generating pitches that mentioned technical indicators (RSI, MACD, etc.), which are banned in this macro/fundamental-only trading system. The validation logic correctly rejected these pitches, but this created a poor user experience with silent failures.

### Changed
- **Reinforced PM pitch prompt** with prominent warnings at THREE locations:
  1. System message header (lines 148-175)
  2. User prompt header (lines 236-260)
  3. Important Rules section (lines 312-325)
- Added visual markers (⚠️🚫 emojis, ALL CAPS) to make the prohibition impossible to miss
- Explicitly listed ALL banned indicators: RSI, MACD, EMA, SMA, Bollinger Bands, Stochastic, Fibonacci, ATR, ADX
- Added positive examples of allowed reasoning (macro regime, fundamental catalysts, narratives)
- Made consequences crystal clear: "INSTANTLY REJECTED"

### Fixed
- Silent errors when PM pitches were rejected for containing technical indicators
- Removed confusing prompt language that mentioned "Include frozen indicators with thresholds" (line 158)

### Files Modified
- `backend/pipeline/stages/pm_pitch.py` - Strengthened prompt in 3 locations (system message, user prompt, rules section)

### Technical Details

**Before:**
```python
# Ban was buried in middle of prompt, easy to miss
"5. Include frozen indicators with thresholds"  # Confusing!
"- **FORBIDDEN**: Do NOT use technical indicators..."  # Hidden in rules
```

**After:**
```python
# Ban appears 3 times, with visual markers
⚠️⚠️⚠️ ABSOLUTE PROHIBITION - YOUR PITCH WILL BE INSTANTLY REJECTED ⚠️⚠️⚠️
DO NOT MENTION ANY TECHNICAL INDICATORS
# Repeated at start of user prompt
# Repeated in rules section
```

### Impact
- **User Experience**: PM models should now avoid technical indicators entirely, preventing rejection errors
- **System Reliability**: Clearer prompts reduce need for retry logic
- **Training Data Quality**: When models do comply, we get cleaner macro/fundamental analysis

### Lessons Learned
- **Prompt engineering hierarchy**: Most important constraints must appear FIRST, not buried in rules
- **Visual markers work**: Emojis and ALL CAPS help LLMs identify critical instructions
- **Repetition matters**: Saying something once is not enough; say it 3 times in different contexts
- **Positive + negative**: Show both what NOT to do AND what TO do instead

### Testing Required
- Generate PM pitches from all 4 models (ChatGPT, Gemini, Claude, Grok)
- Verify no technical indicator keywords appear in thesis_bullets or risk_notes
- Monitor rejection rate (should drop significantly)

### Blocked/TODO
- [ ] Test end-to-end: select research, load data, generate PM, verify prompt works
- [ ] Monitor rejection rate over next 10 pitch generations
- [ ] If rejections persist, consider pre-validation step or additional prompt layers

---


