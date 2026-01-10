"""Provider registry for dynamic provider loading."""

import os
import yaml
from typing import Dict, Optional
from backend.providers.base import BaseLLMProvider, ProviderConfig
from backend.providers import (
    OpenRouterProvider,
    AnthropicProvider,
    GroqProvider,
    OllamaProvider,
    CustomOpenAIProvider,
)


class ProviderRegistry:
    """Registry for managing LLM providers."""

    def __init__(self):
        self._providers: Dict[str, BaseLLMProvider] = {}
        self._provider_configs: Dict[str, ProviderConfig] = {}

    def load_providers(self, config_path: str = "config/providers.yaml") -> None:
        """
        Load provider configurations from YAML file.

        Args:
            config_path: Path to providers.yaml
        """
        with open(config_path, "r") as f:
            configs = yaml.safe_load(f)

        for provider_id, config_data in configs.items():
            config = ProviderConfig(
                provider_id=provider_id,
                api_key=os.getenv(config_data.get("api_key_env", "")),
                base_url=config_data.get("base_url"),
                timeout=config_data.get("timeout", 120.0),
                max_retries=config_data.get("max_retries", 3),
                enabled=config_data.get("enabled", True),
            )
            self._provider_configs[provider_id] = config

            if config.enabled:
                provider = self._create_provider(provider_id, config)
                if provider.validate_key():
                    self._providers[provider_id] = provider
                    print(f"✅ Loaded provider: {provider_id}")
                else:
                    print(f"⚠️  Provider {provider_id} failed validation (skipping)")

    def _create_provider(
        self, provider_id: str, config: ProviderConfig
    ) -> BaseLLMProvider:
        """
        Create provider instance from config.

        Args:
            provider_id: Provider identifier
            config: Provider configuration

        Returns:
            Provider instance
        """
        provider_map = {
            "openrouter": OpenRouterProvider,
            "anthropic": AnthropicProvider,
            "groq": GroqProvider,
            "ollama": OllamaProvider,
            "custom_openai": CustomOpenAIProvider,
        }

        provider_class = provider_map.get(provider_id)
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_id}")

        return provider_class(config)

    def get_provider(self, provider_id: str) -> Optional[BaseLLMProvider]:
        """
        Get provider instance by ID.

        Args:
            provider_id: Provider identifier

        Returns:
            Provider instance or None if not found
        """
        return self._providers.get(provider_id)

    def get_all_providers(self) -> Dict[str, BaseLLMProvider]:
        """Get all loaded providers."""
        return self._providers.copy()

    def parse_model_id(self, model_id: str) -> tuple[str, str]:
        """
        Parse prefixed model ID into (provider_id, model_name).

        Args:
            model_id: Model ID with prefix (e.g., "openrouter:openai/gpt-4o")

        Returns:
            Tuple of (provider_id, model_name)

        Raises:
            ValueError if model ID is invalid
        """
        if ":" not in model_id:
            # Default to openrouter if no prefix
            return "openrouter", model_id

        parts = model_id.split(":", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid model ID format: {model_id}")

        return parts[0], parts[1]

    async def query_model(
        self,
        model_id: str,
        messages: list[dict],
        temperature: Optional[float] = None,
        **kwargs,
    ):
        """
        Query a model by ID (auto-route to correct provider).

        Args:
            model_id: Model ID with provider prefix
            messages: List of message dicts
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            ModelResponse
        """
        provider_id, model_name = self.parse_model_id(model_id)
        provider = self.get_provider(provider_id)

        if not provider:
            raise ValueError(f"Provider not loaded: {provider_id}")

        return await provider.query(
            messages=messages, model=model_name, temperature=temperature, **kwargs
        )
