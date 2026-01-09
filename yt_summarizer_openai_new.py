#!/usr/bin/env python3
"""
YouTube Subtitle Summarizer - Generate AI-powered summaries from YouTube video subtitles.

This script provides backward compatibility while using the new modular structure.
"""

import os
import sys

# Add the package to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from yt_summarizer.cli import main

if __name__ == "__main__":
    sys.exit(main())
