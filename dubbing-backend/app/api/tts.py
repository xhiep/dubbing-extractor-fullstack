"""TTS endpoints."""
import logging
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from ..models.schemas import TTSTestRequest, TTSTestResponse
from ..core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/test", response_model=TTSTestResponse)
async def test_tts(request: TTSTestRequest):
    """Test TTS voice with sample text."""
    try:
        # Import here to avoid circular dependency
        import sys
        backend_dir = Path(__file__).parent.parent.parent.parent
        sys.path.insert(0, str(backend_dir))

        from src.modules.tts.vieneu_engine import synthesize_speech

        # Generate unique filename
        audio_id = str(uuid.uuid4())
        audio_path = settings.TEMP_DIR / f"tts_test_{audio_id}.wav"

        # Synthesize speech
        synthesize_speech(
            text=request.text,
            output_path=str(audio_path),
            voice=request.voice,
        )

        # Get duration
        from src.modules.video_processing.ffmpeg_wrapper import probe_duration
        duration = probe_duration(str(audio_path))

        return TTSTestResponse(
            audio_url=f"/api/tts/audio/{audio_id}",
            duration=duration,
        )

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


@router.get("/voices")
async def list_voices():
    """List available TTS voices."""
    try:
        import sys
        from pathlib import Path
        backend_dir = Path(__file__).parent.parent.parent.parent
        sys.path.insert(0, str(backend_dir))

        from src.modules.tts.vieneu_engine import list_preset_voices

        voices = list_preset_voices()
        return {"voices": voices}

    except Exception as e:
        logger.error(f"Failed to list voices: {e}")
        raise HTTPException(status_code=500, detail=str(e))
