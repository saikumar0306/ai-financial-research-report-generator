"""
chart_generator.py — Generates financial trend charts as PNG files using matplotlib.

Charts generated:
    - Revenue Trend
    - EBITDA Trend
    - Net Profit Trend
    - Margin Trend (Operating & Net Margin)

All charts are saved to the CHARTS_DIR and returned as file paths.
"""

import uuid
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend (no display needed)
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

from config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# ── Color palette ─────────────────────────────────────────────────────────────
COLORS = {
    "primary":   "#1E3A5F",   # Deep navy
    "accent":    "#E8A020",   # Gold
    "green":     "#2ECC71",
    "red":       "#E74C3C",
    "purple":    "#8E44AD",
    "teal":      "#16A085",
    "bg":        "#F8F9FA",
    "grid":      "#DEE2E6",
}


def generate_all_charts(financial_tables: dict) -> dict[str, Optional[str]]:
    """
    Generate all available financial charts from the extracted financial tables.

    Args:
        financial_tables: Dict of metric → list of {year, value} dicts.

    Returns:
        Dict mapping chart_name → absolute path string (or None if no data).
    """
    settings.ensure_dirs()
    session_id = uuid.uuid4().hex[:8]

    chart_paths: dict[str, Optional[str]] = {
        "revenue":    None,
        "ebitda":     None,
        "net_profit": None,
        "margins":    None,
    }

    ft = financial_tables or {}

    # Revenue bar chart
    revenue_data = ft.get("revenue", [])
    if _has_data(revenue_data):
        chart_paths["revenue"] = _bar_chart(
            data=revenue_data,
            title="Revenue Trend (₹ Cr)",
            ylabel="Revenue (₹ Cr)",
            color=COLORS["primary"],
            session_id=session_id,
            name="revenue",
        )

    # EBITDA bar chart
    ebitda_data = ft.get("ebitda", [])
    if _has_data(ebitda_data):
        chart_paths["ebitda"] = _bar_chart(
            data=ebitda_data,
            title="EBITDA Trend (₹ Cr)",
            ylabel="EBITDA (₹ Cr)",
            color=COLORS["teal"],
            session_id=session_id,
            name="ebitda",
        )

    # Net Profit bar chart
    profit_data = ft.get("net_profit", [])
    if _has_data(profit_data):
        chart_paths["net_profit"] = _bar_chart(
            data=profit_data,
            title="Net Profit Trend (₹ Cr)",
            ylabel="Net Profit (₹ Cr)",
            color=COLORS["green"],
            session_id=session_id,
            name="net_profit",
        )

    # Margin trend (dual line chart)
    op_margin = ft.get("operating_margin", [])
    net_margin = ft.get("net_margin", [])
    if _has_data(op_margin) or _has_data(net_margin):
        chart_paths["margins"] = _margin_chart(
            op_margin=op_margin,
            net_margin=net_margin,
            session_id=session_id,
        )

    logger.info(
        "[CHARTS OK ] Chart generation complete — "
        + ", ".join(f"{k}={'OK' if v else 'FAIL'}" for k, v in chart_paths.items())
    )

    return chart_paths


# ── Chart helpers ─────────────────────────────────────────────────────────────

def _has_data(series: list) -> bool:
    """Return True if series is a non-empty list with at least one valid value."""
    if not isinstance(series, list) or not series:
        return False
    return any(
        isinstance(row, dict) and row.get("value") is not None
        for row in series
    )


def _extract_xy(data: list[dict]) -> tuple[list[str], list[float]]:
    """Extract parallel (year, value) lists from a list of {year, value} dicts."""
    years, values = [], []
    for row in data:
        if isinstance(row, dict):
            y = str(row.get("year", ""))
            v = row.get("value")
            try:
                v = float(v)
                years.append(y)
                values.append(v)
            except (TypeError, ValueError):
                continue
    return years, values


def _bar_chart(
    data: list[dict],
    title: str,
    ylabel: str,
    color: str,
    session_id: str,
    name: str,
) -> Optional[str]:
    """Render a styled bar chart and save to disk."""
    years, values = _extract_xy(data)
    if not years:
        return None

    fig, ax = plt.subplots(figsize=(7, 4), facecolor=COLORS["bg"])
    ax.set_facecolor(COLORS["bg"])

    bars = ax.bar(years, values, color=color, width=0.55, zorder=3, edgecolor="white", linewidth=0.8)

    # Value labels on bars
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max(values) * 0.01,
            f"{val:,.0f}",
            ha="center", va="bottom",
            fontsize=8, fontweight="bold", color=COLORS["primary"],
        )

    # Trend line
    if len(values) > 2:
        x_idx = np.arange(len(values))
        z = np.polyfit(x_idx, values, 1)
        p = np.poly1d(z)
        ax.plot(years, p(x_idx), "--", color=COLORS["accent"], linewidth=1.5, zorder=4, label="Trend")
        ax.legend(fontsize=8)

    _style_axes(ax, title, ylabel)
    return _save_fig(fig, name, session_id)


def _margin_chart(
    op_margin: list[dict],
    net_margin: list[dict],
    session_id: str,
) -> Optional[str]:
    """Render a dual-line margin trend chart and save to disk."""
    fig, ax = plt.subplots(figsize=(7, 4), facecolor=COLORS["bg"])
    ax.set_facecolor(COLORS["bg"])

    plotted = False

    if _has_data(op_margin):
        yrs, vals = _extract_xy(op_margin)
        if yrs:
            ax.plot(yrs, vals, "o-", color=COLORS["primary"], linewidth=2.5,
                    markersize=6, label="Operating Margin (%)", zorder=3)
            plotted = True

    if _has_data(net_margin):
        yrs, vals = _extract_xy(net_margin)
        if yrs:
            ax.plot(yrs, vals, "s--", color=COLORS["accent"], linewidth=2.5,
                    markersize=6, label="Net Margin (%)", zorder=3)
            plotted = True

    if not plotted:
        plt.close(fig)
        return None

    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.legend(fontsize=8, loc="upper left")
    _style_axes(ax, "Margin Trend (%)", "Margin (%)")
    return _save_fig(fig, "margins", session_id)


def _style_axes(ax: plt.Axes, title: str, ylabel: str) -> None:
    """Apply consistent styling to chart axes."""
    ax.set_title(title, fontsize=12, fontweight="bold", color=COLORS["primary"], pad=12)
    ax.set_ylabel(ylabel, fontsize=9, color="#555555")
    ax.tick_params(axis="x", labelsize=8, rotation=15)
    ax.tick_params(axis="y", labelsize=8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.grid(axis="y", color=COLORS["grid"], linewidth=0.7, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLORS["grid"])
    ax.spines["bottom"].set_color(COLORS["grid"])
    plt.tight_layout(pad=1.5)


def _save_fig(fig: plt.Figure, name: str, session_id: str) -> str:
    """Save figure to CHARTS_DIR and return absolute path string."""
    filename = f"{name}_{session_id}.png"
    filepath = settings.CHARTS_DIR / filename
    fig.savefig(filepath, dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.debug(f"Chart saved: {filepath}")
    return str(filepath.resolve())
