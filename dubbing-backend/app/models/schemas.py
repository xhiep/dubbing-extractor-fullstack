"""Pydantic models for API request/response."""
from typing import Optional, Literal
from pydantic import BaseModel, Field


# ── Request Models ────────────────────────────────────────────

class ProcessRequest(BaseModel):
    """Request to start video processing."""
    source: str = Field(..., description="Video URL or local file path")
    mode: Literal["monolithic", "step-by-step"] = "monolithic"

    # Whisper options
    whisper_model: str = "medium"
    whisper_language: Optional[str] = None

    # Cover options
    cover_mode: Literal["blur", "blackbar", "none"] = "blur"
    cover_strength: int = 15

    # Subtitle options
    burn_subtitle: bool = True
    srt_max_chars_per_line: int = 45
    subtitle_font_scale: float = 1.0
    subtitle_font_size: int = 0
    subtitle_margin_px: int = 0
    subtitle_timing_scale: float = 1.0
    subtitle_offset_sec: float = 0.0

    # Cover geometry
    blur_padding_px: int = 12
    cover_offset_px: int = 0

    # TTS options
    enable_dubbing: bool = False
    tts_voice: str = "female_north"

    # Video options
    video_speed: float = 1.0
    output_format: str = "mp4"


class StepRequest(BaseModel):
    """Request to run a single step."""
    task_id: str
    step_data: dict = Field(default_factory=dict)


class PreviewRequest(BaseModel):
    """Request to get video preview info."""
    source: str


class PreviewRenderRequest(BaseModel):
    """Request to render a preview video with blur + subtitle."""
    source: str
    start_time: float = Field(default=10.0, description="Start time in seconds")
    duration: float = Field(default=15.0, description="Duration in seconds (max 30)")
    preview_text: str = Field(default="", description="Sample subtitle text to burn into preview")
    cover_mode: Literal["blur", "blackbar", "none"] = "blur"
    cover_strength: int = 15
    burn_subtitle: bool = True
    subtitle_font_scale: float = 1.0
    subtitle_font_size: int = 0
    subtitle_margin_px: int = 0
    srt_max_chars_per_line: int = 45
    blur_padding_px: int = 12
    cover_offset_px: int = 0
    video_speed: float = 1.0


class TTSTestRequest(BaseModel):
    """Request to test TTS voice."""
    text: str = Field(..., max_length=500)
    voice: str = "female_north"


# ── Response Models ───────────────────────────────────────────

class TaskResponse(BaseModel):
    """Response after starting a task."""
    task_id: str
    status: Literal["queued", "running", "completed", "failed"]
    message: str = ""


class StatusResponse(BaseModel):
    """Task status response."""
    task_id: str
    status: Literal["queued", "running", "completed", "failed"]
    current_step: int = 0
    progress: float = 0.0
    message: str = ""
    outputs: dict = Field(default_factory=dict)
    error: Optional[str] = None


class PreviewResponse(BaseModel):
    """Video preview info response."""
    title: str
    duration: float
    thumbnail: Optional[str] = None
    platform: str
    width: int = 0
    height: int = 0


class PreviewRenderResponse(BaseModel):
    """Preview render response."""
    video_url: str
    duration: float
    width: int
    height: int


class TTSTestResponse(BaseModel):
    """TTS test response."""
    audio_url: str
    duration: float


# ── WebSocket Events ──────────────────────────────────────────

class ProgressEvent(BaseModel):
    """Progress update event."""
    task_id: str
    step: int
    progress: float
    message: str


class LogEvent(BaseModel):
    """Log message event."""
    task_id: str
    level: Literal["debug", "info", "warning", "error"]
    message: str
    timestamp: str


class CompletedEvent(BaseModel):
    """Task completed event."""
    task_id: str
    outputs: dict


class ErrorEvent(BaseModel):
    """Error event."""
    task_id: str
    error: str
    step: Optional[int] = None
