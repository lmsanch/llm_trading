# Current Task

**Last Updated**: 2026-01-04

## Active Work
**Status**: Testing Required

**Task**: PM Tab GUI Modifications & Technical Indicator Ban

### Recently Completed
- [x] Strengthened PM pitch prompt to prevent technical indicators
- [x] Added research_date column to pm_pitches table
- [x] Updated frontend to show PM logos and empty states
- [x] Fixed database queries to handle TIMESTAMPTZ properly
- [x] Fixed NoneType errors in pipeline_state initialization
- [x] Updated research report dropdown to show date+time

### Testing Required
- [ ] Test end-to-end PM pitch generation workflow
- [ ] Verify technical indicators are no longer generated
- [ ] Confirm PM reports save and load correctly with research_date

### Next Steps
1. User to test "Generate New Report" for ChatGPT PM
2. Verify no technical indicator keywords appear
3. Confirm report saves to database with correct research_date
4. Test loading existing PM reports for specific research dates

## Context
Working on PM pitch generation system that must be macro/fundamental-only (no technical indicators like RSI, MACD, etc.). Previous attempt generated RSI-based pitch which was correctly rejected, but this created poor UX. Strengthened prompt with prominent warnings to prevent generation of banned indicators.

## Files Being Modified
- `backend/pipeline/stages/pm_pitch.py` - PM pitch prompt
- `backend/main.py` - Database save/load with research_date
- `frontend/src/components/dashboard/tabs/PMsTab.jsx` - PM card display
- `backend/storage/postgres_schema.sql` - Database schema


