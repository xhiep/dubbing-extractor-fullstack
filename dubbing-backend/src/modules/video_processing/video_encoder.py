"""Video encoding with NVENC GPU support."""
import logging
import re
import subprocess
import tempfile
import statistics
from pathlib import Path
from typing import Optional, Callable, Tuple, List, Dict, Any

logger = logging.getLogger(__name__)

from .ffmpeg_wrapper import ffmpeg_cmd, probe_duration
from ...utils.file_utils import safe_path

def _has_nvenc() -> bool:
    try:
        ff = ffmpeg_cmd()
        r  = subprocess.run([ff, "-hide_banner", "-encoders"],
                            capture_output=True, text=True, timeout=5)
        return "h264_nvenc" in r.stdout
    except (subprocess.SubprocessError, OSError) as e:
        logger.debug(f"Could not detect NVENC support: {e}")
        return False

def _build_enc_args(use_nvenc: bool) -> tuple:
    """Trả về (enc_args_list, label)."""
    if use_nvenc:
        return (
            ["-pix_fmt", "yuv420p",
             "-c:v", "h264_nvenc", "-preset", "p4",
             "-cq", "18", "-rc", "vbr", "-b:v", "0"],
            "NVENC GPU",
        )
    return (
        ["-pix_fmt", "yuv420p",
         "-c:v", "libx264", "-crf", "18", "-preset", "fast"],
        "libx264 CPU",
    )

def _merge_intervals(events: list, gap: float = 0.1) -> list[tuple[float, float]]:
    """Gộp các khoảng thời gian [start, end] liền kề (cách nhau <= gap giây).

    Trả về list các (start, end) đã merge — ít phần tử hơn nhiều so với list gốc.
    """
    if not events:
        return []
    intervals = sorted((float(e["start"]), float(e["end"])) for e in events)
    merged: list[tuple[float, float]] = [intervals[0]]
    for s, e in intervals[1:]:
        ps, pe = merged[-1]
        if s <= pe + gap:
            merged[-1] = (ps, max(pe, e))
        else:
            merged.append((s, e))
    return merged


# FFmpeg expression parser có giới hạn độ dài.  Giữ số lượng between() dưới mức
# này để tránh lỗi "Cannot allocate memory" khi init filter graph.
_MAX_BETWEEN_TERMS = 60


def _build_enable_expr(intervals: list[tuple[float, float]]) -> str | None:
    """Xây enable expression từ list (start, end).

    Trả về None nếu quá nhiều intervals (cần fallback blur-always).
    """
    if len(intervals) > _MAX_BETWEEN_TERMS:
        return None  # fallback: blur toàn thời gian
    return "+".join(f"between(t,{s:.3f},{e:.3f})" for s, e in intervals)


def _blur_zone_filter(top_y: int, band_h: int, blur_power: int,
                      enable_expr: str | None) -> tuple[str, str]:
    """Tạo filter cho 1 vùng blur duy nhất.

    Nếu enable_expr là None → blur toàn thời gian (không dùng enable=).
    Nếu enable_expr có giá trị → chỉ blur trong khoảng thời gian đó.

    Trả về (filter_complex_string, output_label).
    """
    luma_r = min(25, max(1, (band_h - 1) // 2))
    chroma_r = min(25, max(1, (band_h // 2 - 1) // 2))
    blur_filter = (
        f"boxblur=luma_radius={luma_r}:luma_power={blur_power}:"
        f"chroma_radius={chroma_r}:chroma_power={blur_power}"
    )
    if enable_expr is None:
        # Blur cố định toàn thời gian — đơn giản nhất, không cần enable
        parts = [
            "[0:v]split=2[base][src]",
            f"[src]crop=iw:{band_h}:0:{top_y},{blur_filter}[blurred]",
            f"[base][blurred]overlay=0:{top_y}[vout]",
        ]
    else:
        parts = [
            "[0:v]split=2[base][src]",
            f"[src]crop=iw:{band_h}:0:{top_y},{blur_filter}[blurred]",
            f"[base][blurred]overlay=0:{top_y}:enable='({enable_expr})'[vout]",
        ]
    return ";".join(parts), "[vout]"


def _build_blackbar_filter(events: list) -> tuple[str, str]:
    """Xây dựng filter blackbar hiệu quả.

    Nhóm events theo vùng (top_y, height), gộp intervals liền kề, tạo 1 drawbox
    per nhóm vùng.  Nếu intervals quá nhiều (> _MAX_BETWEEN_TERMS) → drawbox toàn
    thời gian (không dùng enable=).
    """
    groups: dict[tuple, list] = {}
    for event in events:
        key = (int(event["top_y"]), int(event["height"]))
        groups.setdefault(key, []).append(event)

    parts = []
    prev_label = "[0:v]"
    for idx, ((top_y, height), grp_events) in enumerate(groups.items(), 1):
        out_label = f"[v{idx}]"
        intervals = _merge_intervals(grp_events)
        enable_expr = _build_enable_expr(intervals)
        if enable_expr is None:
            parts.append(
                f"{prev_label}"
                f"drawbox=x=0:y={top_y}:w=iw:h={height}:color=black:t=fill"
                f"{out_label}"
            )
        else:
            parts.append(
                f"{prev_label}"
                f"drawbox=x=0:y={top_y}:w=iw:h={height}:"
                f"color=black:t=fill:enable='({enable_expr})'"
                f"{out_label}"
            )
        prev_label = out_label
    return ";".join(parts), prev_label


def _build_blur_filter(events: list, blur_power: int) -> tuple[str, str]:
    """Xây dựng filter blur hiệu quả.

    Chiến lược (theo thứ tự ưu tiên):
    1. Nhóm events theo vùng (top_y, bottom_y).
    2. Với mỗi nhóm, gộp các intervals liền kề để giảm số between().
    3. Nếu số between() <= _MAX_BETWEEN_TERMS → dùng enable expression.
    4. Nếu quá nhiều → blur toàn thời gian (không dùng enable=) — đơn giản,
       nhanh và không gây lỗi parser FFmpeg.  Chất lượng thực tế tương đương
       vì vùng sub nằm cố định cuối màn hình.
    """
    # --- Nhóm events theo vùng blur (top_y, bottom_y) ---
    groups: dict[tuple, list] = {}
    for event in events:
        key = (int(event["top_y"]), int(event["bottom_y"]), int(event["height"]))
        groups.setdefault(key, []).append(event)

    # Trường hợp phổ biến: 1 nhóm duy nhất
    if len(groups) == 1:
        (top_y, _bottom_y, band_h), grp_events = next(iter(groups.items()))
        intervals = _merge_intervals(grp_events)
        enable_expr = _build_enable_expr(intervals)
        return _blur_zone_filter(top_y, band_h, blur_power, enable_expr)

    # --- Nhiều nhóm vùng: 1 overlay per nhóm ---
    n_groups = len(groups)
    split_labels = "[base0]" + "".join(f"[src{i}]" for i in range(1, n_groups + 1))
    parts = [f"[0:v]split={n_groups + 1}{split_labels}"]
    base = "base0"

    for idx, ((top_y, _bottom_y, band_h), grp_events) in enumerate(groups.items(), 1):
        luma_r = min(25, max(1, (band_h - 1) // 2))
        chroma_r = min(25, max(1, (band_h // 2 - 1) // 2))
        blur_filter = (
            f"boxblur=luma_radius={luma_r}:luma_power={blur_power}:"
            f"chroma_radius={chroma_r}:chroma_power={blur_power}"
        )
        intervals = _merge_intervals(grp_events)
        enable_expr = _build_enable_expr(intervals)

        parts.append(
            f"[src{idx}]crop=iw:{band_h}:0:{top_y},{blur_filter}[blur{idx}]"
        )
        if enable_expr is None:
            parts.append(
                f"[{base}][blur{idx}]overlay=0:{top_y}[base{idx}]"
            )
        else:
            parts.append(
                f"[{base}][blur{idx}]overlay=0:{top_y}:"
                f"enable='({enable_expr})'[base{idx}]"
            )
        base = f"base{idx}"
    return ";".join(parts), f"[{base}]"

def _atempo_chain(speed: float) -> str:
    speed = max(0.5, min(100.0, float(speed)))
    parts = []
    while speed > 2.0:
        parts.append("atempo=2.0")
        speed /= 2.0
    while speed < 0.5:
        parts.append("atempo=0.5")
        speed /= 0.5
    parts.append(f"atempo={speed:.5f}")
    return ",".join(parts)

def _run_ff(cmd, log_cb=None) -> int:
    """Chạy ffmpeg, parse progress, trả về returncode. Raise RuntimeError nếu lỗi."""
    proc = subprocess.Popen(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        encoding="utf-8",
        errors="replace",
    )
    dur       = None
    err_lines = []
    for line in proc.stderr:
        err_lines.append(line.rstrip())
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", line)
        if m:
            h2, mi, s = m.groups()
            dur = int(h2)*3600 + int(mi)*60 + float(s)
        m2 = re.search(r"time=\s*(\d+):(\d+):(\d+\.\d+)", line)
        if m2 and dur:
            h2, mi, s = m2.groups()
            cur = int(h2)*3600 + int(mi)*60 + float(s)
            pct = min(cur / dur * 100, 100)
            if log_cb:
                log_cb(f"  Render: {pct:.1f}%")
    proc.wait()
    if proc.returncode != 0:
        tail = "\n".join(err_lines[-20:])
        raise RuntimeError(f"ffmpeg that bai! (code {proc.returncode})\n{tail}")
    return proc.returncode

def _copy_video_passthrough(src: Path, dst: Path, log_cb=None, video_speed: float = 1.0):
    """Copy video without re-encoding when no speed adjustment is required."""
    def _log(m): 
        if log_cb:
            log_cb(m)

    if abs(float(video_speed) - 1.0) > 0.001:
        raise ValueError("Passthrough chi hop le khi toc do video = 1.0")

    _log("->  Copy video (passthrough)...")
    ff = ffmpeg_cmd()
    cmd = [
        ff, "-y",
        "-i", str(src),
        "-c", "copy",
        "-movflags", "+faststart",
        str(dst),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    _log(f"✓  Video copied: {dst.stat().st_size/1024/1024:.1f} MB")

def _representative_band(events: list, frame_height: int) -> tuple[int, int]:
    tops = [int(event["top_y"]) for event in events]
    bottoms = [int(event["bottom_y"]) for event in events]
    top_y = int(statistics.median(tops))
    bottom_y = int(statistics.median(bottoms))
    if bottom_y <= top_y:
        top_y = min(tops)
        bottom_y = max(bottoms)
    top_y = max(0, min(top_y, frame_height - 2))
    bottom_y = max(top_y + 1, min(bottom_y, frame_height - 1))
    return top_y, bottom_y

def _expand_band_from_center(top_y: int, bottom_y: int, frame_height: int, padding_px: int, offset_px: int = 0) -> tuple[int, int]:
    center_y = (int(top_y) + int(bottom_y)) / 2.0
    base_height = max(2, int(bottom_y) - int(top_y) + 1)
    half_height = base_height / 2.0 + max(0, int(padding_px or 0))
    shift = max(-frame_height, min(frame_height, int(offset_px or 0)))
    new_top = max(0, int(round(center_y - half_height - shift)))
    new_bottom = min(frame_height - 1, int(round(center_y + half_height - shift)))
    if new_bottom <= new_top:
        new_bottom = min(frame_height - 1, new_top + 1)
    return new_top, new_bottom

def render_clean_video(
    src: Path,
    dst: Path,
    mode: str,
    events: list,
    log_cb: Optional[Callable[[str], None]] = None,
    blur_padding_px: int = 0,
    cover_offset_px: int = 0,
    blur_power: int = 4,
    video_speed: float = 1.0,
) -> Dict[str, Any]:
    """Render video with subtitle covering.
    
    Args:
        src: Source video path
        dst: Destination video path
        mode: Cover mode (none, blur, blackbar)
        events: List of subtitle events to cover
        log_cb: Logging callback
    
    Returns:
        Metadata dict with subtitle_top_y and other info
    """
    from .ffmpeg_wrapper import get_dims
    
    def _log(m): 
        if log_cb:
            log_cb(m)
    
    w, h = get_dims(src)
    orient = "Portrait" if h > w else "Landscape"
    meta = {
        "mode": mode,
        "video_speed": float(video_speed or 1.0),
        "applied": False,
        "subtitle_top_y": None,
        "subtitle_bottom_y": None,
        "cover_top_y": None,
        "cover_bottom_y": None,
        "region_count": 0,
    }

    speed = max(0.25, min(4.0, float(video_speed or 1.0)))

    if mode == "none" and abs(speed - 1.0) <= 0.001:
        _log(f"->  {w}x{h} ({orient}) | Giu nguyen sub goc, khong che.")
        _copy_video_passthrough(src, dst, log_cb, speed)
        meta["subtitle_top_y"] = None
        return meta

    effective_mode = mode
    normalized_events = []
    power = max(1, min(10, int(blur_power or 4)))
    pad = max(0, int(blur_padding_px or 0))

    if not events:
        if abs(speed - 1.0) <= 0.001:
            _log("->  Khong co doan nao can che. Giu nguyen video goc.")
            _copy_video_passthrough(src, dst, log_cb, speed)
            return meta
        _log("->  Khong co doan nao can che. Chi doi toc do video/audio.")
        effective_mode = "none"
        meta["subtitle_top_y"] = None
    else:
        subtitle_top_y, subtitle_bottom_y = _representative_band(events, h)
        cover_top_y, cover_bottom_y = _expand_band_from_center(
            subtitle_top_y,
            subtitle_bottom_y,
            h,
            pad,
            cover_offset_px,
        )
        for event in events:
            normalized_events.append({
                **event,
                "top_y": cover_top_y,
                "bottom_y": cover_bottom_y,
                "height": max(2, cover_bottom_y - cover_top_y + 1),
            })
        meta.update({
            "applied": True,
            "subtitle_top_y": subtitle_top_y,
            "subtitle_bottom_y": subtitle_bottom_y,
            "cover_top_y": cover_top_y,
            "cover_bottom_y": cover_bottom_y,
            "region_count": len(normalized_events),
            "blur_padding_px": pad,
            "cover_offset_px": int(cover_offset_px or 0),
            "blur_power": power,
        })

    nvenc = _has_nvenc()
    _log(
        f"->  {w}x{h} ({orient}) | {len(normalized_events)} doan co sub cu | "
        f"che theo mode {effective_mode.upper()}"
    )
    if abs(speed - 1.0) > 0.001:
        _log(f"->  Toc do video output = {speed:.2f}x")
    if effective_mode == "blur":
        _log(f"->  Độ mờ={power} | Nới quanh tâm sub cũ={pad}px | Đẩy vùng che lên={int(cover_offset_px or 0)}px")

    temp_script_path = None
    def _make_cmd(use_nvenc: bool) -> tuple[list, str]:
        nonlocal temp_script_path
        enc_args, label = _build_enc_args(use_nvenc)
        ff = ffmpeg_cmd()
        if effective_mode == "none":
            filter_complex = f"[0:v]setpts=PTS/{speed:.6f}[vout];[0:a]{_atempo_chain(speed)}[aout]"
            output_label = "[vout]"
        elif effective_mode == "blackbar":
            filter_complex, output_label = _build_blackbar_filter(normalized_events)
        else:
            filter_complex, output_label = _build_blur_filter(normalized_events, power)
        if effective_mode != "none" and abs(speed - 1.0) > 0.001:
            filter_complex = (
                f"{filter_complex};"
                f"{output_label}setpts=PTS/{speed:.6f}[vout];"
                f"[0:a]{_atempo_chain(speed)}[aout]"
            )
            output_label = "[vout]"
            
        if len(filter_complex) > 8000:
            if not temp_script_path:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                    f.write(filter_complex)
                    temp_script_path = f.name
            cmd = [
                ff, "-y",
                "-i", str(src),
                "-filter_complex_script", temp_script_path,
                "-map", output_label,
                "-map", "[aout]" if abs(speed - 1.0) > 0.001 or effective_mode == "none" else "0:a?",
                *enc_args,
                "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart",
                str(dst),
            ]
        else:
            cmd = [
                ff, "-y",
                "-i", str(src),
                "-filter_complex", filter_complex,
                "-map", output_label,
                "-map", "[aout]" if abs(speed - 1.0) > 0.001 or effective_mode == "none" else "0:a?",
                *enc_args,
                "-c:a", "aac", "-b:a", "192k",
                "-movflags", "+faststart",
                str(dst),
            ]
        return cmd, label

    for attempt_nvenc in ([True, False] if nvenc else [False]):
        cmd, label = _make_cmd(attempt_nvenc)
        _log(f"->  Encoder: {label}")
        _log("->  Dang render video clean...")
        try:
            _run_ff(cmd, log_cb)
            _log(f"✓  Video ready: {dst.stat().st_size/1024/1024:.1f} MB")
            return meta
        except RuntimeError as e:
            if attempt_nvenc:
                _log("⚠  NVENC that bai, chuyen sang CPU...")
                _log(f"   Chi tiet: {str(e)[:220]}")
                dst.unlink(missing_ok=True)
                continue
            raise

    raise RuntimeError("Khong the render video (ca NVENC lan CPU deu that bai).")
