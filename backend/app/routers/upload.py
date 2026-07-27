"""
upload.py — POST /upload endpoint.

Receives a file upload, validates extension and size,
parses document content in a thread pool executor (non-blocking),
and returns the extracted text.
"""

import asyncio
import functools
import time

from fastapi import APIRouter, File, Form, UploadFile, HTTPException, status

from config import settings
from app.services.document_parser import parse_document
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("")
async def upload_document(
    file: UploadFile = File(..., description="Financial document (PDF, TXT, or CSV)"),
    company_name: str = Form(..., description="Company name for context"),
):
    """
    Upload a financial document and extract its text content.

    The document parsing is performed in a thread-pool executor to avoid
    blocking the async event loop during CPU-intensive PDF parsing.

    Returns:
        JSON with extracted_text and metadata.
    """
    t_start = time.perf_counter()

    # ── Validate file extension ────────────────────────────────────────────────
    import os
    ext = os.path.splitext(file.filename or "")[1].lower()
    if not ext:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File has no extension. Please upload a .pdf, .txt, or .csv file.",
        )
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Allowed formats: {', '.join(sorted(settings.ALLOWED_EXTENSIONS))}"
            ),
        )

    # ── Read file bytes ────────────────────────────────────────────────────────
    logger.info(f"[UPLOAD     ] Reading file: {file.filename!r}")
    try:
        file_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read uploaded file: {exc}",
        )

    # ── Validate file size ─────────────────────────────────────────────────────
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty. Please upload a non-empty document.",
        )
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File too large ({len(file_bytes) / 1024 / 1024:.1f} MB). "
                f"Maximum allowed size is {settings.MAX_UPLOAD_MB} MB."
            ),
        )

    logger.info(
        f"[UPLOAD     ] File accepted: {file.filename!r}  "
        f"size={len(file_bytes):,} bytes  "
        f"ext={ext}  "
        f"company={company_name!r}"
    )

    # ── Parse document in thread pool (non-blocking) ──────────────────────────
    loop = asyncio.get_event_loop()
    try:
        logger.info(f"[UPLOAD     ] Starting document parsing in thread pool...")
        extracted_text = await loop.run_in_executor(
            None,
            functools.partial(parse_document, file_bytes, file.filename or "document.txt"),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"[UPLOAD     ] Document parsing failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Failed to process '{file.filename}': {exc}. "
                "Ensure the file is not password-protected or corrupted."
            ),
        )

    if not extracted_text or not extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Could not extract any text from the document. "
                "The file may be image-only (scanned PDF), password-protected, or corrupted."
            ),
        )

    elapsed = time.perf_counter() - t_start
    logger.info(
        f"[UPLOAD DONE] file={file.filename!r}  "
        f"chars={len(extracted_text):,}  "
        f"elapsed={elapsed:.2f}s"
    )

    return {
        "success":        True,
        "company_name":   company_name,
        "filename":       file.filename,
        "file_type":      ext.lstrip(".").upper(),
        "file_size_kb":   round(len(file_bytes) / 1024, 1),
        "char_count":     len(extracted_text),
        "extracted_text": extracted_text,
    }
