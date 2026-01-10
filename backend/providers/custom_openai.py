"""Custom OpenAI-compatible endpoint provider."""

import os
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
from .base import BaseLLMProvider, ProviderConfig, ModelResponse


class CustomOpenAIProvider(BaseLLMProvider):
    """Provider for any OpenAI-compatible API endpoint."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = AsyncOpenAI(
            api_key=config.api_key or "dummy-key",
            base_url=config.base_url,
            timeout=config.timeout,
        )

    async def query(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """
        Query custom OpenAI-compatible endpoint.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            ModelResponse with content and metadata
        """
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature if temperature is not None else 0.7,
                max_tokens=max_tokens if max_tokens is not None else 4096,
                **kwargs,
            )

            choice = response.choices[0]

            return ModelResponse(
                content=choice.message.content,
                model=response.model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )

        except Exception as e:
            raise Exception(f"Custom OpenAI endpoint query failed: {e}")

    def get_models(self) -> List[str]:
        """
        Get list of available models from endpoint.

        Returns:
            List of model identifiers
        """
        try:
            models = await self.client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            print(f"Warning: Failed to fetch models from custom endpoint: {e}")
            return []

    def validate_key(self) -> bool:
        """
        Validate custom endpoint connection.

        Returns:
            True if endpoint is accessible, False otherwise
        """
        try:
            models = await self.get_models()
            return len(models) > 0
        except Exception:
            return False
