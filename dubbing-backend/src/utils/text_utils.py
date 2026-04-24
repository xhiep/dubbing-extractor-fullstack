"""Text utility functions."""
import re

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mGKHF]")

def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from string."""
    return _ANSI_RE.sub("", text)

def sanitize_filename(name: str) -> str:
    """Sanitize filename by removing invalid characters."""
    name = re.sub(r"[<>:\"/\\|?*]", "_", name)
    name = re.sub(r"\s+", "_", name)
    name = name.strip("._")
    return name[:200] if name else "untitled"

def srt_time(sec: float) -> str:
    """Convert seconds to SRT timestamp format."""
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int((sec - int(sec)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
