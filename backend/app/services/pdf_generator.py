"""
pdf_generator.py — Converts an HTML string to a PDF file.

PDF Generation Strategy (ordered by reliability on Windows):
    1. xhtml2pdf  — pure Python, no native deps, works on Windows out of the box.
    2. reportlab  — pure Python programmatic PDF from parsed HTML data.
    3. pdfkit     — requires wkhtmltopdf binary in PATH.
    4. WeasyPrint — requires GTK3/Pango DLLs (Linux / macOS friendly).

The output deliverable is strictly a PDF file saved in REPORTS_DIR.
"""

import io
import os
import re
import sys
import time
from pathlib import Path

from config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ── Ensure GTK DLLs are accessible on Windows for WeasyPrint (last-resort) ───
if sys.platform == "win32":
    gtk_candidate_dirs = [
        r"C:\Program Files\GTK3-Runtime Win64\bin",
        r"C:\Program Files (x86)\GTK3-Runtime Win64\bin",
        r"C:\GTK3-Runtime\bin",
        r"C:\msys64\ucrt64\bin",
        r"C:\msys64\mingw64\bin",
    ]
    for d in gtk_candidate_dirs:
        if os.path.exists(d):
            try:
                os.add_dll_directory(d)
                os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
                logger.info(f"[PDF GEN    ] Added GTK DLL directory: {d}")
            except Exception as exc:
                logger.warning(f"[PDF GEN    ] Could not add GTK DLL directory {d}: {exc}")


# ── CSS replacements so xhtml2pdf can render the template ────────────────────

# Inline values for CSS custom properties used in the template
_CSS_VAR_MAP = {
    "--primary":     "#1E3A5F",
    "--primary-lt":  "#2C5282",
    "--accent":      "#C8962A",
    "--accent-lt":   "#E8B84B",
    "--success":     "#27AE60",
    "--danger":      "#E74C3C",
    "--warning":     "#F39C12",
    "--bg":          "#F7F9FC",
    "--white":       "#FFFFFF",
    "--text":        "#1A202C",
    "--text-muted":  "#718096",
    "--border":      "#E2E8F0",
    "--shadow":      "rgba(0,0,0,0.06)",
}

# Replacement CSS that xhtml2pdf understands (no grid/flex/custom props)
_XHTML2PDF_COMPAT_CSS = """
/* xhtml2pdf compat overrides — replaces grid/flex layouts with table/block */

/* Reset display:flex / display:grid to block so xhtml2pdf doesn't choke */
.cover-header, .cover-strip, .metrics-bar,
.highlights-grid, .two-col, .charts-grid,
.ratios-grid, .shareholding-grid, .card-header,
.highlight-item, .rec-badge, .price-chip,
.ratio-card, .sh-card, .section-title {
    display: block;
}

/* Cover page — plain block layout */
.cover {
    background-color: #1E3A5F;
    color: white;
    padding: 36px 40px 28px;
    margin-bottom: 0;
}
.cover-company-name { font-size: 22pt; font-weight: bold; margin-bottom: 6px; color: white; }
.cover-industry     { font-size: 10pt; color: #ccddee; margin-bottom: 16px; }
.brand              { font-size: 13pt; font-weight: bold; color: #E8B84B; letter-spacing: 2px; }
.brand-sub          { font-size: 8pt; color: #aabbcc; margin-bottom: 12px; }
.rec-badge          { display: inline-block; padding: 6px 20px; border-radius: 6px;
                      font-size: 13pt; font-weight: bold; margin-bottom: 8px; }
.price-chip         { display: inline-block; border: 1px solid #aaaaaa; padding: 6px 14px;
                      margin-right: 8px; border-radius: 6px; }
.price-label        { font-size: 7pt; color: #aabbcc; text-transform: uppercase; }
.price-value        { font-size: 11pt; font-weight: bold; color: white; }
.cover-footer       { margin-top: 16px; border-top: 1px solid rgba(255,255,255,0.2);
                      padding-top: 8px; font-size: 7.5pt; color: #aabbcc; }

/* Metrics bar — table-based for xhtml2pdf */
.metrics-bar {
    background-color: #1E3A5F;
    padding: 10px 20px;
    margin: 0;
}
.metric-item  { display: inline; padding: 0 12px; border-right: 1px solid #456; font-size: 8pt; }
.metric-label { color: #aabbcc; text-transform: uppercase; font-size: 6.5pt; }
.metric-value { color: #E8B84B; font-weight: bold; }
.metric-divider { display: none; }

/* Highlights — single-column list */
.highlights-band { background-color: #EBF4FF; border-left: 4px solid #C8962A; padding: 14px 20px; }
.highlights-grid { margin-top: 8px; }
.highlight-item  { margin-bottom: 6px; font-size: 9pt; padding-left: 12px; }

/* Strengths & Risks — stack vertically */
.two-col           { width: 100%; }
.card              { border: 1px solid #E2E8F0; border-radius: 6px; padding: 14px; margin-bottom: 12px; }
.card-strengths    { background-color: #F0FFF4; border-color: #9AE6B4; }
.card-risks        { background-color: #FFF5F5; border-color: #FEB2B2; }
.card-strengths .card-header { color: #276749; font-weight: bold; margin-bottom: 8px; }
.card-risks .card-header     { color: #9B2335; font-weight: bold; margin-bottom: 8px; }

/* Charts — single column */
.charts-grid    { width: 100%; }
.chart-container { border: 1px solid #E2E8F0; border-radius: 6px; margin-bottom: 16px; }
.chart-title    { background-color: #1E3A5F; color: white; padding: 6px 12px; font-size: 8pt; font-weight: bold; }
.chart-container img { width: 100%; }
.chart-placeholder { padding: 20px; text-align: center; color: #718096; font-style: italic; }

/* Ratios — 3-per-row inline */
.ratios-grid     { margin-top: 8px; }
.ratio-card      { display: inline-block; width: 30%; border: 1px solid #E2E8F0; border-radius: 6px;
                   padding: 10px 12px; margin: 4px; background-color: #F7F9FC;
                   vertical-align: top; }
.ratio-card-label { font-size: 7pt; color: #718096; text-transform: uppercase; display: block; }
.ratio-card-value { font-size: 13pt; font-weight: bold; color: #1E3A5F; display: block; margin-top: 2px; }

/* Shareholding — 4-per-row inline */
.shareholding-grid { margin-top: 8px; }
.sh-card   { display: inline-block; width: 22%; border: 1px solid #E2E8F0; border-radius: 6px;
             padding: 10px; margin: 4px; background-color: #F7F9FC;
             text-align: center; vertical-align: top; }
.sh-label  { font-size: 7pt; color: #718096; text-transform: uppercase; display: block; }
.sh-value  { font-size: 14pt; font-weight: bold; color: #1E3A5F; display: block; margin-top: 4px; }

/* Section title — no flex */
.section-title {
    font-size: 11pt; font-weight: bold; color: #1E3A5F;
    text-transform: uppercase; letter-spacing: 1px;
    margin-bottom: 14px; padding-bottom: 8px;
    border-bottom: 2px solid #C8962A;
    border-left: 4px solid #C8962A; padding-left: 8px;
}
.section-title::before { display: none; }

/* Remove Google Fonts import (xhtml2pdf can't fetch it) */
"""

_GOOGLE_FONTS_RE = re.compile(
    r"@import\s+url\(['\"]https://fonts\.googleapis\.com[^)]*\)['\"]?\s*;?",
    re.IGNORECASE,
)

_CSS_VAR_USE_RE = re.compile(r"var\(([^)]+)\)")


def _resolve_css_vars(css_text: str, var_map: dict) -> str:
    """Replace var(--name) references with their literal values."""
    def replacer(m: re.Match) -> str:
        var_name = m.group(1).strip().split(",")[0].strip()
        return str(var_map.get(var_name, m.group(0)))
    return _CSS_VAR_USE_RE.sub(replacer, css_text)


def _sanitize_html_for_xhtml2pdf(html: str) -> str:
    """
    Patch the rendered HTML so xhtml2pdf can produce a reasonable PDF.

    Changes made:
    - Remove Google Fonts @import (network unavailable during render)
    - Resolve CSS custom properties (var(--x)) to literal values
    - Inject xhtml2pdf-compatible override CSS that replaces grid/flex layouts
    - Remove :root block (xhtml2pdf doesn't support CSS custom properties)
    - Remove ALL ::before / ::after pseudo-element rules (unicode content crashes xhtml2pdf)
    - Remove unsupported @media rules
    """
    # 1. Remove Google Fonts @import
    html = _GOOGLE_FONTS_RE.sub("", html)

    # 2. Resolve var() references in inline styles / the <style> block
    html = _resolve_css_vars(html, _CSS_VAR_MAP)

    # 3. Remove :root block (xhtml2pdf doesn't understand CSS custom properties)
    html = re.sub(r":root\s*\{[^}]*\}", "", html, flags=re.DOTALL)

    # 4. Remove ALL ::before and ::after pseudo-element CSS rules.
    #    xhtml2pdf crashes or mis-renders when content: has Unicode characters
    #    like '●', '▲', '▼' (the bullet icons used in the template).
    html = re.sub(
        r"[^{}]+::(before|after)\s*\{[^}]*\}",
        "",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )

    # 5. Remove unsupported @media at-rules
    html = re.sub(r"@media[^{]*\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", "", html, flags=re.DOTALL)

    # 6. Inject xhtml2pdf-compatible override CSS just before </style>
    html = html.replace("</style>", _XHTML2PDF_COMPAT_CSS + "\n</style>", 1)

    return html


# ── Lazy backend loaders ──────────────────────────────────────────────────────

def _get_xhtml2pdf():
    try:
        from xhtml2pdf import pisa
        return pisa
    except ImportError:
        logger.debug("[PDF GEN    ] xhtml2pdf module not installed")
        return None


def _get_reportlab():
    try:
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        return True
    except ImportError:
        logger.debug("[PDF GEN    ] reportlab module not installed")
        return None


def _get_pdfkit():
    import shutil
    if not shutil.which("wkhtmltopdf"):
        logger.debug("[PDF GEN    ] wkhtmltopdf binary not found in PATH")
        return None
    try:
        import pdfkit
        return pdfkit
    except ImportError:
        logger.debug("[PDF GEN    ] pdfkit module not installed")
        return None


def _get_weasyprint():
    try:
        from weasyprint import HTML as WeasyHTML
        return WeasyHTML
    except Exception as e:
        logger.debug(f"[PDF GEN    ] WeasyPrint unavailable: {e}")
        return None


# ── Main public function ──────────────────────────────────────────────────────

def generate_pdf(html_content: str, output_filename: str) -> dict:
    """
    Convert HTML content to a PDF and save it to REPORTS_DIR.

    Tries backends in this order (most reliable on Windows first):
        1. xhtml2pdf  — pure Python
        2. reportlab  — pure Python (structured fallback)
        3. pdfkit     — needs wkhtmltopdf
        4. WeasyPrint — needs GTK3/Pango

    Raises RuntimeError if all backends fail.

    Args:
        html_content:    Rendered HTML string from report_builder.
        output_filename: Target filename (must end in .pdf).

    Returns:
        Dict with:
            - "pdf_path": str — absolute path to the saved file
            - "filename": str — the filename (.pdf)
            - "mode":     str — which backend succeeded
    """
    settings.ensure_dirs()

    if not output_filename.endswith(".pdf"):
        output_filename = output_filename.rsplit(".", 1)[0] + ".pdf"

    t_start = time.perf_counter()
    logger.info(f"[PDF GEN    ] Starting PDF generation: {output_filename}")

    # ── Backend 1: xhtml2pdf (primary on Windows) ─────────────────────────────
    pisa_mod = _get_xhtml2pdf()
    if pisa_mod:
        result = _try_xhtml2pdf(pisa_mod, html_content, output_filename)
        if result:
            elapsed = time.perf_counter() - t_start
            logger.info(f"[PDF GEN OK ] xhtml2pdf — {output_filename} in {elapsed:.2f}s")
            return result

    # ── Backend 2: reportlab (pure Python fallback) ───────────────────────────
    if _get_reportlab():
        result = _try_reportlab(html_content, output_filename)
        if result:
            elapsed = time.perf_counter() - t_start
            logger.info(f"[PDF GEN OK ] reportlab — {output_filename} in {elapsed:.2f}s")
            return result

    # ── Backend 3: pdfkit (needs wkhtmltopdf binary) ──────────────────────────
    pdfkit_mod = _get_pdfkit()
    if pdfkit_mod:
        result = _try_pdfkit(pdfkit_mod, html_content, output_filename)
        if result:
            elapsed = time.perf_counter() - t_start
            logger.info(f"[PDF GEN OK ] pdfkit — {output_filename} in {elapsed:.2f}s")
            return result

    # ── Backend 4: WeasyPrint (needs GTK3 on Windows) ─────────────────────────
    weasyprint_cls = _get_weasyprint()
    if weasyprint_cls:
        result = _try_weasyprint(weasyprint_cls, html_content, output_filename)
        if result:
            elapsed = time.perf_counter() - t_start
            logger.info(f"[PDF GEN OK ] WeasyPrint — {output_filename} in {elapsed:.2f}s")
            return result

    elapsed = time.perf_counter() - t_start
    error_msg = (
        f"PDF generation failed after {elapsed:.2f}s. "
        "All PDF backends failed or are not configured. "
        "Ensure xhtml2pdf is installed: pip install xhtml2pdf"
    )
    logger.error(f"[PDF GEN ERROR] {error_msg}")
    raise RuntimeError(error_msg)


# ── Backend implementations ───────────────────────────────────────────────────

def _try_xhtml2pdf(pisa_mod, html_content: str, output_filename: str) -> dict | None:
    """
    Attempt PDF generation via xhtml2pdf (pisa).

    Sanitizes the HTML first to remove CSS that xhtml2pdf doesn't support
    (CSS variables, grid, flex, @import, pseudo-elements on .cover).
    """
    out_path = settings.REPORTS_DIR / output_filename
    try:
        sanitized_html = _sanitize_html_for_xhtml2pdf(html_content)
        with open(out_path, "wb") as pdf_file:
            pisa_status = pisa_mod.CreatePDF(
                sanitized_html,
                dest=pdf_file,
                encoding="utf-8",
            )
        if not pisa_status.err and out_path.exists() and out_path.stat().st_size > 100:
            return {
                "pdf_path": str(out_path.resolve()),
                "filename": output_filename,
                "mode":     "pdf",
            }
        # If pisa reported errors, log them and return None to try next backend
        logger.warning(f"[PDF GEN    ] xhtml2pdf reported errors (err={pisa_status.err}); "
                       "trying next backend")
        if out_path.exists():
            out_path.unlink(missing_ok=True)
    except Exception as exc:
        logger.warning(f"[PDF GEN    ] xhtml2pdf failed: {exc}")
        if out_path.exists():
            out_path.unlink(missing_ok=True)
    return None


def _try_reportlab(html_content: str, output_filename: str) -> dict | None:
    """
    Fallback: use reportlab to build a structured PDF by extracting text
    from the rendered HTML. Produces a clean, professional-looking document
    without needing any native libraries.
    """
    out_path = settings.REPORTS_DIR / output_filename
    try:
        from typing import Any, List  # noqa: F401 — used for story type below
        from reportlab.platypus import (  # type: ignore[import-untyped]
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
        from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore[import-untyped]
        from reportlab.lib import colors  # type: ignore[import-untyped]
        from reportlab.lib.units import mm  # type: ignore[import-untyped]

        doc = SimpleDocTemplate(
            str(out_path),
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
        )

        styles = getSampleStyleSheet()
        PRIMARY   = colors.HexColor("#1E3A5F")
        ACCENT    = colors.HexColor("#C8962A")
        LIGHT_BG  = colors.HexColor("#F7F9FC")
        BORDER    = colors.HexColor("#E2E8F0")

        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontSize=20,
            textColor=PRIMARY,
            spaceAfter=6,
            fontName="Helvetica-Bold",
        )
        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Heading2"],
            fontSize=11,
            textColor=PRIMARY,
            spaceBefore=16,
            spaceAfter=6,
            fontName="Helvetica-Bold",
            borderPad=4,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["BodyText"],
            fontSize=9,
            leading=14,
            spaceAfter=4,
        )
        small_style = ParagraphStyle(
            "Small",
            parent=styles["BodyText"],
            fontSize=7.5,
            textColor=colors.HexColor("#718096"),
            spaceAfter=2,
        )

        # Strip HTML tags for text extraction
        def strip_tags(text):
            return re.sub(r"<[^>]+>", " ", text or "").strip()

        # Extract key values from the rendered HTML via simple regex patterns
        def extract_between(pattern, html, default="N/A"):
            m = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            return strip_tags(m.group(1)).strip() if m else default

        company   = extract_between(r'class="cover-company-name"[^>]*>(.*?)</div>', html_content)
        industry  = extract_between(r'class="cover-industry"[^>]*>(.*?)</div>', html_content)
        rec       = extract_between(r'class="rec-badge"[^>]*>.*?<span[^>]*>(.*?)</span>', html_content)
        date_str  = extract_between(r'Report Date:\s*(.*?)</span>', html_content)
        biz_sum   = extract_between(r'Business Summary.*?<p[^>]*>(.*?)</p>', html_content)
        inv_thesis = extract_between(r'Investment Thesis.*?<p[^>]*>(.*?)</p>', html_content)
        valuation  = extract_between(r'class="valuation-box"[^>]*>(.*?)</div>', html_content)
        outlook    = extract_between(r'class="outlook-box"[^>]*>(.*?)</div>', html_content)

        story = []

        # ── Cover ──
        story.append(Paragraph("BULL AI — FINANCIAL RESEARCH REPORT", small_style))
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(company or "Financial Report", title_style))
        story.append(Paragraph(industry, body_style))
        story.append(Spacer(1, 2 * mm))

        rec_data = [[f"Recommendation: {rec}"]]
        rec_tbl = Table(rec_data, colWidths=[120 * mm])
        rec_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), ACCENT),
            ("TEXTCOLOR",  (0, 0), (-1, -1), colors.white),
            ("FONTNAME",   (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 13),
            ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("ROUNDEDCORNERS", [4]),
        ]))
        story.append(rec_tbl)
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(f"Report Date: {date_str}", small_style))
        story.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=8))

        def section(title, content):
            if content and content != "N/A":
                story.append(Paragraph(title.upper(), h2_style))
                story.append(HRFlowable(width="100%", thickness=1, color=ACCENT, spaceAfter=4))
                story.append(Paragraph(content[:3000], body_style))  # cap at 3000 chars
                story.append(Spacer(1, 3 * mm))

        section("Business Summary", biz_sum)
        section("Investment Thesis", inv_thesis)
        section("Valuation", valuation)
        section("Future Outlook", outlook)

        # ── Disclaimer footer note ──
        story.append(Spacer(1, 6 * mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
        story.append(Spacer(1, 2 * mm))
        story.append(Paragraph(
            "<b>Disclaimer:</b> This report is generated by an AI system for informational purposes only. "
            "It does not constitute financial advice. Investors should conduct their own due diligence "
            "and consult a qualified financial advisor before making investment decisions.",
            small_style,
        ))

        doc.build(story)

        if out_path.exists() and out_path.stat().st_size > 100:
            return {
                "pdf_path": str(out_path.resolve()),
                "filename": output_filename,
                "mode":     "pdf",
            }
    except Exception as exc:
        logger.warning(f"[PDF GEN    ] reportlab failed: {exc}")
        if out_path.exists():
            out_path.unlink(missing_ok=True)
    return None


def _try_pdfkit(pdfkit_mod, html_content: str, output_filename: str) -> dict | None:
    """Attempt PDF generation via pdfkit (wkhtmltopdf). Returns None on failure."""
    out_path = settings.REPORTS_DIR / output_filename
    try:
        options = {
            "page-size":                "A4",
            "margin-top":               "10mm",
            "margin-right":             "10mm",
            "margin-bottom":            "10mm",
            "margin-left":              "10mm",
            "encoding":                 "UTF-8",
            "enable-local-file-access": None,
            "quiet":                    "",
        }
        pdfkit_mod.from_string(html_content, str(out_path), options=options)
        if out_path.exists() and out_path.stat().st_size > 0:
            return {
                "pdf_path": str(out_path.resolve()),
                "filename": output_filename,
                "mode":     "pdf",
            }
    except Exception as exc:
        logger.warning(f"[PDF GEN    ] pdfkit failed: {exc}")
    return None


def _try_weasyprint(weasyprint_cls, html_content: str, output_filename: str) -> dict | None:
    """Attempt PDF generation via WeasyPrint. Returns None on failure."""
    out_path = settings.REPORTS_DIR / output_filename
    try:
        doc = weasyprint_cls(
            string=html_content,
            base_url=str(settings.REPORTS_DIR),
        )
        doc.write_pdf(str(out_path))
        return {
            "pdf_path": str(out_path.resolve()),
            "filename": output_filename,
            "mode":     "pdf",
        }
    except Exception as exc:
        logger.warning(f"[PDF GEN    ] WeasyPrint failed: {exc}")
        return None
