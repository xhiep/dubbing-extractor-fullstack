"""Text-to-speech modules."""
from .vieneu_engine import (
    is_vieneu_available,
    get_vieneu_error,
    list_preset_voices,
    release_tts_resources,
    synthesize_speech,
)
from .audio_dubber import render_dubbed_outputs

__all__ = [
    "is_vieneu_available",
    "get_vieneu_error",
    "list_preset_voices",
    "release_tts_resources",
    "synthesize_speech",
    "render_dubbed_outputs",
]
