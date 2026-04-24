"""FastAPI main application."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import socketio

from .core.config import settings
from .api import process, preview, tts, preview_render, system
from .websocket import sio

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Starting Dubbing Extractor API...")
    yield
    logger.info("Shutting down Dubbing Extractor API...")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers BEFORE mounting static files
app.include_router(process.router, prefix=f"{settings.API_V1_PREFIX}/process", tags=["process"])
app.include_router(preview.router, prefix=f"{settings.API_V1_PREFIX}/preview", tags=["preview"])
app.include_router(preview_render.router, prefix=f"{settings.API_V1_PREFIX}/preview-render", tags=["preview-render"])
app.include_router(tts.router, prefix=f"{settings.API_V1_PREFIX}/tts", tags=["tts"])
app.include_router(system.router, prefix=f"{settings.API_V1_PREFIX}/system", tags=["system"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Serve static files (output directory) - MUST be last
app.mount("/output", StaticFiles(directory=str(settings.OUTPUT_DIR)), name="output")

# Mount Socket.IO AFTER all routes
socket_app = socketio.ASGIApp(
    sio,
    other_asgi_app=app,
    socketio_path="/ws/socket.io",
)


# Export the Socket.IO app for uvicorn
asgi_app = socket_app
