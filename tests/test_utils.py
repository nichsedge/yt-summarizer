"""Test utility functions."""

import pytest
from yt_summarizer.utils import (
    sanitize_filename,
    is_playlist_url,
    extract_video_id,
    extract_playlist_video_ids
)


class TestSanitizeFilename:
    """Test filename sanitization."""

    def test_basic_sanitization(self):
        """Test basic character removal."""
        assert sanitize_filename("test<file>name") == "testfilename"
        assert sanitize_filename('test"file"name') == "testfilename"
        assert sanitize_filename("test/file\\name") == "testfilename"
        assert sanitize_filename("test:file|name") == "testfilename"
        assert sanitize_filename("test?file*name") == "testfilename"

    def test_space_replacement(self):
        """Test space to underscore replacement."""
        assert sanitize_filename("test file name") == "test_file_name"
        assert sanitize_filename("test  multiple  spaces") == "test_multiple_spaces"

    def test_edge_cases(self):
        """Test edge cases."""
        assert sanitize_filename("") == ""
        assert sanitize_filename("___") == ""
        assert sanitize_filename("_test_file_") == "test_file"
        assert sanitize_filename('test"file_with/invalid\\chars') == "testfile_withinvalidchars"


class TestURLHelpers:
    """Test URL parsing functions."""

    def test_is_playlist_url(self):
        """Test playlist URL detection."""
        # Playlist URLs
        assert is_playlist_url("https://www.youtube.com/playlist?list=xxxxx")
        assert is_playlist_url("https://youtube.com/playlist?list=xxxxx")
        assert is_playlist_url("https://www.youtube.com/watch?v=xxxxx&list=yyyyy")

        # Non-playlist URLs
        assert not is_playlist_url("https://www.youtube.com/watch?v=xxxxx")
        assert not is_playlist_url("https://youtu.be/xxxxx")
        assert not is_playlist_url("https://www.youtube.com/embed/xxxxx")
        assert not is_playlist_url("https://example.com/video")

    def test_extract_video_id(self):
        """Test video ID extraction."""
        # Standard watch URL
        assert extract_video_id("https://www.youtube.com/watch?v=VIDEO_ID") == "VIDEO_ID"
        assert extract_video_id("https://youtube.com/watch?v=VIDEO_ID") == "VIDEO_ID"

        # Short URL
        assert extract_video_id("https://youtu.be/VIDEO_ID") == "VIDEO_ID"

        # Embed URL
        assert extract_video_id("https://www.youtube.com/embed/VIDEO_ID") == "VIDEO_ID"

        # With additional parameters
        assert extract_video_id(
            "https://www.youtube.com/watch?v=VIDEO_ID&t=30s"
        ) == "VIDEO_ID"

        # Invalid URLs
        with pytest.raises(ValueError):
            extract_video_id("https://example.com/video")

        with pytest.raises(ValueError):
            extract_video_id("https://www.youtube.com/playlist?list=xxxxx")

    def test_playlist_video_extraction(self):
        """Test extracting video IDs from playlist."""
        # This would require actual HTTP requests, so we'll test with mock
        # TODO: Add mock tests for this function
        pass