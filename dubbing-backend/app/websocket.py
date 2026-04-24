"""WebSocket handlers using Socket.IO."""
import logging
import socketio

logger = logging.getLogger(__name__)

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)


@sio.event
async def connect(sid, environ):
    """Client connected."""
    logger.info(f"Client connected: {sid}")
    await sio.emit("connected", {"message": "Connected to Dubbing Extractor API"}, room=sid)


@sio.event
async def disconnect(sid):
    """Client disconnected."""
    logger.info(f"Client disconnected: {sid}")


@sio.event
async def subscribe(sid, data):
    """Subscribe to task updates."""
    task_id = data.get("task_id")
    if task_id:
        await sio.enter_room(sid, task_id)
        logger.info(f"Client {sid} subscribed to task {task_id}")
        await sio.emit("subscribed", {"task_id": task_id}, room=sid)


@sio.event
async def unsubscribe(sid, data):
    """Unsubscribe from task updates."""
    task_id = data.get("task_id")
    if task_id:
        await sio.leave_room(sid, task_id)
        logger.info(f"Client {sid} unsubscribed from task {task_id}")


# Helper functions to emit events from Celery tasks

async def emit_progress(task_id: str, step: int, progress: float, message: str):
    """Emit progress update."""
    await sio.emit("progress", {
        "task_id": task_id,
        "step": step,
        "progress": progress,
        "message": message,
    }, room=task_id)


async def emit_log(task_id: str, level: str, message: str):
    """Emit log message."""
    from datetime import datetime
    await sio.emit("log", {
        "task_id": task_id,
        "level": level,
        "message": message,
        "timestamp": datetime.now().isoformat(),
    }, room=task_id)


async def emit_completed(task_id: str, outputs: dict):
    """Emit task completed."""
    await sio.emit("completed", {
        "task_id": task_id,
        "outputs": outputs,
    }, room=task_id)


async def emit_error(task_id: str, error: str, step: int = None):
    """Emit error."""
    await sio.emit("error", {
        "task_id": task_id,
        "error": error,
        "step": step,
    }, room=task_id)
