"""Anthropic direct API provider implementation."""

import os
from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from .base import BaseLLMProvider, ProviderConfig, ModelResponse


class AnthropicProvider(BaseLLMProvider):
    """Anthropic direct API provider."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = Anthropic(api_key=config.api_key, timeout=config.timeout)

    async def query(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """
        Query Anthropic model via direct API.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier (e.g., "claude-sonnet-4.5")
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters (e.g., top_k, top_p)

        Returns:
            ModelResponse with content and metadata
        """
        try:
            response = self.client.messages.create(
                model=model,
                messages=messages,
                temperature=temperature if temperature is not None else 0.7,
                max_tokens=max_tokens if max_tokens is not None else 4096,
                **kwargs,
            )

            return ModelResponse(
                content=response.content[0].text,
                model=response.model,
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            )

        except Exception as e:
            raise Exception(f"Anthropic query failed: {e}")

    def get_models(self) -> List[str]:
        """
        Get list of available Anthropic models.

        Returns:
            List of model identifiers
        """
        return [
            "claude-sonnet-4.5",
            "claude-opus-4",
            "claude-haiku-4",
            "claude-3.5-sonnet",
            "claude-3-opus",
            "claude-3-haiku",
        ]

    def validate_key(self) -> bool:
        """
        Validate Anthropic API key.

        Returns:
            True if valid, False otherwise
        """
        if not self.config.api_key:
            return False

        try:
            self.client.messages.create(
                model="claude-haiku-4",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True
        except Exception:
            return False
