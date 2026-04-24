"""Video processing endpoints."""
import logging
import uuid
import os
import subprocess
import platform
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from ..models.schemas import ProcessRequest, TaskResponse, StatusResponse, StepRequest
from ..tasks import process_video_task, run_step_task, get_task_status, run_process_video_sync, run_step_sync, _sync_tasks
from ..core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# Check if Celery is available
CELERY_AVAILABLE = False
try:
    from celery import current_app
    # Try to ping broker
    current_app.control.inspect().stats()
    CELERY_AVAILABLE = True
    logger.info("Celery broker is available")
except Exception as e:
    logger.warning(f"Celery not available, will run tasks synchronously: {e}")


@router.post("/", response_model=TaskResponse)
async def start_processing(request: ProcessRequest, background_tasks: BackgroundTasks):
    """Start video processing (monolithic or step-by-step mode)."""
    try:
        if CELERY_AVAILABLE:
            # Use Celery for async processing
            task = process_video_task.apply_async(
                kwargs={
                    "source": request.source,
                    "options": request.model_dump(exclude={"source", "mode"}),
                    "mode": request.mode,
                }
            )
            task_id = task.id
            logger.info(f"Started Celery task: {task_id}")
        else:
            # Run synchronously in background
            task_id = str(uuid.uuid4())
            logger.info(f"Starting sync task: {task_id}")

            # Run in FastAPI background task
            background_tasks.add_task(
                run_process_video_sync,
                source=request.source,
                options=request.model_dump(exclude={"source", "mode"}),
                mode=request.mode,
                task_id=task_id
            )

        return TaskResponse(
            task_id=task_id,
            status="queued",
            message="Processing started",
        )

    except Exception as e:
        logger.error(f"Failed to start processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step/{step_num}", response_model=TaskResponse)
async def run_step(step_num: int, request: StepRequest, background_tasks: BackgroundTasks):
    """Run a single processing step."""
    if not 1 <= step_num <= 7:
        raise HTTPException(status_code=400, detail="Step must be between 1 and 7")

    try:
        if CELERY_AVAILABLE:
            # Use Celery for async processing
            task = run_step_task.apply_async(
                kwargs={
                    "step_num": step_num,
                    "task_id": request.task_id,
                    "step_data": request.step_data,
                }
            )
            task_id = task.id
            logger.info(f"Started Celery step {step_num} for task {request.task_id}")
        else:
            # Run synchronously in background
            task_id = request.task_id if request.task_id != "new" else str(uuid.uuid4())
            logger.info(f"Starting sync step {step_num} for task {task_id}")

            # Run in FastAPI background task
            background_tasks.add_task(
                run_step_sync,
                step_num=step_num,
                task_id=task_id,
                step_data=request.step_data
            )

        return TaskResponse(
            task_id=task_id,
            status="running",
            message=f"Step {step_num} started",
        )

    except Exception as e:
        logger.error(f"Failed to run step {step_num}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/step-srt/{task_id}")
async def get_step_srt(task_id: str):
    """Get current editable SRT content for a step-by-step task."""
    try:
        from src.modules.workflow import load_step_state

        state = load_step_state(str(settings.OUTPUT_DIR / task_id))
        srt_path = state.get("srt_path")
        if not srt_path:
            raise HTTPException(status_code=404, detail="SRT file not available yet")

        resolved_path = Path(srt_path).resolve()
        output_dir = settings.OUTPUT_DIR.resolve()
        if not str(resolved_path).startswith(str(output_dir)):
            raise HTTPException(status_code=403, detail="Access denied")
        if not resolved_path.exists():
            raise HTTPException(status_code=404, detail="SRT file not found")

        return {
            "task_id": task_id,
            "srt_path": str(resolved_path),
            "content": resolved_path.read_text(encoding="utf-8", errors="ignore"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get SRT for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step-srt/{task_id}")
async def save_step_srt(task_id: str, request: dict):
    """Save edited SRT content for a step-by-step task."""
    try:
        from src.modules.workflow import load_step_state, save_step_state
        from src.modules.transcription.srt_generator import parse_srt

        content = request.get("content", "")
        state = load_step_state(str(settings.OUTPUT_DIR / task_id))
        srt_path = state.get("srt_path")
        if not srt_path:
            raise HTTPException(status_code=404, detail="SRT file not available yet")

        resolved_path = Path(srt_path).resolve()
        output_dir = settings.OUTPUT_DIR.resolve()
        if not str(resolved_path).startswith(str(output_dir)):
            raise HTTPException(status_code=403, detail="Access denied")

        resolved_path.write_text(content, encoding="utf-8")
        parsed = parse_srt(resolved_path)
        if parsed:
            state["segments_vi"] = parsed
        save_step_state(str(settings.OUTPUT_DIR / task_id), state)

        return {
            "task_id": task_id,
            "srt_path": str(resolved_path),
            "saved": True,
            "segment_count": len(parsed),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save SRT for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}", response_model=StatusResponse)
async def get_status(task_id: str):
    """Get task status."""
    try:
        if CELERY_AVAILABLE:
            status = get_task_status(task_id)
        else:
            # Get from sync task storage
            task_data = _sync_tasks.get(task_id, {})
            status = {
                "task_id": task_id,
                "status": task_data.get("status", "unknown"),
                "current_step": task_data.get("step", 0),
                "progress": task_data.get("progress", 0.0),
                "message": task_data.get("message", ""),
                "outputs": task_data.get("result", {}),
                "error": task_data.get("error"),
            }

        return StatusResponse(**status)

    except Exception as e:
        logger.error(f"Failed to get status for task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cancel/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a running task."""
    try:
        from celery import current_app
        current_app.control.revoke(task_id, terminate=True)

        logger.info(f"Cancelled task: {task_id}")
        return {"message": "Task cancelled"}

    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{file_path:path}")
async def download_file(file_path: str):
    """Download a file from the output directory."""
    try:
        # Decode and resolve the file path
        file_path = Path(file_path)

        # Security check: ensure file is within output directory
        output_dir = settings.OUTPUT_DIR.resolve()
        resolved_path = file_path.resolve()

        if not str(resolved_path).startswith(str(output_dir)):
            raise HTTPException(status_code=403, detail="Access denied")

        if not resolved_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if not resolved_path.is_file():
            raise HTTPException(status_code=400, detail="Not a file")

        return FileResponse(
            path=str(resolved_path),
            filename=resolved_path.name,
            media_type="application/octet-stream"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file {file_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/open-folder")
async def open_folder(request: dict):
    """Open a folder in the system file explorer."""
    try:
        folder_path = request.get("folder_path")
        if not folder_path:
            raise HTTPException(status_code=400, detail="folder_path is required")

        folder = Path(folder_path)

        # Security check: ensure folder is within output directory
        output_dir = settings.OUTPUT_DIR.resolve()
        resolved_folder = folder.resolve()

        if not str(resolved_folder).startswith(str(output_dir)):
            raise HTTPException(status_code=403, detail="Access denied")

        if not resolved_folder.exists():
            raise HTTPException(status_code=404, detail="Folder not found")

        if not resolved_folder.is_dir():
            raise HTTPException(status_code=400, detail="Not a directory")

        # Open folder based on OS
        system = platform.system()
        if system == "Windows":
            os.startfile(str(resolved_folder))
        elif system == "Darwin":  # macOS
            subprocess.run(["open", str(resolved_folder)])
        else:  # Linux
            subprocess.run(["xdg-open", str(resolved_folder)])

        return {"message": "Folder opened successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to open folder {folder_path}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
