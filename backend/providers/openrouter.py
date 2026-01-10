"""OpenRouter provider implementation."""

import os
import httpx
from typing import List, Dict, Any, Optional
from .base import BaseLLMProvider, ProviderConfig, ModelResponse


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter API provider for multi-model access."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_url = (
            config.base_url or "https://openrouter.ai/api/v1/chat/completions"
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
        Query a model via OpenRouter API.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: OpenRouter model identifier (e.g., "openai/gpt-4o")
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters (e.g., reasoning_effort)

        Returns:
            ModelResponse with content and metadata
        """
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
        }

        if temperature is not None:
            payload["temperature"] = temperature

        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        payload.update(kwargs)

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(
                    self.api_url, headers=headers, json=payload
                )
                response.raise_for_status()

                data = response.json()
                choice = data["choices"][0]
                message = choice["message"]

                return ModelResponse(
                    content=message.get("content"),
                    reasoning_details=message.get("reasoning_details"),
                    model=data.get("model"),
                    prompt_tokens=data.get("usage", {}).get("prompt_tokens"),
                    completion_tokens=data.get("usage", {}).get("completion_tokens"),
                    total_tokens=data.get("usage", {}).get("total_tokens"),
                )

        except httpx.HTTPStatusError as e:
            raise Exception(
                f"OpenRouter HTTP error: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            raise Exception(f"OpenRouter query failed: {e}")

    def get_models(self) -> List[str]:
        """
        Get list of available models from OpenRouter.

        Returns:
            List of model identifiers
        """
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    "https://openrouter.ai/api/v1/models", headers=headers
                )
                response.raise_for_status()

                data = response.json()
                return [model["id"] for model in data.get("data", [])]

        except Exception as e:
            print(f"Warning: Failed to fetch OpenRouter models: {e}")
            return []

    def validate_key(self) -> bool:
        """
        Validate OpenRouter API key.

        Returns:
            True if valid, False otherwise
        """
        if not self.config.api_key:
            return False

        try:
            models = self.get_models()
            return len(models) > 0
        except Exception:
            return False
