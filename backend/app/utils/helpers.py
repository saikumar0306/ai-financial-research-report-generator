"""
helpers.py — Reusable utility functions shared across the application.
"""

import re
import uuid
from datetime import datetime
from typing import Any


def safe_get(data: dict, *keys: str, default: Any = "N/A") -> Any:
    """
    Safely traverse a nested dict.

    Example:
        safe_get(data, "financial_tables", "revenue", default=[])
    """
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current if current not in (None, "", [], {}) else default


def sanitize_filename(name: str) -> str:
    """
    Convert a company name to a safe filename slug.

    Example:
        sanitize_filename("Reliance Industries Ltd.") → "reliance_industries_ltd"
    """
    slug = re.sub(r"[^\w\s-]", "", name.lower())
    slug = re.sub(r"[\s]+", "_", slug).strip("_")
    return slug[:60]  # max 60 chars


def generate_report_filename(company_name: str) -> str:
    """
    Generate a unique, timestamped PDF filename.

    Example:
        "reliance_industries_2024_07_01_a1b2c3.pdf"
    """
    slug = sanitize_filename(company_name)
    ts = datetime.now().strftime("%Y_%m_%d")
    uid = uuid.uuid4().hex[:6]
    return f"{slug}_{ts}_{uid}.pdf"


def format_currency(value: Any, symbol: str = "₹") -> str:
    """
    Format a numeric value as a currency string with Indian notation.

    Args:
        value: Numeric value or string
        symbol: Currency prefix (default ₹)

    Returns:
        Formatted string, or "N/A" if conversion fails.
    """
    try:
        num = float(str(value).replace(",", "").replace("₹", "").strip())
        return f"{symbol}{num:,.2f} Cr"
    except (ValueError, TypeError):
        return str(value) if value else "N/A"


def ensure_list(value: Any) -> list:
    """
    Ensure a value is returned as a list.

    - If already a list, return as-is.
    - If a string, wrap in a list.
    - If None/empty, return [].
    """
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def truncate_text(text: str, max_chars: int = 5000) -> str:
    """
    Truncate text to a maximum character count for AI prompt safety.
    Adds an ellipsis if truncated.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated for processing]"
