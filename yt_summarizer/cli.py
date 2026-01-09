"""
Command line interface for YouTube Summarizer.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from . import __version__
from .core import YouTubeSubtitleSummarizer, ProviderConfig
from .config import settings, Settings
from .exceptions import YouTubeSummarizerError


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def list_providers():
    """List available AI providers."""
    print("\nAvailable providers:")
    for provider in ProviderConfig().providers.keys():
        provider_settings = settings.get_provider_setting(provider)
        print(f"  - {provider}")
        print(f"    Default model: {provider_settings.default_model}")
        print(f"    API key env: {provider_settings.api_key_env}")
        if provider_settings.base_url:
            print(f"    Base URL: {provider_settings.base_url}")
        print()


def create_sample_config(config_path: Path):
    """Create a sample configuration file."""
    settings.to_file(config_path)
    print(f"Sample configuration created at: {config_path}")
    print("\nYou can now edit this file and use it with --config option.")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate summaries from YouTube video subtitles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://www.youtube.com/watch?v=VIDEO_ID
  %(prog)s --provider openai --model gpt-4 https://www.youtube.com/watch?v=VIDEO_ID
  %(prog)s --config config.json https://www.youtube.com/watch?v=VIDEO_ID
  %(prog)s --list-providers
  %(prog)s --create-config config.json
        """,
    )

    # Arguments
    parser.add_argument("url", nargs="?", help="YouTube video or playlist URL")

    # Options
    parser.add_argument(
        "--provider", "-p", help="AI provider (openai, openrouter, ollama)"
    )
    parser.add_argument("--model", "-m", help="Model name for the provider")
    parser.add_argument("--api-key", "-k", help="API key for authentication")
    parser.add_argument(
        "--config", "-c", type=Path, help="Path to configuration file (JSON format)"
    )
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="List available providers and exit",
    )
    parser.add_argument(
        "--create-config", type=Path, help="Create a sample configuration file and exit"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Handle special commands
    if args.list_providers:
        list_providers()
        return 0

    if args.create_config:
        create_sample_config(args.create_config)
        return 0

    # Load configuration if provided
    if args.config:
        global settings
        settings = Settings.from_file(args.config)

    # Validate arguments
    if not args.url:
        parser.error("YouTube URL is required")

    try:
        # Initialize summarizer
        summarizer = YouTubeSubtitleSummarizer(
            provider=args.provider, model=args.model, api_key=args.api_key
        )

        # Process URL
        if summarizer.is_playlist_url(args.url):
            outputs = summarizer.process_playlist(args.url)
            logging.info(f"🎉 Success! Generated {len(outputs)} files")
            for output in outputs:
                print(f"  - {output}")
        else:
            result_file = summarizer.process_video(args.url)
            logging.info(f"🎉 Success! Your summary is ready: {result_file}")

            # Optionally display preview
            if not args.verbose:
                print("\nPreview:")
                print("-" * 40)
                with open(result_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines[:20]:  # Show first 20 lines
                        print(line.rstrip())
                    if len(lines) > 20:
                        print(f"\n... ({len(lines) - 20} more lines)")
                    print("-" * 40)

        return 0

    except YouTubeSummarizerError as e:
        logging.error(f"Error: {str(e)}")
        return 1
    except KeyboardInterrupt:
        logging.info("Operation cancelled by user")
        return 1
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
