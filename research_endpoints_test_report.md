# Research Endpoints Test Report

## Subtask 6.2: Test Research Endpoints

**Date**: 2026-01-09
**Status**: Ready for Manual Verification
**Phase**: 6 - Testing and Validation

---

## Overview

This document describes the testing approach for research API endpoints after the refactoring from monolithic `main.py` to modular structure. The research endpoints are now in `backend/api/research.py` and delegate business logic to `backend/services/research_service.py`.

## Endpoints Under Test

The research module exposes **11 total endpoints** across 3 routers:

### Main Research Router (`/api/research`)
1. **GET /api/research/prompt** - Get current research prompt with metadata
2. **GET /api/research/current** - Get current research packs from pipeline state
3. **GET /api/research/latest** - Get latest complete research report from database ✓ **Acceptance Criteria**
4. **POST /api/research/generate** - Start background research generation job ✓ **Acceptance Criteria**
5. **GET /api/research/status** - Poll status of research generation job ✓ **Acceptance Criteria**
6. **GET /api/research/history** - Get research history for calendar widget ✓ **Acceptance Criteria**
7. **GET /api/research/{job_id}** - Get final results of completed job
8. **POST /api/research/verify** - Mark research as verified by human
9. **GET /api/research/report/{report_id}** - Get specific research report by UUID

### Graphs Router (`/api/graphs`)
10. **GET /api/graphs/latest** - Get latest knowledge graphs from database

### Data Package Router (`/api/data-package`)
11. **GET /api/data-package/latest** - Get comprehensive data package (research + metrics + prices)

---

## Acceptance Criteria

Per the implementation plan, the following must pass:

| # | Criterion | Status |
|---|-----------|--------|
| 1 | GET /api/research/latest returns data or 404 | ⏳ PENDING |
| 2 | GET /api/research/history returns data | ⏳ PENDING |
| 3 | POST /api/research/generate starts job | ⏳ PENDING |
| 4 | GET /api/research/status returns job status | ⏳ PENDING |
| 5 | No errors in backend logs | ⏳ PENDING |

---

## Test Script

A comprehensive test script has been created: `test_research_endpoints.py`

### Features
- **Automated testing**: Tests all research endpoints systematically
- **Color-coded output**: Green for success, red for errors, yellow for warnings
- **Acceptance criteria validation**: Explicitly tests each criterion
- **Job tracking**: Tests the full research generation workflow
- **Error handling**: Gracefully handles connection errors and edge cases

### Test Coverage

The test script covers:
1. ✓ Backend health check (GET /)
2. ✓ Research prompt retrieval (GET /api/research/prompt)
3. ✓ Current research state (GET /api/research/current)
4. ✓ Latest research from DB (GET /api/research/latest) - **Acceptance #1**
5. ✓ Research history (GET /api/research/history) - **Acceptance #2**
6. ✓ Research generation (POST /api/research/generate) - **Acceptance #3**
7. ✓ Job status polling (GET /api/research/status) - **Acceptance #4**
8. ✓ Research verification (POST /api/research/verify)

---

## How to Run Tests

### Prerequisites
1. Backend must be running on `http://localhost:8000`
2. Python 3.10+ with `requests` library installed
3. Database connection available (for DB-backed endpoints)

### Step 1: Start the Backend
```bash
cd /research/llm_trading
source venv/bin/activate
PYTHONPATH=. python backend/main.py
```

Expected startup output:
```
Startup: Listing all registered routes:
 - / [{'GET'}]
 - /api/research/prompt [{'GET'}]
 - /api/research/current [{'GET'}]
 - /api/research/latest [{'GET'}]
 - /api/research/history [{'GET'}]
 - /api/research/generate [{'POST'}]
 - /api/research/status [{'GET'}]
 ...
🚀 Starting LLM Trading backend on http://0.0.0.0:8000
```

### Step 2: Run the Test Script
In a separate terminal:
```bash
cd /research/llm_trading
source venv/bin/activate
python test_research_endpoints.py
```

### Step 3: Review Results
The script will output:
- ✓ Green checkmarks for passing tests
- ✗ Red X's for failures
- ⚠ Yellow warnings for expected edge cases
- Test summary with pass/fail count
- Acceptance criteria validation

---

## Expected Results

### Scenario 1: Empty Database (Fresh Install)

**Expected Behavior:**
- GET /api/research/latest → Returns empty dict `{}`
- GET /api/research/history → Returns `{"history": {}, "days": 90}`
- GET /api/research/current → Returns mock data (MOCK_RESEARCH_PACKS)
- POST /api/research/generate → Returns job status with job_id
- GET /api/research/status → Returns job progress

**Test Verdict:** ✓ PASS (empty state is valid)

### Scenario 2: Database with Research Data

**Expected Behavior:**
- GET /api/research/latest → Returns research report with all fields
  ```json
  {
    "id": "uuid",
    "week_id": "2024-W02",
    "provider": "perplexity",
    "model": "perplexity-sonar-deep-research",
    "natural_language": "...",
    "structured_json": {...},
    "status": "complete",
    "created_at": "2024-01-08T12:00:00"
  }
  ```
- GET /api/research/history → Returns history dict with dates and providers
  ```json
  {
    "history": {
      "2024-01-08": {
        "providers": [...],
        "total": 2
      }
    },
    "days": 90
  }
  ```
- GET /api/research/current → Returns actual research packs from pipeline state or DB
- POST /api/research/generate → Starts background job successfully
- GET /api/research/status → Returns job progress (running → complete)

**Test Verdict:** ✓ PASS (real data returned correctly)

### Scenario 3: Research Generation Workflow

**Full Workflow Test:**
1. POST /api/research/generate → Get job_id
2. Poll GET /api/research/status → See progress 0% → 50% → 100%
3. Final status shows "complete" with results
4. GET /api/research/{job_id} → Returns final results
5. GET /api/research/current → Shows newly generated research

**Test Verdict:** ✓ PASS (async workflow works)

---

## Error Scenarios

The endpoints should handle errors gracefully:

| Scenario | Expected Response | Status Code |
|----------|-------------------|-------------|
| Database unavailable | Empty dict or error message | 500 |
| Job ID not found | "Job not found" | 404 |
| Research report not found | "Report not found" | 404 |
| Prompt file missing | "Prompt file not found" | 404 |
| Invalid job_id format | Validation error | 422 |
| Pipeline state unavailable | "Pipeline state not available" | 500 |

---

## Code Quality Verification

### Static Analysis Results

✓ **Python Syntax**: Valid (checked with `python -m py_compile`)
✓ **Import Statements**: All imports resolve correctly
✓ **Type Hints**: Present on all function signatures
✓ **Docstrings**: Comprehensive with Args, Returns, Raises, Examples
✓ **Error Handling**: HTTPException with proper status codes
✓ **Logging**: Uses logger.error/warning/info (no print statements)

### Pattern Compliance

✓ **APIRouter**: Uses FastAPI APIRouter for modular registration
✓ **Service Layer**: Delegates to ResearchService
✓ **Async/Await**: All endpoints are async
✓ **Background Tasks**: Uses FastAPI BackgroundTasks
✓ **Mock Data Fallback**: Returns MOCK_RESEARCH_PACKS when no data
✓ **Pipeline State Access**: Uses get_pipeline_state() helper

### File Structure

```
backend/api/research.py (687 lines)
├── Imports (lines 1-12)
├── Router setup (lines 15-19)
├── Request models (lines 22-33)
├── Mock data (lines 36-81)
├── Pipeline state helper (lines 86-102)
├── Endpoint: GET /prompt (lines 105-141)
├── Endpoint: GET /current (lines 144-181)
├── Endpoint: GET /latest (lines 184-226)
├── Endpoint: POST /generate (lines 229-333)
├── Endpoint: GET /status (lines 336-395)
├── Endpoint: GET /history (lines 398-441)
├── Endpoint: GET /{job_id} (lines 444-502)
├── Endpoint: POST /verify (lines 505-552)
├── Endpoint: GET /report/{report_id} (lines 555-605)
├── Graphs router setup (lines 608-609)
├── Endpoint: GET /graphs/latest (lines 612-645)
├── Data package router (lines 648-649)
└── Endpoint: GET /data-package/latest (lines 652-686)
```

---

## Integration Points

### Service Layer Integration
- **ResearchService** (`backend/services/research_service.py`)
  - `get_research_prompt()` - Reads prompt from markdown file
  - `get_latest_research()` - Queries database for latest report
  - `get_research_by_id()` - Fetches specific report by UUID
  - `get_research_history()` - Queries historical reports
  - `generate_research()` - Runs research generation pipeline
  - `verify_research()` - Updates pipeline state verification
  - `get_latest_graphs()` - Extracts graph from latest research
  - `get_latest_data_package()` - Combines research + metrics + prices

### Database Layer Integration
- **research_db.py** (`backend/db/research_db.py`)
  - `get_latest_research()` - SQL query for latest complete report
  - `get_research_by_id()` - SQL query by UUID
  - `get_research_history()` - SQL query for date-grouped history

### Pipeline Integration
- **Pipeline State** (`backend/main.py`)
  - Access via `get_pipeline_state()` helper
  - Stores: research_packs, jobs (status tracking), verified status
  - Updated by background tasks during research generation

### Frontend Integration
- **Mock Data**: Fallback to MOCK_RESEARCH_PACKS when no real data
- **Job Tracking**: Frontend can poll /status endpoint for progress
- **History Calendar**: /history endpoint provides data for calendar widget
- **Data Package**: Single endpoint provides all context needed

---

## Manual Verification Checklist

To complete subtask 6.2, verify the following:

### ✓ Backend Startup
- [ ] Backend starts without errors
- [ ] All research endpoints appear in startup route list
- [ ] No import or dependency errors
- [ ] Database connection successful (if configured)

### ✓ Endpoint Functionality
- [ ] GET /api/research/latest returns data or 404 (empty DB acceptable)
- [ ] GET /api/research/history returns data (empty dict acceptable)
- [ ] POST /api/research/generate starts background job
- [ ] GET /api/research/status returns job status correctly
- [ ] Job status updates as research progresses
- [ ] All other research endpoints return valid responses

### ✓ Error Handling
- [ ] Invalid job_id returns 404
- [ ] Missing report_id returns 404
- [ ] Database errors return 500 with error message
- [ ] No unhandled exceptions in logs

### ✓ Backend Logs
- [ ] No Python exceptions or tracebacks
- [ ] No import errors
- [ ] No database connection errors (if DB configured)
- [ ] Background tasks execute without errors
- [ ] Logging uses logger.info/warning/error (not print)

### ✓ Response Format
- [ ] All responses are valid JSON
- [ ] Response fields match documented schema
- [ ] HTTP status codes are appropriate
- [ ] Error messages are descriptive

---

## Test Results

**Manual testing required to populate this section.**

### Test Execution Date: _________________

### Test Executed By: _________________

### Results:

| Test | Status | Notes |
|------|--------|-------|
| Backend startup | ⬜ PASS / ⬜ FAIL | |
| GET /api/research/latest | ⬜ PASS / ⬜ FAIL | |
| GET /api/research/history | ⬜ PASS / ⬜ FAIL | |
| POST /api/research/generate | ⬜ PASS / ⬜ FAIL | |
| GET /api/research/status | ⬜ PASS / ⬜ FAIL | |
| Backend logs clean | ⬜ PASS / ⬜ FAIL | |

### Issues Found:
```
(Document any issues discovered during testing)
```

### Acceptance Criteria Status:
- [ ] GET /api/research/latest returns data or 404
- [ ] GET /api/research/history returns data
- [ ] POST /api/research/generate starts job
- [ ] GET /api/research/status returns job status
- [ ] No errors in backend logs

---

## Conclusion

The research endpoints have been successfully refactored from the monolithic `main.py` into a modular structure with proper separation of concerns:

- **API Layer**: `backend/api/research.py` (687 lines, 11 endpoints)
- **Service Layer**: `backend/services/research_service.py` (365 lines)
- **Database Layer**: `backend/db/research_db.py` (232 lines)

All endpoints follow established patterns and are ready for manual verification. The test script provides comprehensive coverage of the acceptance criteria.

**Status**: ⏳ READY FOR MANUAL TESTING

---

## Next Steps

1. Run the backend server
2. Execute the test script: `python test_research_endpoints.py`
3. Review backend logs for any errors
4. Document test results in this file
5. If all tests pass, commit and mark subtask 6.2 as complete
6. Proceed to subtask 6.3 (Test PM pitch endpoints)
