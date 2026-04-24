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
from .video_processing.ffmpeg_wrapper import extract_audio_local, get_dims
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
    video_speed: float = 1.0,
    log_cb: Optional[Callable[[str], None]] = None,
) -> List[Dict[str, Any]]:
    """Translate segments to Vietnamese and apply timing adjustments.

    Uses Google Translate to convert transcribed text to Vietnamese.
    Applies timing scale, offset, and video speed adjustments to timestamps.

    Args:
        segs: List of transcription segments with text and timestamps
        subtitle_timing_scale: Timing scale multiplier (default 1.0)
        subtitle_offset_sec: Time offset in seconds to shift all subtitles
        video_speed: Video playback speed multiplier (default 1.0)
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
        segs_vi = _apply_subtitle_timing(segs_vi, subtitle_timing_scale, subtitle_offset_sec, video_speed)
    return segs_vi or []


def step4_cover(
    raw_video: str,
    segs_vi: list,
    out_dir: str,
    cover_mode: str = "blur",
    blur_padding_px: int = 12,
    cover_offset_px: int = 0,
    blur_power: int = 4,
    video_speed: float = 1.0,
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
        video_speed: Video playback speed multiplier
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
        video_speed=video_speed,
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
    video_speed: float = 1.0,
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
        video_speed: Video speed multiplier
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
                "video_speed": video_speed,
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
        segs_vi = step3_translate(segs, subtitle_timing_scale, subtitle_offset_sec, video_speed, log_cb)

        # Bước 4
        result4 = step4_cover(
            raw_video, segs_vi, out_dir, cover_mode,
            blur_padding_px=blur_padding_px,
            cover_offset_px=cover_offset_px,
            blur_power=blur_power,
            video_speed=video_speed,
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
            video_speed=video_speed,
            cover_mode=cover_mode,
            log_cb=log_cb,
        )

        # Bước 6: Burn sub (optional)
        dub_video_source = final_video
        if burn_sub and segs_vi and srt_path:
            burned = step6_burn(
                final_video, srt_path, cover_meta, out_dir,
                subtitle_font_scale=subtitle_font_scale,
                subtitle_font_size=subtitle_font_size,
                subtitle_margin_px=subtitle_margin_px,
                log_cb=log_cb,
            )
            if Path(burned).exists():
                dub_video_source = burned

        # Bước 7: Lồng tiếng (optional)
        if enable_dub and segs_vi:
            dub_segments = list(segs_vi)
            if srt_path:
                parsed = parse_srt(Path(srt_path))
                if parsed:
                    dub_segments = parsed

            step7_dub(
                dub_video_source, dub_segments, out_dir,
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
