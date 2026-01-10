"""Tavily search provider (LLM-optimized, requires API key)."""

import httpx
from typing import List
from .base import BaseSearchProvider, SearchResult, SearchConfig


class TavilyProvider(BaseSearchProvider):
    """Tavily search provider - optimized for LLM applications."""

    def __init__(self, config: SearchConfig):
        super().__init__(config)
        self.api_url = config.base_url or "https://api.tavily.com/search"

    async def search(
        self, query: str, num_results: int = 10, **kwargs
    ) -> List[SearchResult]:
        """
        Search using Tavily API.

        Args:
            query: Search query string
            num_results: Number of results to return
            **kwargs: Additional Tavily parameters

        Returns:
            List of SearchResult objects
        """
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "api_key": self.config.api_key,
            "query": query,
            "max_results": num_results,
            "search_depth": "advanced",
            "include_images": False,
            "include_image_descriptions": False,
            "include_answer": True,
        }

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    self.api_url, json=payload, headers=headers
                )
                response.raise_for_status()

                data = response.json()

                results = []
                for item in data.get("results", []):
                    results.append(
                        SearchResult(
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            snippet=item.get("content", ""),
                            content=item.get("content"),
                            source="tavily",
                            published_date=item.get("publishedDate"),
                            relevance_score=item.get("score"),
                        )
                    )

                return results

        except httpx.HTTPStatusError as e:
            print(f"⚠️  Tavily HTTP error: {e.response.status_code} - {e.response.text}")
            return []
        except Exception as e:
            print(f"⚠️  Tavily search failed: {e}")
            return []

    def get_provider_name(self) -> str:
        return "Tavily"

    def validate_key(self) -> bool:
        if not self.config.api_key:
            return False

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    self.api_url,
                    json={
                        "api_key": self.config.api_key,
                        "query": "test",
                        "max_results": 1,
                    },
                    headers={"Authorization": f"Bearer {self.config.api_key}"},
                )
                return response.status_code == 200
        except Exception:
            return False
