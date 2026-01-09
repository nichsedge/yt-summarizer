#!/usr/bin/env python3
"""
Migration script to help users transition from v0.1 to v0.2.

This script:
1. Creates a sample config file based on your current environment setup
2. Shows how to use the new CLI instead of the interactive interface
"""

import os
import json
from pathlib import Path


def create_config_from_env():
    """Create a config file based on current environment variables."""
    config = {
        "default_provider": os.getenv("AI_PROVIDER", "openrouter"),
        "providers": {
            "openai": {
                "default_model": "gpt-3.5-turbo",
                "api_key_env": "OPENAI_API_KEY",
            },
            "openrouter": {
                "default_model": "openai/gpt-oss-20b:free",
                "base_url": "https://openrouter.ai/api/v1",
                "api_key_env": "OPENROUTER_API_KEY",
                "extra_headers": {
                    "HTTP-Referer": "https://nichsedge.github.io/digital-garden",
                    "X-Title": "Youtube Summarizer",
                },
            },
            "ollama": {
                "default_model": "llama3.2:3b",
                "base_url": "http://localhost:11434/v1",
                "api_key_env": "OLLAMA_API_KEY",
            },
        },
        "processing": {
            "max_tokens_per_chunk": 3000,
            "language_priority": ["en"],
            "prefer_manual_transcripts": True,
        },
        "output": {
            "output_dir": "./output",
            "create_dir_if_missing": True,
            "date_format": "%Y-%m-%d %H:%M:%S",
        },
        "system_prompt": """You are an expert at creating educational summaries. Your task is to:

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

Focus on clarity, accuracy, and educational value.""",
        "user_prompt_template": """Please summarize the following text from a YouTube video transcript (Part {chunk_number} of {total_chunks}):

{text}

Create a well-structured summary optimized for learning, using bullet points and proper markdown formatting.""",
    }

    # Customize AI model if set in environment
    if os.getenv("AI_MODEL"):
        config["providers"][config["default_provider"]]["default_model"] = os.getenv(
            "AI_MODEL"
        )

    return config


def main():
    print("YouTube Summarizer Migration to v0.2")
    print("=" * 50)

    print("\n1. Creating configuration file...")
    config = create_config_from_env()

    config_path = Path("yt-summarizer-config.json")
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"✓ Configuration file created: {config_path}")

    print("\n2. What's new in v0.2:")
    print("   - Modular package structure")
    print("   - Clean CLI interface with argparse")
    print("   - Configuration file support")
    print("   - Comprehensive error handling")
    print("   - Unit tests included")
    print("   - Better documentation")

    print("\n3. New usage examples:")
    print("   # Using the config file")
    print(
        f"   yt-summarizer --config {config_path} https://www.youtube.com/watch?v=VIDEO_ID"
    )
    print("")
    print("   # Using environment variables (same as before)")
    print("   yt-summarizer https://www.youtube.com/watch?v=VIDEO_ID")
    print("")
    print("   # Specifying provider and model")
    print(
        "   yt-summarizer --provider openai --model gpt-4 https://www.youtube.com/watch?v=VIDEO_ID"
    )
    print("")
    print("   # List available providers")
    print("   yt-summarizer --list-providers")

    print("\n4. Python API usage:")
    print("   # Old way (still works but deprecated)")
    print("   python youtube_summarizer_openai.py")
    print("")
    print("   # New way (recommended)")
    print("   from yt_summarizer import YouTubeSubtitleSummarizer")
    print("   summarizer = YouTubeSubtitleSummarizer()")
    print("   summarizer.process_video('https://www.youtube.com/watch?v=VIDEO_ID')")

    print("\n5. Installation:")
    print("   # To install with CLI support (using uv):")
    print("   uv sync")
    print("")
    print("   # Install development dependencies:")
    print("   uv sync --dev")
    print("")
    print("   # Run with uv without activating:")
    print("   uv run yt-summarizer https://www.youtube.com/watch?v=VIDEO_ID")

    print("\n✓ Migration complete! You can now start using the new features.")
    print(f"\nYour configuration file '{config_path}' is ready to use.")


if __name__ == "__main__":
    main()
