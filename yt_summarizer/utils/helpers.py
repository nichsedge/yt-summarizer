"""
Utility functions for YouTube Summarizer.
"""

import html
import json
import logging
import os
import re
from typing import Any
from urllib.parse import parse_qs, urlparse


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize filename to remove invalid characters.

    Args:
        filename: Original filename
        max_length: Maximum length for filename (default: 200)

    Returns:
        Sanitized filename
    """

    # Decode HTML entities (e.g., &#39; -> ')
    sanitized = html.unescape(filename)

    # Keep only alphanumeric and spaces, replace others with underscores
    sanitized = re.sub(r"[^A-Za-z0-9\s]", "_", sanitized)

    # Remove consecutive underscores
    sanitized = re.sub(r"_+", "_", sanitized)

    # Replace whitespace with underscores
    sanitized = re.sub(r"\s+", "_", sanitized)

    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")

    # Limit filename length (before extension)
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip("_")

    return sanitized or "untitled"


def ensure_output_dir(output_dir: str) -> None:
    """
    Ensure output directory exists.

    Args:
        output_dir: Path to output directory
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)


def is_playlist_url(url: str) -> bool:
    """
    Detect if the provided URL is a YouTube playlist URL.

    Args:
        url: URL to check

    Returns:
        True if URL is a playlist, False otherwise
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


def extract_video_id(url: str) -> str:
    """
    Extract YouTube video ID from URL.

    Args:
        url: YouTube video URL

    Returns:
        Video ID string

    Raises:
        ValueError: If URL is invalid or is a playlist URL
    """
    parsed_url = urlparse(url)

    # Guard: don't allow playlist URL here
    if is_playlist_url(url):
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


def get_video_title_from_html(video_id: str, timeout: int = 20) -> str:
    """
    Get video title from YouTube (simple method).

    Args:
        video_id: YouTube video ID
        timeout: Request timeout in seconds

    Returns:
        Video title or default string
    """
    import requests

    try:
        # This is a simple method - for production, consider using YouTube Data API
        url = f"https://www.youtube.com/watch?v={video_id}"
        response = requests.get(url, timeout=timeout)

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


def _extract_ids_from_initial_data(page_html: str) -> list:
    """
    Extract ordered playlist video IDs from the ytInitialData JSON payload.

    Walks the JSON tree collecting playlistVideoRenderer.videoId entries in
    document order, so only videos actually part of the playlist are returned.

    Args:
        page_html: Raw playlist page HTML

    Returns:
        List of unique video IDs in playlist order ([] if payload missing/invalid)
    """
    match = re.search(r"var ytInitialData\s*=\s*({.+?})\s*;\s*</script>", page_html)
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    ids: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            renderer = node.get("playlistVideoRenderer")
            if isinstance(renderer, dict):
                video_id = renderer.get("videoId")
                if isinstance(video_id, str) and video_id:
                    ids.append(video_id)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    return list(dict.fromkeys(ids))


def _extract_ids_from_html(page_html: str) -> list:
    """
    Fallback: scan raw HTML for watch?v= links in order of appearance.

    May include IDs for videos outside the playlist (e.g. recommendations).
    """
    pattern = re.compile(r"watch\?v=([A-Za-z0-9_-]{11})")
    seen: set[str] = set()
    ordered: list = []
    for m in pattern.finditer(page_html):
        vid = m.group(1)
        if vid not in seen:
            seen.add(vid)
            ordered.append(vid)
    return ordered


def extract_playlist_video_ids(playlist_url: str, timeout: int = 30) -> list:
    """
    Extract unique video IDs from a YouTube playlist page without API keys.

    Prefers the structured ytInitialData payload (exact membership and order);
    falls back to a raw HTML link scan when that payload is unavailable.

    Args:
        playlist_url: URL of the YouTube playlist
        timeout: Request timeout in seconds

    Returns:
        List of video IDs in playlist order

    Raises:
        ValueError: If URL is not a valid playlist URL
        requests.RequestException: If request fails
    """
    import requests

    if not is_playlist_url(playlist_url):
        raise ValueError("URL is not a playlist URL")

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    resp = requests.get(playlist_url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    page_html = resp.text

    video_ids = _extract_ids_from_initial_data(page_html)
    if video_ids:
        return video_ids

    logging.debug("ytInitialData missing or unparsable; falling back to HTML scan")
    return _extract_ids_from_html(page_html)
