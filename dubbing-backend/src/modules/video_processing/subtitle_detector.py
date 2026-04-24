"""Subtitle detection in video frames."""
import subprocess
from pathlib import Path
from typing import Optional, Callable, List, Dict

from .ffmpeg_wrapper import ffmpeg_cmd, probe_duration

def _pick_cover_sample_interval(duration: float) -> float:
    if duration <= 30:
        interval = 0.20
    elif duration <= 90:
        interval = 0.25
    elif duration <= 180:
        interval = 0.33
    elif duration <= 420:
        interval = 0.50
    else:
        interval = 0.75
    if duration > 0:
        interval = max(interval, duration / 900)
    return interval

def _group_rows(rows, gap=8):
    if not rows:
        return []
    groups = [[rows[0]]]
    for row in rows[1:]:
        if row - groups[-1][-1] <= gap:
            groups[-1].append(row)
        else:
            groups.append([row])
    return groups

def _analyze_sub_band(pixels: bytes, w: int, h: int, search_h: int, y_off: int) -> dict | None:
    """
    Phan tich 1 mau grayscale o 40% duoi khung hinh.
    Tra ve band sub cu theo dang {top_y, bottom_y, height} neu co.
    """
    if len(pixels) != w * search_h:
        return None

    row_avg = []
    for row in range(search_h):
        chunk = pixels[row * w:(row + 1) * w]
        row_avg.append(sum(chunk) / w)

    mean = sum(row_avg) / max(len(row_avg), 1)
    std = (sum((val - mean) ** 2 for val in row_avg) / max(len(row_avg), 1)) ** 0.5
    bright_thresh = mean + max(std * 1.35, 12)
    gradient_thresh = max(std * 1.05, 16)

    candidates = set()
    for row, avg in enumerate(row_avg):
        if avg >= bright_thresh:
            candidates.add(row)
    for row in range(1, search_h - 1):
        grad = abs(row_avg[row] - row_avg[row - 1]) + abs(row_avg[row] - row_avg[row + 1])
        if grad >= gradient_thresh:
            candidates.add(row)

    clusters = _group_rows(sorted(candidates), gap=8)
    valid = [
        cluster for cluster in clusters
        if (cluster[-1] - cluster[0] + 1) >= 4
        and cluster[0] / max(search_h, 1) >= 0.22
    ]
    if not valid:
        return None

    bottom_anchor = max(cluster[-1] for cluster in valid)
    active = [
        cluster for cluster in valid
        if bottom_anchor - cluster[-1] <= 28
    ]
    top_row = min(cluster[0] for cluster in active)
    bottom_row = max(cluster[-1] for cluster in active)

    top_y = max(0, y_off + top_row - 6)
    bottom_y = min(h - 1, y_off + bottom_row + 10)
    band_h = bottom_y - top_y + 1

    if band_h < 18 or band_h > int(h * 0.28):
        return None

    return {
        "top_y": top_y,
        "bottom_y": bottom_y,
        "height": band_h,
    }

def _merge_sub_events(samples: list, duration: float, interval: float, h: int) -> list:
    if not samples:
        return []

    y_tolerance = max(18, int(h * 0.03))
    merged = []
    for sample in samples:
        sample = dict(sample)
        sample["hits"] = 1
        if not merged:
            merged.append(sample)
            continue

        last = merged[-1]
        gap = sample["start"] - last["end"]
        same_zone = (
            abs(sample["top_y"] - last["top_y"]) <= y_tolerance
            or abs(sample["bottom_y"] - last["bottom_y"]) <= y_tolerance
        )
        if gap <= interval * 1.8 and same_zone:
            last["start"] = min(last["start"], sample["start"])
            last["end"] = max(last["end"], sample["end"])
            last["top_y"] = min(last["top_y"], sample["top_y"])
            last["bottom_y"] = max(last["bottom_y"], sample["bottom_y"])
            last["hits"] += 1
            last["height"] = last["bottom_y"] - last["top_y"] + 1
        else:
            merged.append(sample)

    compact = []
    for event in merged:
        event["start"] = max(0.0, event["start"] - interval * 0.45)
        event["end"] = min(duration, event["end"] + interval * 0.45)
        event["height"] = event["bottom_y"] - event["top_y"] + 1
        if event["height"] < 18:
            continue
        if (event["end"] - event["start"]) < max(interval * 0.60, 0.12):
            continue
        compact.append(event)

    final = []
    for event in compact:
        if final:
            prev = final[-1]
            if (
                event["start"] <= prev["end"] + interval * 0.35
                and abs(event["top_y"] - prev["top_y"]) <= y_tolerance
            ):
                prev["end"] = max(prev["end"], event["end"])
                prev["top_y"] = min(prev["top_y"], event["top_y"])
                prev["bottom_y"] = max(prev["bottom_y"], event["bottom_y"])
                prev["hits"] += event["hits"]
                prev["height"] = prev["bottom_y"] - prev["top_y"] + 1
                continue
        final.append(dict(event))
    return final

def detect_sub_events(src: Path, w: int, h: int, log_cb: Optional[Callable[[str], None]] = None) -> List[Dict[str, float]]:
    """Detect original subtitle regions in video using frame analysis.

    Samples video frames at intervals and analyzes brightness patterns to identify
    subtitle regions. Returns time ranges where subtitles appear with their vertical positions.

    Args:
        src: Path to source video file
        w: Video width in pixels
        h: Video height in pixels
        log_cb: Optional callback function for logging progress

    Returns:
        List of subtitle events, each containing:
            - start: Start time in seconds
            - end: End time in seconds
            - top_y: Top Y coordinate of subtitle region
            - bottom_y: Bottom Y coordinate of subtitle region
            - height: Height of subtitle region in pixels

    Raises:
        RuntimeError: If frame extraction fails
    """
    def _log(m): log_cb and log_cb(m)

    duration = probe_duration(src)
    if duration <= 0:
        _log("->  Khong doc duoc thoi luong video, bo qua che sub thong minh.")
        return []

    t_start = max(0.0, duration * 0.03)
    t_end = max(t_start + 0.5, duration * 0.97)
    scan_dur = max(0.5, t_end - t_start)
    interval = _pick_cover_sample_interval(scan_dur)
    search_h = max(32, int(h * 0.40))
    y_off = h - search_h
    ff = ffmpeg_cmd()

    est_samples = max(1, int(scan_dur / interval))
    _log(f"->  Quet sub cu moi {interval:.2f}s (~{est_samples} mau)...")

    cmd = [
        ff,
        "-v", "error",
        "-ss", f"{t_start:.3f}",
        "-i", str(src),
        "-t", f"{scan_dur:.3f}",
        "-vf", f"fps=1/{interval:.6f},scale={w}:{h},crop={w}:{search_h}:0:{y_off},format=gray",
        "-f", "rawvideo",
        "pipe:1",
    ]
    timeout_s = max(90, int(scan_dur * 3))
    ret = subprocess.run(cmd, capture_output=True, timeout=timeout_s)
    if ret.returncode != 0:
        raise RuntimeError("Khong the quet frame de detect sub cu.")

    frame_size = w * search_h
    raw = ret.stdout
    frame_count = len(raw) // frame_size
    if frame_count <= 0:
        _log("->  Khong lay duoc mau frame nao de detect sub cu.")
        return []

    samples = []
    for idx in range(frame_count):
        begin = idx * frame_size
        pixels = raw[begin:begin + frame_size]
        band = _analyze_sub_band(pixels, w, h, search_h, y_off)
        if not band:
            continue
        start_t = min(duration, t_start + idx * interval)
        end_t = min(duration, start_t + interval)
        samples.append({
            "start": start_t,
            "end": end_t,
            **band,
        })

    if not samples:
        _log("->  Khong tim thay frame nao co sub cu. Video se duoc giu nguyen.")
        return []

    events = _merge_sub_events(samples, duration, interval, h)
    if len(events) > 140:
        _log("->  Qua nhieu doan sub, dang gop lai de render on dinh...")
        events = _merge_sub_events(events, duration, interval * 1.5, h)

    hit_ratio = len(samples) / max(frame_count, 1) * 100
    _log(
        f"->  Detect duoc {len(events)} doan sub | "
        f"{len(samples)}/{frame_count} frame co chu ({hit_ratio:.0f}%)"
    )
    return events

