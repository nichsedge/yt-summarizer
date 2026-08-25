"""Tests for the CLI surface."""

from yt_summarizer.cli import list_providers


def test_list_providers_outputs_all(capsys):
    """--list-providers works without any API key configured."""
    list_providers()
    out = capsys.readouterr().out
    for provider in ("openai", "openrouter", "ollama"):
        assert provider in out
        assert "Default model" in out
