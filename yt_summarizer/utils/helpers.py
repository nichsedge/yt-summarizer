"""
Utility functions for YouTube Summarizer.
"""

import re
import os
from typing import Set
from urllib.parse import urlparse, parse_qs


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to remove invalid characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove invalid characters and replace spaces with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    sanitized = sanitized.replace(' ', '_')
    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    return sanitized


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
        raise ValueError("Provided URL is a playlist. Use process_playlist() for playlists.")

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


def extract_playlist_video_ids(playlist_url: str, timeout: int = 30) -> list:
    """
    Extract unique video IDs from a YouTube playlist HTML without API keys.

    Args:
        playlist_url: URL of the YouTube playlist
        timeout: Request timeout in seconds

    Returns:
        List of video IDs in order of appearance

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
    html = resp.text

    pattern = re.compile(r"watch\?v=([A-Za-z0-9_-]{11})")
    seen: Set[str] = set()
    ordered: list = []
    for m in pattern.finditer(html):
        vid = m.group(1)
        if vid not in seen:
            seen.add(vid)
            ordered.append(vid)

    if not ordered:
        import logging
        logging.warning("No video IDs found in playlist HTML. The page might require JS to render items.")
    return ordered