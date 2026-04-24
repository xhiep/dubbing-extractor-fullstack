"""TTS endpoints."""
import logging
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from ..core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class TTSStatusRequest(BaseModel):
    engine_mode: str = "turbo"
    backbone_repo: str = ""
    backbone_device: str = ""
    remote_api_base: str = "http://localhost:23333/v1"


class TTSTestRequest(BaseModel):
    text: str
    mode: str = "preset"
    preset_voice: str = ""
    ref_audio: str = ""
    ref_text: str = ""
    engine_mode: str = "turbo"
    backbone_repo: str = ""
    backbone_device: str = ""
    remote_api_base: str = "http://localhost:23333/v1"


def _resolve_ref_audio_path(raw_path: str) -> Path:
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        candidate = (settings.BASE_DIR / candidate).resolve()
    else:
        candidate = candidate.resolve()
    return candidate


def _is_allowed_ref_audio_path(path: Path) -> bool:
    allowed_roots = [
        settings.REF_AUDIO_DIR.resolve(),
    ]
    return any(str(path).startswith(str(root)) for root in allowed_roots)


@router.post("/status")
async def check_tts_status(request: TTSStatusRequest):
    """Check if VieNeu-TTS is available."""
    try:
        import sys
        backend_dir = Path(__file__).parent.parent.parent.parent
        sys.path.insert(0, str(backend_dir))

        from src.modules.tts import is_vieneu_available, get_vieneu_error

        available = is_vieneu_available(
            engine_mode=request.engine_mode,
            backbone_repo=request.backbone_repo,
            backbone_device=request.backbone_device,
            remote_api_base=request.remote_api_base,
        )

        error = ""
        if not available:
            error = get_vieneu_error(
                engine_mode=request.engine_mode,
                backbone_repo=request.backbone_repo,
                backbone_device=request.backbone_device,
                remote_api_base=request.remote_api_base,
            )

        return {
            "available": available,
            "error": error,
        }
    except Exception as e:
        logger.error(f"Failed to check TTS status: {e}")
        return {
            "available": False,
            "error": str(e),
        }


@router.get("/voices")
async def list_voices(
    engine_mode: str = "turbo",
    backbone_repo: str = "",
    backbone_device: str = "",
    remote_api_base: str = "http://localhost:23333/v1",
):
    """List available preset voices."""
    try:
        import sys
        backend_dir = Path(__file__).parent.parent.parent.parent
        sys.path.insert(0, str(backend_dir))

        from src.modules.tts import list_preset_voices

        voices = list_preset_voices(
            engine_mode=engine_mode,
            backbone_repo=backbone_repo,
            backbone_device=backbone_device,
            remote_api_base=remote_api_base,
        )

        return {"voices": voices}
    except Exception as e:
        logger.error(f"Failed to list voices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test_tts(request: TTSTestRequest):
    """Test TTS with sample text."""
    try:
        import sys
        backend_dir = Path(__file__).parent.parent.parent.parent
        sys.path.insert(0, str(backend_dir))

        from src.modules.tts import synthesize_speech
        from src.modules.video_processing.ffmpeg_wrapper import probe_duration

        # Generate unique filename
        audio_id = str(uuid.uuid4())
        audio_path = settings.TEMP_DIR / f"tts_test_{audio_id}.wav"

        # Synthesize speech
        synthesize_speech(
            text=request.text,
            out_path=audio_path,
            mode=request.mode,
            preset_voice=request.preset_voice,
            ref_audio=request.ref_audio,
            ref_text=request.ref_text,
            engine_mode=request.engine_mode,
            backbone_repo=request.backbone_repo,
            backbone_device=request.backbone_device,
            remote_api_base=request.remote_api_base,
        )

        # Get duration
        duration = probe_duration(audio_path)

        return {
            "audio_url": f"/api/tts/audio/{audio_id}",
            "duration": duration,
        }
    except Exception as e:
        logger.error(f"Failed to test TTS: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audio/{audio_id}")
async def get_audio(audio_id: str):
    """Get TTS test audio file."""
    audio_path = settings.TEMP_DIR / f"tts_test_{audio_id}.wav"

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        path=str(audio_path),
        media_type="audio/wav",
        filename=f"tts_test.wav",
    )


@router.post("/upload-ref-audio")
async def upload_ref_audio(file: UploadFile = File(...)):
    """Upload reference audio file for voice cloning."""
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail="File must be an audio file")

        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_ext = Path(file.filename).suffix if file.filename else ".wav"
        audio_path = settings.REF_AUDIO_DIR / f"ref_audio_{file_id}{file_ext}"

        # Save uploaded file
        content = await file.read()
        audio_path.write_bytes(content)

        logger.info(f"Uploaded reference audio: {audio_path}")

        return {
            "file_path": str(audio_path),
            "file_id": file_id,
            "filename": file.filename,
        }
    except Exception as e:
        logger.error(f"Failed to upload reference audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ref-audio-status")
async def get_ref_audio_status(path: str):
    """Check whether a persisted reference audio path still exists."""
    try:
        resolved_path = _resolve_ref_audio_path(path)
        exists = resolved_path.exists() and resolved_path.is_file()
        allowed = _is_allowed_ref_audio_path(resolved_path)

        return {
            "path": str(resolved_path),
            "exists": bool(exists and allowed),
            "allowed": allowed,
        }
    except Exception as e:
        logger.error(f"Failed to check reference audio status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
