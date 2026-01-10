"""Web search provider abstractions."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Individual search result."""

    title: str
    url: str
    snippet: str
    content: Optional[str] = None
    source: str = "unknown"
    published_date: Optional[str] = None
    relevance_score: Optional[float] = None


@dataclass
class SearchConfig:
    """Configuration for a search provider."""

    provider_id: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    enabled: bool = True
    timeout: float = 30.0
    max_results: int = 10


class BaseSearchProvider(ABC):
    """Abstract base class for web search providers."""

    def __init__(self, config: SearchConfig):
        self.config = config

    @abstractmethod
    async def search(
        self, query: str, num_results: int = 10, **kwargs
    ) -> List[SearchResult]:
        """
        Perform web search.

        Args:
            query: Search query string
            num_results: Number of results to return
            **kwargs: Provider-specific parameters

        Returns:
            List of SearchResult objects
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider display name."""
        pass

    def validate_key(self) -> bool:
        """
        Validate that API key is configured (if required).

        Returns:
            True if valid/available, False otherwise
        """
        if not self.config.api_key:
            return False
        return len(self.config.api_key) > 0
