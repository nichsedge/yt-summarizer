"""
Transcript processing for YouTube videos.
"""

import logging
import re
from typing import List, Dict

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

from ..config import settings
from ..exceptions import TranscriptError


class TranscriptProcessor:
    """Handles YouTube transcript extraction and processing."""

    def __init__(self):
        """Initialize the transcript processor."""
        self.settings = settings.processing

    def get_subtitles(self, video_id: str) -> str:
        """
        Get English subtitles with priority order.

        Args:
            video_id: YouTube video ID

        Returns:
            Subtitle text as string

        Raises:
            TranscriptError: If transcript extraction fails
        """
        try:
            # Instantiate API per latest docs and list available transcripts
            ytt_api = YouTubeTranscriptApi()
            transcript_list = ytt_api.list(video_id)

            # Priority 1: Preferred language (official if available)
            for lang_code in self.settings.language_priority:
                try:
                    transcript = transcript_list.find_transcript([lang_code])
                    if self.settings.prefer_manual_transcripts and not transcript.is_generated:
                        logging.info(f"Found official {lang_code} subtitles")
                        fetched = transcript.fetch()
                        fetched_list = list(fetched) if not isinstance(fetched, list) else fetched
                        return self._format_transcript(fetched_list)
                except Exception:
                    logging.debug(f"Official {lang_code} subtitles not found.")

            # Priority 2: Auto-generated preferred language
            for lang_code in self.settings.language_priority:
                try:
                    transcript = transcript_list.find_generated_transcript([lang_code])
                    logging.info(f"Found auto-generated {lang_code} subtitles")
                    fetched = transcript.fetch()
                    fetched_list = list(fetched) if not isinstance(fetched, list) else fetched
                    return self._format_transcript(fetched_list)
                except Exception:
                    logging.debug(f"Auto-generated {lang_code} subtitles not found.")

            # Priority 3: First available auto-generated subtitle in any language
            try:
                for transcript in transcript_list:
                    if transcript.is_generated:
                        logging.info(
                            f"Found auto-generated subtitles in {transcript.language_code}"
                        )
                        fetched = transcript.fetch()
                        fetched_list = list(fetched) if not isinstance(fetched, list) else fetched
                        return self._format_transcript(fetched_list)
                logging.debug("No auto-generated subtitles found.")
            except Exception:
                logging.debug("Error accessing auto-generated subtitles.")

            raise TranscriptError("No suitable subtitles found")

        except Exception as e:
            if isinstance(e, TranscriptError):
                raise
            logging.error(f"Error getting subtitles: {str(e)}")
            raise TranscriptError(f"Error getting subtitles: {str(e)}")

    def _format_transcript(self, transcript_data: List[Dict]) -> str:
        """
        Format transcript data into clean text.

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