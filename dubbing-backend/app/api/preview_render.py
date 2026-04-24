"""Preview render endpoint - generate short preview video with blur + subtitle."""
import logging
import tempfile
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from ..models.schemas import PreviewRenderRequest, PreviewRenderResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Store preview videos temporarily
PREVIEW_CACHE = {}


def _build_preview_segments(preview_text: str, duration: float) -> list[dict]:
    """Create a single preview subtitle cue that spans most of the clip."""
    text = (preview_text or "").strip()
    if not text:
        return []

    safe_duration = max(1.0, float(duration or 0.0))
    start = 0.2 if safe_duration > 0.6 else 0.0
    end = max(start + 0.8, safe_duration - 0.2)
    return [{
        "start": start,
        "end": end,
        "text": text,
    }]


def cleanup_preview(preview_id: str):
    """Clean up preview video after serving."""
    if preview_id in PREVIEW_CACHE:
        video_path = PREVIEW_CACHE[preview_id]
        try:
            if Path(video_path).exists():
                Path(video_path).unlink()
            del PREVIEW_CACHE[preview_id]
        except Exception as e:
            logger.error(f"Failed to cleanup preview {preview_id}: {e}")


@router.post("/render", response_model=PreviewRenderResponse)
async def render_preview(request: PreviewRenderRequest):
    """Render a short preview video with blur + subtitle."""
    try:
        import sys
        from pathlib import Path as P

        # Add src to path
        backend_dir = P(__file__).parent.parent.parent
        sys.path.insert(0, str(backend_dir))

        from src.modules.downloader.ytdlp_wrapper import download
        from src.modules.transcription.srt_generator import write_srt
        from src.modules.video_processing.subtitle_burner import burn_subtitle
        from src.modules.video_processing.video_encoder import render_clean_video
        from src.modules.video_processing.ffmpeg_wrapper import get_dims, probe_duration
        from src.modules.video_processing.subtitle_detector import detect_sub_events

        render_video_speed = float(request.render_video_speed or request.video_speed or 1.0)

        # Validate duration
        duration = min(30.0, max(5.0, request.duration))
        start_time = max(0.0, request.start_time)

        logger.info(f"Preview render: {request.source} @ {start_time}s for {duration}s")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # Step 1: Download video segment
            logger.info("Downloading video segment...")
            video_path, audio_path, title = download(
                request.source,
                tmp,
                download_range_start=start_time,
                download_range_end=start_time + duration,
            )

            # Get video info
            w, h = get_dims(video_path)
            actual_duration = probe_duration(video_path)

            # Step 2: Detect original subtitle area from the real clip
            logger.info("Detecting original subtitle area...")
            events = detect_sub_events(video_path, w, h)
            if events:
                logger.info("Detected %s subtitle cover events", len(events))
            else:
                logger.warning("No subtitle events detected in preview clip")

            # Step 3: Render clean video with the same cover pipeline as the final render
            logger.info("Rendering clean preview video...")
            clean_path = tmp / "clean.mp4"
            meta = render_clean_video(
                video_path,
                clean_path,
                mode=request.cover_mode,
                events=events,
                blur_power=request.cover_strength,
                blur_padding_px=request.blur_padding_px,
                cover_offset_px=request.cover_offset_px,
                video_speed=render_video_speed,
            )

            final_path = tmp / f"preview_{uuid.uuid4().hex[:8]}.mp4"
            preview_segments = _build_preview_segments(request.preview_text, actual_duration)

            if request.burn_subtitle and preview_segments:
                logger.info("Burning preview subtitle text...")
                srt_path = tmp / "preview_subtitle.srt"
                write_srt(
                    preview_segments,
                    srt_path,
                    max_chars_per_line=max(10, int(request.srt_max_chars_per_line or 45)),
                )

                burn_subtitle(
                    clean_path,
                    srt_path,
                    final_path,
                    subtitle_top_y=meta.get("subtitle_top_y"),
                    subtitle_bottom_y=meta.get("subtitle_bottom_y"),
                    font_scale=request.subtitle_font_scale,
                    font_size_override=request.subtitle_font_size,
                    margin_offset=request.subtitle_margin_px,
                )
            else:
                logger.info("Skipping subtitle burn for preview")
                clean_path.replace(final_path)

            # Move to permanent location
            preview_id = uuid.uuid4().hex
            preview_dir = Path("outputs/previews")
            preview_dir.mkdir(parents=True, exist_ok=True)
            permanent_path = preview_dir / f"{preview_id}.mp4"
            final_path.rename(permanent_path)

            # Cache the path
            PREVIEW_CACHE[preview_id] = str(permanent_path)

            logger.info(f"Preview ready: {permanent_path}")

            return PreviewRenderResponse(
                video_url=f"/api/preview-render/video/{preview_id}",
                duration=actual_duration,
                width=w,
                height=h,
            )

    except Exception as e:
        logger.error(f"Failed to render preview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/{preview_id}")
async def get_preview_video(preview_id: str):
    """Serve preview video."""
    if preview_id not in PREVIEW_CACHE:
        raise HTTPException(status_code=404, detail="Preview not found")

    video_path = PREVIEW_CACHE[preview_id]
    if not Path(video_path).exists():
        raise HTTPException(status_code=404, detail="Preview file not found")

    # Don't cleanup immediately - let video be streamed multiple times
    return FileResponse(
        video_path,
        media_type="video/mp4",
        filename=f"preview_{preview_id}.mp4",
    )
