import os
import re
import logging
from typing import List, Dict, Optional, Tuple, Set, Any
from urllib.parse import urlparse, parse_qs
import requests
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import tiktoken

# Configure basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class ProviderConfig:
    """Configuration class for AI providers"""

    # Provider configurations
    PROVIDERS = {
        "openai": {
            "default_model": "gpt-3.5-turbo",
            "base_url": None,  # Use OpenAI default
            "api_key_env": "OPENAI_API_KEY",
            "extra_headers": {},
            "extra_body": {},
        },
        "openrouter": {
            "default_model": "openai/gpt-oss-20b:free",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key_env": "OPENROUTER_API_KEY",
            "extra_headers": {
                "HTTP-Referer": "https://nichsedge.github.io/digital-garden",
                "X-Title": "Youtube Summarizer",
            },
            "extra_body": {},
        },
        "ollama": {
            "default_model": "llama3.2:3b",
            "base_url": "http://localhost:11434/v1",
            "api_key_env": "OLLAMA_API_KEY",
            "extra_headers": {},
            "extra_body": {},
        },
    }

    def __init__(self, provider: str = None, model: str = None, api_key: str = None):
        """
        Initialize provider configuration

        Args:
            provider: AI provider (openai, openrouter, ollama)
            model: Model name for the provider
            api_key: API key for authentication
        """
        # Get provider from constructor or environment
        self.provider = provider or os.getenv("AI_PROVIDER", "openrouter")

        # Validate provider
        if self.provider not in self.PROVIDERS:
            raise ValueError(
                f"Unsupported provider: {self.provider}. Supported: {list(self.PROVIDERS.keys())}"
            )

        # Get provider config
        self.provider_config = self.PROVIDERS[self.provider]

        # Get model from constructor or environment or default
        self.model = (
            model or os.getenv("AI_MODEL") or self.provider_config["default_model"]
        )

        # Get API key from constructor or environment
        self.api_key = api_key or os.getenv(self.provider_config["api_key_env"])

        if not self.api_key:
            raise ValueError(
                f"API key required for {self.provider}. Set {self.provider_config['api_key_env']} environment variable or pass api_key parameter."
            )

        # Set base URL
        self.base_url = self.provider_config["base_url"]

        # Set extra headers and body
        self.extra_headers = self.provider_config["extra_headers"].copy()
        self.extra_body = self.provider_config["extra_body"].copy()

    def create_client(self) -> OpenAI:
        """Create and return an OpenAI client configured for this provider"""
        client_kwargs = {"api_key": self.api_key}

        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        return OpenAI(**client_kwargs)

    def get_request_kwargs(self) -> Dict[str, Any]:
        """Get additional kwargs for API requests"""
        kwargs = {}

        if self.extra_headers:
            kwargs["extra_headers"] = self.extra_headers

        if self.extra_body:
            kwargs["extra_body"] = self.extra_body

        return kwargs


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to remove invalid characters

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove invalid characters and replace spaces with underscores
    return re.sub(r'[<>:"/\\|?*]', "", filename).replace(" ", "_")


class YouTubeSubtitleSummarizer:
    def __init__(
        self,
        openai_api_key: str = None,
        provider: str = None,
        model: str = None,
        api_key: str = None,
    ):
        """
        Initialize the YouTube Subtitle Summarizer

        Args:
            openai_api_key: Deprecated: Use api_key parameter instead. OpenAI API key for GPT access
            provider: AI provider (openai, openrouter, ollama)
            model: Model name for the provider
            api_key: API key for authentication
        """
        # Handle deprecated openai_api_key parameter
        if openai_api_key and not api_key:
            api_key = openai_api_key
            logging.warning(
                "openai_api_key parameter is deprecated. Use api_key instead."
            )

        # Initialize provider configuration
        self.provider_config = ProviderConfig(
            provider=provider, model=model, api_key=api_key
        )
        self.client = self.provider_config.create_client()

        # Set encoding based on model
        self.encoding = tiktoken.encoding_for_model(self._get_model_for_encoding())
        self.max_tokens_per_chunk = 3000  # Leave room for system prompt and response

    def _get_model_for_encoding(self) -> str:
        """Get appropriate model name for tiktoken encoding"""
        # Use a simple model name for tiktoken encoding
        if self.provider_config.provider == "openrouter":
            # For OpenRouter models, use a compatible model name for encoding
            return "gpt-3.5-turbo"
        elif self.provider_config.provider == "ollama":
            # For Ollama, use a compatible model name
            return "gpt-3.5-turbo"
        else:
            # Default to OpenAI
            return self.provider_config.model

    def is_playlist_url(self, url: str) -> bool:
        """
        Detect if the provided URL is a YouTube playlist URL.
        """
        parsed = urlparse(url)
        if parsed.hostname not in ("www.youtube.com", "youtube.com"):
            return False
        if parsed.path == "/playlist":
            return True
        # watch URL can embed playlist via list= param
        if parsed.path == "/watch":
            qs = parse_qs(parsed.query)
            return "list" in qs
        return False

    def extract_video_id(self, url: str) -> str:
        """
        Extract YouTube video ID from URL

        Args:
            url: YouTube video URL

        Returns:
            Video ID string
        """
        parsed_url = urlparse(url)

        # Guard: don't allow playlist URL here
        if self.is_playlist_url(url):
            raise ValueError(
                "Provided URL is a playlist. Use process_playlist() for playlists."
            )

        if parsed_url.hostname == "youtu.be":
            return parsed_url.path[1:]
        elif parsed_url.hostname in ("www.youtube.com", "youtube.com"):
            if parsed_url.path == "/watch":
                return parse_qs(parsed_url.query)["v"][0]
            elif parsed_url.path[:7] == "/embed/":
                return parsed_url.path.split("/")[2]
            elif parsed_url.path[:3] == "/v/":
                return parsed_url.path.split("/")[2]

        raise ValueError(f"Invalid YouTube URL: {url}")

    def get_subtitles(self, video_id: str) -> str:
        """
        Get English subtitles with priority order

        Args:
            video_id: YouTube video ID

        Returns:
            Subtitle text as string
        """
        try:
            # Instantiate API per latest docs and list available transcripts
            ytt_api = YouTubeTranscriptApi()
            transcript_list = ytt_api.list(video_id)

            # Priority 1: Official English subtitles (manually created if available)
            try:
                transcript = transcript_list.find_transcript(["en"])
                if not transcript.is_generated:
                    logging.info("Found official English subtitles")
                    fetched = transcript.fetch()
                    # Ensure formatter receives a list of dicts
                    fetched_list = (
                        list(fetched) if not isinstance(fetched, list) else fetched
                    )
                    return self._format_transcript(fetched_list)
            except Exception:
                logging.debug("Official English subtitles not found or error occurred.")

            # Priority 2: Auto-generated English
            try:
                transcript = transcript_list.find_generated_transcript(["en"])
                logging.info("Found auto-generated English subtitles")
                fetched = transcript.fetch()
                fetched_list = (
                    list(fetched) if not isinstance(fetched, list) else fetched
                )
                return self._format_transcript(fetched_list)
            except Exception:
                logging.debug(
                    "Auto-generated English subtitles not found or error occurred."
                )

            # Priority 3: First available auto-generated subtitle
            try:
                for transcript in transcript_list:
                    if transcript.is_generated:
                        logging.info(
                            f"Found auto-generated subtitles in {transcript.language_code}"
                        )
                        fetched = transcript.fetch()
                        fetched_list = (
                            list(fetched) if not isinstance(fetched, list) else fetched
                        )
                        return self._format_transcript(fetched_list)
                logging.debug("No auto-generated subtitles found.")
            except Exception:
                logging.debug("Error accessing auto-generated subtitles.")

            raise Exception("No suitable English subtitles found")

        except Exception as e:
            logging.error(f"Error getting subtitles: {str(e)}")
            raise Exception(f"Error getting subtitles: {str(e)}")

    def extract_playlist_video_ids(self, playlist_url: str) -> List[str]:
        """
        Extract unique video IDs from a YouTube playlist HTML without API keys.

        Strategy:
        - Download playlist page HTML.
        - Regex-scan for watch?v=VIDEO_ID (11-char ID).
        - Deduplicate while preserving order.
        """
        if not self.is_playlist_url(playlist_url):
            raise ValueError("URL is not a playlist URL")

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        resp = requests.get(playlist_url, headers=headers, timeout=30)
        resp.raise_for_status()
        html = resp.text

        pattern = re.compile(r"watch\?v=([A-Za-z0-9_-]{11})")
        seen: Set[str] = set()
        ordered: List[str] = []
        for m in pattern.finditer(html):
            vid = m.group(1)
            if vid not in seen:
                seen.add(vid)
                ordered.append(vid)

        if not ordered:
            logging.warning(
                "No video IDs found in playlist HTML. The page might require JS to render items."
            )
        return ordered

    def process_playlist(self, playlist_url: str) -> List[str]:
        """
        Process a playlist URL by extracting each video's subtitles, summarizing,
        and saving individual markdown files per video.

        Returns a list of paths to generated files.
        """
        logging.info("Detected playlist URL. Extracting video IDs...")
        video_ids = self.extract_playlist_video_ids(playlist_url)
        logging.info(f"Found {len(video_ids)} video IDs in playlist")

        output_files: List[str] = []
        for idx, vid in enumerate(video_ids, 1):
            try:
                logging.info(f"Processing video {idx}/{len(video_ids)}: {vid}")
                video_url = f"https://www.youtube.com/watch?v={vid}"
                out_path = self.process_video(video_url)
                output_files.append(out_path)
            except Exception as e:
                logging.error(f"Failed to process video {vid}: {e}")
                continue

        return output_files

    def _format_transcript(self, transcript_data: List[Dict]) -> str:
        """
        Format transcript data into clean text

        Args:
            transcript_data: Raw transcript data from YouTube API

        Returns:
            Formatted transcript text
        """
        formatter = TextFormatter()
        formatted_text = formatter.format_transcript(transcript_data)

        # Clean up the text
        formatted_text = re.sub(r"\n+", " ", formatted_text)
        formatted_text = re.sub(r"\s+", " ", formatted_text)
        formatted_text = formatted_text.strip()

        return formatted_text

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))

    def split_text_into_chunks(self, text: str) -> List[str]:
        """
        Split text into chunks suitable for GPT processing

        Args:
            text: Full subtitle text

        Returns:
            List of text chunks
        """
        # Split by sentences first
        sentences = re.split(r"(?<=[.!?])\s+", text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            # Check if adding this sentence would exceed token limit
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence

            if self.count_tokens(test_chunk) > self.max_tokens_per_chunk:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # Single sentence is too long, split it further
                    words = sentence.split()
                    temp_chunk = ""
                    for word in words:
                        test_word_chunk = (
                            temp_chunk + " " + word if temp_chunk else word
                        )
                        if (
                            self.count_tokens(test_word_chunk)
                            > self.max_tokens_per_chunk
                        ):
                            if temp_chunk:
                                chunks.append(temp_chunk.strip())
                                temp_chunk = word
                            else:
                                chunks.append(word)
                        else:
                            temp_chunk = test_word_chunk
                    if temp_chunk:
                        current_chunk = temp_chunk
            else:
                current_chunk = test_chunk

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def summarize_chunk(self, chunk: str, chunk_number: int, total_chunks: int) -> str:
        """
        Summarize a text chunk using configured AI provider

        Args:
            chunk: Text chunk to summarize
            chunk_number: Current chunk number
            total_chunks: Total number of chunks

        Returns:
            Summarized text in bullet points
        """
        system_prompt = """You are an expert at creating educational summaries. Your task is to:

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

        user_prompt = f"""Please summarize the following text from a YouTube video transcript (Part {chunk_number} of {total_chunks}):

{chunk}

Create a well-structured summary optimized for learning, using bullet points and proper markdown formatting."""

        try:
            # Get provider-specific request kwargs
            request_kwargs = self.provider_config.get_request_kwargs()

            # Create the API request
            response = self.client.chat.completions.create(
                model=self.provider_config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                **request_kwargs,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"Error summarizing chunk {chunk_number} with {self.provider_config.provider}: {str(e)}"

    def merge_summaries(self, summaries: List[str], video_title: str = "") -> str:
        """
        Merge all summaries into a single Markdown document

        Args:
            summaries: List of summary strings
            video_title: Optional video title for the document

        Returns:
            Complete Markdown document
        """
        # Create header
        title = video_title if video_title else "YouTube Video Summary"
        markdown_doc = f"# {title}\n\n"

        # Add metadata
        markdown_doc += f"*Generated on: {self._get_current_date()}*\n"
        markdown_doc += f"*Total sections: {len(summaries)}*\n\n"

        # Add table of contents if multiple sections
        if len(summaries) > 1:
            markdown_doc += "## Table of Contents\n\n"
            for i in range(len(summaries)):
                markdown_doc += f"- [Part {i + 1}](#part-{i + 1})\n"
            markdown_doc += "\n---\n\n"

        # Add each summary
        for i, summary in enumerate(summaries, 1):
            if len(summaries) > 1:
                markdown_doc += f"## Part {i}\n\n"
            markdown_doc += summary + "\n\n"

            if i < len(summaries):
                markdown_doc += "---\n\n"

        return markdown_doc

    def _get_current_date(self) -> str:
        """Get current date as string"""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_video_title(self, video_id: str) -> str:
        """
        Get video title from YouTube (simple method)

        Args:
            video_id: YouTube video ID

        Returns:
            Video title or default string
        """
        try:
            # This is a simple method - for production, consider using YouTube Data API
            url = f"https://www.youtube.com/watch?v={video_id}"
            response = requests.get(url, timeout=20)

            # Extract title from HTML (basic regex)
            title_match = re.search(r"<title>([^<]+)</title>", response.text)
            if title_match:
                title = title_match.group(1)
                # Remove " - YouTube" suffix
                title = re.sub(r" - YouTube$", "", title)
                return title
        except Exception:
            pass

        return "YouTube Video Summary"

    def process_video(self, video_url: str) -> str:
        """
        Complete process: extract subtitles, split, summarize, and merge

        Args:
            video_url: YouTube video URL

        Returns:
            Path to generated markdown file
        """
        try:
            # Extract video ID
            logging.info(f"Extracting video ID from URL...")
            video_id = self.extract_video_id(video_url)
            logging.info(f"Video ID: {video_id}")

            # Get video title
            logging.info(f"Getting video title...")
            video_title = self.get_video_title(video_id)
            logging.info(f"✓ Title: {video_title}")

            # Get subtitles
            logging.info(f"Extracting subtitles...")
            subtitles = self.get_subtitles(video_id)
            logging.info(f"Subtitles extracted: {len(subtitles)} characters")

            # Split into chunks
            logging.info(f"Splitting into chunks...")
            chunks = self.split_text_into_chunks(subtitles)
            logging.info(f"Split into {len(chunks)} chunks")

            # Summarize each chunk
            logging.info(f"Generating summaries...")
            summaries = []
            for i, chunk in enumerate(chunks, 1):
                logging.info(f"  Processing chunk {i}/{len(chunks)}...")
                summary = self.summarize_chunk(chunk, i, len(chunks))
                summaries.append(summary)

            # Merge summaries
            logging.info(f"Merging summaries...")
            final_document = self.merge_summaries(summaries, video_title)

            # Save to file
            output_file = "./output/" + sanitize_filename(video_title) + ".md"
            logging.info(f"Saving to file...")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(final_document)

            logging.info(f"Complete! Summary saved to: {output_file}")
            return output_file

        except Exception as e:
            logging.error(f"Error: {str(e)}")
            raise


def main():
    """
    Example usage of the YouTube Subtitle Summarizer with configurable providers
    """
    print("YouTube Subtitle Summarizer - Configurable AI Providers")
    print("=" * 60)

    # Show available providers
    print("\nAvailable providers:")
    for provider in ProviderConfig.PROVIDERS.keys():
        print(f"  - {provider}")

    print("\nConfiguration options:")
    print("1. Use environment variables (AI_PROVIDER, AI_MODEL, API_KEY)")
    print("2. Use constructor parameters")
    print("3. Use default settings (OpenAI)")

    # Get user preference
    config_method = input("\nChoose configuration method (1/2/3) [1]: ").strip() or "1"

    summarizer = None

    if config_method == "1":
        # Environment variables method
        print("\nUsing environment variables...")
        provider = os.getenv("AI_PROVIDER")
        model = os.getenv("AI_MODEL")

        if provider:
            print(f"Provider: {provider}")
        if model:
            print(f"Model: {model}")

        summarizer = YouTubeSubtitleSummarizer()

    elif config_method == "2":
        # Constructor parameters method
        print("\nUsing constructor parameters...")
        provider = (
            input("Enter provider (openai/openrouter/ollama) [openai]: ").strip()
            or "openai"
        )
        model = input(f"Enter model for {provider} (leave empty for default): ").strip()

        # For demo purposes, we'll use a placeholder API key
        # In real usage, you'd set this via environment variable or pass it directly
        api_key = os.getenv(f"{provider.upper()}_API_KEY")

        if not api_key:
            print(
                f"\nWarning: {provider.upper()}_API_KEY not found in environment variables"
            )
            print("Please set the appropriate API key environment variable:")
            if provider == "openai":
                print("  export OPENAI_API_KEY=your-key")
            elif provider == "openrouter":
                print("  export OPENROUTER_API_KEY=your-key")
            elif provider == "ollama":
                print("  export OLLAMA_API_KEY=your-key")

            # Continue with demo but warn about potential failure
            print("\nContinuing with demo (may fail without proper API key)...")

        summarizer = YouTubeSubtitleSummarizer(
            provider=provider, model=model, api_key=api_key
        )

    else:
        # Default method
        print("\nUsing default settings (OpenAI)...")
        summarizer = YouTubeSubtitleSummarizer()

    # Input can be a video or playlist URL
    url = input("\nEnter YouTube video or playlist URL: ").strip()

    try:
        if summarizer.is_playlist_url(url):
            outputs = summarizer.process_playlist(url)
            logging.info(f"🎉 Success! Generated {len(outputs)} files")
        else:
            result_file = summarizer.process_video(url)
            logging.info(f"🎉 Success! Your summary is ready: {result_file}")
            # Optionally display the first few lines
            with open(result_file, "r", encoding="utf-8") as f:
                preview = f.read()[:500]
                logging.info(f"\nPreview:\n{preview}...")
    except Exception as e:
        logging.error(f"Failed to process input: {str(e)}")


if __name__ == "__main__":
    main()
