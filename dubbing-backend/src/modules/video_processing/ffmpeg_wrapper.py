"""FFmpeg wrapper functions."""
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Callable, Tuple

logger = logging.getLogger(__name__)

HERE = Path(__file__).parent.parent.parent.parent
LOCAL_FFMPEG = HERE / "bin" / "ffmpeg" / "ffmpeg.exe"
LOCAL_FFPROBE = HERE / "bin" / "ffmpeg" / "ffprobe.exe"


def _safe_path(path: Path) -> str:
    """Return a Windows-safe path string for ffmpeg invocations."""
    return str(path)

def ffmpeg_cmd() -> str:
    if LOCAL_FFMPEG.exists():
        return str(LOCAL_FFMPEG)
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    raise RuntimeError("Khong tim thay ffmpeg!\n  -> Hay chay install.bat truoc.")

def ffprobe_cmd() -> str:
    if LOCAL_FFPROBE.exists():
        return str(LOCAL_FFPROBE)
    if shutil.which("ffprobe"):
        return "ffprobe"
    raise RuntimeError("Khong tim thay ffprobe!")

def extract_audio_local(video_path: Path, out_audio: Path, log_cb: Optional[Callable[[str], None]] = None) -> Path:
    """Extract audio track from local video file using FFmpeg.

    Converts video audio to mono MP3 at 16kHz sample rate, optimized for
    speech recognition. Handles Unicode filenames on Windows.

    Args:
        video_path: Path to input video file
        out_audio: Path where audio file will be saved
        log_cb: Optional callback function for logging progress

    Returns:
        Path to extracted audio file

    Raises:
        RuntimeError: If FFmpeg extraction fails
        FileNotFoundError: If output audio file was not created
    """
    def _log(m): log_cb and log_cb(m)
    _log("->  Trich xuat audio tu file local...")

    # Dung short path (8.3) tren Windows de tranh loi Unicode voi ten file tieng Trung/dac biet
    video_str = _safe_path(video_path)
    # Xây audio_str từ short path của parent + tên file gốc
    audio_parent_short = _safe_path(out_audio.parent)
    sep = "\\" if os.name == "nt" else "/"
    audio_str = audio_parent_short.rstrip("\\/") + sep + out_audio.name

    cmd = [
        ffmpeg_cmd(), "-y", "-i", video_str,
        "-vn", "-ar", "16000", "-ac", "1",
        "-codec:a", "libmp3lame", "-qscale:a", "2",
        audio_str
    ]
    _log(f"->  CMD: {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        # Log TOAN BO stderr de de debug
        full_err = result.stderr or "(khong co stderr)"
        _log(f"[ffmpeg stderr]:\n{full_err}")
        raise RuntimeError(f"ffmpeg loi khi trich audio (return code {result.returncode}):\n{full_err[-800:]}")

    if not out_audio.exists():
        raise FileNotFoundError("Khong tao duoc file audio!")
    _log(f"✓  Audio: {out_audio.stat().st_size/1024/1024:.1f} MB")
    return out_audio

# ─── CONFIG PERSISTENCE ───────────────────────────────────────────────────────

def get_dims(path: Path) -> Tuple[int, int]:
    """Get video dimensions using ffprobe.

    Args:
        path: Path to video file

    Returns:
        Tuple of (width, height) in pixels

    Raises:
        RuntimeError: If ffprobe fails to read video
    """
    cmd  = [ffprobe_cmd(), "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "json", str(path)]
    data = json.loads(subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout)
    s    = data.get("streams", [{}])[0]
    return s.get("width", 1920), s.get("height", 1080)

def probe_duration(path: Path) -> float:
    cmd = [
        ffprobe_cmd(),
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    out = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).stdout.strip()
    try:
        return float(out)
    except (ValueError, TypeError) as e:
        logger.debug(f"Could not parse duration from ffprobe output: {e}")
        return 0.0

