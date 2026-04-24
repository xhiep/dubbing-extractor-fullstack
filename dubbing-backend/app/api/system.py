"""System maintenance endpoints."""
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..core.config import settings
from . import preview_render

logger = logging.getLogger(__name__)
router = APIRouter()


def _clear_directory_contents(root: Path) -> dict:
    root = root.resolve()
    removed_files = 0
    removed_dirs = 0

    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
        return {"path": str(root), "removed_files": 0, "removed_dirs": 0}

    for child in list(root.iterdir()):
        if child.is_dir():
            shutil.rmtree(child)
            removed_dirs += 1
        else:
            child.unlink(missing_ok=True)
            removed_files += 1

    root.mkdir(parents=True, exist_ok=True)
    return {
        "path": str(root),
        "removed_files": removed_files,
        "removed_dirs": removed_dirs,
    }


@router.post("/cleanup-storage")
async def cleanup_storage():
    """Remove preview caches and temp files without touching persistent reference audio."""
    try:
        targets = [
            settings.TEMP_DIR,
            settings.PREVIEW_SOURCE_CACHE_DIR,
            settings.PREVIEW_RENDER_DIR,
            settings.BASE_DIR / "outputs" / "preview_sources",
            settings.BASE_DIR / "outputs" / "previews",
        ]

        results = []
        for target in targets:
            results.append(_clear_directory_contents(target))

        preview_render.PREVIEW_CACHE.clear()
        preview_render.PREVIEW_IMAGE_CACHE.clear()
        preview_render.PREVIEW_SOURCE_CACHE.clear()

        logger.info("Cleaned cache/temp storage")
        return {
            "success": True,
            "message": "Cache va temp da duoc don dep.",
            "results": results,
        }
    except Exception as exc:
        logger.error("Failed to clean storage: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
