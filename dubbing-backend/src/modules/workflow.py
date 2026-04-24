"""Main video processing workflow."""
import json
import logging
import os
import shutil
import statistics
import gc
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Dict, List, Any

logger = logging.getLogger(__name__)

from .downloader.platform_detector import detect_platform
from .downloader.ytdlp_wrapper import download
from .transcription.whisper_engine import transcribe
from .transcription.translator import translate
from .transcription.srt_generator import write_srt, parse_srt
from .video_processing.ffmpeg_wrapper import extract_audio_local, get_dims, retime_video_with_audio
from .video_processing.subtitle_detector import detect_sub_events
from .video_processing.video_encoder import render_clean_video
from .video_processing.subtitle_burner import burn_subtitle
from .tts.audio_dubber import render_dubbed_outputs
from .tts.vieneu_engine import release_tts_resources
from ..utils.file_utils import is_local_file, ensure_dir
from ..utils.text_utils import sanitize_filename
from ..config import config


def _make_log(log_cb: Optional[Callable]):
    def _log(msg):
        if log_cb:
            try:
                log_cb(msg)
            except UnicodeEncodeError:
                fallback = str(msg).encode("ascii", "replace").decode("ascii")
                log_cb(fallback)
    return _log


def _log_runtime_memory(log_cb: Optional[Callable], stage: str) -> None:
    _log = _make_log(log_cb)
    parts = []

    try:
        import psutil
        process = psutil.Process(os.getpid())
        rss_mb = process.memory_info().rss / 1024 / 1024
        parts.append(f"rss={rss_mb:.0f}MB")
    except (ImportError, AttributeError) as e:
        logger.debug(f"Could not get memory info: {e}")

    try:
        import torch
        if torch.cuda.is_available():
            allocated_mb = torch.cuda.memory_allocated() / 1024 / 1024
            reserved_mb = torch.cuda.memory_reserved() / 1024 / 1024
            parts.append(f"cuda_alloc={allocated_mb:.0f}MB")
            parts.append(f"cuda_reserved={reserved_mb:.0f}MB")
    except (ImportError, AttributeError) as e:
        logger.debug(f"Could not get CUDA memory info: {e}")

    if parts:
        _log(f"[MEM] {stage}: " + " | ".join(parts))


def _apply_subtitle_timing(segments: list, subtitle_timing_scale: float, subtitle_offset_sec: float, video_speed: float) -> list:
    adjusted = []
    scale = subtitle_timing_scale if subtitle_timing_scale > 0 else 1.0
    speed = video_speed if video_speed > 0 else 1.0
    effective_scale = scale / speed
    for seg in segments:
        start = max(0.0, float(seg["start"]) * effective_scale + subtitle_offset_sec)
        end = max(start + 0.05, float(seg["end"]) * effective_scale + subtitle_offset_sec)
        new_seg = dict(seg)
        new_seg["start"] = start
        new_seg["end"] = end
        adjusted.append(new_seg)
    return adjusted


def _retime_cover_events(detected_events: list, segments: list) -> list:
    if not detected_events:
        return []
    if not segments:
        return detected_events
    top_y = int(statistics.median(int(event["top_y"]) for event in detected_events))
    bottom_y = int(statistics.median(int(event["bottom_y"]) for event in detected_events))
    if bottom_y <= top_y:
        top_y = min(int(event["top_y"]) for event in detected_events)
        bottom_y = max(int(event["bottom_y"]) for event in detected_events)
    height = max(18, bottom_y - top_y + 1)
    retimed = []
    for seg in segments:
        start = max(0.0, float(seg.get("start", 0.0) or 0.0) - 0.04)
        end = max(start + 0.08, float(seg.get("end", 0.0) or 0.0) + 0.04)
        retimed.append({
            "start": start,
            "end": end,
            "top_y": top_y,
            "bottom_y": bottom_y,
            "height": height,
        })
    return retimed


# ─────────────────────────────────────────────
#  CÁC HÀM STEP RIÊNG LẺ
# ─────────────────────────────────────────────

def step1_prepare(
    source_input: str,
    log_cb: Optional[Callable[[str], None]] = None,
) -> Dict[str, str]:
    """Download video or use local file and extract audio.

    Handles both remote URLs (YouTube, Bilibili, Douyin) and local video files.
    Creates output directory and extracts audio for transcription.

    Args:
        source_input: Video URL or local file path
        log_cb: Optional callback function for logging progress

    Returns:
        Dictionary containing paths and metadata:
            - raw_video: Path to video file
            - raw_audio: Path to extracted audio (MP3)
            - title: Video title or filename
            - out_dir: Output directory path
            - temp_dir: Temporary working directory path

    Raises:
        FileNotFoundError: If local file does not exist
        RuntimeError: If download or audio extraction fails
    """
    _log = _make_log(log_cb)
    _log("\n" + "="*52 + "\n  BƯỚC 1: TẢI VIDEO & AUDIO\n" + "="*52)

    temp_dir = Path(config.get("output_base_dir", "output")) / "_temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    if is_local_file(source_input):
        raw_video = Path(source_input)
        title = raw_video.stem
        _log(f"->  File: {raw_video.name}  ({raw_video.stat().st_size/1024/1024:.1f} MB)")
        raw_audio = extract_audio_local(raw_video, temp_dir / "audio_goc.mp3", log_cb)
    else:
        raw_video, raw_audio, title = download(source_input, temp_dir, log_cb)

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe_title = sanitize_filename(title)
    out_dir = Path(config.get("output_base_dir", "output")) / f"{safe_title}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    _log(f"✓  Output: {out_dir}")

    shutil.copy2(raw_audio, out_dir / "audio_goc.mp3")

    return {
        "raw_video": str(raw_video),
        "raw_audio": str(out_dir / "audio_goc.mp3"),
        "title": title,
        "out_dir": str(out_dir),
        "temp_dir": str(temp_dir),
    }


def step2_transcribe(
    audio_path: str,
    log_cb: Optional[Callable[[str], None]] = None,
) -> List[Dict[str, Any]]:
    """Transcribe audio using Whisper speech recognition.

    Uses Whisper model to convert speech to text with timestamps.
    Automatically selects CPU or CUDA device based on hardware compatibility.

    Args:
        audio_path: Path to audio file (MP3 format)
        log_cb: Optional callback function for logging progress

    Returns:
        List of transcription segments, each containing:
            - start: Start time in seconds
            - end: End time in seconds
            - text: Transcribed text

    Raises:
        RuntimeError: If Whisper transcription fails
    """
    _log = _make_log(log_cb)
    _log("\n" + "="*52 + "\n  BƯỚC 2: NHẬN DẠNG GIỌNG NÓI (WHISPER)\n" + "="*52)
    segs = transcribe(Path(audio_path), log_cb)
    return segs or []


def step3_translate(
    segs: list,
    subtitle_timing_scale: float = 1.0,
    subtitle_offset_sec: float = 0.0,
    render_video_speed: float = 1.0,
    log_cb: Optional[Callable[[str], None]] = None,
) -> List[Dict[str, Any]]:
    """Translate segments to Vietnamese and apply timing adjustments.

    Uses Google Translate to convert transcribed text to Vietnamese.
    Applies timing scale, offset, and video speed adjustments to timestamps.

    Args:
        segs: List of transcription segments with text and timestamps
        subtitle_timing_scale: Timing scale multiplier (default 1.0)
        subtitle_offset_sec: Time offset in seconds to shift all subtitles
        render_video_speed: Render playback speed multiplier (default 1.0)
        log_cb: Optional callback function for logging progress

    Returns:
        List of translated segments, each containing:
            - start: Adjusted start time in seconds
            - end: Adjusted end time in seconds
            - text: Vietnamese translated text
            - original: Original text before translation

    Raises:
        ConnectionError: If translation API is unreachable
    """
    _log = _make_log(log_cb)
    if not segs:
        _log("⚠  Không có segment để dịch.")
        return []
    _log("\n" + "="*52 + "\n  BƯỚC 3: DỊCH SANG TIẾNG VIỆT\n" + "="*52)
    segs_vi = translate(segs, log_cb)
    if segs_vi:
        segs_vi = _apply_subtitle_timing(segs_vi, subtitle_timing_scale, subtitle_offset_sec, render_video_speed)
    return segs_vi or []


def step4_cover(
    raw_video: str,
    segs_vi: list,
    out_dir: str,
    cover_mode: str = "blur",
    blur_padding_px: int = 12,
    cover_offset_px: int = 0,
    blur_power: int = 4,
    render_video_speed: float = 1.0,
    log_cb: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    """Cover original subtitles and render clean video.

    Detects original subtitle regions using OpenCV and covers them with blur
    or black bars. Adjusts video speed if specified.

    Args:
        raw_video: Path to raw video file
        segs_vi: List of Vietnamese subtitle segments for timing
        out_dir: Output directory path
        cover_mode: Covering method (none, blur, blackbar)
        blur_padding_px: Extra padding around subtitle region in pixels
        cover_offset_px: Vertical offset to shift cover region
        blur_power: Blur intensity (1-10)
        render_video_speed: Render playback speed multiplier
        log_cb: Optional callback function for logging progress

    Returns:
        Dictionary containing:
            - final_video: Path to rendered video
            - cover_meta: Metadata about subtitle covering (positions, mode)

    Raises:
        RuntimeError: If video encoding fails
    """
    _log = _make_log(log_cb)
    _log("\n" + "="*52 + "\n  BƯỚC 4: CHE PHỤ ĐỀ GỐC\n" + "="*52)

    valid_modes = ["none", "blur", "blackbar"]
    if cover_mode not in valid_modes:
        cover_mode = "blur"

    raw_video_path = Path(raw_video)
    out_dir_path = Path(out_dir)
    final_video = out_dir_path / "video_ready.mp4"

    w, h = get_dims(raw_video_path)
    detected_events = detect_sub_events(raw_video_path, w, h, log_cb)
    timed_cover_events = _retime_cover_events(detected_events, segs_vi)

    if timed_cover_events and detected_events:
        _log(f"->  Dùng vị trí sub cũ đã detect, canh theo {len(timed_cover_events)} mốc thời gian subtitle mới.")

    cover_meta = render_clean_video(
        raw_video_path,
        final_video,
        cover_mode,
        timed_cover_events or detected_events,
        log_cb,
        blur_padding_px=blur_padding_px,
        cover_offset_px=cover_offset_px,
        blur_power=blur_power,
        video_speed=render_video_speed,
    )

    return {
        "final_video": str(final_video),
        "cover_meta": cover_meta or {},
    }


def step5_export(
    segs_vi: list,
    out_dir: str,
    title: str,
    cover_meta: dict,
    raw_video: str,
    srt_max_chars_per_line: int = 45,
    subtitle_font_scale: float = 1.0,
    subtitle_font_size: int = 0,
    subtitle_margin_px: int = 0,
    blur_padding_px: int = 12,
    blur_power: int = 4,
    cover_offset_px: int = 0,
    subtitle_offset_sec: float = 0.0,
    subtitle_timing_scale: float = 1.0,
    render_video_speed: float = 1.0,
    output_video_speed: float = 1.0,
    cover_mode: str = "blur",
    log_cb: Optional[Callable[[str], None]] = None,
) -> Optional[str]:
    """Export SRT subtitle file, script, bilingual reference, and render metadata.

    Creates multiple output files for different use cases: SRT for video players,
    plain text script for review, bilingual reference for comparison, and JSON
    metadata for reproducing render settings.

    Args:
        segs_vi: List of Vietnamese subtitle segments
        out_dir: Output directory path
        title: Video title for file headers
        cover_meta: Metadata from subtitle covering step
        raw_video: Path to raw video (for dimensions)
        srt_max_chars_per_line: Maximum characters per subtitle line
        subtitle_font_scale: Font size scale multiplier
        subtitle_font_size: Override font size in points
        subtitle_margin_px: Margin offset in pixels
        blur_padding_px: Blur padding used in covering
        blur_power: Blur power used in covering
        cover_offset_px: Cover offset used in covering
        subtitle_offset_sec: Subtitle time offset
        subtitle_timing_scale: Subtitle timing scale
        render_video_speed: Render speed multiplier
        output_video_speed: Final output speed relative to original video
        cover_mode: Cover mode used
        log_cb: Optional callback function for logging progress

    Returns:
        Path to SRT file if successful, None if no segments to export
    """
    _log = _make_log(log_cb)
    _log("\n" + "="*52 + "\n  BƯỚC 5: XUẤT FILE OUTPUT\n" + "="*52)

    if not segs_vi:
        _log("⚠  Không có segment để xuất.")
        return None

    out_dir_path = Path(out_dir)
    raw_video_path = Path(raw_video)
    w, h = get_dims(raw_video_path)

    srt_path = out_dir_path / "file_sub_viet.srt"
    write_srt(segs_vi, srt_path, max_chars_per_line=srt_max_chars_per_line)
    _log(f"✓  Exported: {srt_path.name}")

    render_meta_path = out_dir_path / "render_meta.json"
    render_meta_path.write_text(
        json.dumps(
            {
                "cover_mode": cover_mode,
                "video_width": w,
                "video_height": h,
                "subtitle_top_y": cover_meta.get("subtitle_top_y"),
                "subtitle_bottom_y": cover_meta.get("subtitle_bottom_y"),
                "cover_top_y": cover_meta.get("cover_top_y"),
                "cover_bottom_y": cover_meta.get("cover_bottom_y"),
                "cover_offset_px": cover_offset_px,
                "subtitle_offset_sec": subtitle_offset_sec,
                "subtitle_timing_scale": subtitle_timing_scale,
                "render_video_speed": render_video_speed,
                "output_video_speed": output_video_speed,
                "video_speed": render_video_speed,
                "subtitle_font_scale": subtitle_font_scale,
                "subtitle_font_size": subtitle_font_size,
                "subtitle_margin_px": subtitle_margin_px,
                "srt_max_chars_per_line": srt_max_chars_per_line,
                "blur_padding_px": blur_padding_px,
                "blur_power": blur_power,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _log(f"✓  Exported: {render_meta_path.name}")

    script_path = out_dir_path / "kich_ban_dich.txt"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(f"KICH BAN DICH: {title}\n")
        f.write("=" * 60 + "\n\n")
        for seg in segs_vi:
            f.write(f"{seg['text']}\n")
    _log(f"✓  Exported: {script_path.name}")

    bilingual_path = out_dir_path / "song_ngu_tham_chieu.txt"
    with open(bilingual_path, "w", encoding="utf-8") as f:
        f.write(f"SONG NGU THAM CHIEU: {title}\n")
        f.write("=" * 60 + "\n\n")
        for seg in segs_vi:
            if "original" in seg:
                f.write(f"[CN] {seg['original']}\n")
            f.write(f"[VI] {seg['text']}\n\n")
    _log(f"✓  Exported: {bilingual_path.name}")

    return str(srt_path)


def step6_burn(
    final_video: str,
    srt_path: str,
    cover_meta: dict,
    out_dir: str,
    subtitle_font_scale: float = 1.0,
    subtitle_font_size: int = 0,
    subtitle_margin_px: int = 0,
    log_cb: Optional[Callable[[str], None]] = None,
) -> str:
    """Burn Vietnamese subtitles into video using FFmpeg.

    Embeds SRT subtitles directly into video frames with customizable styling.
    Positions subtitles based on detected original subtitle locations.

    Args:
        final_video: Path to clean video (after subtitle covering)
        srt_path: Path to SRT subtitle file
        cover_meta: Metadata containing subtitle position info
        out_dir: Output directory path
        subtitle_font_scale: Font size scale multiplier
        subtitle_font_size: Override font size in points (0 = auto)
        subtitle_margin_px: Additional margin offset in pixels
        log_cb: Optional callback function for logging progress

    Returns:
        Path to video with burned subtitles

    Raises:
        RuntimeError: If FFmpeg subtitle burning fails
    """
    _log = _make_log(log_cb)
    _log("\n" + "="*52 + "\n  BƯỚC 6: GHI PHỤ ĐỀ TV VÀO VIDEO\n" + "="*52)

    burned = Path(out_dir) / "video_sub_viet.mp4"
    burn_subtitle(
        Path(final_video),
        Path(srt_path),
        burned,
        cover_meta.get("subtitle_top_y"),
        cover_meta.get("subtitle_bottom_y"),
        log_cb,
        font_scale=subtitle_font_scale,
        font_size_override=subtitle_font_size,
        margin_offset=subtitle_margin_px,
    )
    return str(burned)


def step7_dub(
    video_source: str,
    dub_segments: list,
    out_dir: str,
    dub_mode: str = "preset",
    dub_backend_mode: str = "turbo",
    dub_remote_api_base: str = "http://localhost:23333/v1",
    dub_preset_voice: str = "",
    dub_ref_audio: str = "",
    dub_ref_text: str = "",
    dub_voice_volume: float = 1.35,
    dub_source_volume: float = 0.18,
    dub_mix_mode: str = "nen_nho",
    output_video_name: str = "video_long_tieng.mp4",
    log_cb: Optional[Callable[[str], None]] = None,
) -> Dict[str, Path]:
    """Dub video with Vietnamese voice using VieNeu-TTS.

    Synthesizes Vietnamese speech for each subtitle segment and mixes it with
    the original video audio. Supports preset voices and voice cloning.

    Args:
        video_source: Path to source video file
        dub_segments: List of subtitle segments to synthesize
        out_dir: Output directory path
        dub_mode: Voice mode (preset or clone)
        dub_backend_mode: TTS backend (turbo, turbo_gpu, fast, remote)
        dub_remote_api_base: API base URL for remote mode
        dub_preset_voice: Preset voice name
        dub_ref_audio: Reference audio path for voice cloning
        dub_ref_text: Reference text for voice cloning
        dub_voice_volume: Dubbed voice volume multiplier
        dub_source_volume: Original audio volume multiplier
        dub_mix_mode: Mixing mode (nen_nho or tat_goc)
        output_video_name: Output video filename
        log_cb: Optional callback function for logging progress

    Returns:
        Dictionary containing:
            - dub_track: Path to dubbed audio track (WAV)
            - dub_video: Path to final dubbed video (MP4)

    Raises:
        RuntimeError: If TTS synthesis or audio mixing fails
        ValueError: If no segments provided
    """
    _log = _make_log(log_cb)
    _log("\n" + "="*52 + "\n  BƯỚC 7: LỒNG TIẾNG TIẾNG VIỆT\n" + "="*52)

    dubbed = render_dubbed_outputs(
        Path(video_source),
        dub_segments,
        Path(out_dir),
        mode=dub_mode,
        engine_mode=dub_backend_mode,
        remote_api_base=dub_remote_api_base,
        preset_voice=dub_preset_voice,
        ref_audio=dub_ref_audio,
        ref_text=dub_ref_text,
        dub_volume=dub_voice_volume,
        source_volume=dub_source_volume,
        mix_mode=dub_mix_mode,
        output_video_name=output_video_name,
        log_cb=log_cb,
    )
    _log(f"✓  Exported: {dubbed['dub_track'].name}")
    _log(f"✓  Exported: {dubbed['dub_video'].name}")
    return dubbed


# ─────────────────────────────────────────────
#  PIPELINE ĐẦY ĐỦ (giữ nguyên cho nút "Bắt Đầu Xử Lý")
# ─────────────────────────────────────────────

def process_video(
    source_input: str,
    cover_mode: str = "blur",
    burn_sub: bool = False,
    log_cb: Optional[Callable[[str], None]] = None,
    subtitle_offset_sec: float = 0.0,
    subtitle_timing_scale: float = 1.0,
    render_video_speed: float = 1.0,
    output_video_speed: float = 1.0,
    video_speed: float = 1.0,
    srt_max_chars_per_line: int = 45,
    subtitle_font_scale: float = 1.0,
    subtitle_font_size: int = 0,
    subtitle_margin_px: int = 0,
    blur_padding_px: int = 12,
    cover_offset_px: int = 0,
    blur_power: int = 4,
    enable_dub: bool = False,
    dub_mode: str = "preset",
    dub_backend_mode: str = "turbo",
    dub_remote_api_base: str = "http://localhost:23333/v1",
    dub_preset_voice: str = "",
    dub_ref_audio: str = "",
    dub_ref_text: str = "",
    dub_voice_volume: float = 1.35,
    dub_source_volume: float = 0.18,
    dub_mix_mode: str = "nen_nho",
) -> Optional[str]:
    """Process video: download, transcribe, translate, and add subtitles.

    Args:
        source_input: Video URL or local file path
        cover_mode: Subtitle covering mode (none, blur, blackbar)
        burn_sub: Whether to burn subtitles into video
        log_cb: Logging callback function

    Returns:
        Output directory path if successful, None otherwise
    """
    _log = _make_log(log_cb)
    effective_render_speed, effective_output_speed = _resolve_speed_options(
        {
            "render_video_speed": render_video_speed,
            "output_video_speed": output_video_speed,
            "video_speed": video_speed,
        }
    )

    total_steps = 5
    if burn_sub:
        total_steps += 1
    if enable_dub:
        total_steps += 1

    temp_dir = None

    try:
        _log_runtime_memory(log_cb, "start")
        # Bước 1
        result1 = step1_prepare(source_input, log_cb)
        raw_video = result1["raw_video"]
        raw_audio = result1["raw_audio"]
        title = result1["title"]
        out_dir = result1["out_dir"]
        temp_dir = result1["temp_dir"]

        # Bước 2
        segs = step2_transcribe(raw_audio, log_cb)

        # Bước 3
        segs_vi = step3_translate(
            segs,
            subtitle_timing_scale,
            subtitle_offset_sec,
            effective_render_speed,
            log_cb,
        )

        # Bước 4
        result4 = step4_cover(
            raw_video, segs_vi, out_dir, cover_mode,
            blur_padding_px=blur_padding_px,
            cover_offset_px=cover_offset_px,
            blur_power=blur_power,
            render_video_speed=effective_render_speed,
            log_cb=log_cb,
        )
        final_video = result4["final_video"]
        cover_meta = result4["cover_meta"]

        # Bước 5
        srt_path = step5_export(
            segs_vi, out_dir, title, cover_meta, raw_video,
            srt_max_chars_per_line=srt_max_chars_per_line,
            subtitle_font_scale=subtitle_font_scale,
            subtitle_font_size=subtitle_font_size,
            subtitle_margin_px=subtitle_margin_px,
            blur_padding_px=blur_padding_px,
            blur_power=blur_power,
            cover_offset_px=cover_offset_px,
            subtitle_offset_sec=subtitle_offset_sec,
            subtitle_timing_scale=subtitle_timing_scale,
            render_video_speed=effective_render_speed,
            output_video_speed=effective_output_speed,
            cover_mode=cover_mode,
            log_cb=log_cb,
        )

        # Bước 6: Burn sub (optional)
        final_output_video = final_video
        if burn_sub and segs_vi and srt_path:
            burned = step6_burn(
                final_video, srt_path, cover_meta, out_dir,
                subtitle_font_scale=subtitle_font_scale,
                subtitle_font_size=subtitle_font_size,
                subtitle_margin_px=subtitle_margin_px,
                log_cb=log_cb,
            )
            if Path(burned).exists():
                final_output_video = burned

        # Bước 7: Lồng tiếng (optional)
        if enable_dub and segs_vi:
            dub_segments = list(segs_vi)
            if srt_path:
                parsed = parse_srt(Path(srt_path))
                if parsed:
                    dub_segments = parsed

            dubbed = step7_dub(
                final_output_video, dub_segments, out_dir,
                dub_mode=dub_mode,
                dub_backend_mode=dub_backend_mode,
                dub_remote_api_base=dub_remote_api_base,
                dub_preset_voice=dub_preset_voice,
                dub_ref_audio=dub_ref_audio,
                dub_ref_text=dub_ref_text,
                dub_voice_volume=dub_voice_volume,
                dub_source_volume=dub_source_volume,
                dub_mix_mode=dub_mix_mode,
                output_video_name="video_sub_viet_long_tieng.mp4" if burn_sub else "video_long_tieng.mp4",
                log_cb=log_cb,
            )
            final_output_video = str(dubbed["dub_video"])

        retimed_final_output = _retime_final_video_if_needed(
            final_output_video,
            out_dir,
            effective_render_speed,
            effective_output_speed,
            "final_speed",
            log_cb=log_cb,
        )
        if retimed_final_output != final_output_video:
            target_path = Path(final_output_video)
            retimed_path = Path(retimed_final_output)
            if target_path.exists():
                target_path.unlink()
            retimed_path.replace(target_path)

        # Summary
        out_dir_path = Path(out_dir)
        _log("\n" + "="*52)
        _log("  HOÀN TẤT!")
        for f in sorted(out_dir_path.iterdir()):
            icon = {".mp4": "🎥", ".mp3": "🎵", ".srt": "📝", ".txt": "📄"}.get(f.suffix, "📁")
            mb = f.stat().st_size / 1024 / 1024
            _log(f"  {icon}  {f.name:<38} {mb:6.1f} MB")
        _log("="*52)
        _log_runtime_memory(log_cb, "finish")

        return str(out_dir_path.resolve())

    except Exception as e:
        _log(f"\n❌  LỖI: {str(e)}")
        import traceback
        _log(traceback.format_exc())
        return None

    finally:
        release_tts_resources()
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
        _log_runtime_memory(log_cb, "cleanup")
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


STEP_STATE_FILENAME = "pipeline_state.json"


def load_step_state(output_dir: str) -> dict:
    workspace = Path(output_dir)
    state_path = workspace / STEP_STATE_FILENAME
    if not state_path.exists():
        return {
            "task_id": workspace.name,
            "workspace_dir": str(workspace),
            "completed_steps": [],
        }

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state.setdefault("task_id", workspace.name)
        state.setdefault("workspace_dir", str(workspace))
        state.setdefault("completed_steps", [])
        return state
    except Exception:
        return {
            "task_id": workspace.name,
            "workspace_dir": str(workspace),
            "completed_steps": [],
        }


def save_step_state(output_dir: str, state: dict) -> None:
    workspace = Path(output_dir)
    workspace.mkdir(parents=True, exist_ok=True)
    state["workspace_dir"] = str(workspace)
    state["task_id"] = state.get("task_id") or workspace.name
    state_path = workspace / STEP_STATE_FILENAME
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _step_options(step_data: dict, state: dict) -> dict:
    options = dict(state.get("options") or {})
    options.update(step_data.get("options") or {})
    return options


def _ensure_completed_step(state: dict, step_num: int) -> None:
    completed = set(state.get("completed_steps") or [])
    completed.add(step_num)
    state["completed_steps"] = sorted(completed)


def _clear_downstream_state(state: dict, step_num: int) -> None:
    if step_num <= 1:
        for key in (
            "segments",
            "segments_vi",
            "srt_path",
            "final_video",
            "cover_meta",
            "burned_video_render",
            "burned_video",
            "dub_track",
            "dub_video",
        ):
            state.pop(key, None)
    elif step_num <= 2:
        for key in (
            "segments_vi",
            "srt_path",
            "final_video",
            "cover_meta",
            "burned_video_render",
            "burned_video",
            "dub_track",
            "dub_video",
        ):
            state.pop(key, None)
    elif step_num <= 3:
        for key in (
            "final_video",
            "cover_meta",
            "burned_video_render",
            "burned_video",
            "dub_track",
            "dub_video",
        ):
            state.pop(key, None)
    elif step_num <= 4:
        for key in ("burned_video_render", "burned_video", "dub_track", "dub_video"):
            state.pop(key, None)
    elif step_num <= 5:
        for key in ("burned_video_render", "burned_video", "dub_track", "dub_video"):
            state.pop(key, None)
    elif step_num <= 6:
        for key in ("dub_track", "dub_video"):
            state.pop(key, None)

    state["completed_steps"] = [value for value in state.get("completed_steps", []) if value < step_num]


def _load_srt_segments_from_state(state: dict) -> list:
    srt_path = state.get("srt_path")
    if srt_path and Path(srt_path).exists():
        parsed = parse_srt(Path(srt_path))
        if parsed:
            state["segments_vi"] = parsed
            return parsed
    return list(state.get("segments_vi") or [])


def _write_step3_srt(state: dict, max_chars_per_line: int) -> Optional[str]:
    out_dir = state.get("out_dir")
    segs_vi = state.get("segments_vi") or []
    if not out_dir or not segs_vi:
        return None

    srt_path = Path(out_dir) / "file_sub_viet.srt"
    write_srt(segs_vi, srt_path, max_chars_per_line=max_chars_per_line)
    state["srt_path"] = str(srt_path)
    return str(srt_path)


def _collect_step_outputs(state: dict, step_num: int) -> dict:
    srt_path = state.get("srt_path")
    srt_content = ""
    if srt_path and Path(srt_path).exists():
        srt_content = Path(srt_path).read_text(encoding="utf-8", errors="ignore")

    return {
        "task_id": state.get("task_id"),
        "current_step": step_num,
        "completed_steps": state.get("completed_steps", []),
        "title": state.get("title"),
        "out_dir": state.get("out_dir"),
        "video_path": state.get("burned_video") or state.get("dub_video") or state.get("final_video") or state.get("raw_video"),
        "audio_path": state.get("raw_audio"),
        "srt_path": srt_path,
        "srt_content": srt_content,
        "cover_meta": state.get("cover_meta") or {},
        "dub_audio_path": state.get("dub_track"),
        "dub_video_path": state.get("dub_video"),
        "render_video_speed": state.get("options", {}).get("render_video_speed", state.get("options", {}).get("video_speed", 1.0)),
        "output_video_speed": state.get("options", {}).get("output_video_speed", 1.0),
    }


def _resolve_speed_options(options: dict) -> tuple[float, float]:
    render_video_speed = float(options.get("render_video_speed", options.get("video_speed", 1.0)) or 1.0)
    output_video_speed = float(options.get("output_video_speed", 1.0) or 1.0)
    render_video_speed = max(0.25, min(4.0, render_video_speed))
    output_video_speed = max(0.25, min(4.0, output_video_speed))
    return render_video_speed, output_video_speed


def _retime_final_video_if_needed(
    video_path: str,
    out_dir: str,
    render_video_speed: float,
    output_video_speed: float,
    suffix: str,
    log_cb: Optional[Callable[[str], None]] = None,
) -> str:
    factor = output_video_speed / render_video_speed
    if abs(factor - 1.0) <= 0.001:
        return video_path

    src = Path(video_path)
    dst = Path(out_dir) / f"{src.stem}_{suffix}{src.suffix}"
    retime_video_with_audio(src, dst, factor, log_cb=log_cb)
    return str(dst)


def run_single_step(
    step_num: int,
    task_id: str,
    output_dir: str,
    step_data: dict,
    log_cb: Optional[Callable[[str], None]] = None,
    progress_cb: Optional[Callable[[int, float, str], None]] = None,
) -> dict:
    """Run a step-by-step pipeline target, auto-filling missing prerequisites."""
    _log = _make_log(log_cb)
    state = load_step_state(output_dir)
    state["task_id"] = task_id
    state["source"] = step_data.get("source") or state.get("source")
    state["options"] = _step_options(step_data, state)

    step_names = {
        1: "Prepare Source",
        2: "Transcribe Audio",
        3: "Translate Subtitle",
        4: "Cover Original Subtitle",
        5: "Export Files",
        6: "Burn Subtitle",
        7: "Generate Dub",
    }

    def _progress(current_step: int, progress: float, message: str):
        if progress_cb:
            progress_cb(current_step, progress, message)

    if not state.get("source"):
        raise ValueError("source is required for step-by-step processing")

    if step_data.get("srt_content") and state.get("srt_path"):
        Path(state["srt_path"]).write_text(step_data["srt_content"], encoding="utf-8")
        parsed = parse_srt(Path(state["srt_path"]))
        if parsed:
            state["segments_vi"] = parsed
            save_step_state(output_dir, state)

    try:
        for current_step in range(1, step_num + 1):
            force_run = current_step == step_num
            options = state.get("options") or {}
            render_video_speed, output_video_speed = _resolve_speed_options(options)
            _log(f"Starting step {current_step}: {step_names.get(current_step, current_step)}")

            if current_step == 1:
                raw_video = state.get("raw_video")
                raw_audio = state.get("raw_audio")
                if force_run or not raw_video or not raw_audio or not Path(raw_audio).exists():
                    _clear_downstream_state(state, 1)
                    _progress(1, 10, "Preparing source...")
                    result = step1_prepare(state["source"], log_cb)
                    state.update(result)
                    _ensure_completed_step(state, 1)
                    save_step_state(output_dir, state)
                _progress(1, 100, "Step 1 completed")

            elif current_step == 2:
                if not state.get("raw_audio"):
                    raise ValueError("raw_audio missing after step 1")
                if force_run or not state.get("segments"):
                    _clear_downstream_state(state, 2)
                    _progress(2, 15, "Transcribing audio...")
                    state["segments"] = step2_transcribe(state["raw_audio"], log_cb)
                    _ensure_completed_step(state, 2)
                    save_step_state(output_dir, state)
                _progress(2, 100, "Step 2 completed")

            elif current_step == 3:
                if not state.get("segments"):
                    raise ValueError("segments missing after step 2")
                if force_run or not state.get("segments_vi"):
                    _clear_downstream_state(state, 3)
                    _progress(3, 20, "Translating subtitle...")
                    state["segments_vi"] = step3_translate(
                        state["segments"],
                        options.get("subtitle_timing_scale", 1.0),
                        options.get("subtitle_offset_sec", 0.0),
                        render_video_speed,
                        log_cb,
                    )
                _write_step3_srt(state, options.get("srt_max_chars_per_line", 45))
                _ensure_completed_step(state, 3)
                save_step_state(output_dir, state)
                _progress(3, 100, "Step 3 completed")

            elif current_step == 4:
                segs_vi = _load_srt_segments_from_state(state)
                if not state.get("raw_video") or not state.get("out_dir"):
                    raise ValueError("step 1 output missing")
                if force_run or not state.get("final_video"):
                    _clear_downstream_state(state, 4)
                    _progress(4, 20, "Covering original subtitle...")
                    result = step4_cover(
                        state["raw_video"],
                        segs_vi,
                        state["out_dir"],
                        options.get("cover_mode", "blur"),
                        blur_padding_px=options.get("blur_padding_px", 12),
                        cover_offset_px=options.get("cover_offset_px", 0),
                        blur_power=options.get("cover_strength", 15),
                        render_video_speed=render_video_speed,
                        log_cb=log_cb,
                    )
                    state["final_video"] = result.get("final_video")
                    state["cover_meta"] = result.get("cover_meta") or {}
                    _ensure_completed_step(state, 4)
                    save_step_state(output_dir, state)
                _progress(4, 100, "Step 4 completed")

            elif current_step == 5:
                segs_vi = _load_srt_segments_from_state(state)
                if not state.get("out_dir") or not state.get("raw_video"):
                    raise ValueError("step 1 output missing")
                _progress(5, 25, "Exporting files...")
                state["srt_path"] = step5_export(
                    segs_vi,
                    state["out_dir"],
                    state.get("title") or "Untitled",
                    state.get("cover_meta") or {},
                    state["raw_video"],
                    srt_max_chars_per_line=options.get("srt_max_chars_per_line", 45),
                    subtitle_font_scale=options.get("subtitle_font_scale", 1.0),
                    subtitle_font_size=options.get("subtitle_font_size", 0),
                    subtitle_margin_px=options.get("subtitle_margin_px", 0),
                    blur_padding_px=options.get("blur_padding_px", 12),
                    blur_power=options.get("cover_strength", 15),
                    cover_offset_px=options.get("cover_offset_px", 0),
                    subtitle_offset_sec=options.get("subtitle_offset_sec", 0.0),
                    subtitle_timing_scale=options.get("subtitle_timing_scale", 1.0),
                    render_video_speed=render_video_speed,
                    output_video_speed=output_video_speed,
                    cover_mode=options.get("cover_mode", "blur"),
                    log_cb=log_cb,
                )
                _ensure_completed_step(state, 5)
                save_step_state(output_dir, state)
                _progress(5, 100, "Step 5 completed")

            elif current_step == 6:
                if not options.get("burn_subtitle", True):
                    _progress(6, 100, "Burn subtitle disabled, skipped")
                    continue
                if not state.get("final_video") or not state.get("srt_path"):
                    raise ValueError("step 4/5 output missing")
                _progress(6, 30, "Burning subtitle into video...")
                state["burned_video_render"] = step6_burn(
                    state["final_video"],
                    state["srt_path"],
                    state.get("cover_meta") or {},
                    state["out_dir"],
                    subtitle_font_scale=options.get("subtitle_font_scale", 1.0),
                    subtitle_font_size=options.get("subtitle_font_size", 0),
                    subtitle_margin_px=options.get("subtitle_margin_px", 0),
                    log_cb=log_cb,
                )
                state["burned_video"] = _retime_final_video_if_needed(
                    state["burned_video_render"],
                    state["out_dir"],
                    render_video_speed,
                    output_video_speed,
                    "burned_speed",
                    log_cb=log_cb,
                )
                _ensure_completed_step(state, 6)
                save_step_state(output_dir, state)
                _progress(6, 100, "Step 6 completed")

            elif current_step == 7:
                segs_vi = _load_srt_segments_from_state(state)
                if not segs_vi:
                    raise ValueError("subtitle data missing before dubbing")
                video_source = state.get("burned_video_render") or state.get("final_video") or state.get("raw_video")
                _progress(7, 30, "Generating dub...")
                dubbed = step7_dub(
                    video_source,
                    segs_vi,
                    state["out_dir"],
                    dub_mode=options.get("dub_mode", "preset"),
                    dub_backend_mode=options.get("dub_backend_mode", "turbo"),
                    dub_remote_api_base=options.get("dub_remote_api_base", "http://localhost:23333/v1"),
                    dub_preset_voice=options.get("dub_preset_voice", ""),
                    dub_ref_audio=options.get("dub_ref_audio", ""),
                    dub_ref_text=options.get("dub_ref_text", ""),
                    dub_voice_volume=options.get("dub_voice_volume", 1.35),
                    dub_source_volume=options.get("dub_source_volume", 0.18),
                    dub_mix_mode=options.get("dub_mix_mode", "nen_nho"),
                    output_video_name="video_sub_viet_long_tieng.mp4" if options.get("burn_subtitle", True) else "video_long_tieng.mp4",
                    log_cb=log_cb,
                )
                state["dub_track"] = str(dubbed["dub_track"])
                state["dub_video"] = _retime_final_video_if_needed(
                    str(dubbed["dub_video"]),
                    state["out_dir"],
                    render_video_speed,
                    output_video_speed,
                    "dubbed_speed",
                    log_cb=log_cb,
                )
                _ensure_completed_step(state, 7)
                save_step_state(output_dir, state)
                _progress(7, 100, "Step 7 completed")

            else:
                raise ValueError(f"Unsupported step: {current_step}")

        return _collect_step_outputs(state, step_num)
    except Exception as e:
        _log(f"Step {step_num} failed: {e}")
        raise
