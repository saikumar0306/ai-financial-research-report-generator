"""
files.py — GET /download/{filename} and GET /preview/{filename} endpoints.

Serves generated report files from REPORTS_DIR.
Content type is auto-detected from the actual file content:
  - Real PDF (%PDF header)  → application/pdf
  - HTML content            → text/html (legacy files before xhtml2pdf fix)
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Files"])


def _detect_media_type(file_path: Path) -> str:
    """Detect whether the file is a real PDF or HTML content."""
    try:
        with open(file_path, "rb") as f:
            header = f.read(10)
        if header.startswith(b"%PDF"):
            return "application/pdf"
        if header.strip()[:5].lower() in (b"<!doc", b"<html"):
            return "text/html"
    except Exception:
        pass
    return "application/pdf"


@router.get("/download/{filename}")
async def download_report(filename: str):
    """
    Download a generated report file.

    Auto-detects content type from file header (PDF or HTML).
    Returns Content-Disposition: attachment.
    """
    file_path = _resolve_file(filename)
    safe_name = file_path.name
    media_type = _detect_media_type(file_path)

    logger.info(f"[DOWNLOAD   ] Serving {media_type}: {safe_name}")

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=safe_name,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.get("/preview/{filename}")
async def preview_report(filename: str):
    """
    Preview a generated report inline in the browser.

    Auto-detects content type from file header (PDF or HTML).
    Returns Content-Disposition: inline.
    """
    file_path = _resolve_file(filename)
    safe_name = file_path.name
    media_type = _detect_media_type(file_path)

    logger.info(f"[PREVIEW    ] Serving {media_type} inline: {safe_name}")
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{safe_name}"'},
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_file(filename: str) -> Path:
    """
    Safely resolve a filename inside REPORTS_DIR.
    Prevents path traversal attacks.

    Raises:
        HTTPException 404 if the file is not found.
        HTTPException 400 if the filename is invalid.
    """
    if not filename or not filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty.",
        )

    # Strip any path separators to prevent traversal
    safe_name  = Path(filename).name
    file_path  = settings.REPORTS_DIR / safe_name

    if not file_path.exists():
        logger.warning(f"[FILES      ] File not found: {safe_name}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Report file '{safe_name}' not found. "
                "It may have been deleted or not yet generated."
            ),
        )

    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{safe_name}' is not a file.",
        )

    return file_path

