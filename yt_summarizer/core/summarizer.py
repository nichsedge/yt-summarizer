"""
Main YouTube subtitle summarizer class.
"""

import logging
from typing import List

from ..config import settings
from ..exceptions import PlaylistError, VideoProcessingError, YouTubeSummarizerError
from ..utils import (
    TokenCounter,
    extract_playlist_video_ids,
    extract_video_id,
    get_video_title_from_html,
    is_playlist_url,
)
from .provider_config import ProviderConfig
from .summary import SummaryGenerator
from .transcript import TranscriptProcessor


class YouTubeSubtitleSummarizer:
    """Main class for summarizing YouTube videos from subtitles."""

    def __init__(
        self,
        provider: str = None,
        model: str = None,
        api_key: str = None,
        openai_api_key: str = None,
    ):
        """
        Initialize the YouTube Subtitle Summarizer.

        Args:
            provider: AI provider (openai, openrouter, ollama)
            model: Model name for the provider
            api_key: API key for authentication
            openai_api_key: Deprecated: Use api_key parameter instead

        Raises:
            YouTubeSummarizerError: If initialization fails
        """
        # Handle deprecated openai_api_key parameter
        if openai_api_key and not api_key:
            api_key = openai_api_key
            logging.warning(
                "openai_api_key parameter is deprecated. Use api_key instead."
            )

        try:
            # Initialize provider configuration
            self.provider_config = ProviderConfig(
                provider=provider, model=model, api_key=api_key
            )

            # Initialize components
            self.transcript_processor = TranscriptProcessor()
            self.token_counter = TokenCounter()
            self.summary_generator = SummaryGenerator(
                self.provider_config, self.token_counter
            )

            logging.info(
                f"Initialized with {self.provider_config.provider}/{self.provider_config.model}"
            )
        except Exception as e:
            raise YouTubeSummarizerError(f"Failed to initialize summarizer: {str(e)}")

    def process_video(self, video_url: str) -> str:
        """
        Complete process: extract subtitles, split, summarize, and merge.

        Args:
            video_url: YouTube video URL

        Returns:
            Path to generated markdown file

        Raises:
            VideoProcessingError: If video processing fails
        """
        try:
            video_id = extract_video_id(video_url)
            video_title = get_video_title_from_html(video_id)
            logging.info(f"Summarizing: {video_title}")

            subtitles = self.transcript_processor.get_subtitles(video_id)
            chunks = self.token_counter.split_text_into_chunks(
                subtitles, settings.processing.max_tokens_per_chunk
            )

            summaries = []
            for i, chunk in enumerate(chunks, 1):
                if len(chunks) > 1:
                    logging.info(f"  Processing section {i}/{len(chunks)}...")
                summary = self.summary_generator.summarize_chunk(chunk, i, len(chunks))
                summaries.append(summary)

            final_document = self.summary_generator.merge_summaries(
                summaries, video_title
            )

            output_file = self.summary_generator.save_summary(
                final_document, video_title
            )
            return output_file

        except Exception as e:
            logging.error(f"Error processing video: {str(e)}")
            if isinstance(e, (VideoProcessingError, PlaylistError)):
                raise
            raise VideoProcessingError(f"Failed to process video: {str(e)}")

    def process_playlist(self, playlist_url: str) -> List[str]:
        """
        Process a playlist URL by extracting each video's subtitles, summarizing,
        and saving individual markdown files per video.

        Args:
            playlist_url: YouTube playlist URL

        Returns:
            List of paths to generated files

        Raises:
            PlaylistError: If playlist processing fails
        """
        try:
            video_ids = extract_playlist_video_ids(playlist_url)
            logging.info(f"Processing playlist: {len(video_ids)} videos found")

            output_files: List[str] = []
            for idx, vid in enumerate(video_ids, 1):
                try:
                    video_url = f"https://www.youtube.com/watch?v={vid}"
                    logging.info(f"[{idx}/{len(video_ids)}] Processing video: {vid}")
                    out_path = self.process_video(video_url)
                    output_files.append(out_path)
                except Exception as e:
                    logging.error(f"Failed to process video {vid}: {e}")
                    continue

            return output_files
        except Exception as e:
            logging.error(f"Error processing playlist: {str(e)}")
            raise PlaylistError(f"Failed to process playlist: {str(e)}")
