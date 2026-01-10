"""Base abstract class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pydantic import BaseModel


@dataclass
class ProviderConfig:
    """Configuration for a provider."""

    provider_id: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: float = 120.0
    max_retries: int = 3
    enabled: bool = True


@dataclass
class ModelResponse:
    """Response from an LLM model."""

    content: str
    reasoning_details: Optional[str] = None
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    cached: bool = False


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: ProviderConfig):
        self.config = config

    @abstractmethod
    async def query(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """
        Query an LLM model.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            ModelResponse with content and metadata
        """
        pass

    @abstractmethod
    def get_models(self) -> List[str]:
        """
        Get list of available models for this provider.

        Returns:
            List of model identifiers
        """
        pass

    def validate_key(self) -> bool:
        """
        Validate that the API key is configured.

        Returns:
            True if valid, False otherwise
        """
        return self.config.api_key is not None and len(self.config.api_key) > 0
