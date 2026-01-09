"""
YouTube Summarizer - A tool to generate summaries from YouTube video subtitles.

This package provides functionality to:
- Extract subtitles from YouTube videos
- Process YouTube playlists
- Generate AI-powered summaries using multiple providers
- Export summaries as markdown files
"""

__version__ = "0.2.0"
__author__ = "YouTube Summarizer Team"

from .core.summarizer import YouTubeSubtitleSummarizer
from .core.provider_config import ProviderConfig
from .core.transcript import TranscriptProcessor
from .core.summary import SummaryGenerator

__all__ = [
    "YouTubeSubtitleSummarizer",
    "ProviderConfig",
    "TranscriptProcessor",
    "SummaryGenerator"
]