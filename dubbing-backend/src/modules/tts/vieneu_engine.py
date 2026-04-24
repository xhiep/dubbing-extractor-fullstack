"""VieNeu-TTS wrapper."""
from __future__ import annotations

import gc
import importlib
import logging
from pathlib import Path
from typing import Optional, Callable, List

logger = logging.getLogger(__name__)

from ...utils.runtime_env import ensure_local_runtime_env

ensure_local_runtime_env()

_TTS_CACHE: dict[tuple[str, str], object] = {}
_VOICE_CACHE: dict[tuple[str, str], object] = {}
_IMPORT_ERROR: Optional[str] = None

DEFAULT_ENGINE_MODE = "turbo"
DEFAULT_BACKBONE_REPO = ""
DEFAULT_BACKBONE_DEVICE = ""
DEFAULT_REMOTE_API_BASE = "http://localhost:23333/v1"


def release_tts_resources() -> None:
    """Release cached TTS engines and voices to free memory.

    Calls cleanup methods on cached engines, clears caches, and triggers
    garbage collection. Also empties CUDA cache if available.

    This function is safe to call multiple times and handles exceptions
    during cleanup to avoid masking original errors.
    """
    for engine in list(_TTS_CACHE.values()):
        for attr in ("close", "cleanup", "shutdown", "unload"):
            fn = getattr(engine, attr, None)
            if callable(fn):
                try:
                    fn()
                except Exception:
                    pass

    _TTS_CACHE.clear()
    _VOICE_CACHE.clear()
    gc.collect()

    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


def _import_vieneu():
    global _IMPORT_ERROR
    if _IMPORT_ERROR:
        raise RuntimeError(_IMPORT_ERROR)
    try:
        module = importlib.import_module("vieneu")
        return getattr(module, "Vieneu")
    except Exception as exc:
        _IMPORT_ERROR = str(exc)
        raise RuntimeError(_IMPORT_ERROR) from exc


def get_vieneu_error(
    engine_mode: str = DEFAULT_ENGINE_MODE,
    backbone_repo: str = DEFAULT_BACKBONE_REPO,
    backbone_device: str = DEFAULT_BACKBONE_DEVICE,
    remote_api_base: str = DEFAULT_REMOTE_API_BASE,
) -> str:
    try:
        _get_engine(engine_mode, backbone_repo, backbone_device, remote_api_base)
        return ""
    except Exception as exc:
        return str(exc)


def is_vieneu_available(
    engine_mode: str = DEFAULT_ENGINE_MODE,
    backbone_repo: str = DEFAULT_BACKBONE_REPO,
    backbone_device: str = DEFAULT_BACKBONE_DEVICE,
    remote_api_base: str = DEFAULT_REMOTE_API_BASE,
) -> bool:
    return not bool(get_vieneu_error(engine_mode, backbone_repo, backbone_device, remote_api_base))


def _build_engine_kwargs(
    engine_mode: str,
    backbone_repo: str,
    backbone_device: str,
    remote_api_base: str,
) -> dict:
    kwargs = {"mode": engine_mode or DEFAULT_ENGINE_MODE}
    mode = kwargs["mode"]

    if mode == "remote":
        kwargs["api_base"] = remote_api_base or DEFAULT_REMOTE_API_BASE
        if backbone_repo:
            kwargs["model_name"] = backbone_repo
        return kwargs

    if backbone_repo:
        kwargs["backbone_repo"] = backbone_repo
    if backbone_device:
        if mode in ("turbo", "turbo_gpu"):
            kwargs["device"] = backbone_device
        else:
            kwargs["backbone_device"] = backbone_device
    return kwargs


def _get_engine(
    engine_mode: str = DEFAULT_ENGINE_MODE,
    backbone_repo: str = DEFAULT_BACKBONE_REPO,
    backbone_device: str = DEFAULT_BACKBONE_DEVICE,
    remote_api_base: str = DEFAULT_REMOTE_API_BASE,
):
    import os
    if engine_mode == "fast" and os.name == "nt":
        raise RuntimeError("Backend 'fast' (LMDeploy) hiện tại không hỗ trợ tốt trên Windows do thiếu thư viện Triton/Triton compiler. Vui lòng chọn backend 'turbo_gpu' để tăng tốc độ trên Windows thay vì 'fast'.")

    key = (engine_mode, backbone_repo, backbone_device, remote_api_base)
    if key in _TTS_CACHE:
        return _TTS_CACHE[key]
    Vieneu = _import_vieneu()
    kwargs = _build_engine_kwargs(engine_mode, backbone_repo, backbone_device, remote_api_base)
    engine = Vieneu(**kwargs)
    _TTS_CACHE[key] = engine
    return engine


def list_preset_voices(
    engine_mode: str = DEFAULT_ENGINE_MODE,
    backbone_repo: str = DEFAULT_BACKBONE_REPO,
    backbone_device: str = DEFAULT_BACKBONE_DEVICE,
    remote_api_base: str = DEFAULT_REMOTE_API_BASE,
) -> List[str]:
    engine = _get_engine(engine_mode, backbone_repo, backbone_device, remote_api_base)
    try:
        voices = engine.list_preset_voices()
    except (AttributeError, RuntimeError) as e:
        logger.error(f"Could not list preset voices: {e}")
        voices = []
    result = []
    for voice in voices or []:
        if isinstance(voice, (list, tuple)) and len(voice) >= 2:
            name = str(voice[1])
        else:
            name = getattr(voice, "name", None) or str(voice)
        if name:
            result.append(name)
    return result


def synthesize_speech(
    text: str,
    out_path: Path,
    mode: str = "preset",
    preset_voice: str = "",
    ref_audio: str = "",
    ref_text: str = "",
    prepared_voice=None,
    engine_mode: str = DEFAULT_ENGINE_MODE,
    backbone_repo: str = DEFAULT_BACKBONE_REPO,
    backbone_device: str = DEFAULT_BACKBONE_DEVICE,
    remote_api_base: str = DEFAULT_REMOTE_API_BASE,
    log_cb: Optional[Callable[[str], None]] = None,
) -> Path:
    """Synthesize Vietnamese speech from text using VieNeu-TTS.

    Supports both preset voices and voice cloning from reference audio.
    Caches voice encodings to improve performance for repeated synthesis.

    Args:
        text: Text to synthesize (Vietnamese)
        out_path: Path where audio file will be saved
        mode: Voice mode (preset or clone)
        preset_voice: Name of preset voice to use
        ref_audio: Path to reference audio for voice cloning
        ref_text: Reference text for voice cloning
        prepared_voice: Pre-encoded voice object (optional)
        engine_mode: TTS backend mode (turbo, turbo_gpu, fast, remote)
        backbone_repo: Custom model repository path
        backbone_device: Device for model (cpu, cuda)
        remote_api_base: API base URL for remote mode
        log_cb: Optional callback function for logging progress

    Returns:
        Path to synthesized audio file

    Raises:
        ValueError: If text is empty
        FileNotFoundError: If reference audio file not found
        RuntimeError: If TTS synthesis fails
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("Text TTS dang rong.")

    def _log(msg):
        if log_cb:
            log_cb(msg)

    engine = _get_engine(engine_mode, backbone_repo, backbone_device, remote_api_base)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    voice = None
    kwargs = {}
    if prepared_voice is not None:
        voice = prepared_voice
    if mode == "clone":
        ref_audio_path = Path(ref_audio)
        if not ref_audio_path.exists():
            raise FileNotFoundError("Khong tim thay file audio mau de clone giong.")
        if voice is None:
            cache_key = (
                engine_mode,
                str(ref_audio_path.resolve()),
                backbone_repo or "default",
                remote_api_base or DEFAULT_REMOTE_API_BASE,
            )
            if cache_key not in _VOICE_CACHE:
                _VOICE_CACHE[cache_key] = engine.encode_reference(str(ref_audio_path))
            voice = _VOICE_CACHE[cache_key]
        _log(f"->  VieNeu clone giong tu: {ref_audio_path.name}")
        if ref_text.strip():
            kwargs["ref_text"] = ref_text.strip()
    else:
        if preset_voice:
            try:
                voice = engine.get_preset_voice(preset_voice)
            except Exception as exc:
                raise RuntimeError(f"Khong lay duoc giong mau '{preset_voice}': {exc}") from exc
            _log(f"->  VieNeu dung giong mau: {preset_voice}")

    audio = engine.infer(text=text, voice=voice, **kwargs)
    engine.save(audio, str(out_path))
    return out_path
