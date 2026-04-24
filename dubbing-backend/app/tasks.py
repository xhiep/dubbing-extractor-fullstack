"""Celery tasks for background video processing."""
import logging
import sys
from pathlib import Path
from celery import Celery, Task
from celery.signals import task_prerun, task_postrun, task_failure

from .core.config import settings

logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(settings.BASE_DIR))

# Create Celery app
celery_app = Celery(
    "dubbing",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.TASK_TIMEOUT,
)


class CallbackTask(Task):
    """Base task with WebSocket callbacks."""

    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds."""
        logger.info(f"Task {task_id} completed successfully")
        # Emit WebSocket event (handled in workflow callbacks)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails."""
        logger.error(f"Task {task_id} failed: {exc}")
        # Emit WebSocket event
        import asyncio
        from .websocket import emit_error
        try:
            asyncio.create_task(emit_error(task_id, str(exc)))
        except Exception as e:
            logger.error(f"Failed to emit error event: {e}")


@celery_app.task(base=CallbackTask, bind=True)
def process_video_task(self, source: str, options: dict, mode: str = "monolithic"):
    """Process video in background (monolithic mode)."""
    from src.modules.workflow import process_video
    import asyncio
    from .websocket import emit_progress, emit_log, emit_completed

    task_id = self.request.id
    output_dir = settings.OUTPUT_DIR / task_id

    def log_callback(msg: str):
        """Log callback."""
        logger.info(f"[{task_id}] {msg}")
        try:
            asyncio.run(emit_log(task_id, "info", msg))
        except Exception as e:
            logger.error(f"Failed to emit log: {e}")

    def progress_callback(step: int, progress: float, message: str):
        """Progress callback."""
        logger.info(f"[{task_id}] Step {step}: {progress}% - {message}")
        try:
            asyncio.run(emit_progress(task_id, step, progress, message))
        except Exception as e:
            logger.error(f"Failed to emit progress: {e}")

    try:
        # Run workflow
        result = process_video(
            source_input=source,
            log_cb=log_callback,
            **options,
        )

        # Emit completion
        try:
            asyncio.run(emit_completed(task_id, result))
        except Exception as e:
            logger.error(f"Failed to emit completion: {e}")

        return result

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        try:
            asyncio.run(emit_error(task_id, str(e)))
        except Exception as emit_err:
            logger.error(f"Failed to emit error: {emit_err}")
        raise


@celery_app.task(base=CallbackTask, bind=True)
def run_step_task(self, step_num: int, task_id: str, step_data: dict):
    """Run a single processing step."""
    from src.modules.workflow import run_single_step
    import asyncio
    from .websocket import emit_progress, emit_log, emit_completed, emit_error

    output_dir = settings.OUTPUT_DIR / task_id

    def log_callback(msg: str):
        """Log callback."""
        logger.info(f"[{task_id}] Step {step_num}: {msg}")
        try:
            asyncio.run(emit_log(task_id, "info", msg))
        except Exception as e:
            logger.error(f"Failed to emit log: {e}")

    def progress_callback(step: int, progress: float, message: str):
        try:
            asyncio.run(emit_progress(task_id, step, progress, message))
        except Exception as e:
            logger.error(f"Failed to emit progress: {e}")

    try:
        result = run_single_step(
            step_num=step_num,
            task_id=task_id,
            output_dir=str(output_dir),
            step_data=step_data,
            log_cb=log_callback,
            progress_cb=progress_callback,
        )

        try:
            asyncio.run(emit_completed(task_id, result))
        except Exception as e:
            logger.error(f"Failed to emit completion: {e}")

        return result

    except Exception as e:
        logger.error(f"Step {step_num} failed for task {task_id}: {e}")
        try:
            asyncio.run(emit_error(task_id, str(e), step_num))
        except Exception as emit_err:
            logger.error(f"Failed to emit error: {emit_err}")
        raise


def get_task_status(task_id: str) -> dict:
    """Get task status from Celery."""
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_app)

    status_map = {
        "PENDING": "queued",
        "STARTED": "running",
        "SUCCESS": "completed",
        "FAILURE": "failed",
        "RETRY": "running",
        "REVOKED": "failed",
    }

    return {
        "task_id": task_id,
        "status": status_map.get(result.state, "unknown"),
        "current_step": 0,  # TODO: Track from task meta
        "progress": 0.0,  # TODO: Track from task meta
        "message": str(result.info) if result.info else "",
        "outputs": result.result if result.successful() else {},
        "error": str(result.info) if result.failed() else None,
    }


# Sync task storage for when Celery is not available
_sync_tasks = {}


def run_process_video_sync(source: str, options: dict, mode: str, task_id: str):
    """Run process_video synchronously (fallback when Celery unavailable)."""
    from src.modules.workflow import process_video
    import asyncio
    from .websocket import emit_progress, emit_log, emit_completed, emit_error

    output_dir = settings.OUTPUT_DIR / task_id
    _sync_tasks[task_id] = {"status": "running", "progress": 0, "message": "Starting..."}

    def log_callback(msg: str):
        """Log callback."""
        logger.info(f"[{task_id}] {msg}")
        try:
            asyncio.run(emit_log(task_id, "info", msg))
        except Exception as e:
            logger.error(f"Failed to emit log: {e}")

    # Map frontend parameter names to backend parameter names
    if 'burn_subtitle' in options:
        options['burn_sub'] = options.pop('burn_subtitle')
    if 'cover_strength' in options:
        options['blur_power'] = options.pop('cover_strength')
    if 'enable_dubbing' in options:
        options['enable_dub'] = options.pop('enable_dubbing')

    # Filter options to only valid process_video parameters
    valid_keys = {
        'cover_mode', 'burn_sub', 'subtitle_offset_sec',
        'subtitle_timing_scale', 'video_speed', 'srt_max_chars_per_line',
        'subtitle_font_scale', 'subtitle_font_size', 'subtitle_margin_px',
        'blur_padding_px', 'cover_offset_px', 'blur_power',
        'enable_dub', 'dub_mode', 'dub_backend_mode', 'dub_remote_api_base',
        'dub_preset_voice', 'dub_ref_audio', 'dub_ref_text',
        'dub_voice_volume', 'dub_source_volume', 'dub_mix_mode'
    }
    filtered_options = {k: v for k, v in options.items() if k in valid_keys}

    try:
        # Run workflow
        result = process_video(
            source_input=source,
            log_cb=log_callback,
            **filtered_options,
        )

        # Convert result to dict format if it's a string (output directory path)
        if isinstance(result, str):
            from pathlib import Path
            out_dir = Path(result)

            # Find actual output files (they may have different names)
            video_file = None
            audio_file = None
            srt_file = None

            if out_dir.exists():
                # Look for video files
                for ext in ['.mp4', '.mkv', '.webm']:
                    video_files = list(out_dir.glob(f'*{ext}'))
                    if video_files:
                        video_file = str(video_files[0])
                        break

                # Look for audio files
                for ext in ['.mp3', '.wav', '.m4a']:
                    audio_files = list(out_dir.glob(f'*{ext}'))
                    if audio_files:
                        audio_file = str(audio_files[0])
                        break

                # Look for subtitle files
                srt_files = list(out_dir.glob('*.srt'))
                if srt_files:
                    srt_file = str(srt_files[0])

            result_dict = {
                "out_dir": str(out_dir),
                "video_path": video_file,
                "audio_path": audio_file,
                "srt_path": srt_file,
            }
        else:
            result_dict = result if isinstance(result, dict) else {}

        _sync_tasks[task_id] = {"status": "completed", "progress": 100, "message": "Done", "result": result_dict}

        # Emit completion
        try:
            asyncio.run(emit_completed(task_id, result_dict))
        except Exception as e:
            logger.error(f"Failed to emit completion: {e}")

        return result_dict

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")
        _sync_tasks[task_id] = {"status": "failed", "progress": 0, "message": str(e), "error": str(e)}
        try:
            asyncio.run(emit_error(task_id, str(e)))
        except Exception as emit_err:
            logger.error(f"Failed to emit error: {emit_err}")
        raise


def run_step_sync(step_num: int, task_id: str, step_data: dict):
    """Run a single step synchronously (fallback when Celery unavailable)."""
    from src.modules.workflow import run_single_step
    import asyncio
    from .websocket import emit_progress, emit_log, emit_error, emit_completed

    output_dir = settings.OUTPUT_DIR / task_id
    _sync_tasks[task_id] = {"status": "running", "progress": 0, "message": f"Running step {step_num}...", "step": step_num}

    def log_callback(msg: str):
        """Log callback."""
        logger.info(f"[{task_id}] Step {step_num}: {msg}")
        try:
            asyncio.run(emit_log(task_id, "info", msg))
        except Exception as e:
            logger.error(f"Failed to emit log: {e}")

    def progress_callback(step: int, progress: float, message: str):
        """Progress callback."""
        logger.info(f"[{task_id}] Step {step}: {progress}% - {message}")
        _sync_tasks[task_id] = {"status": "running", "progress": progress, "message": message, "step": step}
        try:
            asyncio.run(emit_progress(task_id, step, progress, message))
        except Exception as e:
            logger.error(f"Failed to emit progress: {e}")

    try:
        # Run single step
        result = run_single_step(
            step_num=step_num,
            task_id=task_id,
            output_dir=str(output_dir),
            step_data=step_data,
            log_cb=log_callback,
            progress_cb=progress_callback,
        )

        _sync_tasks[task_id] = {"status": "completed", "progress": 100, "message": f"Step {step_num} completed", "result": result, "step": step_num}

        try:
            asyncio.run(emit_completed(task_id, result))
        except Exception as e:
            logger.error(f"Failed to emit completion: {e}")

        return result

    except Exception as e:
        logger.error(f"Sync step {step_num} failed for task {task_id}: {e}")
        _sync_tasks[task_id] = {"status": "failed", "progress": 0, "message": str(e), "error": str(e), "step": step_num}
        try:
            asyncio.run(emit_error(task_id, str(e)))
        except Exception as emit_err:
            logger.error(f"Failed to emit error: {emit_err}")
        raise
