import httpx
import os
from typing import List, Dict, Any, Optional


class AlpacaClient:
    """Direct REST API client for Alpaca paper trading."""

    PAPER_URL = "https://paper-api.alpaca.markets"

    def __init__(
        self,
        key_id: str | None = None,
        secret_key: str | None = None,
        paper: bool = True,
    ):
        self.key_id = key_id or os.getenv("APCA_API_KEY_ID")
        self.secret_key = secret_key or os.getenv("APCA_API_SECRET_KEY")
        self.base_url = self.PAPER_URL if paper else "https://api.alpaca.markets"
        self.headers = {
            "APCA-API-KEY-ID": self.key_id,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json",
        }

    async def get_account(self) -> Dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers
        ) as client:
            response = await client.get("/v2/account")
            response.raise_for_status()
            return response.json()

    async def get_positions(self, symbol: str | None = None) -> List[Dict[str, Any]]:
        endpoint = f"/v2/positions/{symbol}" if symbol else "/v2/positions"
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers
        ) as client:
            response = await client.get(endpoint)
            response.raise_for_status()
            return response.json()

    async def get_orders(
        self,
        status: str | None = None,
        limit: int | None = None,
        symbol: str | None = None,
    ) -> List[Dict[str, Any]]:
        params = {}
        if status:
            params["status"] = status
        if limit:
            params["limit"] = limit
        if symbol:
            params["symbol"] = symbol

        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers
        ) as client:
            response = await client.get("/v2/orders", params=params)
            response.raise_for_status()
            return response.json()

    async def place_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        order_type: str = "market",
        limit_price: str | None = None,
        stop_price: str | None = None,
        time_in_force: str = "gtc",
        extended_hours: bool = False,
    ) -> Dict[str, Any]:
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

        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers
        ) as client:
            response = await client.post("/v2/orders", json=payload)
            if response.status_code != 200:
                error_data = response.json()
                raise Exception(
                    f"Order failed: {error_data.get('message', 'Unknown error')}"
                )
            return response.json()

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(
            base_url=self.base_url, headers=self.headers
        ) as client:
            response = await client.delete(f"/v2/orders/{order_id}")
            response.raise_for_status()
            return response.json()
