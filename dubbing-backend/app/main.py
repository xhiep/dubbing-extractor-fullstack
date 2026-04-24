"""FastAPI main application."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import socketio

from .core.config import settings
from .api import process, preview, tts
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

# Mount Socket.IO
socket_app = socketio.ASGIApp(
    sio,
    other_asgi_app=app,
    socketio_path="/ws/socket.io",
)

# Include routers
app.include_router(process.router, prefix=f"{settings.API_V1_PREFIX}/process", tags=["process"])
app.include_router(preview.router, prefix=f"{settings.API_V1_PREFIX}/preview", tags=["preview"])
app.include_router(tts.router, prefix=f"{settings.API_V1_PREFIX}/tts", tags=["tts"])

# Serve static files (output directory)
app.mount("/output", StaticFiles(directory=str(settings.OUTPUT_DIR)), name="output")


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


# Export the Socket.IO app for uvicorn
asgi_app = socket_app
