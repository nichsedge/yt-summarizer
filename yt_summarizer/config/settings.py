"""
Configuration settings and management for YouTube Summarizer.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class ProviderSettings:
    """Settings for an AI provider."""

    default_model: str
    base_url: Optional[str] = None
    api_key_env: str = ""
    extra_headers: Dict[str, str] = field(default_factory=dict)
    extra_body: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingSettings:
    """Settings for transcript processing."""

    max_tokens_per_chunk: int = 3000
    language_priority: list = field(default_factory=lambda: ["en"])
    prefer_manual_transcripts: bool = True


@dataclass
class OutputSettings:
    """Settings for output generation."""

    output_dir: str = "./output"
    create_dir_if_missing: bool = True
    date_format: str = "%Y-%m-%d %H:%M:%S"


@dataclass
class Settings:
    """Main configuration settings."""

    # Provider configurations
    providers: Dict[str, ProviderSettings] = field(
        default_factory=lambda: {
            "openai": ProviderSettings(
                default_model="gpt-3.5-turbo", api_key_env="OPENAI_API_KEY"
            ),
            "openrouter": ProviderSettings(
                default_model="openai/gpt-oss-20b:free",
                base_url="https://openrouter.ai/api/v1",
                api_key_env="OPENROUTER_API_KEY",
                extra_headers={
                    "HTTP-Referer": "https://nichsedge.github.io/digital-garden",
                    "X-Title": "Youtube Summarizer",
                },
            ),
            "ollama": ProviderSettings(
                default_model="llama3.2:3b",
                base_url="http://localhost:11434/v1",
                api_key_env="OLLAMA_API_KEY",
            ),
        }
    )

    # Processing settings
    processing: ProcessingSettings = field(default_factory=ProcessingSettings)

    # Output settings
    output: OutputSettings = field(default_factory=OutputSettings)

    # Default provider to use
    default_provider: str = "openrouter"

    # System prompt template
    system_prompt: str = """You are an expert at creating educational summaries. Your task is to:

1. Extract the most important concepts, ideas, and information from the provided text
2. Format the summary as clear, well-structured bullet points
3. Optimize for learning and retention
4. Use proper markdown formatting
5. Group related concepts together
6. Include specific details, examples, and key insights
7. Make it suitable for students and learners

Format your response with:
- Main topic headers using ##
- Key points as bullet points with -
- Sub-points indented with proper spacing
- Important terms or concepts in **bold**
- Examples or specific details in clear, concise language

Focus on clarity, accuracy, and educational value."""

    # User prompt template
    user_prompt_template: str = """Please summarize the following text from a YouTube video transcript (Part {chunk_number} of {total_chunks}):

{text}

Create a well-structured summary optimized for learning, using bullet points and proper markdown formatting."""

    @classmethod
    def from_file(cls, config_path: Path) -> "Settings":
        """Load settings from a JSON configuration file."""
        if not config_path.exists():
            return cls()

        with open(config_path, "r") as f:
            data = json.load(f)

        # Convert dictionaries to appropriate dataclass instances
        providers = {}
        for name, provider_data in data.get("providers", {}).items():
            providers[name] = ProviderSettings(**provider_data)
        data["providers"] = providers

        if "processing" in data:
            data["processing"] = ProcessingSettings(**data["processing"])

        if "output" in data:
            data["output"] = OutputSettings(**data["output"])

        return cls(**data)

    def to_file(self, config_path: Path):
        """Save settings to a JSON configuration file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert dataclasses to dictionaries for JSON serialization
        data = {
            "providers": {
                name: {
                    "default_model": p.default_model,
                    "base_url": p.base_url,
                    "api_key_env": p.api_key_env,
                    "extra_headers": p.extra_headers,
                    "extra_body": p.extra_body,
                }
                for name, p in self.providers.items()
            },
            "processing": {
                "max_tokens_per_chunk": self.processing.max_tokens_per_chunk,
                "language_priority": self.processing.language_priority,
                "prefer_manual_transcripts": self.processing.prefer_manual_transcripts,
            },
            "output": {
                "output_dir": self.output.output_dir,
                "create_dir_if_missing": self.output.create_dir_if_missing,
                "date_format": self.output.date_format,
            },
            "default_provider": self.default_provider,
            "system_prompt": self.system_prompt,
            "user_prompt_template": self.user_prompt_template,
        }

        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_provider_setting(self, provider: str) -> ProviderSettings:
        """Get settings for a specific provider."""
        if provider not in self.providers:
            raise ValueError(f"Provider {provider} not configured")
        return self.providers[provider]


# Global settings instance
settings = Settings()
