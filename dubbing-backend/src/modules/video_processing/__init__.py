"""Video processing module."""
from .ffmpeg_wrapper import ffmpeg_cmd, ffprobe_cmd, extract_audio_local, get_dims, probe_duration
from .subtitle_detector import detect_sub_events
from .video_encoder import render_clean_video
from .subtitle_burner import burn_subtitle

__all__ = [
    "ffmpeg_cmd",
    "ffprobe_cmd",
    "extract_audio_local",
    "get_dims",
    "probe_duration",
    "detect_sub_events",
    "render_clean_video",
    "burn_subtitle",
]
