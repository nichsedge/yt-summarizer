"""Tests for playlist video ID extraction."""

import json

import pytest
import requests as requests_module

from yt_summarizer.utils import extract_playlist_video_ids
from yt_summarizer.utils.helpers import (
    _extract_ids_from_html,
    _extract_ids_from_initial_data,
)


def initial_data_html(video_ids):
    contents = [{"playlistVideoRenderer": {"videoId": vid}} for vid in video_ids]
    data = {
        "contents": {
            "twoColumnBrowseResultsRenderer": {
                "tabs": [
                    {
                        "tabRenderer": {
                            "content": {
                                "sectionListRenderer": {
                                    "contents": [
                                        {
                                            "itemSectionRenderer": {
                                                "contents": [
                                                    {
                                                        "playlistVideoListRenderer": {
                                                            "contents": contents
                                                        }
                                                    }
                                                ]
                                            }
                                        }
                                    ]
                                }
                            }
                        }
                    }
                ]
            }
        }
    }
    return "<html><script>var ytInitialData = " + json.dumps(data) + ";</script></html>"


class TestInitialDataExtraction:
    def test_extracts_playlist_videos_in_order(self):
        html = initial_data_html(["AAAAAAAAAAA", "BBBBBBBBBBB", "CCCCCCCCCCC"])
        assert _extract_ids_from_initial_data(html) == [
            "AAAAAAAAAAA",
            "BBBBBBBBBBB",
            "CCCCCCCCCCC",
        ]

    def test_ignores_non_playlist_renderers_and_duplicates(self):
        html = initial_data_html(["AAAAAAAAAAA", "AAAAAAAAAAA"])
        # Decoy: a recommended video rendered as compactVideoRenderer.
        decoy = '<a href="/watch?v=DDDDDDDDDDD">rec</a>'
        assert _extract_ids_from_initial_data(html + decoy) == ["AAAAAAAAAAA"]

    def test_missing_payload_returns_empty(self):
        assert _extract_ids_from_initial_data("<html>nothing here</html>") == []

    def test_malformed_json_returns_empty(self):
        html = "<script>var ytInitialData = {broken];</script></html>"
        assert _extract_ids_from_initial_data(html) == []


class TestHtmlFallback:
    def test_scans_watch_links(self):
        html = (
            '<a href="/watch?v=AAAAAAAAAAA">1</a>'
            '<a href="/watch?v=BBBBBBBBBBB">2</a>'
            '<a href="/watch?v=AAAAAAAAAAA">1 again</a>'
        )
        assert _extract_ids_from_html(html) == ["AAAAAAAAAAA", "BBBBBBBBBBB"]


class TestExtractPlaylistVideoIds:
    def _patch_requests(self, monkeypatch, html):
        class FakeResponse:
            text = html

            def raise_for_status(self):
                pass

        monkeypatch.setattr(requests_module, "get", lambda *a, **k: FakeResponse())

    def test_prefers_initial_data_over_raw_links(self, monkeypatch):
        html = initial_data_html(["AAAAAAAAAAA"]) + (
            '<a href="/watch?v=ZZZZZZZZZZZ">recommended</a>'
        )
        self._patch_requests(monkeypatch, html)
        result = extract_playlist_video_ids("https://www.youtube.com/playlist?list=xyz")
        assert result == ["AAAAAAAAAAA"]

    def test_falls_back_to_link_scan_without_payload(self, monkeypatch):
        html = (
            '<a href="/watch?v=AAAAAAAAAAA">1</a>'
            '<a href="/watch?v=BBBBBBBBBBB">2</a>'
        )
        self._patch_requests(monkeypatch, html)
        result = extract_playlist_video_ids("https://www.youtube.com/playlist?list=xyz")
        assert result == ["AAAAAAAAAAA", "BBBBBBBBBBB"]

    def test_rejects_non_playlist_url(self):
        with pytest.raises(ValueError, match="not a playlist URL"):
            extract_playlist_video_ids("https://www.youtube.com/watch?v=x")
