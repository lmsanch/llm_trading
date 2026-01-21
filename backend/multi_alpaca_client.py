"""Multi-account Alpaca client for managing 6 paper trading accounts."""

import os
import asyncio
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from backend.http_pool import get_alpaca_client

load_dotenv()

# ============================================================================
# ALPACA ACCOUNT CONFIGURATION
# ============================================================================

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
    'CLAUDE': {
        'key_id': os.getenv('ALPACA_CLAUDE_KEY_ID'),
        'secret_key': os.getenv('ALPACA_CLAUDE_SECRET_KEY'),
        'account_id': 'PA38PAHFRFYC',
        'email': 'lmsanch@gmail.com'
    },
    'GROQ': {
        'key_id': os.getenv('ALPACA_GROQ_KEY_ID'),
        'secret_key': os.getenv('ALPACA_GROQ_SECRET_KEY'),
        'account_id': 'PA33MEQA4WT7',
        'email': 'strategy1a@dnnalpha.ai'
    },
    'DEEPSEEK': {
        'key_id': os.getenv('ALPACA_DEEPSEEK_KEY_ID'),
        'secret_key': os.getenv('ALPACA_DEEPSEEK_SECRET_KEY'),
        'account_id': 'PA3KKW3TN54V',
        'email': 'strategy1a@dnnalpha.ai'
    },
    'COUNCIL': {
        'key_id': os.getenv('ALPACA_COUNCIL_KEY_ID'),
        'secret_key': os.getenv('ALPACA_COUNCIL_SECRET_KEY'),
        'account_id': 'PA3MQLPXBSO1',
        'email': 'lmsanch@gmail.com'
    }
}

PAPER_URL = "https://paper-api.alpaca.markets"


# ============================================================================
# CLIENT CLASS
# ============================================================================

class AlpacaAccountClient:
    """Alpaca client for a single account."""
    
    def __init__(self, account_name: str, paper: bool = True):
        """
        Initialize Alpaca client for specific account.
        
        Args:
            account_name: Account nickname (CHATGPT, GEMINI, etc.)
            paper: Use paper trading URL
        """
        if account_name not in ALPACA_ACCOUNTS:
            raise ValueError(f"Unknown account: {account_name}")
        
        account_config = ALPACA_ACCOUNTS[account_name]
        self.account_name = account_name
        self.account_id = account_config['account_id']
        self.base_url = PAPER_URL if paper else "https://api.alpaca.markets"
        self.headers = {
            "APCA-API-KEY-ID": account_config['key_id'],
            "APCA-API-SECRET-KEY": account_config['secret_key'],
            "Content-Type": "application/json",
        }
    
    async def get_account(self) -> Dict[str, Any]:
        """Get account information."""
        client = get_alpaca_client()
        response = await client.get(f"{self.base_url}/v2/account", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    async def get_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all positions or specific symbol position."""
        endpoint = f"/v2/positions/{symbol}" if symbol else "/v2/positions"
        client = get_alpaca_client()
        response = await client.get(f"{self.base_url}{endpoint}", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    async def get_orders(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get orders with optional filters."""
        params = {}
        if status:
            params["status"] = status
        if limit:
            params["limit"] = limit
        if symbol:
            params["symbol"] = symbol

        client = get_alpaca_client()
        response = await client.get(f"{self.base_url}/v2/orders", params=params, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
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
    ) -> Dict[str, Any]:
        """
        Place an order.
        
        Args:
            symbol: Ticker symbol (e.g., "SPY")
            qty: Quantity (number of shares)
            side: "buy" or "sell"
            order_type: "market", "limit", "stop", "stop_limit"
            limit_price: Limit price for limit orders
            stop_price: Stop price for stop orders
            time_in_force: "day", "gtc", "ioc", "fok"
            extended_hours: Allow extended hours trading
        
        Returns:
            Order response dict
        """
        payload = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force,
            "extended_hours": extended_hours,
        }
        
        if limit_price:
            payload["limit_price"] = limit_price
        if stop_price:
            payload["stop_price"] = stop_price

        client = get_alpaca_client()
        response = await client.post(f"{self.base_url}/v2/orders", json=payload, headers=self.headers)
        if response.status_code != 200:
            error_data = response.json()
            raise Exception(
                f"Order failed for {self.account_name}: {error_data.get('message', 'Unknown error')}"
            )
        return response.json()
    
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order by ID."""
        client = get_alpaca_client()
        response = await client.delete(f"{self.base_url}/v2/orders/{order_id}", headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    async def close_position(self, symbol: str) -> Dict[str, Any]:
        """
        Close a position (liquidate all shares).

        Args:
            symbol: Ticker symbol to close position for

        Returns:
            Order response dict
        """
        # Get current position to determine qty and side
        positions = await self.get_positions(symbol=symbol)
        if not positions:
            raise ValueError(f"No position found for {symbol} in account {self.account_name}")

        position = positions[0]
        qty = abs(float(position['qty']))
        side = "sell" if float(position['qty']) > 0 else "buy"

        return await self.place_order(
            symbol=symbol,
            qty=int(qty),
            side=side,
            order_type="market",
            time_in_force="day"
        )

    async def get_bars(
        self,
        symbol: str,
        timeframe: str = "1Day",
        limit: int = 100,
        start: Optional[str] = None,
        end: Optional[str] = None,
        adjustment: str = "raw",
        feed: str = "iex"
    ) -> List[Dict[str, Any]]:
        """
        Get historical bar data from Alpaca Data API.

        Note: Uses data.alpaca.markets (not paper-api) for historical bars.

        Args:
            symbol: Ticker symbol (e.g., "SPY")
            timeframe: Bar timeframe ("1Day", "1Hour", "5Min", "1Min")
            limit: Number of bars to return (max 10000)
            start: Start date (RFC-3339 format)
            end: End date (RFC-3339 format)
            adjustment: Adjustment type ("raw", "dividend", "split", "total")
            feed: Data feed ("iex" for free, "sip" for paid)

        Returns:
            List of bar dicts with keys: t (timestamp), o, h, l, c, v, vw, n
        """
        # Alpaca Data API (separate from trading API)
        data_base_url = "https://data.alpaca.markets"

        params = {
            "timeframe": timeframe,
            "limit": limit,
            "adjustment": adjustment,
        }

        # Only use 'feed' for paid (sip) or if explicitly needed
        # For paper trading, 'iex' is typically not needed with data API
        if feed != "iex":
            params["feed"] = feed

        if start:
            params["start"] = start
        if end:
            params["end"] = end

        client = get_alpaca_client()
        response = await client.get(f"{data_base_url}/v2/stocks/{symbol}/bars", params=params, headers=self.headers)
        response.raise_for_status()
        return response.json().get("bars", [])


# ============================================================================
# MULTI-ACCOUNT MANAGER
# ============================================================================

class MultiAlpacaManager:
    """Manager for all 6 Alpaca paper trading accounts."""
    
    def __init__(self):
        """Initialize all account clients."""
        self.clients = {
            account_name: AlpacaAccountClient(account_name)
            for account_name in ALPACA_ACCOUNTS.keys()
        }
    
    def get_client(self, account_name: str) -> AlpacaAccountClient:
        """Get client for specific account."""
        if account_name not in self.clients:
            raise ValueError(f"Unknown account: {account_name}")
        return self.clients[account_name]
    
    async def get_all_accounts(self) -> Dict[str, Dict[str, Any]]:
        """Get account info for all accounts."""
        results = {}
        tasks = [client.get_account() for client in self.clients.values()]
        account_info_list = await asyncio.gather(*tasks)
        
        for account_name, account_info in zip(self.clients.keys(), account_info_list):
            results[account_name] = account_info
        
        return results
    
    async def get_all_positions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get positions for all accounts."""
        results = {}
        tasks = [client.get_positions() for client in self.clients.values()]
        positions_list = await asyncio.gather(*tasks)
        
        for account_name, positions in zip(self.clients.keys(), positions_list):
            results[account_name] = positions
        
        return results
    
    async def place_order_for_account(
        self,
        account_name: str,
        symbol: str,
        qty: int,
        side: str,
        order_type: str = "market",
        limit_price: Optional[str] = None,
        stop_price: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Place order for specific account.
        
        Args:
            account_name: Account nickname
            symbol: Ticker symbol
            qty: Quantity
            side: "buy" or "sell"
            order_type: Order type
            limit_price: Limit price
            stop_price: Stop price
        
        Returns:
            Order response dict
        """
        client = self.get_client(account_name)
        return await client.place_order(
            symbol=symbol,
            qty=qty,
            side=side,
            order_type=order_type,
            limit_price=limit_price,
            stop_price=stop_price
        )
    
    async def place_orders_parallel(
        self,
        orders: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Place orders for multiple accounts in parallel.
        
        Args:
            orders: List of dicts with keys:
                - account_name: Account nickname
                - symbol: Ticker symbol
                - qty: Quantity
                - side: "buy" or "sell"
                - order_type: Order type
                - limit_price: Limit price
                - stop_price: Stop price
        
        Returns:
            Dict mapping account name to order response
        """
        tasks = [
            self.place_order_for_account(
                account_name=order['account_name'],
                symbol=order['symbol'],
                qty=order['qty'],
                side=order['side'],
                order_type=order.get('order_type', 'market'),
                limit_price=order.get('limit_price'),
                stop_price=order.get('stop_price')
            )
            for order in orders
        ]
        
        results = await asyncio.gather(*tasks)
        
        return {
            order['account_name']: result
            for order, result in zip(orders, results)
        }
    
    async def close_all_positions(self, account_name: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Close all positions for one or all accounts.
        
        Args:
            account_name: Specific account or None for all accounts
        
        Returns:
            Dict mapping account name to close order response
        """
        if account_name:
            # Close positions for specific account
            client = self.get_client(account_name)
            positions = await client.get_positions()
            
            results = {}
            for position in positions:
                symbol = position['symbol']
                results[symbol] = await client.close_position(symbol)
            
            return {account_name: results}
        else:
            # Close positions for all accounts
            results = {}
            for acc_name, client in self.clients.items():
                positions = await client.get_positions()
                account_results = {}
                for position in positions:
                    symbol = position['symbol']
                    account_results[symbol] = await client.close_position(symbol)
                results[acc_name] = account_results
            
            return results


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_account_config(account_name: str) -> Dict[str, Any]:
    """Get configuration for specific account."""
    if account_name not in ALPACA_ACCOUNTS:
        raise ValueError(f"Unknown account: {account_name}")
    return ALPACA_ACCOUNTS[account_name].copy()


def get_all_account_names() -> List[str]:
    """Get list of all account names."""
    return list(ALPACA_ACCOUNTS.keys())


def verify_credentials() -> Dict[str, bool]:
    """
    Verify that all required credentials are set.
    
    Returns:
        Dict mapping account name to credential status (True/False)
    """
    results = {}
    for account_name, config in ALPACA_ACCOUNTS.items():
        has_key = config['key_id'] is not None
        has_secret = config['secret_key'] is not None
        results[account_name] = has_key and has_secret
    
    return results


# ============================================================================
# MAIN (for testing)
# ============================================================================

async def main():
    """Test multi-account Alpaca client."""
    
    print("🔍 Checking Alpaca credentials...\n")
    
    # Verify credentials
    credentials = verify_credentials()
    for account_name, has_creds in credentials.items():
        status = "✅" if has_creds else "❌"
        print(f"{status} {account_name}: {'Credentials set' if has_creds else 'Missing credentials'}")
    
    print("\n🚀 Testing account connections...\n")
    
    # Initialize manager
    manager = MultiAlpacaManager()
    
    # Get account info for all accounts
    try:
        accounts = await manager.get_all_accounts()
        
        for account_name, account_info in accounts.items():
            print(f"\n✅ {account_name}")
            print(f"   Account ID: {account_info['id']}")
            print(f"   Buying Power: ${account_info.get('buying_power', 'N/A')}")
            print(f"   Cash: ${account_info.get('cash', 'N/A')}")
            print(f"   Portfolio Value: ${account_info.get('portfolio_value', 'N/A')}")
        
        # Get positions for all accounts
        print("\n\n📊 Current Positions...\n")
        all_positions = await manager.get_all_positions()
        
        for account_name, positions in all_positions.items():
            if positions:
                print(f"\n{account_name}:")
                for pos in positions:
                    print(f"   - {pos['symbol']}: {pos['qty']} shares @ ${pos.get('avg_entry_price', 'N/A')}")
            else:
                print(f"\n{account_name}: No open positions")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nNote: Make sure all Alpaca credentials are set in .env file:")
        print("  ALPACA_CHATGPT_KEY_ID")
        print("  ALPACA_CHATGPT_SECRET_KEY")
        print("  ALPACA_GEMINI_KEY_ID")
        print("  ALPACA_GEMINI_SECRET_KEY")
        print("  ALPACA_CLAUDE_KEY_ID")
        print("  ALPACA_CLAUDE_SECRET_KEY")
        print("  ALPACA_GROQ_KEY_ID")
        print("  ALPACA_GROQ_SECRET_KEY")
        print("  ALPACA_DEEPSEEK_KEY_ID")
        print("  ALPACA_DEEPSEEK_SECRET_KEY")
        print("  ALPACA_COUNCIL_KEY_ID")
        print("  ALPACA_COUNCIL_SECRET_KEY")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
