"""Whisper transcription engine with explicit resource cleanup between runs."""
import gc
import logging
import os
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
from contextlib import contextmanager

import torch
import whisper

logger = logging.getLogger(__name__)

from ...config import config
from ..video_processing.ffmpeg_wrapper import LOCAL_FFMPEG

_active_model = None


@contextmanager
def managed_whisper_model(model_name: str, device: str):
    """Load and automatically cleanup Whisper model.

    Ensures model is properly unloaded even if transcription fails.
    Moves model to CPU, deletes reference, and clears caches on exit.

    Args:
        model_name: Whisper model size (tiny/base/small/medium/large)
        device: Device to load on (cpu/cuda)

    Yields:
        Loaded Whisper model instance

    Example:
        with managed_whisper_model("base", "cuda") as model:
            result = model.transcribe("audio.wav")
    """
    model = None
    try:
        logger.info(f"Loading Whisper {model_name} on {device}")
        model = whisper.load_model(model_name, device=device)
        yield model
    finally:
        if model is not None:
            logger.info("Cleaning up Whisper model")
            try:
                model.cpu()
            except Exception as e:
                logger.warning(f"Error moving model to CPU: {e}")
            del model
            gc.collect()
            if device == "cuda":
                try:
                    torch.cuda.empty_cache()
                except Exception:
                    pass


def _detect_unstable_cuda_reason() -> str | None:
    """Return a reason when CUDA should be avoided for Whisper on this machine."""
    if not torch.cuda.is_available():
        return None

    try:
        gpu_name = torch.cuda.get_device_name(0)
    except Exception:
        gpu_name = ""

    try:
        capability = torch.cuda.get_device_capability(0)
    except Exception:
        capability = None

    gpu_name_upper = gpu_name.upper()
    if "RTX 50" in gpu_name_upper or "RTX 5060" in gpu_name_upper:
        return f"GPU {gpu_name} chua on dinh voi Whisper CUDA tren ban PyTorch hien tai"
    if capability and capability[0] >= 12:
        return f"GPU compute capability sm_{capability[0]}{capability[1]} chua duoc ho tro on dinh"
    return None


def _get_device() -> tuple[str, bool, str | None]:
    """Return the preferred Whisper device, fp16 flag, and optional fallback reason."""
    unstable_reason = _detect_unstable_cuda_reason()
    if torch.cuda.is_available() and not unstable_reason:
        return "cuda", True, None
    if unstable_reason:
        return "cpu", False, unstable_reason
    return "cpu", False


def _load_model(model_name: str, device: str):
    """Load a Whisper model after dropping any stale instance first."""
    global _active_model
    _unload_model()
    _active_model = whisper.load_model(model_name, device=device)
    return _active_model


def _unload_model():
    """Explicitly free the active Whisper model from RAM/VRAM."""
    global _active_model
    if _active_model is not None:
        try:
            _active_model.cpu()
        except Exception:
            pass
        _active_model = None
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _is_oom_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return (
        "out of memory" in text
        or "not enough memory" in text
        or "defaultcpuallocator" in text
        or "cuda out of memory" in text
    )


def _run_transcription(audio: Path, model_name: str, device: str, use_fp16: bool, log_cb=None) -> list:
    def _log(message):
        if log_cb:
            log_cb(message)

    if device == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        _log(f"->  GPU detected: {gpu_name}")
        torch.cuda.empty_cache()
    else:
        _log("->  Chay Whisper tren CPU")

    _log(f"->  Tai Whisper [{model_name}] tren {device.upper()}...")

    with managed_whisper_model(model_name, device) as model:
        _log("->  Model san sang. Dang nhan dang...")

        kwargs = {"verbose": False, "task": "transcribe", "fp16": use_fp16}
        if config["source_language"]:
            kwargs["language"] = config["source_language"]

        result = model.transcribe(str(audio), **kwargs)
        segments = result.get("segments", [])
        _log(f"->  {len(segments)} cau | ngon ngu: {result.get('language', '?')}")
        return segments


def transcribe(audio: Path, log_cb: Optional[Callable[[str], None]] = None) -> List[Dict[str, Any]]:
    """Transcribe audio file using Whisper speech recognition.

    Automatically selects optimal device (CUDA or CPU) based on hardware compatibility.
    Falls back to CPU if CUDA runs out of memory. Cleans up model resources after completion.

    Args:
        audio: Path to audio file (MP3, WAV, etc.)
        log_cb: Optional callback function for logging progress

    Returns:
        List of transcription segments, each containing:
            - start: Start time in seconds
            - end: End time in seconds
            - text: Transcribed text
            - id: Segment ID

    Raises:
        RuntimeError: If transcription fails on both CUDA and CPU
    """
    def _log(message):
        if log_cb:
            log_cb(message)

    if LOCAL_FFMPEG.exists():
        ffmpeg_dir = str(LOCAL_FFMPEG.parent)
        path_parts = os.environ.get("PATH", "").split(os.pathsep)
        if ffmpeg_dir not in path_parts:
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

    model_name = config["whisper_model"]
    device_info = _get_device()
    if len(device_info) == 3:
        device, use_fp16, fallback_reason = device_info
    else:
        device, use_fp16 = device_info
        fallback_reason = None

    if fallback_reason:
        _log(f"->  Bo qua CUDA: {fallback_reason}")

    try:
        return _run_transcription(audio, model_name, device, use_fp16, log_cb)
    except RuntimeError as exc:
        if device == "cuda" and _is_oom_error(exc):
            _log("! Whisper het bo nho tren CUDA. Thu lai tren CPU de tranh vo ung dung...")
            _unload_model()
            return _run_transcription(audio, model_name, "cpu", False, log_cb)
        raise
    finally:
        _unload_model()
