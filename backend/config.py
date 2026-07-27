"""
config.py — Central configuration loaded from environment variables.
All settings are accessed through the `settings` singleton.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

class Settings:
    # ── Gemini AI ──────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip(' "\'')
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip(' "\'')

    # ── CORS ───────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
        if o.strip()
    ]

    # ── File storage ───────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).parent
    CHARTS_DIR: Path = BASE_DIR / os.getenv("CHARTS_DIR", "charts")
    REPORTS_DIR: Path = BASE_DIR / os.getenv("REPORTS_DIR", "generated_reports")
    TEMPLATES_DIR: Path = BASE_DIR / "templates"

    # ── Allowed upload extensions ─────────────────────────────────────────
    ALLOWED_EXTENSIONS: set[str] = {".pdf", ".txt", ".csv"}
    MAX_UPLOAD_MB: int = 20

    # ── Logging ────────────────────────────────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def ensure_dirs(self) -> None:
        """Create output directories if they don't exist."""
        self.CHARTS_DIR.mkdir(parents=True, exist_ok=True)
        self.REPORTS_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
