"""
Provider configuration for AI providers.
"""

import os
from typing import Dict, Any, Optional
from openai import OpenAI

from ..config import settings
from ..exceptions import ConfigurationError, ProviderError


class ProviderConfig:
    """Configuration class for AI providers."""

    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        """
        Initialize provider configuration.

        Args:
            provider: AI provider (openai, openrouter, ollama)
            model: Model name for the provider
            api_key: API key for authentication

        Raises:
            ConfigurationError: If provider is unsupported or API key is missing
            ProviderError: If provider configuration is invalid
        """
        # Get provider from constructor or environment
        self.provider = provider or os.getenv("AI_PROVIDER") or settings.default_provider

        # Validate provider
        try:
            self.provider_settings = settings.get_provider_setting(self.provider)
        except ValueError as e:
            raise ConfigurationError(str(e))

        # Get model from constructor or environment or default
        self.model = model or os.getenv("AI_MODEL") or self.provider_settings.default_model

        # Get API key from constructor or environment
        self.api_key = api_key or os.getenv(self.provider_settings.api_key_env)

        if not self.api_key:
            raise ConfigurationError(
                f"API key required for {self.provider}. "
                f"Set {self.provider_settings.api_key_env} environment variable "
                f"or pass api_key parameter."
            )

        # Set base URL
        self.base_url = self.provider_settings.base_url

        # Set extra headers and body
        self.extra_headers = self.provider_settings.extra_headers.copy()
        self.extra_body = self.provider_settings.extra_body.copy()

    def create_client(self) -> OpenAI:
        """
        Create and return an OpenAI client configured for this provider.

        Returns:
            Configured OpenAI client

        Raises:
            ProviderError: If client creation fails
        """
        try:
            client_kwargs = {"api_key": self.api_key}

            if self.base_url:
                client_kwargs["base_url"] = self.base_url

            return OpenAI(**client_kwargs)
        except Exception as e:
            raise ProviderError(f"Failed to create client for {self.provider}: {str(e)}")

    def get_request_kwargs(self) -> Dict[str, Any]:
        """Get additional kwargs for API requests."""
        kwargs = {}

        if self.extra_headers:
            kwargs["extra_headers"] = self.extra_headers

        if self.extra_body:
            kwargs["extra_body"] = self.extra_body

        return kwargs

    def __repr__(self) -> str:
        return f"ProviderConfig(provider={self.provider}, model={self.model})"