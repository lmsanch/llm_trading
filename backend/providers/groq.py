"""Groq provider implementation for ultra-fast inference."""

from typing import List, Dict, Any, Optional
from groq import Groq
from .base import BaseLLMProvider, ProviderConfig, ModelResponse


class GroqProvider(BaseLLMProvider):
    """Groq API provider for ultra-fast Llama/Mixtral inference."""

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = Groq(api_key=config.api_key)

    async def query(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ModelResponse:
        """
        Query Groq model for ultra-fast inference.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier (e.g., "llama-3.3-70b-versatile")
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            ModelResponse with content and metadata
        """
        try:
            response = self.client.chat.completions.create(
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
            raise Exception(f"Groq query failed: {e}")

    def get_models(self) -> List[str]:
        """
        Get list of available Groq models.

        Returns:
            List of model identifiers
        """
        return [
            "llama-3.3-70b-versatile",
            "llama-3.3-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
            "deepseek-r1-distill-llama-70b",
        ]

    def validate_key(self) -> bool:
        """
        Validate Groq API key.

        Returns:
            True if valid, False otherwise
        """
        if not self.config.api_key:
            return False

        try:
            self.client.chat.completions.create(
                model="llama-3.3-8b-instant",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True
        except Exception:
            return False
