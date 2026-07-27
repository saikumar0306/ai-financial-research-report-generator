"""
extract.py — POST /extract endpoint.

Receives extracted text + company name and calls Gemini AI
to return a structured financial JSON object.

The AI call runs in a thread pool executor via the async wrapper
in ai_extractor.py — this endpoint itself is non-blocking.
"""

import asyncio
import time

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, field_validator

from app.services.ai_extractor import extract_financial_data
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/extract", tags=["AI Extraction"])

# Maximum time to wait for Gemini extraction (seconds)
EXTRACTION_TIMEOUT_SECONDS = 180  # 3 minutes


class ExtractRequest(BaseModel):
    company_name: str
    extracted_text: str

    @field_validator("company_name")
    @classmethod
    def company_name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("company_name must not be empty")
        return v

    @field_validator("extracted_text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("extracted_text must not be empty")
        return v


@router.post("")
async def extract_data(request: ExtractRequest):
    """
    Send document text to Gemini AI and return structured financial JSON.

    Applies a timeout of 3 minutes to prevent indefinite hanging.
    The Gemini call runs in a background thread pool (non-blocking).

    Returns:
        JSON with the full extracted financial data structure.
    """
    t_start = time.perf_counter()
    logger.info(
        f"[EXTRACT    ] Request: company={request.company_name!r}  "
        f"chars={len(request.extracted_text):,}"
    )

    try:
        financial_data = await asyncio.wait_for(
            extract_financial_data(
                company_name=request.company_name,
                document_text=request.extracted_text,
            ),
            timeout=EXTRACTION_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        elapsed = time.perf_counter() - t_start
        logger.error(
            f"[EXTRACT    ] Timeout after {elapsed:.1f}s for {request.company_name!r}"
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=(
                f"AI extraction timed out after {EXTRACTION_TIMEOUT_SECONDS}s. "
                "The document may be too complex. Try a shorter document or try again."
            ),
        )
    except RuntimeError as exc:
        elapsed = time.perf_counter() - t_start
        logger.error(f"[EXTRACT    ] RuntimeError after {elapsed:.1f}s: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        elapsed = time.perf_counter() - t_start
        logger.error(f"[EXTRACT    ] Unexpected error after {elapsed:.1f}s: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI extraction failed unexpectedly: {exc}",
        )

    elapsed = time.perf_counter() - t_start
    logger.info(
        f"[EXTRACT OK ] company={request.company_name!r}  "
        f"elapsed={elapsed:.2f}s  "
        f"rec={financial_data.get('recommendation', 'N/A')}"
    )

    return {
        "success":      True,
        "company_name": request.company_name,
        "elapsed_sec":  round(elapsed, 2),
        "data":         financial_data,
    }
