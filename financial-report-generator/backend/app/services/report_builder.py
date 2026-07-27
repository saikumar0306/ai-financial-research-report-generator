"""
report_builder.py — Renders the Geojit-style HTML report from extracted data + chart paths.

Uses Jinja2 to inject structured data into the report_template.html template.
Charts are embedded as base64 data URIs so the HTML is fully self-contained.
"""

import base64
from pathlib import Path
from datetime import datetime
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import settings
from app.utils.logger import get_logger
from app.utils.helpers import safe_get, ensure_list

logger = get_logger(__name__)


def build_html_report(
    data: dict,
    chart_paths: dict[str, Optional[str]],
) -> str:
    """
    Render the full HTML report string.

    Args:
        data:        Validated financial data dict from ai_extractor.
        chart_paths: Dict mapping chart name → PNG file path (or None).

    Returns:
        Rendered HTML string (fully self-contained with base64 charts).
    """
    env = Environment(
        loader=FileSystemLoader(str(settings.TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )

    # Register custom filters
    env.filters["na"] = _na_filter
    env.filters["percent"] = _percent_filter

    template = env.get_template("report_template.html")

    # Encode charts as base64
    chart_b64: dict[str, Optional[str]] = {}
    for chart_name, path in chart_paths.items():
        chart_b64[chart_name] = _image_to_b64(path)

    context = {
        # Company basics
        "company_name":    data.get("company_name", "N/A"),
        "recommendation":  data.get("recommendation", "N/A"),
        "industry":        data.get("industry", "N/A"),
        "market_cap":      data.get("market_cap", "N/A"),
        "current_price":   data.get("current_price", "N/A"),
        "target_price":    data.get("target_price", "N/A"),
        "report_date":     datetime.now().strftime("%d %B %Y"),

        # Narrative
        "business_summary":  data.get("business_summary", ""),
        "investment_thesis": data.get("investment_thesis", ""),
        "future_outlook":    data.get("future_outlook", ""),
        "valuation":         data.get("valuation", ""),

        # Lists
        "strengths":        ensure_list(data.get("strengths", [])),
        "risks":            ensure_list(data.get("risks", [])),
        "highlights":       ensure_list(data.get("highlights", [])),
        "peer_comparison":  data.get("peer_comparison", []),

        # Financial tables
        "ft": data.get("financial_tables", {}),

        # Shareholding
        "shareholding": data.get("shareholding", {}),

        # Key metrics
        "key_metrics": data.get("key_metrics", {}),

        # Charts (base64 or None)
        "charts": chart_b64,

        # Recommendation styling
        "rec_color":  _recommendation_color(data.get("recommendation", "")),
        "rec_bg":     _recommendation_bg(data.get("recommendation", "")),
    }

    html = template.render(**context)
    logger.info(f"HTML report rendered ({len(html):,} chars)")
    return html


# ── Template filters ──────────────────────────────────────────────────────────

def _na_filter(value) -> str:
    """Return 'N/A' if value is empty/None, otherwise return value as-is."""
    if value is None or str(value).strip() in ("", "Not Available", "N/A"):
        return "N/A"
    return str(value)


def _percent_filter(value) -> str:
    """Format a numeric value as a percentage string."""
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return str(value)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _image_to_b64(path: Optional[str]) -> Optional[str]:
    """Read a PNG file and return a base64 data URI string."""
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        logger.warning(f"Chart file not found: {path}")
        return None
    try:
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except Exception as exc:
        logger.warning(f"Could not encode chart {path}: {exc}")
        return None


def _recommendation_color(rec: str) -> str:
    """Return hex text color for a recommendation badge."""
    rec_upper = rec.upper()
    mapping = {
        "BUY":        "#FFFFFF",
        "ACCUMULATE": "#FFFFFF",
        "HOLD":       "#FFFFFF",
        "REDUCE":     "#FFFFFF",
        "SELL":       "#FFFFFF",
    }
    return mapping.get(rec_upper, "#1E3A5F")


def _recommendation_bg(rec: str) -> str:
    """Return hex background color for a recommendation badge."""
    rec_upper = rec.upper()
    mapping = {
        "BUY":        "#27AE60",
        "ACCUMULATE": "#2ECC71",
        "HOLD":       "#F39C12",
        "REDUCE":     "#E67E22",
        "SELL":       "#E74C3C",
    }
    return mapping.get(rec_upper, "#1E3A5F")
