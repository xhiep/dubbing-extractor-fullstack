"""Preview render endpoint - generate short preview video with blur + subtitle."""
import logging
import tempfile
import uuid
import subprocess
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from ..models.schemas import PreviewRenderRequest, PreviewRenderResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Store preview videos temporarily
PREVIEW_CACHE = {}
PREVIEW_IMAGE_CACHE = {}


def _build_frontend_preview_band(height: int, top_y: int | None, bottom_y: int | None) -> list[dict]:
    if top_y is None or bottom_y is None:
        return []
    safe_height = max(1, int(height or 1))
    top = max(0, min(int(top_y), safe_height - 2))
    bottom = max(top + 1, min(int(bottom_y), safe_height - 1))
    return [{
        "start": 0.0,
        "end": 86400.0,
        "top_y": top,
        "bottom_y": bottom,
        "height": max(2, bottom - top + 1),
    }]


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


def _extract_preview_frame(video_path: Path, output_path: Path, seek_sec: float = 0.35) -> None:
    import sys
    from pathlib import Path as P

    backend_dir = P(__file__).parent.parent.parent
    sys.path.insert(0, str(backend_dir))
    from src.modules.video_processing.ffmpeg_wrapper import ffmpeg_cmd

    cmd = [
        ffmpeg_cmd(),
        "-y",
        "-ss", f"{max(0.0, float(seek_sec)):.3f}",
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", "2",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "").strip()[-1200:])


def _build_layout_response(
    source: str,
    start_time: float,
    duration: float,
    cover_mode: str,
    cover_strength: int,
    preview_text: str,
    burn_subtitle: bool,
    srt_max_chars_per_line: int,
    subtitle_font_scale: float,
    subtitle_font_size: int,
    subtitle_margin_px: int,
    blur_padding_px: int,
    cover_offset_px: int,
    render_video_speed: float,
):
    import sys
    from pathlib import Path as P

    backend_dir = P(__file__).parent.parent.parent
    sys.path.insert(0, str(backend_dir))

    from src.modules.downloader.ytdlp_wrapper import download
    from src.modules.transcription.srt_generator import write_srt
    from src.modules.video_processing.subtitle_burner import burn_subtitle as burn_preview_subtitle
    from src.modules.video_processing.subtitle_burner import compute_subtitle_layout
    from src.modules.video_processing.ffmpeg_wrapper import get_dims, probe_duration
    from src.modules.video_processing.subtitle_detector import detect_sub_events
    from src.modules.video_processing.video_encoder import _representative_band, _expand_band_from_center, render_clean_video

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        video_path, _audio_path, _title = download(
            source,
            tmp,
            download_range_start=start_time,
            download_range_end=start_time + duration,
        )

        width, height = get_dims(video_path)
        actual_duration = probe_duration(video_path)
        events = detect_sub_events(video_path, width, height)

        subtitle_top_y = None
        subtitle_bottom_y = None
        cover_top_y = None
        cover_bottom_y = None
        subtitle_layout = None
        clean_video_path = tmp / "layout_clean.mp4"
        final_video_path = clean_video_path
        if events:
            subtitle_top_y, subtitle_bottom_y = _representative_band(events, height)
            cover_top_y, cover_bottom_y = _expand_band_from_center(
                subtitle_top_y,
                subtitle_bottom_y,
                height,
                blur_padding_px,
                cover_offset_px,
            )
            subtitle_layout = compute_subtitle_layout(
                height,
                subtitle_top_y,
                subtitle_bottom_y,
                font_scale=subtitle_font_scale,
                font_size_override=subtitle_font_size,
                margin_offset=subtitle_margin_px,
            )

        frontend_preview_events = _build_frontend_preview_band(height, subtitle_top_y, subtitle_bottom_y)
        render_meta = render_clean_video(
            video_path,
            clean_video_path,
            mode=cover_mode,
            events=frontend_preview_events or events,
            blur_power=cover_strength,
            blur_padding_px=blur_padding_px,
            cover_offset_px=cover_offset_px,
            video_speed=render_video_speed,
        )

        if burn_subtitle and (preview_text or "").strip():
            srt_path = tmp / "layout_preview_subtitle.srt"
            preview_segments = _build_preview_segments(preview_text, actual_duration)
            write_srt(
                preview_segments,
                srt_path,
                max_chars_per_line=max(10, int(srt_max_chars_per_line or 45)),
            )
            final_video_path = tmp / "layout_preview_burned.mp4"
            burn_preview_subtitle(
                clean_video_path,
                srt_path,
                final_video_path,
                subtitle_top_y=subtitle_top_y if subtitle_top_y is not None else render_meta.get("subtitle_top_y"),
                subtitle_bottom_y=subtitle_bottom_y if subtitle_bottom_y is not None else render_meta.get("subtitle_bottom_y"),
                font_scale=subtitle_font_scale,
                font_size_override=subtitle_font_size,
                margin_offset=subtitle_margin_px,
            )

        preview_id = uuid.uuid4().hex
        preview_dir = Path("outputs/previews")
        preview_dir.mkdir(parents=True, exist_ok=True)
        frame_path = preview_dir / f"{preview_id}.jpg"
        _extract_preview_frame(final_video_path, frame_path, seek_sec=0.6)
        PREVIEW_IMAGE_CACHE[preview_id] = str(frame_path)

        return {
            "image_url": f"/api/preview-render/image/{preview_id}",
            "width": width,
            "height": height,
            "subtitle_top_y": subtitle_top_y,
            "subtitle_bottom_y": subtitle_bottom_y,
            "cover_top_y": cover_top_y,
            "cover_bottom_y": cover_bottom_y,
            "subtitle_layout": subtitle_layout or {"font_size": None, "margin_v": None},
            "cover_mode": cover_mode,
            "cover_strength": cover_strength,
        }


@router.post("/layout")
async def get_preview_layout(request: PreviewRenderRequest):
    """Return actual frame image and detected subtitle band for web preview alignment."""
    try:
        duration = min(8.0, max(3.0, request.duration or 5.0))
        start_time = max(0.0, request.start_time)
        return _build_layout_response(
            source=request.source,
            start_time=start_time,
            duration=duration,
            cover_mode=request.cover_mode,
            cover_strength=request.cover_strength,
            preview_text=request.preview_text,
            burn_subtitle=request.burn_subtitle,
            srt_max_chars_per_line=request.srt_max_chars_per_line,
            subtitle_font_scale=request.subtitle_font_scale,
            subtitle_font_size=request.subtitle_font_size,
            subtitle_margin_px=request.subtitle_margin_px,
            blur_padding_px=request.blur_padding_px,
            cover_offset_px=request.cover_offset_px,
            render_video_speed=float(request.render_video_speed or request.video_speed or 1.0),
        )
    except Exception as e:
        logger.error(f"Failed to build preview layout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
            frontend_preview_events = _build_frontend_preview_band(
                h,
                request.preview_subtitle_top_y,
                request.preview_subtitle_bottom_y,
            )
            events = frontend_preview_events or detect_sub_events(video_path, w, h)
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
                    subtitle_top_y=request.preview_subtitle_top_y if request.preview_subtitle_top_y is not None else meta.get("subtitle_top_y"),
                    subtitle_bottom_y=request.preview_subtitle_bottom_y if request.preview_subtitle_bottom_y is not None else meta.get("subtitle_bottom_y"),
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


@router.get("/image/{preview_id}")
async def get_preview_image(preview_id: str):
    """Serve cached preview frame image."""
    if preview_id not in PREVIEW_IMAGE_CACHE:
        raise HTTPException(status_code=404, detail="Preview image not found")

    image_path = PREVIEW_IMAGE_CACHE[preview_id]
    if not Path(image_path).exists():
        raise HTTPException(status_code=404, detail="Preview image file not found")

    return FileResponse(
        image_path,
        media_type="image/jpeg",
        filename=f"preview_{preview_id}.jpg",
    )
