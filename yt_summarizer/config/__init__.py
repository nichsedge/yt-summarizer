"""
Configuration module for YouTube Summarizer.
"""

from .settings import Settings, ProviderSettings, ProcessingSettings, OutputSettings, settings

__all__ = [
    "Settings",
    "ProviderSettings",
    "ProcessingSettings",
    "OutputSettings",
    "settings"
]