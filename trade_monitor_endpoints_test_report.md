# Trade and Monitor Endpoints Test Report

## Overview

This document describes the test suite for trade execution and monitoring API endpoints after refactoring from the monolithic `main.py` into modular structure.

**Test Suite**: `test_trade_monitor_endpoints.py`
**Endpoints Tested**: 4 endpoints across 2 API modules
**Created**: 2026-01-09
**Subtask**: 6.5 - Test trade and monitor endpoints

---

## Endpoints Under Test

### Monitor Endpoints (backend/api/monitor.py)

1. **GET /api/positions** - Get current positions across all trading accounts
2. **GET /api/accounts** - Get account summaries for all trading accounts

### Trade Endpoints (backend/api/trades.py)

3. **GET /api/trades/pending** - Get pending trades from pipeline state
4. **POST /api/trades/execute** - Execute trades using bracket orders

---

## Acceptance Criteria

From `implementation_plan.json` subtask 6.5:

| # | Criterion | Status | Test Coverage |
|---|-----------|--------|---------------|
| 1 | GET /api/positions returns data or mock data | ✅ TEST READY | `test_get_positions()` |
| 2 | GET /api/accounts returns data or mock data | ✅ TEST READY | `test_get_accounts()` |
| 3 | GET /api/trades/pending returns data | ✅ TEST READY | `test_get_pending_trades()` |
| 4 | POST /api/trades/execute handles requests correctly | ✅ TEST READY | `test_execute_trades_empty()`, `test_execute_trades_invalid()` |
| 5 | No errors in backend logs | ⏳ MANUAL CHECK | Requires running backend and reviewing logs |

---

## Test Script Features

### test_trade_monitor_endpoints.py (475 lines)

**Automated Testing Features:**
- Tests all 4 trade and monitor endpoints systematically
- Color-coded console output (green/red/yellow/blue)
- Acceptance criteria validation
- Comprehensive error handling
- Edge case testing (empty requests, invalid IDs)
- Mock data fallback verification
- Multi-account validation (all 6 accounts)

**Test Functions:**
1. `test_health_check()` - Verify backend is running
2. `test_get_positions()` - Test positions endpoint
3. `test_get_accounts()` - Test accounts endpoint
4. `test_get_pending_trades()` - Test pending trades endpoint
5. `test_execute_trades_empty()` - Test execute with empty list (should fail)
6. `test_execute_trades_invalid()` - Test execute with invalid IDs

**Output Features:**
- ANSI color codes for readability
- Structured test headers
- Success/error/warning/info messages
- Test summary with pass/fail counts
- Acceptance criteria checklist

---

## Architecture Validated

### Monitor Endpoints Architecture

**API Layer**: `backend/api/monitor.py` (236 lines, 2 endpoints)
- 1 router: monitoring (prefix="/api")
- Uses MultiAlpacaManager for multi-account queries
- Mock data fallback (MOCK_POSITIONS, MOCK_ACCOUNTS)
- Comprehensive error handling and logging
- No HTTP exceptions (returns mock data on error to avoid breaking frontend)

**Integration Layer**: `backend/multi_alpaca_client.py`
- `MultiAlpacaManager` - Manages all 6 trading accounts
- `get_all_positions()` - Fetches positions from all accounts in parallel
- `get_all_accounts()` - Fetches account summaries from all accounts in parallel
- Uses asyncio.gather for concurrent API calls

**Alpaca API Integration**:
- Queries live data from Alpaca Trading API
- 6 paper trading accounts: COUNCIL, CHATGPT, GEMINI, CLAUDE, GROQ, DEEPSEEK
- Real-time position and account data

### Trade Endpoints Architecture

**API Layer**: `backend/api/trades.py` (224 lines, 2 endpoints)
- 1 router: trades (prefix="/api/trades")
- Uses TradeService for business logic
- ExecuteTradesRequest Pydantic model for request validation
- Comprehensive error handling and logging
- Per-trade error handling (failed trades don't prevent others from executing)

**Service Layer**: `backend/services/trade_service.py` (271 lines)
- 2 service methods for trade operations:
  - `get_pending_trades()` - Retrieves pending trades from pipeline state
  - `execute_trades()` - Async method that executes trades using bracket orders
- Pipeline state integration
- Database access via pitch_db module
- Multi-account trading via MultiAlpacaManager
- Bracket order creation (main + take profit + stop loss)

**Database Layer**: `backend/db/pitch_db.py`
- `find_pitch_by_id()` - Retrieves pitch data for trade execution
- Contains entry/exit policies (entry_price, target_price, stop_price)

**Trading Integration**:
- `backend/alpaca_integration/orders.py` - Bracket order creation
- `create_bracket_order_from_pitch()` - Creates bracket orders from pitch data
- `backend/multi_alpaca_client.py` - Multi-account trading execution

---

## How to Run Tests

### Step 1: Start the backend

```bash
cd /research/llm_trading
source venv/bin/activate
PYTHONPATH=. python backend/main.py
```

Expected output:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Step 2: Run test script (in another terminal)

```bash
cd /research/llm_trading
source venv/bin/activate
python test_trade_monitor_endpoints.py
```

### Step 3: Review results

- Test script outputs color-coded results
- Check acceptance criteria validation
- Review backend logs for errors
- Document results in this file

---

## Expected Test Output

### Success Scenario

```
======================================================================
Trade and Monitor Endpoints Test Suite
Testing backend at: http://localhost:8000
======================================================================

======================================================================
TEST: Health Check - GET /
======================================================================
✓ Backend is running (status: 200)
ℹ Status: healthy

======================================================================
TEST: Get Positions - GET /api/positions
======================================================================
✓ Positions retrieved (status: 200)
✓ Found 6 position entries
ℹ First position structure:
✓   account: COUNCIL
✓   symbol: SPY
✓   qty: 50
✓   avg_price: 475.20
✓   current_price: 482.30
✓   pl: 355
ℹ Accounts found: {'COUNCIL', 'CHATGPT', 'GEMINI', 'CLAUDE', 'GROQ', 'DEEPSEEK'}

======================================================================
TEST: Get Accounts - GET /api/accounts
======================================================================
✓ Accounts retrieved (status: 200)
✓ Found 6 accounts
ℹ First account structure:
✓   name: COUNCIL
✓   equity: 100355
✓   cash: 75920
✓   pl: 355
✓ All 6 accounts present: ['CHATGPT', 'CLAUDE', 'COUNCIL', 'DEEPSEEK', 'GEMINI', 'GROQ']
ℹ Account P&L summary:
ℹ   COUNCIL: $355.00
ℹ   CHATGPT: $284.00
ℹ   GEMINI: $-39.00
ℹ   CLAUDE: $0.00
ℹ   GROQ: $249.00
ℹ   DEEPSEEK: $18.00
ℹ Total P&L across all accounts: $867.00

======================================================================
TEST: Get Pending Trades - GET /api/trades/pending
======================================================================
✓ Pending trades retrieved (status: 200)
ℹ No pending trades found (empty list)
ℹ This is normal if no council decision has been made yet

======================================================================
TEST: Execute Trades (Empty List) - POST /api/trades/execute
======================================================================
✓ Correctly rejected empty trade_ids (status: 400)
ℹ Error message: trade_ids list cannot be empty

======================================================================
TEST: Execute Trades (Invalid IDs) - POST /api/trades/execute
======================================================================
✓ Execute request accepted (status: 200)
✓ Response has correct structure
ℹ Overall status: success
ℹ Message: Processed 2 trade(s): 0 submitted, 2 errors, 0 skipped
ℹ Results for 2 trade(s):
⚠   Trade 99999: error - Pitch not found in database
⚠   Trade 99998: error - Pitch not found in database

======================================================================
TEST SUMMARY
======================================================================

  health                    PASS
  positions                 PASS
  accounts                  PASS
  pending_trades            PASS
  execute_empty             PASS
  execute_invalid           PASS

======================================================================
✓ ALL TESTS PASSED (6/6)
======================================================================

ACCEPTANCE CRITERIA CHECK
======================================================================

  ✓ GET /api/positions returns data or mock data
  ✓ GET /api/accounts returns data or mock data
  ✓ GET /api/trades/pending returns data
  ✓ POST /api/trades/execute handles requests correctly
  ⚠ MANUAL CHECK: No errors in backend logs
```

---

## Different Scenarios

### Scenario 1: Mock Data Fallback (Alpaca API unavailable)

If MultiAlpacaManager cannot connect to Alpaca API:

```
======================================================================
TEST: Get Positions - GET /api/positions
======================================================================
✓ Positions retrieved (status: 200)
✓ Found 6 position entries
ℹ Accounts found: {'COUNCIL', 'CHATGPT', 'GEMINI', 'CLAUDE', 'GROQ', 'DEEPSEEK'}
```

**Backend logs:**
```
ERROR: Error getting positions: Connection refused
WARNING: Falling back to mock positions data
```

This is **expected behavior** - endpoints should never fail, they fall back to mock data.

### Scenario 2: Live Alpaca Data

If MultiAlpacaManager successfully connects:

```
======================================================================
TEST: Get Positions - GET /api/positions
======================================================================
✓ Positions retrieved (status: 200)
✓ Found 6 position entries
ℹ First position structure:
✓   account: COUNCIL
✓   symbol: SPY
✓   qty: 50
✓   avg_price: 475.20
✓   current_price: 482.30
✓   pl: 355.50
```

**Backend logs:**
```
INFO: Retrieved 6 position entries
```

### Scenario 3: Pending Trades Present

If council has created pending trades:

```
======================================================================
TEST: Get Pending Trades - GET /api/trades/pending
======================================================================
✓ Pending trades retrieved (status: 200)
✓ Found 3 pending trades
ℹ First pending trade structure:
✓   id: 42
✓   account: COUNCIL
✓   symbol: SPY
✓   direction: BUY
✓   qty: 100
✓   status: pending
ℹ   conviction: 0.82
ℹ   entry_price: 471.20
ℹ   target_price: 485.00
ℹ   stop_price: 465.00
```

### Scenario 4: Valid Trade Execution

If executing with valid pitch IDs:

```
======================================================================
TEST: Execute Trades (Valid IDs) - POST /api/trades/execute
======================================================================
✓ Execute request accepted (status: 200)
✓ Response has correct structure
ℹ Overall status: success
ℹ Message: Processed 2 trade(s): 2 submitted, 0 errors, 0 skipped
ℹ Results for 2 trade(s):
✓   Trade 42: submitted - Bracket order submitted for COUNCIL
✓   Trade 43: submitted - Bracket order submitted for CHATGPT
```

**Backend logs:**
```
INFO: Executing 2 trade(s)
INFO: Creating bracket order for COUNCIL: BUY 100 SPY at 471.20
INFO: Bracket order submitted: order_id=abc123
INFO: Trade execution complete: 2 submitted, 0 errors, 0 skipped
```

---

## Error Scenarios

### 1. Backend Not Running

```
======================================================================
TEST: Health Check - GET /
======================================================================
✗ Cannot connect to backend. Is it running?
ℹ Expected backend at: http://localhost:8000

Backend is not running. Cannot proceed with tests.
ℹ Please start the backend with:
ℹ   cd /research/llm_trading
ℹ   PYTHONPATH=. python backend/main.py
```

**Resolution**: Start the backend server

### 2. Pipeline State Not Available

```
======================================================================
TEST: Get Pending Trades - GET /api/trades/pending
======================================================================
✓ Pending trades retrieved (status: 200)
ℹ No pending trades found (empty list)
```

**Backend logs:**
```
WARNING: Pipeline state not available, returning empty list
```

**Resolution**: This is normal behavior - endpoint returns empty list instead of failing

### 3. Invalid Request Body

```
======================================================================
TEST: Execute Trades (Invalid Request) - POST /api/trades/execute
======================================================================
✓ Validation error (status: 422)
ℹ Missing required field: trade_ids
```

**Resolution**: This is expected - Pydantic validation is working correctly

---

## Response Structures

### GET /api/positions

```json
[
    {
        "account": "COUNCIL",
        "symbol": "SPY",
        "qty": 50,
        "avg_price": 475.20,
        "current_price": 482.30,
        "pl": 355.0
    },
    {
        "account": "CLAUDE",
        "symbol": "-",
        "qty": 0,
        "avg_price": 0.0,
        "current_price": 0.0,
        "pl": 0.0
    }
]
```

**Notes**:
- Returns one entry per account
- Accounts with no positions show "-" symbol
- P&L is unrealized profit/loss

### GET /api/accounts

```json
[
    {
        "name": "COUNCIL",
        "equity": 100355.0,
        "cash": 75920.0,
        "pl": 355.0
    },
    {
        "name": "CHATGPT",
        "equity": 100284.0,
        "cash": 80984.0,
        "pl": 284.0
    }
]
```

**Notes**:
- Returns exactly 6 accounts
- P&L calculated as (equity - 100000)
- Starting balance for all accounts is $100,000

### GET /api/trades/pending

```json
[
    {
        "id": 42,
        "account": "COUNCIL",
        "symbol": "SPY",
        "direction": "BUY",
        "qty": 100,
        "status": "pending",
        "conviction": 0.82,
        "entry_price": 471.20,
        "target_price": 485.00,
        "stop_price": 465.00
    }
]
```

**Notes**:
- Returns empty list if no pending trades
- All trades have status="pending"
- Optional fields: conviction, entry_price, target_price, stop_price

### POST /api/trades/execute

**Request:**
```json
{
    "trade_ids": [42, 43]
}
```

**Response (Success):**
```json
{
    "status": "success",
    "message": "Processed 2 trade(s): 2 submitted, 0 errors, 0 skipped",
    "results": [
        {
            "trade_id": 42,
            "status": "submitted",
            "order_id": "abc123",
            "symbol": "SPY",
            "side": "buy",
            "qty": 100,
            "limit_price": 471.20,
            "take_profit_price": 485.00,
            "stop_loss_price": 465.00,
            "message": "Bracket order submitted for COUNCIL"
        },
        {
            "trade_id": 43,
            "status": "skipped",
            "message": "FLAT position - no trade executed"
        }
    ]
}
```

**Response (Error):**
```json
{
    "status": "success",
    "message": "Processed 1 trade(s): 0 submitted, 1 errors, 0 skipped",
    "results": [
        {
            "trade_id": 99999,
            "status": "error",
            "message": "Pitch not found in database"
        }
    ]
}
```

**Notes**:
- Per-trade error handling
- Failed trades don't prevent other trades from executing
- FLAT positions are automatically skipped
- Bracket orders include main + take profit + stop loss

---

## Code Quality Verification

### Python Syntax Validation

```bash
python -m py_compile test_trade_monitor_endpoints.py
# No output = success
```

✅ **Status**: Valid Python syntax

### Script Permissions

```bash
chmod +x test_trade_monitor_endpoints.py
```

✅ **Status**: Made executable

### Import Statements

```python
import requests
import json
import time
from typing import Dict, Any, List
```

✅ **Status**: Uses standard library and requests

### Error Handling

✅ All test functions have try/except blocks
✅ Connection errors handled gracefully
✅ HTTP errors reported clearly
✅ Unexpected exceptions caught and logged

---

## Pattern Compliance

✅ **Follows project patterns**: Uses requests library like previous tests
✅ **Comprehensive testing**: Covers all acceptance criteria
✅ **User-friendly output**: Color-coded with clear status messages
✅ **Automated**: Can be run repeatedly for regression testing
✅ **Documented**: Full test report with usage instructions
✅ **Follows test_research_endpoints.py, test_pitch_endpoints.py, and test_council_endpoints.py patterns exactly**
✅ **Edge case testing**: Tests empty requests and invalid IDs
✅ **Multi-account validation**: Verifies all 6 accounts are present

---

## Integration with Existing Codebase

The test script verifies the refactored trade and monitor endpoints work correctly:

- **API Layer**: Tests `backend/api/trades.py` and `backend/api/monitor.py` endpoints
- **Service Layer**: Indirectly tests `backend/services/trade_service.py`
- **Database Layer**: Indirectly tests `backend/db/pitch_db.py`
- **Pipeline State**: Tests pending trades retrieval from pipeline state
- **Multi-Account Trading**: Tests MultiAlpacaManager integration
- **Bracket Orders**: Tests bracket order creation and execution
- **Mock Data Fallback**: Verifies graceful degradation when live data unavailable

---

## Manual Verification Checklist

To complete subtask 6.5, perform these manual checks:

### Pre-Test Setup
- [ ] Backend is running at http://localhost:8000
- [ ] Database is accessible (if using real data)
- [ ] Alpaca API credentials configured (if using live data)
- [ ] All 6 accounts are configured in MultiAlpacaManager

### Test Execution
- [ ] Run `python test_trade_monitor_endpoints.py`
- [ ] All 6 tests pass (health, positions, accounts, pending_trades, execute_empty, execute_invalid)
- [ ] Acceptance criteria checklist shows ✓ for all items

### Backend Log Review
- [ ] No ERROR messages in backend logs (WARNING is OK)
- [ ] Monitor endpoints log successful data retrieval or mock fallback
- [ ] Trade endpoints log successful pending trades retrieval
- [ ] Execute endpoint logs successful request handling
- [ ] No stack traces or exceptions

### Data Validation
- [ ] GET /api/positions returns 6 entries (one per account)
- [ ] GET /api/accounts returns exactly 6 accounts
- [ ] Account names are: COUNCIL, CHATGPT, GEMINI, CLAUDE, GROQ, DEEPSEEK
- [ ] All required fields present in responses
- [ ] P&L calculations are correct (equity - 100000)

### Error Handling
- [ ] Empty trade_ids returns 400 or 422 error
- [ ] Invalid trade_ids returns appropriate error messages
- [ ] Pipeline state unavailable handled gracefully (empty list)
- [ ] Alpaca API errors handled gracefully (mock data fallback)

### Edge Cases
- [ ] Positions endpoint handles accounts with no positions (shows "-" symbol)
- [ ] Pending trades endpoint handles empty pipeline state (returns [])
- [ ] Execute endpoint handles FLAT positions correctly (skipped)
- [ ] Execute endpoint handles per-trade errors without failing entire request

---

## Test Results

### Run Date: _______________
### Tester: _______________

| Test | Status | Notes |
|------|--------|-------|
| Health Check | ☐ PASS ☐ FAIL | |
| Get Positions | ☐ PASS ☐ FAIL | |
| Get Accounts | ☐ PASS ☐ FAIL | |
| Get Pending Trades | ☐ PASS ☐ FAIL | |
| Execute Trades (Empty) | ☐ PASS ☐ FAIL | |
| Execute Trades (Invalid) | ☐ PASS ☐ FAIL | |

### Backend Logs

```
[Paste relevant backend log output here]
```

### Issues Found

```
[Document any issues or unexpected behavior here]
```

### Acceptance Criteria Status

- [ ] GET /api/positions returns data or mock data
- [ ] GET /api/accounts returns data or mock data
- [ ] GET /api/trades/pending returns data
- [ ] POST /api/trades/execute handles requests correctly
- [ ] No errors in backend logs

---

## Next Steps

1. **Mark Complete**: If all tests pass, update `implementation_plan.json`:
   ```json
   {
     "id": "6.5",
     "status": "completed",
     "notes": "Test suite created and executed. All 4 endpoints tested successfully. See trade_monitor_endpoints_test_report.md for details."
   }
   ```

2. **Commit Changes**:
   ```bash
   git add test_trade_monitor_endpoints.py trade_monitor_endpoints_test_report.md .auto-claude/specs/015-split-monolithic-main-py-into-modular-api-route-ha/build-progress.txt
   git commit -m "auto-claude: 6.5 - Test trade and monitor endpoints"
   ```

3. **Proceed to Next Subtask**: 6.6 - Test legacy chat endpoints

---

## Summary

Created comprehensive test suite for trade execution and monitoring endpoints after refactoring from monolithic main.py to modular structure.

**Files Created:**
1. `test_trade_monitor_endpoints.py` (475 lines) - Automated test script
2. `trade_monitor_endpoints_test_report.md` (this file) - Complete documentation

**Endpoints Tested:**
- GET /api/positions (monitor)
- GET /api/accounts (monitor)
- GET /api/trades/pending (trades)
- POST /api/trades/execute (trades)

**Architecture Validated:**
- API Layer: backend/api/trades.py (224 lines, 2 endpoints)
- API Layer: backend/api/monitor.py (236 lines, 2 endpoints)
- Service Layer: backend/services/trade_service.py (271 lines)
- Database Layer: backend/db/pitch_db.py
- Integration Layer: backend/multi_alpaca_client.py
- Trading Integration: backend/alpaca_integration/orders.py

**Test Coverage:**
- ✅ All 5 acceptance criteria covered
- ✅ Edge cases tested (empty requests, invalid IDs)
- ✅ Multi-account validation (all 6 accounts)
- ✅ Mock data fallback verification
- ✅ Error handling verification
- ✅ Response structure validation

**Ready for**: Manual test execution in main codebase
