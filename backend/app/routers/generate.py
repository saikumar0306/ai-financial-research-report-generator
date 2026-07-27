"""
generate.py — POST /generate endpoint.

Receives validated financial JSON, generates charts,
builds the HTML report, converts to PDF, and returns the filename.

All CPU-bound operations (charts, HTML rendering, PDF generation) run
in a thread-pool executor to avoid blocking the async event loop.
"""

import asyncio
import functools
import time

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.services.chart_generator import generate_all_charts
from app.services.report_builder import build_html_report
from app.services.pdf_generator import generate_pdf
from app.utils.helpers import generate_report_filename
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/generate", tags=["Report Generation"])

# Timeout for the full generation pipeline
GENERATION_TIMEOUT_SECONDS = 120  # 2 minutes


class GenerateRequest(BaseModel):
    """Request body — the full financial data dict returned by /extract."""
    data: dict


@router.post("")
async def generate_report(request: GenerateRequest):
    """
    Generate a full financial research report (charts + HTML + PDF).

    Steps (all run in thread pool executor):
        1. Generate financial charts (matplotlib)
        2. Build HTML report (Jinja2 template)
        3. Convert HTML → PDF (WeasyPrint / pdfkit / HTML fallback)

    Returns:
        JSON with filename, mode (pdf/html_as_pdf), and generation metadata.
    """
    t_pipeline_start = time.perf_counter()
    data = request.data
    company_name = data.get("company_name", "company")

    logger.info(f"[GENERATE   ] Starting report pipeline for: {company_name!r}")

    loop = asyncio.get_event_loop()

    # ── Step 1: Charts (CPU-bound, run in executor) ───────────────────────────
    chart_paths = {}
    try:
        t0 = time.perf_counter()
        logger.info(f"[GENERATE   ] [1/3] Generating charts...")
        chart_paths = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                functools.partial(generate_all_charts, data.get("financial_tables", {}))
            ),
            timeout=30,
        )
        charts_ok = [k for k, v in chart_paths.items() if v]
        logger.info(
            f"[GENERATE   ] [1/3] Charts done in {time.perf_counter()-t0:.2f}s — "
            f"generated={charts_ok}"
        )
    except asyncio.TimeoutError:
        logger.warning("[GENERATE   ] [1/3] Chart generation timed out (non-fatal) — continuing")
        chart_paths = {}
    except Exception as exc:
        logger.warning(f"[GENERATE   ] [1/3] Chart generation failed (non-fatal): {exc}")
        chart_paths = {}

    # ── Step 2: HTML render (CPU-bound, run in executor) ──────────────────────
    try:
        t0 = time.perf_counter()
        logger.info(f"[GENERATE   ] [2/3] Rendering HTML report...")
        html_content = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                functools.partial(build_html_report, data, chart_paths)
            ),
            timeout=30,
        )
        logger.info(
            f"[GENERATE   ] [2/3] HTML rendered in {time.perf_counter()-t0:.2f}s — "
            f"{len(html_content):,} chars"
        )
    except asyncio.TimeoutError:
        logger.error("[GENERATE   ] [2/3] HTML rendering timed out")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Report template rendering timed out. Please try again.",
        )
    except Exception as exc:
        logger.error(f"[GENERATE   ] [2/3] HTML render failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report template rendering failed: {exc}",
        )

    # ── Step 3: PDF generation (CPU-bound, run in executor) ───────────────────
    output_filename = generate_report_filename(company_name)
    try:
        t0 = time.perf_counter()
        logger.info(f"[GENERATE   ] [3/3] Generating PDF: {output_filename}")
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                functools.partial(generate_pdf, html_content, output_filename)
            ),
            timeout=60,
        )
        logger.info(
            f"[GENERATE   ] [3/3] PDF done in {time.perf_counter()-t0:.2f}s — "
            f"mode={result['mode']}  file={result['filename']}"
        )
    except asyncio.TimeoutError:
        logger.error("[GENERATE   ] [3/3] PDF generation timed out")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PDF generation timed out. Please try again.",
        )
    except Exception as exc:
        logger.error(f"[GENERATE   ] [3/3] PDF generation failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF generation failed: {exc}",
        )

    total_elapsed = time.perf_counter() - t_pipeline_start
    logger.info(
        f"[GENERATE OK] Pipeline complete — "
        f"company={company_name!r}  "
        f"file={result['filename']}  "
        f"mode={result['mode']}  "
        f"total={total_elapsed:.2f}s"
    )

    return {
        "success":          True,
        "filename":         result["filename"],
        "mode":             result["mode"],
        "company":          company_name,
        "charts_generated": [k for k, v in chart_paths.items() if v],
        "elapsed_sec":      round(total_elapsed, 2),
    }
