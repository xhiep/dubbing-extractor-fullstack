"""Video processing endpoints."""
import logging
from fastapi import APIRouter, HTTPException
from ..models.schemas import ProcessRequest, TaskResponse, StatusResponse, StepRequest
from ..tasks import process_video_task, run_step_task, get_task_status

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=TaskResponse)
async def start_processing(request: ProcessRequest):
    """Start video processing (monolithic or step-by-step mode)."""
    try:
        # Start Celery task
        task = process_video_task.apply_async(
            kwargs={
                "source": request.source,
                "options": request.model_dump(exclude={"source", "mode"}),
                "mode": request.mode,
            }
        )

        logger.info(f"Started processing task: {task.id}")

        return TaskResponse(
            task_id=task.id,
            status="queued",
            message="Processing started",
        )

    except Exception as e:
        logger.error(f"Failed to start processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/step/{step_num}", response_model=TaskResponse)
async def run_step(step_num: int, request: StepRequest):
    """Run a single processing step."""
    if not 1 <= step_num <= 7:
        raise HTTPException(status_code=400, detail="Step must be between 1 and 7")

    try:
        task = run_step_task.apply_async(
            kwargs={
                "step_num": step_num,
                "task_id": request.task_id,
                "step_data": request.step_data,
            }
        )

        logger.info(f"Started step {step_num} for task {request.task_id}")

        return TaskResponse(
            task_id=task.id,
            status="running",
            message=f"Step {step_num} started",
        )

    except Exception as e:
        logger.error(f"Failed to run step {step_num}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}", response_model=StatusResponse)
async def get_status(task_id: str):
    """Get task status."""
    try:
        status = get_task_status(task_id)
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
