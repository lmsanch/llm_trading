# LLM Trading Backend Architecture

## Overview

This document describes the modular architecture of the LLM Trading backend after the refactoring from a monolithic 2,239-line `main.py` into a clean, layered structure.

**Key Achievement**: Reduced `main.py` from 2,239 lines to 89 lines (96% reduction) while maintaining all 30+ API endpoints.

## Architecture Principles

The backend follows a **3-layer architecture** with clear separation of concerns:

1. **API Layer** (`backend/api/`): HTTP routing and request/response handling
2. **Service Layer** (`backend/services/`): Business logic and orchestration
3. **Database Layer** (`backend/db/`): Data access and SQL operations

### Design Goals

- ✅ **Single Responsibility**: Each module has one clear purpose
- ✅ **Dependency Flow**: API → Service → Database (unidirectional)
- ✅ **Testability**: Each layer can be tested independently
- ✅ **Maintainability**: Easy to locate and modify specific features
- ✅ **Scalability**: Simple to add new endpoints following established patterns

---

## Directory Structure

```
backend/
├── main.py                      # FastAPI app setup, router registration (89 lines)
├── dependencies.py              # FastAPI dependency injection utilities
├── config.py                    # Configuration and environment variables
│
├── api/                         # API Layer: HTTP routing
│   ├── __init__.py
│   ├── market.py               # Market data endpoints (3 endpoints)
│   ├── research.py             # Research endpoints (11 endpoints)
│   ├── pitches.py              # PM pitch endpoints (4 endpoints)
│   ├── council.py              # Council endpoints (2 endpoints)
│   ├── trades.py               # Trade execution endpoints (2 endpoints)
│   ├── monitor.py              # Position/account monitoring (2 endpoints)
│   └── conversations.py        # Legacy chat endpoints (5 endpoints)
│
├── services/                    # Service Layer: Business logic
│   ├── __init__.py
│   ├── market_service.py       # Market data fetching and processing
│   ├── research_service.py     # Research generation and retrieval
│   ├── pitch_service.py        # PM pitch generation and approval
│   ├── council_service.py      # Council synthesis (peer review + chairman)
│   └── trade_service.py        # Trade execution with bracket orders
│
├── db/                          # Database Layer: Data access
│   ├── __init__.py
│   ├── database.py             # Connection utilities and context managers
│   ├── market_db.py            # Market data queries
│   ├── research_db.py          # Research CRUD operations
│   ├── pitch_db.py             # PM pitch CRUD operations
│   └── council_db.py           # Council decision CRUD operations
│
├── alpaca_integration/          # Trading integration
│   ├── __init__.py
│   ├── orders.py               # Bracket order creation
│   └── multi_alpaca_client.py  # Multi-account management
│
├── pipeline/                    # AI pipeline stages (existing)
│   └── stages/
│       ├── research.py         # Research generation
│       ├── pm_pitch.py         # PM pitch generation
│       ├── peer_review.py      # Peer review stage
│       └── chairman.py         # Chairman decision stage
│
└── storage/                     # Data fetching and persistence (existing)
    ├── data_fetcher.py         # Market data fetching
    └── conversation_storage.py # Chat conversation persistence
```

---

## Layer Patterns

### 1. API Layer Pattern

**Location**: `backend/api/`

**Responsibilities**:
- Define HTTP routes using FastAPI routers
- Handle request validation (Pydantic models)
- Call service layer methods
- Return HTTP responses with proper status codes
- Handle exceptions and convert to HTTPException

**Pattern Template**:

```python
"""[Domain] API endpoints."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from backend.services.[domain]_service import [Domain]Service

logger = logging.getLogger(__name__)

# Create router with prefix and tags
router = APIRouter(prefix="/api/[domain]", tags=["[domain]"])

# Initialize service at module level
[domain]_service = [Domain]Service()


@router.get("/endpoint")
async def get_endpoint() -> Dict[str, Any]:
    """
    Endpoint description.

    Returns:
        Dict containing response data

    Raises:
        HTTPException: 404 if not found
        HTTPException: 500 on server error

    Example Response:
        {
            "field": "value"
        }
    """
    try:
        result = await [domain]_service.method()
        if result is None:
            raise HTTPException(status_code=404, detail="Not found")
        return result
    except HTTPException:
        raise  # Re-raise to preserve status code
    except Exception as e:
        logger.error(f"Error in endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**Key Points**:
- ✅ Use `APIRouter` with prefix and tags
- ✅ Initialize service once at module level
- ✅ All endpoint functions are `async`
- ✅ Comprehensive docstrings with Returns, Raises, Example
- ✅ Re-raise `HTTPException` to preserve status codes
- ✅ Use `logger.error` with `exc_info=True` for debugging
- ✅ Type hints on all function signatures

### 2. Service Layer Pattern

**Location**: `backend/services/`

**Responsibilities**:
- Implement business logic
- Orchestrate database operations
- Call pipeline stages for AI operations
- Transform and format data
- Handle errors and logging

**Pattern Template**:

```python
"""[Domain] service for [domain] business logic."""

import logging
from typing import Dict, Optional, Any
from backend.db.[domain]_db import db_function1, db_function2

logger = logging.getLogger(__name__)


class [Domain]Service:
    """
    Service class for [domain] operations.

    Provides business logic for:
    - Feature 1
    - Feature 2
    - Feature 3
    """

    def __init__(self):
        """Initialize the [Domain]Service."""
        pass

    async def method_name(self, param: str) -> Optional[Dict[str, Any]]:
        """
        Method description.

        Args:
            param: Parameter description

        Returns:
            Dict containing result data
            Returns None if not found

        Raises:
            Exception: If operation fails

        Database Tables:
            - table_name: Description of table usage
        """
        try:
            # Call database layer
            result = db_function1(param)

            if result is None:
                logger.warning(f"No data found for {param}")
                return None

            # Transform data if needed
            transformed = self._transform(result)

            return transformed
        except Exception as e:
            logger.error(f"Error in method: {e}", exc_info=True)
            raise

    def _transform(self, data: Dict) -> Dict:
        """Private helper method for data transformation."""
        # Transform logic here
        return data
```

**Key Points**:
- ✅ Service class encapsulates related business logic
- ✅ Async methods for I/O operations (database, API calls)
- ✅ Import database functions from `backend.db.*`
- ✅ Use `logger.warning/error/info` (no print statements)
- ✅ Comprehensive docstrings with Args, Returns, Raises, Database Tables
- ✅ Private methods prefixed with `_` for internal helpers
- ✅ Type hints for all parameters and return values

### 3. Database Layer Pattern

**Location**: `backend/db/`

**Responsibilities**:
- Execute SQL queries
- Handle database connections
- Return raw data (no business logic)
- Use context managers for safe connection handling

**Pattern Template**:

```python
"""[Domain] database operations."""

import logging
from typing import Optional, List, Dict, Any
from backend.db.database import DatabaseConnection

logger = logging.getLogger(__name__)


def fetch_data(param: str) -> Optional[Dict[str, Any]]:
    """
    Fetch data from database.

    Args:
        param: Query parameter

    Returns:
        Dict containing query results
        Returns None if no data found

    Raises:
        psycopg2.Error: If database query fails

    Database Tables:
        - table_name: SELECT column1, column2 WHERE condition
    """
    try:
        with DatabaseConnection() as conn:
            with conn.cursor() as cur:
                # Execute query
                cur.execute("""
                    SELECT column1, column2
                    FROM table_name
                    WHERE condition = %s
                """, (param,))

                row = cur.fetchone()

                if row is None:
                    logger.info(f"No data found for {param}")
                    return None

                # Parse results
                result = {
                    "field1": row[0],
                    "field2": row[1]
                }

                return result
    except Exception as e:
        logger.error(f"Database error in fetch_data: {e}", exc_info=True)
        raise


def save_data(data: Dict[str, Any]) -> None:
    """
    Save data to database.

    Args:
        data: Data to save

    Raises:
        psycopg2.Error: If database insert fails

    Database Tables:
        - table_name: INSERT INTO (column1, column2) VALUES (...)
    """
    try:
        with DatabaseConnection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO table_name (column1, column2)
                    VALUES (%s, %s)
                """, (data["field1"], data["field2"]))

                logger.info(f"Saved data to table_name")
    except Exception as e:
        logger.error(f"Database error in save_data: {e}", exc_info=True)
        raise
```

**Key Points**:
- ✅ Use `DatabaseConnection()` context manager for automatic commit/rollback
- ✅ Module-level functions (not a class)
- ✅ Return raw data structures (dicts, lists)
- ✅ SQL queries use parameterized statements to prevent injection
- ✅ Comprehensive docstrings with Database Tables section
- ✅ Log info/warning/error messages (no print statements)
- ✅ Type hints for all parameters and return values

---

## How to Add New Endpoints

Follow these steps to add a new endpoint to the backend:

### Step 1: Create Database Operations (if needed)

**File**: `backend/db/[domain]_db.py`

```python
"""[Domain] database operations."""

import logging
from typing import Optional, Dict, Any
from backend.db.database import DatabaseConnection

logger = logging.getLogger(__name__)


def fetch_[entity](entity_id: int) -> Optional[Dict[str, Any]]:
    """Fetch [entity] from database."""
    try:
        with DatabaseConnection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, name, created_at
                    FROM [table_name]
                    WHERE id = %s
                """, (entity_id,))

                row = cur.fetchone()
                if row is None:
                    return None

                return {
                    "id": row[0],
                    "name": row[1],
                    "created_at": row[2].isoformat() if row[2] else None
                }
    except Exception as e:
        logger.error(f"Database error in fetch_[entity]: {e}", exc_info=True)
        raise
```

### Step 2: Create Service Method

**File**: `backend/services/[domain]_service.py`

```python
"""[Domain] service for [domain] business logic."""

import logging
from typing import Optional, Dict, Any
from backend.db.[domain]_db import fetch_[entity]

logger = logging.getLogger(__name__)


class [Domain]Service:
    """Service class for [domain] operations."""

    def __init__(self):
        """Initialize the service."""
        pass

    async def get_[entity](self, entity_id: int) -> Optional[Dict[str, Any]]:
        """
        Get [entity] by ID.

        Args:
            entity_id: ID of the entity to retrieve

        Returns:
            Dict containing entity data
            Returns None if not found

        Database Tables:
            - [table_name]: SELECT id, name, created_at
        """
        try:
            entity = fetch_[entity](entity_id)

            if entity is None:
                logger.warning(f"Entity {entity_id} not found")
                return None

            # Add business logic here (transformations, enrichment, etc.)

            return entity
        except Exception as e:
            logger.error(f"Error getting entity: {e}", exc_info=True)
            raise
```

### Step 3: Create API Endpoint

**File**: `backend/api/[domain].py`

```python
"""[Domain] API endpoints."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from backend.services.[domain]_service import [Domain]Service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/[domain]", tags=["[domain]"])
[domain]_service = [Domain]Service()


@router.get("/[entity]/{entity_id}")
async def get_[entity](entity_id: int) -> Dict[str, Any]:
    """
    Get [entity] by ID.

    Args:
        entity_id: ID of the entity to retrieve

    Returns:
        Dict containing entity data

    Raises:
        HTTPException: 404 if entity not found
        HTTPException: 500 on server error

    Example Response:
        {
            "id": 1,
            "name": "Example",
            "created_at": "2024-01-09T12:00:00"
        }
    """
    try:
        entity = await [domain]_service.get_[entity](entity_id)

        if entity is None:
            raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

        return entity
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_[entity] endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

### Step 4: Register Router in main.py

**File**: `backend/main.py`

```python
# Import the new router
from backend.api.[domain] import router as [domain]_router

# Register with the app
app.include_router([domain]_router)
```

### Step 5: Test the Endpoint

1. **Start the backend**:
   ```bash
   cd /research/llm_trading
   PYTHONPATH=. python backend/main.py
   ```

2. **Test with curl**:
   ```bash
   curl http://localhost:8000/api/[domain]/[entity]/1
   ```

3. **Check the logs** for any errors

---

## Common Import Patterns

### API Module Imports

```python
# Standard library
import logging
from typing import Dict, Any, List, Optional

# FastAPI
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field

# Service layer
from backend.services.[domain]_service import [Domain]Service

# Dependencies
from backend.dependencies import get_pipeline_state

logger = logging.getLogger(__name__)
```

### Service Module Imports

```python
# Standard library
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

# Database layer
from backend.db.[domain]_db import fetch_data, save_data

# Pipeline stages (if needed)
from backend.pipeline.stages.research import ResearchStage

logger = logging.getLogger(__name__)
```

### Database Module Imports

```python
# Standard library
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

# Database utilities
from backend.db.database import DatabaseConnection

# psycopg2 (if needed for types)
import psycopg2

logger = logging.getLogger(__name__)
```

---

## Pipeline State Management

### Global State

The `PipelineState` class in `main.py` stores the in-memory state for the trading pipeline:

```python
class PipelineState:
    """In-memory state for the trading pipeline."""

    def __init__(self):
        self.current_week = get_week_id()
        self.research_status = "pending"
        self.pm_status = "pending"
        self.council_status = "pending"
        self.execution_status = "pending"
        self.research_packs = None
        self.pm_pitches = None
        self.pm_pitches_raw = None
        self.peer_reviews = None
        self.council_decision = None
        self.execution_results = None
        self.pending_trades = []
        self.executed_trades = []
        self.jobs = {}  # job_id -> status_dict

# Global state instance
pipeline_state = PipelineState()
```

### Accessing State in API Modules

**Option 1: Direct import** (current pattern):

```python
def get_pipeline_state():
    """Get the global pipeline state."""
    from backend.main import pipeline_state
    return pipeline_state

# In endpoint
@router.get("/endpoint")
async def endpoint():
    state = get_pipeline_state()
    return {"status": state.research_status}
```

**Option 2: Dependency injection** (recommended for new code):

```python
from backend.dependencies import get_pipeline_state
from fastapi import Depends

@router.get("/endpoint")
async def endpoint(state = Depends(get_pipeline_state)):
    return {"status": state.research_status}
```

---

## Background Tasks

For long-running operations (research generation, pitch generation, council synthesis), use FastAPI's `BackgroundTasks`:

```python
from fastapi import BackgroundTasks
import uuid

@router.post("/generate")
async def generate_endpoint(background_tasks: BackgroundTasks):
    """Start background task."""
    job_id = str(uuid.uuid4())
    state = get_pipeline_state()

    # Initialize job status
    state.jobs[job_id] = {
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "progress": 0
    }

    # Schedule background task
    background_tasks.add_task(
        background_function,
        job_id,
        state
    )

    return {
        "job_id": job_id,
        "status": "running",
        "message": "Task started"
    }


async def background_function(job_id: str, state):
    """Background task implementation."""
    try:
        # Do work here
        result = await some_async_operation()

        # Update job status
        state.jobs[job_id] = {
            "status": "completed",
            "result": result,
            "completed_at": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Background task error: {e}", exc_info=True)
        state.jobs[job_id] = {
            "status": "failed",
            "error": str(e),
            "failed_at": datetime.now().isoformat()
        }
```

---

## Error Handling Patterns

### API Layer

```python
try:
    result = await service.method()
    if result is None:
        raise HTTPException(status_code=404, detail="Not found")
    return result
except HTTPException:
    raise  # Re-raise to preserve status code
except Exception as e:
    logger.error(f"Error in endpoint: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail=str(e))
```

### Service Layer

```python
try:
    data = db_function()
    if data is None:
        logger.warning("No data found")
        return None
    return data
except Exception as e:
    logger.error(f"Service error: {e}", exc_info=True)
    raise  # Let API layer handle HTTP conversion
```

### Database Layer

```python
try:
    with DatabaseConnection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM table")
            return cur.fetchall()
except Exception as e:
    logger.error(f"Database error: {e}", exc_info=True)
    raise  # Let service layer handle
```

---

## Database Connection Management

### Using DatabaseConnection Context Manager

The `DatabaseConnection` class provides automatic commit/rollback:

```python
from backend.db.database import DatabaseConnection

def save_data(data: Dict):
    """Save data with automatic transaction handling."""
    with DatabaseConnection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO table (col1, col2)
                VALUES (%s, %s)
            """, (data["field1"], data["field2"]))
            # Automatic commit on success
            # Automatic rollback on exception
```

### Multiple Operations in One Transaction

```python
def save_multiple(items: List[Dict]):
    """Save multiple items in a single transaction."""
    with DatabaseConnection() as conn:
        with conn.cursor() as cur:
            # All operations in same transaction
            for item in items:
                cur.execute("""
                    INSERT INTO table (col1, col2)
                    VALUES (%s, %s)
                """, (item["field1"], item["field2"]))
            # Single commit for all inserts
```

---

## Logging Best Practices

### Never Use Print Statements

❌ **Wrong**:
```python
print("Starting operation")
print(f"Error: {e}")
```

✅ **Correct**:
```python
logger.info("Starting operation")
logger.error(f"Error: {e}", exc_info=True)
```

### Log Levels

- `logger.debug()` - Detailed diagnostic information
- `logger.info()` - General informational messages
- `logger.warning()` - Warning messages (operation succeeded but something unusual)
- `logger.error()` - Error messages (operation failed)

### Include Exception Info

Always use `exc_info=True` in error logs:

```python
try:
    result = operation()
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
    raise
```

This includes the full stack trace in the logs for debugging.

---

## Testing

### Test Structure

Tests are organized by endpoint group:

- `test_research_endpoints.py` - Tests research API endpoints
- `test_pitch_endpoints.py` - Tests PM pitch API endpoints
- `test_council_endpoints.py` - Tests council API endpoints
- `test_trade_monitor_endpoints.py` - Tests trade and monitor API endpoints
- `test_conversation_endpoints.py` - Tests chat conversation API endpoints

### Running Tests

1. **Start the backend**:
   ```bash
   cd /research/llm_trading
   PYTHONPATH=. python backend/main.py
   ```

2. **Run test script** (in another terminal):
   ```bash
   python test_research_endpoints.py
   ```

3. **Check results**: Tests output color-coded results with acceptance criteria validation

---

## API Endpoints Overview

### Market Endpoints (`/api/market`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/market/snapshot` | Get market snapshot for research |
| GET | `/api/market/metrics` | Get 7-day returns and correlation |
| GET | `/api/market/prices` | Get current OHLCV prices |

### Research Endpoints (`/api/research`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/research/prompt` | Get research prompt with metadata |
| GET | `/api/research/current` | Get current research from pipeline |
| GET | `/api/research/latest` | Get latest research from database |
| GET | `/api/research/history` | Get research history for calendar |
| POST | `/api/research/generate` | Start research generation job |
| GET | `/api/research/status` | Poll research job status |
| GET | `/api/research/{job_id}` | Get research job results |
| POST | `/api/research/verify` | Mark research as verified |
| GET | `/api/research/report/{id}` | Get specific research report |
| GET | `/api/graphs/latest` | Get latest knowledge graph |
| GET | `/api/data-package/latest` | Get combined data package |

### PM Pitch Endpoints (`/api/pitches`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/pitches/current` | Get current PM pitches |
| POST | `/api/pitches/generate` | Start pitch generation job |
| GET | `/api/pitches/status` | Poll pitch job status |
| POST | `/api/pitches/{id}/approve` | Approve specific pitch |

### Council Endpoints (`/api/council`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/council/current` | Get current council decision |
| POST | `/api/council/synthesize` | Start council synthesis |

### Trade Endpoints (`/api/trades`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/trades/pending` | Get pending trades |
| POST | `/api/trades/execute` | Execute trades with bracket orders |

### Monitor Endpoints (`/api`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/positions` | Get positions across all accounts |
| GET | `/api/accounts` | Get account summaries |

### Conversation Endpoints (`/api/conversations`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/conversations` | List all conversations |
| POST | `/api/conversations` | Create new conversation |
| GET | `/api/conversations/{id}` | Get conversation with history |
| POST | `/api/conversations/{id}/message` | Send message (blocking) |
| POST | `/api/conversations/{id}/message/stream` | Send message (streaming SSE) |

---

## Migration from Monolithic main.py

### Before (Monolithic)

```
backend/main.py (2,239 lines)
├── All imports
├── PipelineState class
├── Mock data constants
├── Formatting functions
├── Database connection utilities
├── Database query functions
├── Service/business logic
├── 31 API endpoint definitions
├── FastAPI app setup
└── Uvicorn entry point
```

### After (Modular)

```
backend/
├── main.py (89 lines)           # Just app setup and router registration
├── api/ (7 files)               # HTTP routing
├── services/ (5 files)          # Business logic
├── db/ (5 files)                # Data access
└── [existing modules]           # Pipeline, storage, etc.
```

### Benefits Achieved

- ✅ **96% reduction** in main.py size (2,239 → 89 lines)
- ✅ **Single Responsibility**: Each module has one clear purpose
- ✅ **Easy Navigation**: Feature code is easy to locate
- ✅ **Testability**: Each layer can be tested independently
- ✅ **Maintainability**: Changes are localized to relevant modules
- ✅ **Scalability**: Adding endpoints follows clear patterns
- ✅ **No Breaking Changes**: All APIs work identically

---

## Quick Reference

### Creating a New Endpoint Checklist

- [ ] Create database functions in `backend/db/[domain]_db.py`
- [ ] Create service methods in `backend/services/[domain]_service.py`
- [ ] Create API endpoints in `backend/api/[domain].py`
- [ ] Register router in `backend/main.py`
- [ ] Test the endpoint with curl or test script
- [ ] Verify no errors in backend logs

### Code Quality Checklist

- [ ] All functions have comprehensive docstrings
- [ ] Type hints on all function signatures
- [ ] Use `logger` instead of `print` statements
- [ ] Use `DatabaseConnection` context manager
- [ ] HTTP exceptions have appropriate status codes
- [ ] Re-raise `HTTPException` to preserve status codes
- [ ] Use `exc_info=True` in error logs

### Documentation Requirements

Every function/method should have:

- [ ] Description of what it does
- [ ] `Args:` section for parameters
- [ ] `Returns:` section for return value
- [ ] `Raises:` section for exceptions
- [ ] `Database Tables:` section (if applicable)
- [ ] `Example Response:` section (for API endpoints)

---

## Support

For questions or issues with the backend architecture:

1. Check this documentation first
2. Review existing modules for pattern examples
3. Check test scripts for endpoint usage examples
4. Review implementation plan in `.auto-claude/specs/015-*/implementation_plan.json`

---

**Last Updated**: 2026-01-09
**Refactoring Task**: Split monolithic main.py into modular API route handlers
**Status**: ✅ Completed (all 30 endpoints refactored and tested)
