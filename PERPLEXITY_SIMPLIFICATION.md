# Research Pipeline Simplification - Perplexity Only

**Date**: 2026-01-02  
**Status**: Complete

---

## Summary

The research pipeline has been simplified to use **only Perplexity Sonar Deep Research**, removing all Gemini-related UI elements, backend logic, and configuration.

---

## Changes Made

### Frontend Changes

#### 1. **ResearchTab.jsx** - Main Research Component
- **Default model selection**: Changed from `{perplexity: false, gemini: false}` to `{perplexity: true}`
- **Orchestration Setup**: Removed model selection UI, now shows single "Research Provider" card with Perplexity pre-selected
- **Running State**: Changed from grid of 2 cards to single centered card showing Perplexity progress
- **Complete State**: Simplified result display to single ResearchPackCard instead of grid layout
- **Removed**: All Gemini-specific UI elements, tabs, and conditional rendering

### Backend Changes

#### 2. **backend/main.py** - FastAPI Backend
- **GenerateResearchRequest**: Changed default models from `["perplexity", "gemini"]` to `["perplexity"]`
- **Job initialization**: Simplified to always create perplexity status, removed gemini-specific branches
- **Progress updates**: Removed all gemini-specific progress tracking
- **Job completion**: Simplified to single perplexity completion handler

#### 3. **backend/pipeline/stages/research.py** - Research Stage
- **Default models**: Changed from `["perplexity", "gemini"]` to `["perplexity"]`
- **Documentation**: Updated docstring to reflect Perplexity-only operation

---

## What Was NOT Changed

### Kept for Future Use
- **Gemini client code**: `backend/research/gemini_client.py` - preserved for potential future reactivation
- **Database schema**: Still supports both providers in `research_reports` table
- **PM Pitch logic**: No changes needed, works with single research pack
- **Mock data**: Gemini references in mock data kept for testing
- **Account mappings**: GEMINI Alpaca account unchanged (used by PM, not research)

---

## User Experience

### Before
1. User had to select between Perplexity and/or Gemini
2. Both providers would run in parallel
3. Two research cards displayed side-by-side
4. Calendar showed both providers with color coding

### After
1. Perplexity is always selected (no choice needed)
2. Single provider runs (faster, simpler)
3. One research card displayed (focused, cleaner)
4. Calendar shows single provider reports

---

## Technical Details

### Session Storage Keys
Still stores `selectedModels` but now only contains `{perplexity: true}`

### API Endpoints
- `/api/research/generate` - Now expects `models: ["perplexity"]` by default
- `/api/research/status` - Returns perplexity-only progress
- All other endpoints unchanged

### Pipeline Flow
```
Research Stage
  ↓ (Perplexity Sonar Deep Research ONLY)
PM Pitch Stage
  ↓ (5 PM models receive single research pack)
Peer Review Stage
  ↓ (anonymized evaluation)
Chairman Stage
  ↓ (Claude Opus 4.5 synthesis)
Execution Stage
  ↓ (place approved trades)
```

---

## Files Modified

1. `/frontend/src/components/dashboard/tabs/ResearchTab.jsx`
2. `/backend/main.py`
3. `/backend/pipeline/stages/research.py`

---

## Testing Checklist

- [ ] Research generation starts with Perplexity only
- [ ] Progress bar updates correctly
- [ ] Single research card displays on completion
- [ ] Calendar shows historical Perplexity reports
- [ ] No Gemini UI elements visible
- [ ] Backend job tracking works correctly
- [ ] Database saves research correctly
- [ ] PM Pitch stage receives research data

---

## Rollback Instructions

If needed to restore Gemini support:

1. Revert `ResearchTab.jsx` to previous version
2. Revert `backend/main.py` default models to `["perplexity", "gemini"]`
3. Revert `backend/pipeline/stages/research.py` default to include gemini
4. Gemini client code still exists, no need to restore

---

## Notes

- This simplification makes the system **faster** (one provider instead of two)
- UI is **cleaner** and more focused
- **No functionality lost** - Perplexity provides comprehensive research
- Gemini code preserved if needed later
- Database still supports both providers for historical data

---

**Status**: Ready for testing
