# Alpaca Multi-Account Trading Architecture

This document explains how the LLM Trading system manages **6 parallel Alpaca paper trading accounts** to compare the performance of different AI trading strategies.

## Overview

The system uses **6 separate Alpaca paper trading accounts** to run controlled experiments:

| Account | Strategy | Purpose |
|---------|----------|---------|
| **CHATGPT** | Individual PM | Test GPT-5.1 trading decisions |
| **GEMINI** | Individual PM | Test Gemini 3 Pro trading decisions |
| **CLAUDE** | Individual PM | Test Sonnet 4.5 trading decisions |
| **GROQ** | Individual PM | Test Groq trading decisions |
| **DEEPSEEK** | Individual PM | Test Deepseek trading decisions |
| **COUNCIL** | Council Synthesis | Test Chairman's synthesized decisions |

Each account operates independently with:
- **Isolated capital** ($100K paper trading balance per account)
- **Separate API keys** (prevents cross-contamination)
- **Independent order execution** (trades don't affect each other)
- **Parallel performance tracking** (direct comparison of strategies)

## Quick Start

### 1. Environment Variables

Set up credentials in `.env` for all 6 accounts:

```bash
# Account 1: CHATGPT (Individual PM)
ALPACA_CHATGPT_KEY_ID=your_key_here
ALPACA_CHATGPT_SECRET_KEY=your_secret_here

# Account 2: GEMINI (Individual PM)
ALPACA_GEMINI_KEY_ID=your_key_here
ALPACA_GEMINI_SECRET_KEY=your_secret_here

# Account 3: CLAUDE (Individual PM)
ALPACA_CLAUDE_KEY_ID=your_key_here
ALPACA_CLAUDE_SECRET_KEY=your_secret_here

# Account 4: GROQ (Individual PM)
ALPACA_GROQ_KEY_ID=your_key_here
ALPACA_GROQ_SECRET_KEY=your_secret_here

# Account 5: DEEPSEEK (Individual PM)
ALPACA_DEEPSEEK_KEY_ID=your_key_here
ALPACA_DEEPSEEK_SECRET_KEY=your_secret_here

# Account 6: COUNCIL (Council Synthesis)
ALPACA_COUNCIL_KEY_ID=your_key_here
ALPACA_COUNCIL_SECRET_KEY=your_secret_here

# Personal Account (for historical market data only)
ALPACA_PERSONAL_KEY_ID=your_key_here
ALPACA_PERSONAL_SECRET_KEY=your_secret_here
```

**Important:** Paper trading accounts do NOT have access to historical market data API. The personal account is required for fetching historical data in `backend/storage/fetch_market_data.py`.

### 2. Basic Usage

```python
from backend.multi_alpaca_client import MultiAlpacaManager

# Initialize manager (connects to all 6 accounts)
manager = MultiAlpacaManager()

# Get account info for all accounts
accounts = await manager.get_all_accounts()
print(accounts['COUNCIL']['buying_power'])  # "$100000.00"

# Get positions across all accounts
positions = await manager.get_all_positions()
print(positions['CHATGPT'])  # [{'symbol': 'SPY', 'qty': '10', ...}]

# Place order for specific account
order = await manager.place_order_for_account(
    account_name='COUNCIL',
    symbol='SPY',
    qty=100,
    side='buy',
    order_type='market'
)

# Place orders in parallel across multiple accounts
orders = [
    {'account_name': 'CHATGPT', 'symbol': 'SPY', 'qty': 10, 'side': 'buy'},
    {'account_name': 'GEMINI', 'symbol': 'QQQ', 'qty': 5, 'side': 'buy'},
    {'account_name': 'COUNCIL', 'symbol': 'GLD', 'qty': 20, 'side': 'sell'},
]
results = await manager.place_orders_parallel(orders)
```

## Architecture

### Account Configuration

Account configuration is defined in `backend/multi_alpaca_client.py`:

```python
ALPACA_ACCOUNTS = {
    'CHATGPT': {
        'key_id': os.getenv('ALPACA_CHATGPT_KEY_ID'),
        'secret_key': os.getenv('ALPACA_CHATGPT_SECRET_KEY'),
        'account_id': 'PA3IUYCYRWGK',
        'email': 'strategy1a@dnnalpha.ai'
    },
    'GEMINI': {
        'key_id': os.getenv('ALPACA_GEMINI_KEY_ID'),
        'secret_key': os.getenv('ALPACA_GEMINI_SECRET_KEY'),
        'account_id': 'PA3M2HMSLN00',
        'email': 'lmsanch@gmail.com'
    },
    # ... (4 more accounts)
}
```

**Key Points:**
- **Account nicknames** (CHATGPT, GEMINI, etc.) are used throughout the codebase
- **Account IDs** (PA3IUYCYRWGK, etc.) are Alpaca's internal identifiers
- **API keys** are loaded from environment variables (never hardcoded)
- **Email addresses** identify which Alpaca user owns each sub-account

### Class Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│ MultiAlpacaManager                                          │
│   - Manages all 6 accounts                                  │
│   - Parallel operations (get_all_accounts, place_orders)    │
│   - Account routing (place_order_for_account)               │
└────────────────────────┬────────────────────────────────────┘
                         │ contains 6 instances of
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ AlpacaAccountClient                                         │
│   - Single account operations                               │
│   - Account-specific credentials                            │
│   - HTTP requests to Alpaca API                             │
└────────────────────────┬────────────────────────────────────┘
                         │ uses
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ HTTP Connection Pool (backend/http_pool.py)                 │
│   - Shared httpx client for all accounts                    │
│   - Connection reuse across accounts                        │
│   - Automatic retry and timeout handling                    │
└─────────────────────────────────────────────────────────────┘
```

## Core Classes

### 1. MultiAlpacaManager

**Purpose:** High-level manager for all 6 accounts with parallel operations.

**Location:** `backend/multi_alpaca_client.py`

**Key Methods:**

```python
class MultiAlpacaManager:
    def __init__(self):
        """Initialize all 6 account clients."""

    def get_client(self, account_name: str) -> AlpacaAccountClient:
        """Get client for specific account (CHATGPT, GEMINI, etc.)."""

    async def get_all_accounts(self) -> Dict[str, Dict]:
        """Get account info for all accounts in parallel."""

    async def get_all_positions(self) -> Dict[str, List[Dict]]:
        """Get positions for all accounts in parallel."""

    async def place_order_for_account(
        self,
        account_name: str,
        symbol: str,
        qty: int,
        side: str,
        order_type: str = "market",
        limit_price: Optional[str] = None,
        stop_price: Optional[str] = None
    ) -> Dict:
        """Place order for specific account."""

    async def place_orders_parallel(
        self,
        orders: List[Dict]
    ) -> Dict[str, Dict]:
        """Place orders for multiple accounts in parallel."""

    async def close_all_positions(
        self,
        account_name: Optional[str] = None
    ) -> Dict[str, Dict]:
        """Close all positions for one or all accounts."""
```

### 2. AlpacaAccountClient

**Purpose:** Single account operations with account-specific credentials.

**Location:** `backend/multi_alpaca_client.py`

**Key Methods:**

```python
class AlpacaAccountClient:
    def __init__(self, account_name: str, paper: bool = True):
        """Initialize client for specific account."""

    async def get_account(self) -> Dict:
        """Get account information (balance, buying power, etc.)."""

    async def get_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get all positions or specific symbol position."""

    async def get_orders(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        symbol: Optional[str] = None
    ) -> List[Dict]:
        """Get orders with optional filters."""

    async def place_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        order_type: str = "market",
        limit_price: Optional[str] = None,
        stop_price: Optional[str] = None,
        time_in_force: str = "gtc",
        extended_hours: bool = False
    ) -> Dict:
        """Place an order."""

    async def cancel_order(self, order_id: str) -> Dict:
        """Cancel an order by ID."""

    async def close_position(self, symbol: str) -> Dict:
        """Close a position (liquidate all shares)."""

    async def get_bars(
        self,
        symbol: str,
        timeframe: str = "1Day",
        limit: int = 100,
        start: Optional[str] = None,
        end: Optional[str] = None,
        adjustment: str = "raw",
        feed: str = "iex"
    ) -> List[Dict]:
        """Get historical bar data from Alpaca Data API."""
```

## Common Usage Patterns

### Pattern 1: Check Account Status

```python
from backend.multi_alpaca_client import MultiAlpacaManager

async def check_account_status():
    """Check buying power and positions for all accounts."""
    manager = MultiAlpacaManager()

    # Get account info
    accounts = await manager.get_all_accounts()

    for account_name, account_info in accounts.items():
        print(f"{account_name}:")
        print(f"  Buying Power: ${account_info['buying_power']}")
        print(f"  Cash: ${account_info['cash']}")
        print(f"  Portfolio Value: ${account_info['portfolio_value']}")

    # Get positions
    positions = await manager.get_all_positions()

    for account_name, account_positions in positions.items():
        print(f"\n{account_name} Positions:")
        for pos in account_positions:
            print(f"  {pos['symbol']}: {pos['qty']} shares @ ${pos['avg_entry_price']}")
```

### Pattern 2: Execute Council Decision

```python
from backend.multi_alpaca_client import MultiAlpacaManager

async def execute_council_decision(symbol: str, qty: int, side: str):
    """Execute a trade for the COUNCIL account only."""
    manager = MultiAlpacaManager()

    # Place order for COUNCIL account
    order = await manager.place_order_for_account(
        account_name='COUNCIL',
        symbol=symbol,
        qty=qty,
        side=side,
        order_type='market'
    )

    print(f"✅ Order submitted: {order['id']}")
    print(f"   Symbol: {order['symbol']}")
    print(f"   Qty: {order['qty']}")
    print(f"   Side: {order['side']}")
    print(f"   Status: {order['status']}")

    return order
```

### Pattern 3: Execute Same Trade Across All Accounts

```python
from backend.multi_alpaca_client import MultiAlpacaManager, get_all_account_names

async def execute_same_trade_all_accounts(symbol: str, qty: int, side: str):
    """Execute identical trade across all 6 accounts in parallel."""
    manager = MultiAlpacaManager()

    # Build order list for all accounts
    orders = [
        {
            'account_name': account_name,
            'symbol': symbol,
            'qty': qty,
            'side': side,
            'order_type': 'market'
        }
        for account_name in get_all_account_names()
    ]

    # Execute in parallel
    results = await manager.place_orders_parallel(orders)

    # Report results
    for account_name, order in results.items():
        print(f"✅ {account_name}: Order {order['id']} submitted")

    return results
```

### Pattern 4: Close All Positions (Emergency Exit)

```python
from backend.multi_alpaca_client import MultiAlpacaManager

async def emergency_exit():
    """Close all positions across all accounts (panic button)."""
    manager = MultiAlpacaManager()

    # Close all positions for all accounts
    results = await manager.close_all_positions(account_name=None)

    for account_name, close_orders in results.items():
        print(f"\n{account_name}:")
        for symbol, order in close_orders.items():
            print(f"  ✅ Closed {symbol}: Order {order['id']}")

    return results
```

### Pattern 5: Execute Different Trades Per Account

```python
from backend.multi_alpaca_client import MultiAlpacaManager

async def execute_per_account_strategies(strategies: Dict[str, Dict]):
    """
    Execute different trades for each account based on their individual strategies.

    Args:
        strategies: Dict mapping account name to trade params
            {
                'CHATGPT': {'symbol': 'SPY', 'qty': 10, 'side': 'buy'},
                'GEMINI': {'symbol': 'QQQ', 'qty': 5, 'side': 'sell'},
                'COUNCIL': {'symbol': 'GLD', 'qty': 20, 'side': 'buy'},
                ...
            }
    """
    manager = MultiAlpacaManager()

    # Build order list from strategies
    orders = [
        {
            'account_name': account_name,
            'symbol': trade['symbol'],
            'qty': trade['qty'],
            'side': trade['side'],
            'order_type': trade.get('order_type', 'market'),
            'limit_price': trade.get('limit_price'),
            'stop_price': trade.get('stop_price')
        }
        for account_name, trade in strategies.items()
    ]

    # Execute in parallel
    results = await manager.place_orders_parallel(orders)

    # Report results
    for account_name, order in results.items():
        print(f"✅ {account_name}: {order['symbol']} {order['side']} {order['qty']} @ {order.get('limit_price', 'market')}")

    return results
```

## Integration Points

### 1. Trade Execution Pipeline

**File:** `backend/pipeline/stages/execution.py`

The execution stage uses `MultiAlpacaManager` to execute trades across accounts:

```python
from backend.multi_alpaca_client import MultiAlpacaManager

class ExecutionStage(Stage):
    async def run(self, context: PipelineContext) -> PipelineContext:
        manager = MultiAlpacaManager()

        # Get approved trades from context
        approved_trades = context.get("approved_trades")

        # Execute trades in parallel
        orders = [
            {
                'account_name': trade['account'],
                'symbol': trade['symbol'],
                'qty': trade['qty'],
                'side': trade['side']
            }
            for trade in approved_trades
        ]

        results = await manager.place_orders_parallel(orders)

        return context.set("execution_results", results)
```

### 2. Trade Service

**File:** `backend/services/trade_service.py`

The trade service uses `MultiAlpacaManager` for order execution:

```python
from backend.multi_alpaca_client import MultiAlpacaManager

class TradeService:
    def __init__(self):
        self.manager = MultiAlpacaManager()

    async def execute_trades(self, trade_ids: List[int], pipeline_state):
        # Fetch trade data from database
        # ...

        # Build orders
        orders = [...]

        # Execute via multi-account manager
        results = await self.manager.place_orders_parallel(orders)

        return results
```

### 3. API Endpoints

**File:** `backend/api/trades.py`

Trade execution endpoints use the trade service (which uses `MultiAlpacaManager`):

```python
@router.post("/execute")
async def execute_trades(request: ExecuteTradesRequest):
    """Execute trades using bracket orders."""

    # TradeService internally uses MultiAlpacaManager
    result = await trade_service.execute_trades(
        trade_ids=request.trade_ids,
        pipeline_state=pipeline_state,
    )

    return result
```

### 4. Monitoring Dashboard

**File:** `backend/api/monitor.py`

The monitor endpoint uses `MultiAlpacaManager` to check account status:

```python
from backend.multi_alpaca_client import MultiAlpacaManager

@router.get("/accounts")
async def get_accounts_status():
    """Get status for all 6 accounts."""
    manager = MultiAlpacaManager()

    accounts = await manager.get_all_accounts()
    positions = await manager.get_all_positions()

    return {
        "accounts": accounts,
        "positions": positions
    }
```

## Adding a New Account

Follow these steps to add a 7th account (e.g., "GPT4O"):

### Step 1: Create Alpaca Paper Trading Account

1. Go to https://alpaca.markets/
2. Sign up for a new paper trading account
3. Generate API keys for the account
4. Note the account ID (e.g., "PA3XXXXXX")

### Step 2: Update Environment Variables

Add credentials to `.env`:

```bash
# Account 7: GPT4O (Individual PM)
ALPACA_GPT4O_KEY_ID=your_key_here
ALPACA_GPT4O_SECRET_KEY=your_secret_here
```

### Step 3: Update Account Configuration

Edit `backend/multi_alpaca_client.py` and add to `ALPACA_ACCOUNTS` dict:

```python
ALPACA_ACCOUNTS = {
    'CHATGPT': { ... },
    'GEMINI': { ... },
    'CLAUDE': { ... },
    'GROQ': { ... },
    'DEEPSEEK': { ... },
    'COUNCIL': { ... },
    'GPT4O': {  # NEW ACCOUNT
        'key_id': os.getenv('ALPACA_GPT4O_KEY_ID'),
        'secret_key': os.getenv('ALPACA_GPT4O_SECRET_KEY'),
        'account_id': 'PA3XXXXXX',  # Your new account ID
        'email': 'your_email@example.com'
    }
}
```

### Step 4: Update Tests

Add test cases for the new account in `tests/test_alpaca_manager.py`:

```python
def test_all_accounts_have_clients(self):
    """Test that all 7 accounts have initialized clients."""
    manager = MultiAlpacaManager()
    expected_accounts = ['CHATGPT', 'GEMINI', 'CLAUDE', 'GROQ', 'DEEPSEEK', 'COUNCIL', 'GPT4O']

    for account_name in expected_accounts:
        assert account_name in manager.clients
```

### Step 5: Verify Credentials

Test the new account credentials:

```bash
python backend/multi_alpaca_client.py
```

Output should show:
```
✅ GPT4O: Credentials set
✅ GPT4O
   Account ID: PA3XXXXXX
   Buying Power: $100000.00
   Cash: $100000.00
   Portfolio Value: $100000.00
```

### Step 6: Update Documentation

Update this file to reflect 7 accounts instead of 6:
- Update the account table in the Overview section
- Update test counts in relevant sections
- Update any hardcoded "6 accounts" references

## Environment Variable Structure

### Naming Convention

All Alpaca account credentials follow this pattern:

```bash
ALPACA_{ACCOUNT_NAME}_KEY_ID
ALPACA_{ACCOUNT_NAME}_SECRET_KEY
```

Where `{ACCOUNT_NAME}` matches the account nickname in `ALPACA_ACCOUNTS` dict.

### Why Account Names Matter

Account names are used throughout the system:

1. **Environment variables:** `ALPACA_CHATGPT_KEY_ID`
2. **Configuration dict keys:** `ALPACA_ACCOUNTS['CHATGPT']`
3. **API requests:** `manager.place_order_for_account(account_name='CHATGPT', ...)`
4. **Database records:** `pm_pitches.account = 'CHATGPT'`
5. **Frontend display:** Shows "CHATGPT" in account dropdown

**Important:** Account names must be:
- **UPPERCASE** (consistent with environment variable convention)
- **Alphanumeric only** (no spaces or special characters)
- **Unique** (no duplicates)

### Personal Account vs. Paper Trading Accounts

The system uses **7 total Alpaca accounts**:

| Account Type | Count | Purpose | Has Market Data API? |
|--------------|-------|---------|---------------------|
| Paper Trading | 6 | Trading execution | ❌ No |
| Personal | 1 | Historical data | ✅ Yes |

**Key Differences:**

- **Paper trading accounts:** Can place orders, check positions, but CANNOT fetch historical market data
- **Personal account:** Used ONLY for fetching historical market data (not for trading)

**Why?** Alpaca's paper trading accounts do not have access to the historical data API. The personal account is required for `backend/storage/fetch_market_data.py`.

## Testing

### Unit Tests

**File:** `tests/test_alpaca_manager.py`

Comprehensive test suite covering:
- Manager initialization (all 6 clients)
- Parallel operations (`get_all_accounts`, `get_all_positions`)
- Single account operations (`place_order_for_account`)
- Parallel order placement (`place_orders_parallel`)
- Position closing (`close_all_positions`)
- Partial failure handling
- Result aggregation and account mapping

Run tests:

```bash
pytest tests/test_alpaca_manager.py -v
```

### Integration Tests

**File:** `tests/test_alpaca_client.py`

Tests basic Alpaca client operations:

```bash
pytest tests/test_alpaca_client.py -v
```

### Manual Testing

Test all accounts interactively:

```bash
python backend/multi_alpaca_client.py
```

This script will:
1. Verify credentials for all accounts
2. Connect to each account
3. Display account info (balance, buying power, portfolio value)
4. List current positions for each account

## Common Issues

### Issue 1: Missing Credentials

**Error:** `Unknown account: CHATGPT` or `None` values in credentials

**Cause:** Environment variables not set

**Solution:**
```bash
# Check .env file
cat .env | grep ALPACA_CHATGPT

# Should see:
# ALPACA_CHATGPT_KEY_ID=your_key_here
# ALPACA_CHATGPT_SECRET_KEY=your_secret_here
```

### Issue 2: Invalid API Keys

**Error:** `401 Unauthorized` or `403 Forbidden`

**Cause:** Invalid or expired API keys

**Solution:**
1. Log in to Alpaca dashboard
2. Regenerate API keys
3. Update `.env` file with new keys
4. Restart application

### Issue 3: Order Rejected

**Error:** `Order failed: Insufficient buying power`

**Cause:** Account has insufficient funds

**Solution:**
```python
# Check buying power first
manager = MultiAlpacaManager()
account = await manager.get_client('CHATGPT').get_account()
print(f"Buying power: ${account['buying_power']}")

# Adjust order size to fit available buying power
```

### Issue 4: Rate Limiting

**Error:** `429 Too Many Requests`

**Cause:** Exceeded Alpaca's rate limits (200 requests/minute)

**Solution:**
- Use `place_orders_parallel()` instead of sequential calls
- Add delays between operations if needed
- Implement exponential backoff retry logic

### Issue 5: Market Closed

**Error:** `Order rejected: Market is closed`

**Cause:** Attempting to place order outside market hours

**Solution:**
```python
# Use extended_hours parameter for pre/post market trading
order = await client.place_order(
    symbol='SPY',
    qty=10,
    side='buy',
    extended_hours=True  # Enable extended hours trading
)
```

## Related Files

| File | Purpose |
|------|---------|
| `backend/multi_alpaca_client.py` | Multi-account client implementation |
| `backend/http_pool.py` | Shared HTTP connection pool |
| `backend/api/trades.py` | Trade execution API endpoints |
| `backend/services/trade_service.py` | Trade execution business logic |
| `backend/pipeline/stages/execution.py` | Pipeline execution stage |
| `tests/test_alpaca_manager.py` | Multi-account manager tests |
| `tests/test_alpaca_client.py` | Basic client tests |
| `.env.example` | Environment variable template |
| `CLAUDE.md` | Project technical documentation |

## Reference Documentation

### Alpaca API Documentation

- **Trading API:** https://alpaca.markets/docs/trading/
- **Market Data API:** https://alpaca.markets/docs/market-data/
- **Paper Trading:** https://alpaca.markets/docs/trading/paper-trading/

### Internal Documentation

- **API Endpoints:** [docs/API_ENDPOINTS.md](./API_ENDPOINTS.md)
- **Performance Metrics:** [docs/PERFORMANCE_METRICS.md](./PERFORMANCE_METRICS.md)
- **Database Architecture:** [CLAUDE.md](../CLAUDE.md#database-architecture)
- **Pipeline Architecture:** [PIPELINE.md](../PIPELINE.md)

## Best Practices

### 1. Always Use MultiAlpacaManager

✅ **Good:**
```python
from backend.multi_alpaca_client import MultiAlpacaManager

manager = MultiAlpacaManager()
order = await manager.place_order_for_account('COUNCIL', 'SPY', 10, 'buy')
```

❌ **Bad:**
```python
from market.alpaca_client import AlpacaClient

# Don't use single-account client directly
client = AlpacaClient(key_id=..., secret_key=...)
order = await client.place_order('SPY', 10, 'buy')
```

### 2. Use Parallel Operations When Possible

✅ **Good:**
```python
# Execute 6 trades in parallel (fast)
results = await manager.place_orders_parallel(orders)
```

❌ **Bad:**
```python
# Execute 6 trades sequentially (slow)
for order in orders:
    result = await manager.place_order_for_account(...)
```

### 3. Handle Errors Per Account

✅ **Good:**
```python
results = await manager.place_orders_parallel(orders)

for account_name, result in results.items():
    if result.get('status') == 'error':
        logger.error(f"{account_name} failed: {result['message']}")
    else:
        logger.info(f"{account_name} success: Order {result['id']}")
```

❌ **Bad:**
```python
# Don't let one account failure break all accounts
try:
    results = await manager.place_orders_parallel(orders)
except Exception as e:
    logger.error(f"All orders failed: {e}")
```

### 4. Use Account-Specific Credentials

✅ **Good:**
```python
# Each account has its own credentials
ALPACA_ACCOUNTS = {
    'CHATGPT': {
        'key_id': os.getenv('ALPACA_CHATGPT_KEY_ID'),
        'secret_key': os.getenv('ALPACA_CHATGPT_SECRET_KEY'),
        ...
    }
}
```

❌ **Bad:**
```python
# Don't reuse the same credentials for all accounts
ALPACA_ACCOUNTS = {
    'CHATGPT': {
        'key_id': os.getenv('APCA_API_KEY_ID'),  # ❌ Same for all
        'secret_key': os.getenv('APCA_API_SECRET_KEY'),  # ❌ Same for all
        ...
    }
}
```

### 5. Verify Credentials on Startup

✅ **Good:**
```python
from backend.multi_alpaca_client import verify_credentials

async def startup():
    credentials = verify_credentials()

    for account_name, has_creds in credentials.items():
        if not has_creds:
            logger.error(f"❌ {account_name}: Missing credentials")
            raise ValueError(f"Missing credentials for {account_name}")
        else:
            logger.info(f"✅ {account_name}: Credentials verified")
```

❌ **Bad:**
```python
# Don't wait until order execution to discover missing credentials
async def execute_trade():
    try:
        order = await manager.place_order_for_account(...)
    except Exception as e:
        logger.error("Missing credentials!")  # Too late!
```

## Performance Considerations

### Connection Pooling

The system uses a shared HTTP connection pool (`backend/http_pool.py`) for all accounts:

- **Connection reuse:** Reduces latency by reusing TCP connections
- **Automatic retry:** Built-in retry logic for transient failures
- **Timeout handling:** Prevents hanging requests
- **Concurrent requests:** Supports parallel operations across accounts

### Parallel Execution

Use parallel operations for better performance:

| Operation | Sequential Time | Parallel Time | Speedup |
|-----------|----------------|---------------|---------|
| Get 6 accounts | ~3 seconds | ~500ms | **6x faster** |
| Place 6 orders | ~4 seconds | ~700ms | **5.7x faster** |
| Get 6 positions | ~2 seconds | ~400ms | **5x faster** |

### Rate Limiting

Alpaca rate limits:
- **200 requests/minute** per account
- **GET requests:** More lenient
- **POST requests:** Stricter limits

Best practices:
- Use `place_orders_parallel()` to stay within limits
- Batch operations when possible
- Add exponential backoff for retries

## Security Considerations

### 1. Never Hardcode Credentials

✅ **Good:**
```python
'key_id': os.getenv('ALPACA_CHATGPT_KEY_ID')
```

❌ **Bad:**
```python
'key_id': 'PKXXXXXXXXXX'  # ❌ Never hardcode!
```

### 2. Use Paper Trading Accounts

✅ **Good:**
```python
# Always use paper trading for testing
client = AlpacaAccountClient(account_name='COUNCIL', paper=True)
```

❌ **Bad:**
```python
# Never use live accounts for testing
client = AlpacaAccountClient(account_name='COUNCIL', paper=False)
```

### 3. Separate Production and Development Keys

Use different API keys for each environment:
- `.env.development` - Development keys
- `.env.production` - Production keys
- `.env.test` - Test keys (separate accounts)

### 4. Rotate Keys Regularly

- Rotate API keys every 90 days
- Use Alpaca's dashboard to revoke old keys
- Update `.env` file with new keys
- Restart application to load new keys

## Summary

The Alpaca multi-account architecture enables:

✅ **Parallel Strategy Testing:** Compare 6 AI strategies side-by-side
✅ **Isolated Execution:** Each account operates independently
✅ **Performance Comparison:** Direct A/B testing of trading decisions
✅ **Risk Management:** Separate capital per strategy
✅ **Scalability:** Easy to add new accounts

**Key Takeaways:**
1. Use `MultiAlpacaManager` for all account operations
2. Credentials are loaded from environment variables
3. Account names (CHATGPT, GEMINI, etc.) are used throughout the system
4. Parallel operations provide significant performance improvements
5. Each account has isolated capital and orders

For questions or issues, see the [Related Files](#related-files) section or consult [CLAUDE.md](../CLAUDE.md).
