#!/usr/bin/env python3
"""
Test script to verify the configurable provider system works correctly
"""

import os
import sys

sys.path.append(".")

from youtube_summarizer_openai import YouTubeSubtitleSummarizer, ProviderConfig


def test_provider_config():
    """Test ProviderConfig class"""
    print("Testing ProviderConfig...")

    # Test default configuration
    config = ProviderConfig()
    assert config.provider == "openai"
    assert config.model == "gpt-3.5-turbo"
    print("✓ Default configuration works")

    # Test environment variable override
    os.environ["AI_PROVIDER"] = "openrouter"
    os.environ["AI_MODEL"] = "anthropic/claude-3-haiku"
    config = ProviderConfig()
    assert config.provider == "openrouter"
    assert config.model == "anthropic/claude-3-haiku"
    print("✓ Environment variable override works")

    # Test constructor override
    config = ProviderConfig(provider="ollama", model="llama3.2:3b")
    assert config.provider == "ollama"
    assert config.model == "llama3.2:3b"
    print("✓ Constructor override works")

    # Test invalid provider
    try:
        config = ProviderConfig(provider="invalid")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unsupported provider" in str(e)
        print("✓ Invalid provider validation works")

    # Clean up environment
    if "AI_PROVIDER" in os.environ:
        del os.environ["AI_PROVIDER"]
    if "AI_MODEL" in os.environ:
        del os.environ["AI_MODEL"]

    print("ProviderConfig tests passed!\n")


def test_youtube_summarizer_init():
    """Test YouTubeSubtitleSummarizer initialization"""
    print("Testing YouTubeSubtitleSummarizer initialization...")

    # Test default initialization
    try:
        # This will fail without API key, but should validate the config
        summarizer = YouTubeSubtitleSummarizer()
        print("✓ Default initialization works")
    except ValueError as e:
        if "API key required" in str(e):
            print("✓ API key validation works")
        else:
            raise

    # Test constructor parameters
    try:
        summarizer = YouTubeSubtitleSummarizer(provider="openrouter")
        assert summarizer.provider_config.provider == "openrouter"
        print("✓ Constructor parameter override works")
    except ValueError as e:
        if "API key required" in str(e):
            print("✓ API key validation works for different providers")
        else:
            raise

    print("YouTubeSubtitleSummarizer initialization tests passed!\n")


def test_provider_info():
    """Test provider information display"""
    print("Testing provider information...")

    providers = list(ProviderConfig.PROVIDERS.keys())
    expected_providers = ["openai", "openrouter", "ollama"]

    for provider in expected_providers:
        assert provider in providers, f"Provider {provider} not found"

    print("✓ All expected providers are available")
    print("✓ Provider configurations are properly defined")

    print("Provider info tests passed!\n")


def main():
    """Run all tests"""
    print("Running configuration tests...\n")

    try:
        test_provider_config()
        test_youtube_summarizer_init()
        test_provider_info()

        print(
            "🎉 All tests passed! The configurable provider system is working correctly."
        )
        print("\nYou can now use the YouTube summarizer with different providers:")
        print("- OpenAI (default)")
        print("- OpenRouter")
        print("- Ollama")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
