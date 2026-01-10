"""Ollama provider for local model inference."""

import httpx
from typing import List, Dict, Any, Optional
from .base import BaseLLMProvider, ProviderConfig, ModelResponse


class OllamaProvider(BaseLLMProvider):
    """Ollama provider for local open-source models."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"

    async def query(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """
        Query local Ollama model.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier (e.g., "llama3:70b")
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            ModelResponse with content and metadata
        """
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }

        if temperature is not None:
            payload["options"] = {"temperature": temperature}

        if max_tokens is not None:
            if "options" not in payload:
                payload["options"] = {}
            payload["options"]["num_predict"] = max_tokens

        payload["options"] = {**(payload.get("options", {})), **kwargs}

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()

                data = response.json()

                return ModelResponse(
                    content=data.get("message", {}).get("content", ""),
                    model=model,
                    prompt_tokens=data.get("prompt_eval_count"),
                    completion_tokens=data.get("eval_count"),
                    total_tokens=data.get("prompt_eval_count", 0)
                    + data.get("eval_count", 0),
                )

        except Exception as e:
            raise Exception(f"Ollama query failed: {e}")

    def get_models(self) -> List[str]:
        """
        Get list of available Ollama models.

        Returns:
            List of model identifiers
        """
        url = f"{self.base_url}/api/tags"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                data = response.json()
                return [model["name"] for model in data.get("models", [])]

        except Exception as e:
            print(f"Warning: Failed to fetch Ollama models: {e}")
            return []

    def validate_key(self) -> bool:
        """
        Validate Ollama connection.

        Returns:
            True if Ollama is accessible, False otherwise
        """
        try:
            models = await self.get_models()
            return len(models) > 0
        except Exception:
            return False
