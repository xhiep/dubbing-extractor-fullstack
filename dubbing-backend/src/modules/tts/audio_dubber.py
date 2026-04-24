"""Audio dubbing helpers using FFmpeg + VieNeu-TTS."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional, Callable, Dict, List

from ..video_processing.ffmpeg_wrapper import ffmpeg_cmd, probe_duration
from .vieneu_engine import synthesize_speech


def _log(log_cb, msg: str):
    if log_cb:
        log_cb(msg)


def _run(cmd: list[str], log_cb=None):
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-1200:]
        raise RuntimeError(f"FFmpeg loi:\n{tail}")
    return proc


def _atempo_chain(speed: float) -> str:
    speed = max(0.5, min(100.0, speed))
    parts = []
    while speed > 2.0:
        parts.append("atempo=2.0")
        speed /= 2.0
    while speed < 0.5:
        parts.append("atempo=0.5")
        speed /= 0.5
    parts.append(f"atempo={speed:.5f}")
    return ",".join(parts)


def _fit_segment_duration(src: Path, dst: Path, target_duration: float, log_cb=None) -> Path:
    if target_duration <= 0.05:
        shutil.copy2(src, dst)
        return dst

    current = max(0.01, probe_duration(src))
    speed = current / target_duration
    filters = []
    if speed < 0.96 or speed > 1.04:
        filters.append(_atempo_chain(speed))
    filters.append("apad")
    filters.append(f"atrim=0:{target_duration:.3f}")
    cmd = [
        ffmpeg_cmd(), "-y",
        "-i", str(src),
        "-filter:a", ",".join(filters),
        "-ar", "24000",
        "-ac", "1",
        str(dst),
    ]
    _run(cmd, log_cb)
    return dst


def _build_dub_track(segment_files: list[tuple[Path, float]], total_duration: float, out_path: Path, log_cb=None) -> Path:
    ff = ffmpeg_cmd()
    cmd = [
        ff,
        "-y",
        "-f", "lavfi",
        "-i", "anullsrc=r=24000:cl=mono",
    ]
    for path, _start in segment_files:
        cmd.extend(["-i", str(path)])

    mix_inputs = ["[0:a]"]
    filters = []
    for idx, (_path, start_sec) in enumerate(segment_files, start=1):
        delay_ms = max(0, int(round(start_sec * 1000)))
        filters.append(f"[{idx}:a]adelay={delay_ms}|{delay_ms}[seg{idx}]")
        mix_inputs.append(f"[seg{idx}]")
    filters.append(
        "".join(mix_inputs) +
        f"amix=inputs={len(mix_inputs)}:duration=longest:dropout_transition=0:normalize=0,"
        f"atrim=0:{max(total_duration, 0.1):.3f}[aout]"
    )
    cmd.extend([
        "-filter_complex", ";".join(filters),
        "-map", "[aout]",
        "-ar", "24000",
        "-ac", "1",
        str(out_path),
    ])
    _run(cmd, log_cb)
    return out_path


def _volume_filter(volume: float) -> str:
    volume = max(0.0, float(volume))
    if abs(volume - 1.0) < 0.001:
        return "anull"
    return f"volume={volume:.3f}"


def _mux_dubbed_video(
    video_path: Path,
    dub_track: Path,
    out_path: Path,
    source_volume: float,
    dub_volume: float,
    log_cb=None,
) -> Path:
    ff = ffmpeg_cmd()
    source_volume = max(0.0, min(1.0, float(source_volume)))
    source_filter = _volume_filter(source_volume)
    dub_filter = _volume_filter(dub_volume)
    cmd = [
        ff,
        "-y",
        "-i", str(video_path),
        "-i", str(dub_track),
        "-filter_complex",
        (
            f"[0:a]{source_filter}[orig];"
            f"[1:a]{dub_filter}[dub];"
            f"[orig][dub]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[aout]"
        ),
        "-map", "0:v:0",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(out_path),
    ]
    _run(cmd, log_cb)
    return out_path


def render_dubbed_outputs(
    video_path: Path,
    segments: list[dict],
    out_dir: Path,
    mode: str,
    engine_mode: str,
    remote_api_base: str,
    preset_voice: str,
    ref_audio: str,
    ref_text: str,
    dub_volume: float = 1.35,
    source_volume: float = 0.18,
    mix_mode: str = "nen_nho",
    output_video_name: str = "video_long_tieng.mp4",
    log_cb: Optional[Callable[[str], None]] = None,
) -> Dict[str, Path]:
    """Render dubbed video with Vietnamese TTS audio mixed with original.

    Synthesizes speech for each subtitle segment, adjusts timing to match segment
    duration, builds a complete dubbed audio track, and mixes it with the original
    video audio at specified volume levels.

    Args:
        video_path: Path to source video file
        segments: List of subtitle segments with text and timing
        out_dir: Output directory for dubbed files
        mode: Voice mode (preset or clone)
        engine_mode: TTS backend mode (turbo, turbo_gpu, fast, remote)
        remote_api_base: API base URL for remote mode
        preset_voice: Name of preset voice
        ref_audio: Path to reference audio for voice cloning
        ref_text: Reference text for voice cloning
        dub_volume: Dubbed voice volume multiplier
        source_volume: Original audio volume multiplier
        mix_mode: Mixing mode (nen_nho keeps original, tat_goc mutes it)
        output_video_name: Output video filename
        log_cb: Optional callback function for logging progress

    Returns:
        Dictionary containing:
            - dub_track: Path to dubbed audio track (WAV)
            - dub_video: Path to final dubbed video (MP4)

    Raises:
        ValueError: If no segments provided
        RuntimeError: If TTS synthesis or FFmpeg mixing fails
    """
    if not segments:
        raise ValueError("Khong co cau dich de long tieng.")

    ff = ffmpeg_cmd()
    if not ff:
        raise RuntimeError("Khong tim thay ffmpeg de long tieng.")

    dub_dir = out_dir / "dub_segments"
    dub_dir.mkdir(parents=True, exist_ok=True)
    placements: list[tuple[Path, float]] = []
    for index, seg in enumerate(segments, start=1):
        text = " ".join((seg.get("text") or "").split())
        if not text:
            continue
        start = float(seg.get("start", 0.0) or 0.0)
        end = max(start + 0.1, float(seg.get("end", 0.0) or 0.0))
        raw_wav = dub_dir / f"seg_{index:04d}_raw.wav"
        fit_wav = dub_dir / f"seg_{index:04d}.wav"
        _log(log_cb, f"->  TTS cau {index}/{len(segments)}")
        synthesize_speech(
            text=text,
            out_path=raw_wav,
            mode=mode,
            engine_mode=engine_mode,
            remote_api_base=remote_api_base,
            preset_voice=preset_voice,
            ref_audio=ref_audio,
            ref_text=ref_text,
            log_cb=log_cb,
        )
        _fit_segment_duration(raw_wav, fit_wav, end - start, log_cb)
        placements.append((fit_wav, start))

    if not placements:
        raise RuntimeError("VieNeu khong tao duoc doan audio nao.")

    total_duration = max(probe_duration(video_path), max(start + probe_duration(path) for path, start in placements))
    dub_track = out_dir / "audio_long_tieng.wav"
    dubbed_video = out_dir / output_video_name
    _log(log_cb, "->  Dang ghep track long tieng...")
    _build_dub_track(placements, total_duration, dub_track, log_cb)
    _log(log_cb, "->  Dang mux video long tieng...")
    final_source_volume = 0.0 if mix_mode == "tat_goc" else source_volume
    _mux_dubbed_video(video_path, dub_track, dubbed_video, final_source_volume, dub_volume, log_cb)
    return {
        "dub_track": dub_track,
        "dub_video": dubbed_video,
    }
