"""
Transcript processing for YouTube videos.
"""

import logging
import re
from typing import Any

from youtube_transcript_api import FetchedTranscript, YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

from ..config import Settings
from ..config import settings as default_settings
from ..exceptions import TranscriptError


class TranscriptProcessor:
    """Handles YouTube transcript extraction and processing."""

    def __init__(self, settings: Settings | None = None) -> None:
        """Initialize the transcript processor."""
        self.settings = (settings or default_settings).processing

    def get_subtitles(self, video_id: str) -> str:
        """
        Get subtitles with priority order.

        Priority (prefer_manual_transcripts=True):
          1. Manual transcript in each configured language
          2. Auto-generated transcript in each configured language
          3. Auto-generated transcript in any language
          4. Manual transcript in any language

        With prefer_manual_transcripts=False, generated and manual tiers swap,
        so auto-generated transcripts are preferred.

        Args:
            video_id: YouTube video ID

        Returns:
            Subtitle text as string

        Raises:
            TranscriptError: If transcript extraction fails
        """
        try:
            ytt_api = YouTubeTranscriptApi()
            transcript_list = list(ytt_api.list(video_id))
        except TranscriptError:
            raise
        except Exception as e:
            logging.error(f"Error listing subtitles: {str(e)}")
            raise TranscriptError(f"Error listing subtitles: {str(e)}") from e

        manual = [t for t in transcript_list if not t.is_generated]
        generated = [t for t in transcript_list if t.is_generated]

        primary, secondary = (
            (manual, generated)
            if self.settings.prefer_manual_transcripts
            else (generated, manual)
        )
        tiers = []
        for pool in (primary, secondary):
            for lang_code in self.settings.language_priority:
                tiers.append([t for t in pool if self._matches_language(t, lang_code)])
        tiers.append(generated)
        tiers.append(manual)

        for tier in tiers:
            if not tier:
                continue
            transcript = tier[0]
            kind = "auto-generated" if transcript.is_generated else "manual"
            logging.debug(f"Using {kind} subtitles in {transcript.language_code}")
            try:
                fetched: FetchedTranscript = transcript.fetch()
            except Exception as e:
                logging.error(f"Error fetching subtitles: {str(e)}")
                raise TranscriptError(f"Error fetching subtitles: {str(e)}") from e
            return self._format_transcript(fetched)

        raise TranscriptError("No suitable subtitles found")

    @staticmethod
    def _matches_language(transcript: Any, lang_code: str) -> bool:
        """
        Match a transcript's language code against a configured code.

        'en' matches both 'en' and regional variants like 'en-US'.
        """
        code = transcript.language_code or ""
        return code == lang_code or code.split("-")[0] == lang_code.split("-")[0]

    def _format_transcript(self, transcript_data: FetchedTranscript) -> str:
        """
        Format transcript data into clean text.

        Args:
            transcript_data: Fetched transcript (iterable of snippets)

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
