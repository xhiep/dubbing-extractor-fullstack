"""Burn subtitles into video."""
import logging
import subprocess
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)

from .ffmpeg_wrapper import ffmpeg_cmd, get_dims
from .video_encoder import _has_nvenc, _build_enc_args, _run_ff
from ...utils.file_utils import safe_path

def _check_libass() -> bool:
    """Check if ffmpeg has libass support for subtitle rendering."""
    try:
        ff = ffmpeg_cmd()
        r  = subprocess.run([ff, "-hide_banner", "-filters"],
                            capture_output=True, text=True, timeout=5)
        return "subtitles" in r.stdout
    except (subprocess.SubprocessError, OSError) as e:
        logger.debug(f"Could not check libass support: {e}")
        return False

def _compute_burn_margin(h: int, subtitle_top_y: Optional[int], subtitle_bottom_y: Optional[int]) -> int:
    """Calculate margin for burning subtitles.
    
    Args:
        h: Video height
        subtitle_top_y: Top Y position of detected old subtitles
    
    Returns:
        Margin value in pixels
    """
    if subtitle_bottom_y is not None:
        return min(max(28, h - subtitle_bottom_y + 18), int(h * 0.22))
    if subtitle_top_y is None:
        return max(28, int(h * 0.035))
    return min(max(28, h - subtitle_top_y + 14), int(h * 0.22))

def compute_subtitle_layout(
    video_height: int,
    subtitle_top_y: Optional[int],
    subtitle_bottom_y: Optional[int] = None,
    font_scale: float = 1.0,
    font_size_override: int = 0,
    margin_offset: int = 0,
) -> dict:
    """Return the same subtitle sizing/position values used by burn_subtitle."""
    margin_v = _compute_burn_margin(video_height, subtitle_top_y, subtitle_bottom_y) + margin_offset
    margin_v = max(8, min(margin_v, int(video_height * 0.45)))
    if font_size_override and font_size_override > 0:
        font_size = max(10, int(font_size_override))
    else:
        font_size = max(14, int(video_height * 0.030 * max(font_scale, 0.5)))
    return {
        "margin_v": margin_v,
        "font_size": font_size,
    }

def burn_subtitle(
    src: Path,
    srt: Path,
    dst: Path,
    subtitle_top_y: Optional[int],
    subtitle_bottom_y: Optional[int] = None,
    log_cb: Optional[Callable[[str], None]] = None,
    font_scale: float = 1.0,
    font_size_override: int = 0,
    margin_offset: int = 0,
) -> None:
    """Burn Vietnamese subtitles into video using FFmpeg libass.

    Embeds SRT subtitles directly into video frames with customizable styling.
    Automatically positions subtitles based on detected original subtitle locations.
    Uses NVENC GPU encoding when available, falls back to CPU.

    Args:
        src: Path to source video file
        srt: Path to SRT subtitle file
        dst: Path where output video will be saved
        subtitle_top_y: Top Y coordinate of original subtitles (for positioning)
        subtitle_bottom_y: Bottom Y coordinate of original subtitles
        log_cb: Optional callback function for logging progress
        font_scale: Font size scale multiplier
        font_size_override: Override font size in points (0 = auto-calculate)
        margin_offset: Additional margin offset in pixels

    Raises:
        RuntimeError: If FFmpeg subtitle burning fails
    """
    def _log(m):
        if log_cb:
            log_cb(m)
    
    # Check libass support
    if not _check_libass():
        _log("⚠  ffmpeg thieu libass - khong the burn subtitle")
        return
    
    _, h = get_dims(src)
    layout = compute_subtitle_layout(
        h,
        subtitle_top_y,
        subtitle_bottom_y,
        font_scale=font_scale,
        font_size_override=font_size_override,
        margin_offset=margin_offset,
    )
    margin_v = layout["margin_v"]
    font_size = layout["font_size"]
    
    _log(f"->  Ghi sub | MarginV={margin_v}px | FontSize={font_size}pt")
    
    # Escape SRT path for ffmpeg
    srt_esc = str(srt).replace("\\", "\\\\").replace(":", "\\:")
    style = (
        f"FontName=Arial,"
        f"FontSize={font_size},"
        f"PrimaryColour=&H00FFFFFF,"
        f"OutlineColour=&H00000000,"
        f"BackColour=&H60000000,"
        f"Bold=1,"
        f"Outline=2,"
        f"Shadow=1,"
        f"Alignment=2,"
        f"MarginV={margin_v}"
    )
    
    nvenc = _has_nvenc()
    enc_args, label = _build_enc_args(nvenc)
    _log(f"->  Encoder: {label}")
    
    ff = ffmpeg_cmd()
    cmd = [
        ff, "-y",
        "-i", str(src),
        "-vf", f"subtitles='{srt_esc}':force_style='{style}'",
        "-map", "0:v:0",
        "-map", "0:a?",
        *enc_args,
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(dst),
    ]
    
    _log("->  Dang render sub vao video...")
    try:
        _run_ff(cmd, log_cb)
    except RuntimeError:
        if not nvenc:
            raise
        _log("⚠  NVENC that bai khi burn sub, thu CPU...")
        enc_args_cpu, _ = _build_enc_args(False)
        cmd_cpu = [
            ff, "-y",
            "-i", str(src),
            "-vf", f"subtitles='{srt_esc}':force_style='{style}'",
            "-map", "0:v:0",
            "-map", "0:a?",
            *enc_args_cpu,
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(dst),
        ]
        _run_ff(cmd_cpu, log_cb)
    
    _log(f"✓  Video co sub: {dst.stat().st_size/1024/1024:.1f} MB")
