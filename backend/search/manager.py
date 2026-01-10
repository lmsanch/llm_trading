"""Search manager for orchestrating web search + content extraction."""

import asyncio
from typing import List, Dict, Any, Optional
from .base import BaseSearchProvider, SearchResult, SearchConfig
from .tavily import TavilyProvider
from .brave import BraveProvider
from .jina_reader import fetch_article_content, enrich_search_results


class SearchManager:
    """Manager for web search with content extraction."""

    def __init__(self, config_path: str = "config/search.yaml"):
        self.config_path = config_path
        self._providers: Dict[str, BaseSearchProvider] = {}
        self._default_provider: Optional[str] = None
        self._load_config()

    def _load_config(self):
        """Load search provider configuration."""
        import yaml
        import os

        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)

            self._default_provider = config.get("default_provider", "tavily")
            max_results = config.get("max_results", 10)
            enable_jina = config.get("enable_jina_reader", True)

            providers_config = config.get("providers", {})

            for provider_id, provider_data in providers_config.items():
                api_key_env = provider_data.get("api_key_env")
                search_config = SearchConfig(
                    provider_id=provider_id,
                    api_key=os.getenv(api_key_env) if api_key_env else None,
                    base_url=provider_data.get("base_url"),
                    enabled=provider_data.get("enabled", True),
                    timeout=provider_data.get("timeout", 30.0),
                    max_results=max_results,
                )

                provider = self._create_provider(provider_id, search_config)
                if provider.validate_key():
                    self._providers[provider_id] = provider
                    print(f"✅ Loaded search provider: {provider_id}")
                else:
                    print(
                        f"⚠️  Search provider {provider_id} failed validation (skipping)"
                    )

            self.enable_jina_reader = enable_jina

        except FileNotFoundError:
            print(f"⚠️  Search config not found: {self.config_path} (using defaults)")
            self._default_provider = "duckduckgo"
            self.enable_jina_reader = True

    def _create_provider(
        self, provider_id: str, config: SearchConfig
    ) -> BaseSearchProvider:
        """Create provider instance."""
        provider_map = {
            "tavily": TavilyProvider,
            "brave": BraveProvider,
        }

        provider_class = provider_map.get(provider_id)
        if not provider_class:
            raise ValueError(f"Unknown search provider: {provider_id}")

        return provider_class(config)

    def get_provider(
        self, provider_id: Optional[str] = None
    ) -> BaseSearchProvider | None:
        """Get provider instance by ID."""
        provider_id = provider_id or self._default_provider
        return self._providers.get(provider_id)

    async def search(
        self,
        query: str,
        provider_id: Optional[str] = None,
        num_results: int = 10,
        fetch_full_content: bool = True,
    ) -> List[SearchResult]:
        """
        Perform web search with optional full content extraction.

        Args:
            query: Search query string
            provider_id: Provider to use (default from config)
            num_results: Number of results
            fetch_full_content: Whether to fetch full article content via Jina

        Returns:
            List of enriched SearchResult objects
        """
        provider = self.get_provider(provider_id)
        if not provider:
            raise ValueError(f"Search provider not found: {provider_id}")

        print(f"🔍 Searching with {provider.get_provider_name()}: {query}")

        results = await provider.search(query, num_results=num_results)

        if fetch_full_content and self.enable_jina_reader:
            print(f"📄 Fetching full content for {min(len(results), 10)} articles...")
            results = await enrich_search_results(results, max_articles=num_results)

        return results

    async def search_for_tickers(
        self,
        tickers: List[str],
        search_terms: Optional[List[str]] = None,
        provider_id: Optional[str] = None,
    ) -> Dict[str, List[SearchResult]]:
        """
        Search for multiple tickers in parallel.

        Args:
            tickers: List of ticker symbols (e.g., ["SPY", "QQQ"])
            search_terms: Optional list of search terms to combine with tickers
            provider_id: Provider to use

        Returns:
            Dict mapping ticker to search results
        """
        queries = []

        for ticker in tickers:
            if search_terms:
                for term in search_terms:
                    queries.append(f"{ticker} ETF {term}")
            else:
                queries.append(f"{ticker} ETF latest news")

        tasks = [self.search(query, provider_id=provider_id) for query in queries]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        ticker_results = {}
        for i, result in enumerate(results_list):
            if not isinstance(result, Exception):
                ticker = tickers[i % len(tickers)]
                if ticker not in ticker_results:
                    ticker_results[ticker] = []
                ticker_results[ticker].extend(result)

        return ticker_results

    def get_providers(self) -> List[str]:
        """Get list of available provider IDs."""
        return list(self._providers.keys())

    def get_default_provider(self) -> str | None:
        """Get default provider ID."""
        return self._default_provider
