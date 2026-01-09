# YouTube Summarizer

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Generate AI-powered summaries from YouTube video subtitles using multiple AI providers.

## Features

- 📺 Extract subtitles from YouTube videos (manual or auto-generated)
- 🤝 Support for multiple AI providers (OpenAI, OpenRouter, Ollama)
- 📝 Generate well-structured, educational summaries in markdown
- 📚 Process entire playlists
- ⚙️ Configurable via environment variables or config files
- 🖥️ Clean CLI interface
- 🧪 Modular, testable codebase

## Installation

### Prerequisites

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) - the modern Python package installer.

### From Source

```bash
git clone https://github.com/yourusername/yt-summarizer.git
cd yt-summarizer
uv sync
```

### Using uv

```bash
uv add yt-summarizer
```

## Quick Start

### 1. Set up API Keys

Set environment variables for your preferred AI provider:

```bash
# For OpenAI
export OPENAI_API_KEY="your-openai-api-key"

# For OpenRouter
export OPENROUTER_API_KEY="your-openrouter-api-key"

# For Ollama (local)
export OLLAMA_API_KEY="your-ollama-api-key"
```

### 2. Run the Summarizer

```bash
# Activate the virtual environment (if installed from source)
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Summarize a single video
yt-summarizer https://www.youtube.com/watch?v=VIDEO_ID

# Use a specific provider
yt-summarizer --provider openai --model gpt-4 https://www.youtube.com/watch?v=VIDEO_ID

# Summarize a playlist
yt-summarizer https://www.youtube.com/playlist?list=PLAYLIST_ID

# Use verbose logging
yt-summarizer --verbose https://www.youtube.com/watch?v=VIDEO_ID

# Or run directly with uv (no activation needed)
uv run yt-summarizer https://www.youtube.com/watch?v=VIDEO_ID
```

## Configuration

### Environment Variables

- `AI_PROVIDER`: Default AI provider (openai, openrouter, ollama)
- `AI_MODEL`: Default model for the provider
- `OPENAI_API_KEY`: OpenAI API key
- `OPENROUTER_API_KEY`: OpenRouter API key
- `OLLAMA_API_KEY`: Ollama API key

### Configuration File

Create a JSON configuration file:

```bash
yt-summarizer --create-config config.json
```

Then use it:

```bash
yt-summarizer --config config.json https://www.youtube.com/watch?v=VIDEO_ID
```

Example configuration:

```json
{
  "default_provider": "openrouter",
  "providers": {
    "openrouter": {
      "default_model": "anthropic/claude-3.5-sonnet",
      "base_url": "https://openrouter.ai/api/v1",
      "api_key_env": "OPENROUTER_API_KEY",
      "extra_headers": {
        "HTTP-Referer": "https://your-site.com",
        "X-Title": "YouTube Summarizer"
      }
    }
  },
  "processing": {
    "max_tokens_per_chunk": 3000,
    "language_priority": ["en"],
    "prefer_manual_transcripts": true
  },
  "output": {
    "output_dir": "./summaries",
    "create_dir_if_missing": true
  }
}
```

## CLI Options

```
usage: yt-summarizer [-h] [--provider PROVIDER] [--model MODEL] [--api-key API_KEY]
                     [--config CONFIG] [--list-providers] [--create-config CREATE_CONFIG]
                     [--verbose] [--version] [url]

Generate summaries from YouTube video subtitles

positional arguments:
  url                   YouTube video or playlist URL

options:
  -h, --help            show this help message and exit
  --provider, -p        AI provider (openai, openrouter, ollama)
  --model, -m           Model name for the provider
  --api-key, -k         API key for authentication
  --config, -c          Path to configuration file (JSON format)
  --list-providers      List available providers and exit
  --create-config       Create a sample configuration file and exit
  --verbose, -v         Enable verbose logging
  --version             show program's version number and exit
```

## Python API

You can also use the YouTube Summarizer in your Python code:

```python
from yt_summarizer import YouTubeSubtitleSummarizer

# Initialize with default settings
summarizer = YouTubeSubtitleSummarizer()

# Process a single video
output_file = summarizer.process_video("https://www.youtube.com/watch?v=VIDEO_ID")
print(f"Summary saved to: {output_file}")

# Process a playlist
output_files = summarizer.process_playlist("https://www.youtube.com/playlist?list=PLAYLIST_ID")
print(f"Generated {len(output_files)} summaries")
```

### Custom Configuration

```python
from yt_summarizer import YouTubeSubtitleSummarizer

# Initialize with specific provider and model
summarizer = YouTubeSubtitleSummarizer(
    provider="openai",
    model="gpt-4",
    api_key="your-api-key"
)

# Process video
summary_file = summarizer.process_video("https://www.youtube.com/watch?v=VIDEO_ID")
```

## Supported AI Providers

### OpenAI
- Models: GPT-3.5 Turbo, GPT-4, GPT-4 Turbo
- Requires: `OPENAI_API_KEY`
- Default: `gpt-3.5-turbo`

### OpenRouter
- Models: Multiple provider options
- Requires: `OPENROUTER_API_KEY`
- Default: `openai/gpt-oss-20b:free`

### Ollama
- Models: Local models (e.g., llama3.2:3b)
- Requires: `OLLAMA_API_KEY` (optional)
- Base URL: `http://localhost:11434/v1`
- Default: `llama3.2:3b`

## Output Format

Summaries are generated as structured Markdown documents with:

- Main title from video
- Generation metadata
- Table of contents (for multi-section summaries)
- Well-formatted bullet points
- Headers and sub-points
- Bold emphasis for key terms

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### Development Setup

```bash
git clone https://github.com/yourusername/yt-summarizer.git
cd yt-summarizer

# Install with dev dependencies
uv sync --dev

# Or install manually
uv add --dev pytest pytest-cov pytest-mock black ruff mypy
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=yt_summarizer --cov-report=html

# Or use the Makefile
make test
```

### Code Style

This project uses:
- Black for code formatting
- Ruff for linting
- mypy for type checking

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### v0.2.0
- Refactored into modular package structure
- Added comprehensive error handling
- Added configuration file support
- Added CLI interface with argparse
- Added unit tests
- Improved documentation

### v0.1.0
- Initial release
- Basic YouTube subtitle extraction
- OpenAI, OpenRouter, and Ollama support
- Playlist processing

## uv Commands

Here are some useful `uv` commands for this project:

```bash
# Install dependencies
uv sync

# Install with development dependencies
uv sync --dev

# Run the CLI without activating virtual environment
uv run yt-summarizer --provider openai https://www.youtube.com/watch?v=VIDEO_ID

# Run tests
uv run pytest

# Update dependencies
uv sync --upgrade

# Build package
uv build

# Clean caches
uv cache clean
```

## Troubleshooting

### "No suitable subtitles found"
- Ensure the video has subtitles available
- Try different language codes in configuration
- Some videos may not have accessible subtitles

### "API key required"
- Check that the correct environment variable is set
- Verify the API key is valid and active
- Consider using a configuration file instead

### Large video processing fails
- Videos with very long content may hit API limits
- The tool automatically chunks large transcripts
- Consider using a model with higher token limits

## Support

If you encounter issues or have questions:

1. Check the [Issues](https://github.com/yourusername/yt-summarizer/issues) page
2. Create a new issue with details about your problem
3. Include verbose logs (`--verbose`) when reporting issues