"""Tests for transcript selection logic."""

from unittest.mock import MagicMock, patch

import pytest

from yt_summarizer.config import Settings
from yt_summarizer.core.transcript import TranscriptProcessor
from yt_summarizer.exceptions import TranscriptError


class FakeSnippet:
    """Formatter reads snippet.text."""

    def __init__(self, text):
        self.text = text


class FakeTranscript:
    """Minimal stand-in for youtube_transcript_api.Transcript."""

    def __init__(self, language_code, is_generated):
        self.language_code = language_code
        self.is_generated = is_generated

    def fetch(self):
        return [FakeSnippet(f"text-from-{self.language_code}-{self.is_generated}")]


def make_processor(prefer_manual=True):
    settings = Settings()
    settings.processing.prefer_manual_transcripts = prefer_manual
    return TranscriptProcessor(settings=settings)


def get_subtitles_with(transcripts, prefer_manual=True):
    processor = make_processor(prefer_manual)
    api = MagicMock()
    api.list.return_value = transcripts
    with patch("yt_summarizer.core.transcript.YouTubeTranscriptApi", return_value=api):
        return processor.get_subtitles("abc12345678")


class TestGetSubtitles:
    def test_prefers_manual_in_priority_language(self):
        result = get_subtitles_with(
            [
                FakeTranscript("en", is_generated=True),
                FakeTranscript("en", is_generated=False),
            ]
        )
        assert "text-from-en-False" in result

    def test_uses_generated_when_no_manual(self):
        result = get_subtitles_with([FakeTranscript("en", is_generated=True)])
        assert "text-from-en-True" in result

    def test_prefer_manual_false_prefers_generated(self):
        result = get_subtitles_with(
            [
                FakeTranscript("en", is_generated=False),
                FakeTranscript("en", is_generated=True),
            ],
            prefer_manual=False,
        )
        assert "text-from-en-True" in result

    def test_regional_language_variant_matches(self):
        result = get_subtitles_with([FakeTranscript("en-US", is_generated=False)])
        assert "text-from-en-US-False" in result

    def test_falls_back_to_other_language(self):
        result = get_subtitles_with(
            [
                FakeTranscript("fr", is_generated=False),
                FakeTranscript("de", is_generated=True),
            ]
        )
        # Priority tiers exhaust en, then any auto-generated (de) wins over manual fr.
        assert "text-from-de-True" in result

    def test_falls_back_to_manual_any_language(self):
        result = get_subtitles_with([FakeTranscript("fr", is_generated=False)])
        assert "text-from-fr-False" in result

    def test_no_subtitles_raises(self):
        with pytest.raises(TranscriptError, match="No suitable subtitles"):
            get_subtitles_with([])

    def test_listing_error_is_wrapped(self):
        processor = make_processor()
        api = MagicMock()
        api.list.side_effect = RuntimeError("boom")
        with (
            patch(
                "yt_summarizer.core.transcript.YouTubeTranscriptApi",
                return_value=api,
            ),
            pytest.raises(TranscriptError, match="boom"),
        ):
            processor.get_subtitles("abc12345678")

    def test_fetch_error_is_wrapped(self):
        processor = make_processor()
        bad = FakeTranscript("en", is_generated=False)
        bad.fetch = lambda: (_ for _ in ()).throw(RuntimeError("fetch failed"))
        api = MagicMock()
        api.list.return_value = [bad]
        with (
            patch(
                "yt_summarizer.core.transcript.YouTubeTranscriptApi",
                return_value=api,
            ),
            pytest.raises(TranscriptError, match="fetch failed"),
        ):
            processor.get_subtitles("abc12345678")

    def test_matches_language_helper(self):
        transcript = FakeTranscript("pt-BR", is_generated=False)
        assert TranscriptProcessor._matches_language(transcript, "pt")
        assert TranscriptProcessor._matches_language(transcript, "pt-BR")
        assert not TranscriptProcessor._matches_language(transcript, "es")
