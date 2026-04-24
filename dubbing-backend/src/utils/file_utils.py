"""File utility functions."""
from pathlib import Path
import os

def is_local_file(path: str) -> bool:
    """Check if path is a local file."""
    if not path:
        return False
    if path.startswith(("http://", "https://", "ftp://")):
        return False
    return Path(path).exists()

def safe_path(p: Path) -> str:
    """Convert Path to string with forward slashes for FFmpeg."""
    return str(p).replace("\\", "/")

def ensure_dir(path: Path) -> Path:
    """Ensure directory exists, create if not."""
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_file_size_mb(path: Path) -> float:
    """Get file size in MB."""
    if not path.exists():
        return 0.0
    return path.stat().st_size / 1024 / 1024
