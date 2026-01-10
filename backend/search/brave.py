"""Brave search provider (privacy-focused, requires API key)."""

import httpx
from typing import List
from .base import BaseSearchProvider, SearchResult, SearchConfig


class BraveProvider(BaseSearchProvider):
    """Brave search provider - privacy-focused."""

    def __init__(self, config: SearchConfig):
        super().__init__(config)
        self.api_url = (
            config.base_url or "https://api.search.brave.com/res/v1/web/search"
        )

    async def search(
        self, query: str, num_results: int = 10, **kwargs
    ) -> List[SearchResult]:
        """
        Search using Brave API.

        Args:
            query: Search query string
            num_results: Number of results to return
            **kwargs: Additional Brave parameters

        Returns:
            List of SearchResult objects
        """
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Accept": "application/json",
        }

        params = {
            "q": query,
            "count": num_results,
            "text_decorations": True,
            "result_filter": "web",
        }

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.get(
                    self.api_url, params=params, headers=headers
                )
                response.raise_for_status()

                data = response.json()

                results = []
                for item in data.get("web", {}).get("results", []):
                    results.append(
                        SearchResult(
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            snippet=item.get("description", ""),
                            content=None,
                            source="brave",
                            published_date=None,
                            relevance_score=item.get("score"),
                        )
                    )

                return results

        except httpx.HTTPStatusError as e:
            print(f"⚠️  Brave HTTP error: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            print(f"⚠️  Brave search failed: {e}")
            return []

    def get_provider_name(self) -> str:
        return "Brave"

    def validate_key(self) -> bool:
        if not self.config.api_key:
            return False

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(
                    self.api_url,
                    params={"q": "test", "count": 1},
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                return response.status_code == 200
        except Exception:
            return False
