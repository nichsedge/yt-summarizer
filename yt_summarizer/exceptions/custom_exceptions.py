"""
Custom exception classes for YouTube Summarizer.
"""


class YouTubeSummarizerError(Exception):
    """Base exception for all YouTube Summarizer errors."""

    pass


class TranscriptError(YouTubeSummarizerError):
    """Raised when transcript extraction or processing fails."""

    pass


class VideoProcessingError(YouTubeSummarizerError):
    """Raised when video processing fails."""

    pass


class PlaylistError(YouTubeSummarizerError):
    """Raised when playlist processing fails."""

    pass


class ConfigurationError(YouTubeSummarizerError):
    """Raised when configuration is invalid."""

    pass


class ProviderError(YouTubeSummarizerError):
    """Raised when AI provider operation fails."""

    pass
