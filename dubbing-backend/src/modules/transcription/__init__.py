"""Transcription module."""
from .whisper_engine import transcribe
from .translator import translate
from .srt_generator import write_srt

__all__ = ["transcribe", "translate", "write_srt"]
