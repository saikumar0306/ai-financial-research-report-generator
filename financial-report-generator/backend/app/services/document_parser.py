"""
document_parser.py — Detects file type and extracts clean text content.

Supported formats:
    - PDF  → PyMuPDF (text) + pdfplumber (tables)
    - CSV  → pandas
    - TXT  → plain read

Performance notes:
    - This module runs synchronously and MUST be called inside run_in_executor()
      from async FastAPI endpoints to avoid blocking the event loop.
    - MAX_TEXT_CHARS is set to 30,000 to capture enough context for AI extraction
      while staying within model token limits.
"""

import io
import time
from pathlib import Path

import pandas as pd
import pdfplumber
import fitz  # PyMuPDF

from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Max characters sent to AI ─────────────────────────────────────────────────
# 30k chars ≈ ~7,500 tokens — fits within Gemini Flash context limits while
# capturing far more financial content than the original 12k limit.
MAX_TEXT_CHARS = 30_000


def parse_document(file_bytes: bytes, filename: str) -> str:
    """
    Parse an uploaded document and return clean extracted text.

    This is a synchronous, CPU-bound function.
    Callers inside async endpoints MUST use run_in_executor.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        filename:   Original filename (used for extension detection).

    Returns:
        Extracted text string (truncated to MAX_TEXT_CHARS).

    Raises:
        ValueError: If the file extension is unsupported or parsing fails.
    """
    t_start = time.perf_counter()
    ext = Path(filename).suffix.lower()
    logger.info(f"[PARSE START] file={filename!r}  ext={ext}  size={len(file_bytes):,} bytes")

    if ext == ".pdf":
        text = _parse_pdf(file_bytes)
    elif ext == ".csv":
        text = _parse_csv(file_bytes)
    elif ext == ".txt":
        text = _parse_txt(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {ext!r}. Allowed: .pdf, .csv, .txt")

    if not text or not text.strip():
        raise ValueError(
            f"Could not extract any text from '{filename}'. "
            "The file may be image-only, password-protected, or corrupted."
        )

    cleaned   = _clean_text(text)
    truncated = _truncate_text(cleaned, MAX_TEXT_CHARS)

    elapsed = time.perf_counter() - t_start
    logger.info(
        f"[PARSE DONE ] file={filename!r}  "
        f"raw={len(cleaned):,} chars  "
        f"sent={len(truncated):,} chars  "
        f"elapsed={elapsed:.2f}s"
    )
    return truncated


# ── Internal parsers ──────────────────────────────────────────────────────────

def _parse_pdf(file_bytes: bytes) -> str:
    """
    Extract text and tables from a PDF using PyMuPDF + pdfplumber.

    Strategy:
        1. PyMuPDF  → fast text layer extraction, preserves reading order.
        2. pdfplumber → structured table extraction (complements text).
    Tables are formatted as readable strings and appended after the text.
    """
    sections: list[str] = []
    table_sections: list[str] = []

    # ── Phase 1: Text via PyMuPDF ──────────────────────────────────────────────
    try:
        t0 = time.perf_counter()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        total_pages = len(doc)
        for page_num, page in enumerate(doc, start=1):
            page_text = page.get_text("text")
            if page_text.strip():
                sections.append(f"=== PAGE {page_num}/{total_pages} ===\n{page_text.strip()}")
        doc.close()
        logger.debug(
            f"PyMuPDF: extracted {len(sections)} text pages in {time.perf_counter()-t0:.2f}s"
        )
    except Exception as exc:
        logger.warning(f"PyMuPDF text extraction failed: {exc} — will rely on pdfplumber")

    # ── Phase 2: Tables via pdfplumber ─────────────────────────────────────────
    try:
        t0 = time.perf_counter()
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                for t_idx, table in enumerate(tables, start=1):
                    if not table or len(table) < 2:
                        continue
                    try:
                        # Use first row as header, handle None cells
                        header = [str(c or "").strip() for c in table[0]]
                        rows   = [[str(c or "").strip() for c in row] for row in table[1:]]
                        df     = pd.DataFrame(rows, columns=header)
                        table_str = df.to_string(index=False)
                        table_sections.append(
                            f"=== TABLE (Page {page_num}, Table {t_idx}) ===\n{table_str}"
                        )
                    except Exception as te:
                        logger.debug(f"Table formatting error p{page_num}t{t_idx}: {te}")
                        continue

        logger.debug(
            f"pdfplumber: extracted {len(table_sections)} tables in {time.perf_counter()-t0:.2f}s"
        )
    except Exception as exc:
        logger.warning(f"pdfplumber table extraction failed: {exc}")

    # Combine: text first, then tables
    all_sections = sections + table_sections
    if not all_sections:
        return ""

    combined = "\n\n".join(all_sections)
    logger.info(
        f"PDF extraction complete: {len(sections)} text pages, "
        f"{len(table_sections)} tables, "
        f"{len(combined):,} raw chars"
    )
    return combined


def _parse_csv(file_bytes: bytes) -> str:
    """Read a CSV file via pandas and convert to a readable, AI-friendly string."""
    try:
        df = pd.read_csv(io.BytesIO(file_bytes))
        logger.debug(f"CSV loaded: {df.shape[0]} rows × {df.shape[1]} cols")
        summary = (
            f"CSV Financial Data — {df.shape[0]} rows, {df.shape[1]} columns\n"
            f"Columns: {', '.join(str(c) for c in df.columns)}\n\n"
            f"{df.to_string(index=False)}"
        )
        return summary
    except Exception as exc:
        logger.error(f"CSV parsing failed: {exc}")
        raise ValueError(f"Failed to parse CSV file: {exc}") from exc


def _parse_txt(file_bytes: bytes) -> str:
    """Decode a plain-text file, trying common encodings in order."""
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            text = file_bytes.decode(encoding)
            logger.debug(f"TXT decoded as {encoding}: {len(text):,} chars")
            return text
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not decode text file with any supported encoding (tried utf-8, latin-1, cp1252).")


def _clean_text(text: str) -> str:
    """Remove excessive whitespace, null bytes, and other noise."""
    import re
    text = text.replace("\x00", "")           # remove null bytes
    text = re.sub(r"\n{4,}", "\n\n\n", text)  # collapse excessive blank lines
    text = re.sub(r"[ \t]{3,}", "  ", text)   # collapse excessive inline spaces
    text = re.sub(r"\r\n", "\n", text)         # normalize line endings
    return text.strip()


def _truncate_text(text: str, max_chars: int) -> str:
    """
    Truncate text to max_chars, preserving whole lines where possible.
    Adds a clear marker so the AI knows the document continues.
    """
    if len(text) <= max_chars:
        return text

    # Try to truncate at a newline boundary
    truncated = text[:max_chars]
    last_newline = truncated.rfind("\n")
    if last_newline > max_chars * 0.9:  # Only use newline if near the end
        truncated = truncated[:last_newline]

    return (
        truncated
        + "\n\n"
        + "[... DOCUMENT TRUNCATED FOR PROCESSING — extract data from above content only ...]"
    )
