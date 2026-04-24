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
            source=source,
            output_dir=str(output_dir),
            log_cb=log_callback,
            progress_cb=progress_callback,
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
    from src.modules.workflow import (
        step1_prepare,
        step2_transcribe,
        step3_translate,
        step4_cover,
        step5_export,
        step6_burn,
        step7_dub,
    )
    import asyncio
    from .websocket import emit_progress, emit_log, emit_completed

    step_functions = {
        1: step1_prepare,
        2: step2_transcribe,
        3: step3_translate,
        4: step4_cover,
        5: step5_export,
        6: step6_burn,
        7: step7_dub,
    }

    output_dir = settings.OUTPUT_DIR / task_id

    def log_callback(msg: str):
        """Log callback."""
        logger.info(f"[{task_id}] Step {step_num}: {msg}")
        try:
            asyncio.run(emit_log(task_id, "info", msg))
        except Exception as e:
            logger.error(f"Failed to emit log: {e}")

    try:
        func = step_functions[step_num]
        result = func(
            output_dir=str(output_dir),
            log_cb=log_callback,
            **step_data,
        )

        # Emit progress
        try:
            asyncio.run(emit_progress(task_id, step_num, 100.0, f"Step {step_num} completed"))
        except Exception as e:
            logger.error(f"Failed to emit progress: {e}")

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
