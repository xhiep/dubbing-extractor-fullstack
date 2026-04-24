"""Downloader module."""
from .platform_detector import detect_platform, normalize_douyin_url
from .url_resolver import resolve_short_douyin_url
from .ytdlp_wrapper import download

__all__ = [
    "detect_platform",
    "normalize_douyin_url",
    "resolve_short_douyin_url",
    "download",
]
