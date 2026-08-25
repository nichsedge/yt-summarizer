"""
Command line interface for YouTube Summarizer.
"""

import argparse
import logging
import sys
import traceback
from pathlib import Path

from . import __version__
from .config import settings
from .core import YouTubeSubtitleSummarizer
from .exceptions import YouTubeSummarizerError
from .utils import is_playlist_url


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def list_providers() -> None:
    """List available AI providers."""
    print("\nAvailable providers:")
    for provider in settings.providers.keys():
        provider_settings = settings.get_provider_setting(provider)
        print(f"  - {provider}")
        print(f"    Default model: {provider_settings.default_model}")
        print(f"    API key env: {provider_settings.api_key_env}")
        if provider_settings.base_url:
            print(f"    Base URL: {provider_settings.base_url}")
        print()


def create_sample_config(config_path: Path) -> None:
    """Create a sample configuration file."""
    settings.to_file(config_path)
    print(f"Sample configuration created at: {config_path}")
    print("\nYou can now edit this file and use it with --config option.")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
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

    parser.add_argument("url", nargs="?", help="YouTube video or playlist URL")
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
        "--force",
        "-f",
        action="store_true",
        help="Regenerate summaries even if the output file already exists",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def load_configuration(config_file: Path | None) -> int | None:
    """
    Apply --config or auto-detected ./config.json to global settings.

    Returns:
        Exit code on failure, None on success.
    """
    if not config_file:
        default_config = Path("config.json")
        if default_config.exists():
            config_file = default_config
            logging.info(f"Using configuration from {config_file}")

    if not config_file:
        return None

    try:
        settings.update_from_file(config_file)
    except Exception as e:
        logging.error(f"Failed to load configuration from {config_file}: {e}")
        return 1
    return None


def print_preview(result_file: str, max_lines: int = 20) -> None:
    """Print the first lines of a generated summary."""
    print("\nPreview:")
    print("-" * 40)
    with open(result_file, encoding="utf-8") as f:
        lines = f.readlines()
        for line in lines[:max_lines]:
            print(line.rstrip())
        if len(lines) > max_lines:
            print(f"\n... ({len(lines) - max_lines} more lines)")
        print("-" * 40)


def prompt_for_url(url: str | None) -> tuple[str | None, int]:
    """
    Resolve the URL argument or ask interactively.

    Returns:
        (url, exit_code): exactly one is meaningful; (None, 0) means a clean
        EOF abort, (None, nonzero) an error.
    """
    if url:
        return url, 0
    try:
        prompted = input("Enter YouTube URL: ").strip()
    except EOFError:
        print()
        return None, 0
    except KeyboardInterrupt:
        print()
        return None, 1
    if not prompted:
        logging.error("YouTube URL is required")
        return None, 1
    return prompted, 0


def run(args: argparse.Namespace) -> int:
    """Process the resolved URL with a configured summarizer."""
    url, code = prompt_for_url(args.url)
    if url is None:
        return code

    try:
        summarizer = YouTubeSubtitleSummarizer(
            provider=args.provider,
            model=args.model,
            api_key=args.api_key,
            force=args.force,
        )

        if is_playlist_url(url):
            outputs = summarizer.process_playlist(url)
            logging.info(f"Done! {len(outputs)} summaries generated.")
        else:
            result_file = summarizer.process_video(url)
            logging.info(f"Done! Summary saved to: {result_file}")
            if not args.verbose:
                print_preview(result_file)

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
            traceback.print_exc()
        return 1


def main() -> int:
    """Main CLI entry point."""
    args = build_parser().parse_args()
    setup_logging(args.verbose)

    if args.list_providers:
        list_providers()
        return 0

    if args.create_config:
        create_sample_config(args.create_config)
        return 0

    status = load_configuration(args.config)
    if status is not None:
        return status

    return run(args)


if __name__ == "__main__":
    sys.exit(main())
