"""Video preview endpoints."""
import logging
from fastapi import APIRouter, HTTPException
from ..models.schemas import PreviewRequest, PreviewResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=PreviewResponse)
async def get_preview(request: PreviewRequest):
    """Get video preview information."""
    try:
        # Import here to avoid circular dependency
        import sys
        from pathlib import Path

        # Add src to path
        backend_dir = Path(__file__).parent.parent.parent.parent
        sys.path.insert(0, str(backend_dir))

        from src.modules.downloader.ytdlp_wrapper import fetch_preview_info
        from src.modules.downloader.platform_detector import detect_platform

        # Get platform
        platform = detect_platform(request.source)

        # Fetch preview info
        info = fetch_preview_info(request.source)

        return PreviewResponse(
            title=info.get("title", "Unknown"),
            duration=info.get("duration", 0.0),
            thumbnail=info.get("thumbnail"),
            platform=platform,
            width=info.get("width", 0),
            height=info.get("height", 0),
        )

    except Exception as e:
        logger.error(f"Failed to get preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))
