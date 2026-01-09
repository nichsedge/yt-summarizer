"""Test configuration management."""

import json
import tempfile
from pathlib import Path

import pytest
from yt_summarizer.config import Settings, ProviderSettings, ProcessingSettings, OutputSettings


class TestProviderSettings:
    """Test provider settings."""

    def test_provider_settings_creation(self):
        """Test creating provider settings."""
        settings = ProviderSettings(
            default_model="gpt-4",
            base_url="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY"
        )

        assert settings.default_model == "gpt-4"
        assert settings.base_url == "https://api.openai.com/v1"
        assert settings.api_key_env == "OPENAI_API_KEY"
        assert settings.extra_headers == {}
        assert settings.extra_body == {}


class TestSettings:
    """Test main settings class."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()

        assert settings.default_provider == "openrouter"
        assert isinstance(settings.providers, dict)
        assert "openai" in settings.providers
        assert "openrouter" in settings.providers
        assert "ollama" in settings.providers
        assert isinstance(settings.processing, ProcessingSettings)
        assert isinstance(settings.output, OutputSettings)
        assert settings.processing.max_tokens_per_chunk == 3000
        assert settings.output.output_dir == "./output"

    def test_get_provider_setting(self):
        """Test getting provider settings."""
        settings = Settings()

        openai_settings = settings.get_provider_setting("openai")
        assert isinstance(openai_settings, ProviderSettings)
        assert openai_settings.default_model == "gpt-3.5-turbo"

        with pytest.raises(ValueError):
            settings.get_provider_setting("nonexistent")

    def test_save_and_load(self):
        """Test saving and loading settings."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = Path(f.name)

        try:
            # Create custom settings
            original_settings = Settings()
            original_settings.default_provider = "openai"
            original_settings.processing.max_tokens_per_chunk = 4000
            original_settings.output.output_dir = "./custom_output"

            # Save to file
            original_settings.to_file(config_path)

            # Load from file
            loaded_settings = Settings.from_file(config_path)

            # Verify values
            assert loaded_settings.default_provider == "openai"
            assert loaded_settings.processing.max_tokens_per_chunk == 4000
            assert loaded_settings.output.output_dir == "./custom_output"
            assert loaded_settings.providers["openai"].default_model == "gpt-3.5-turbo"

        finally:
            # Clean up
            if config_path.exists():
                config_path.unlink()

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file returns defaults."""
        nonexistent_path = Path("/tmp/nonexistent_config.json")
        settings = Settings.from_file(nonexistent_path)

        # Should return default settings
        assert settings.default_provider == "openrouter"
        assert settings.processing.max_tokens_per_chunk == 3000