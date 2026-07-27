"""
main.py — FastAPI application entry point.

Registers all routers, configures CORS, and runs startup checks.
"""

import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure the backend root is on the Python path (for config.py and app/)
sys.path.insert(0, str(Path(__file__).parent))

import google.genai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from config import settings
from app.routers import upload, extract, generate, files
from app.utils.logger import get_logger

logger = get_logger("bull_ai.main")


# ── Lifespan event handler ───────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    sdk_version = getattr(genai, "__version__", "unknown")
    api_key_status = "Loaded [OK]" if settings.GEMINI_API_KEY else "MISSING [WARNING]"

    startup_msg = (
        "\n" + "=" * 60 + "\n"
        "  Bull AI Financial Report Generator — STARTED\n"
        f"  Gemini SDK     : google-genai (v{sdk_version})\n"
        f"  Selected Model : {settings.GEMINI_MODEL}\n"
        f"  API Key Loaded : {api_key_status}\n"
        f"  Charts Dir     : {settings.CHARTS_DIR}\n"
        f"  Reports Dir    : {settings.REPORTS_DIR}\n"
        f"  CORS Origins   : {settings.CORS_ORIGINS}\n"
        + "=" * 60
    )
    print(startup_msg)
    logger.info(f"Gemini SDK: google-genai v{sdk_version} | Model: {settings.GEMINI_MODEL} | API Key: {api_key_status}")
    yield
    logger.info("Bull AI server shutting down.")



# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="Bull AI — Financial Research Report Generator",
        description=(
            "Upload a financial document (PDF/TXT/CSV), extract structured data "
            "using Google Gemini, and generate a Geojit-style research report PDF."
        ),
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Register Routers (supports both /api/path and /path) ───────────────────
    app.include_router(upload.router,   prefix="/api")
    app.include_router(extract.router,  prefix="/api")
    app.include_router(generate.router, prefix="/api")
    app.include_router(files.router,    prefix="/api")

    app.include_router(upload.router,   prefix="")
    app.include_router(extract.router,  prefix="")
    app.include_router(generate.router, prefix="")
    app.include_router(files.router,    prefix="")

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    @app.get("/api/health", tags=["Health"])
    async def health():
        return {
            "status": "ok",
            "service": "Bull AI Financial Report Generator",
            "gemini_sdk": "google-genai",
            "gemini_sdk_version": getattr(genai, "__version__", "unknown"),
            "gemini_model": settings.GEMINI_MODEL,
            "gemini_configured": bool(settings.GEMINI_API_KEY),
        }

    # ── Test Gemini Endpoint ──────────────────────────────────────────────────
    @app.get("/test-gemini", tags=["Testing"])
    @app.get("/api/test-gemini", tags=["Testing"])
    async def test_gemini():
        """
        Send a lightweight 'Hello' prompt to Gemini to verify API connectivity.
        """
        if not settings.GEMINI_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="GEMINI_API_KEY is not set. Please add your key to backend/.env",
            )

        models_to_try = [settings.GEMINI_MODEL]
        for fb in ["gemini-3.6-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]:
            if fb not in models_to_try:
                models_to_try.append(fb)

        last_error = None
        for model_name in models_to_try:
            try:
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                response = client.models.generate_content(
                    model=model_name,
                    contents="Hello",
                )
                return {
                    "status": "success",
                    "sdk": "google-genai",
                    "sdk_version": getattr(genai, "__version__", "unknown"),
                    "model": model_name,
                    "prompt": "Hello",
                    "response": (response.text or "").strip(),
                }
            except Exception as exc:
                logger.warning(f"Test Gemini call failed for model {model_name}: {exc}")
                last_error = exc

        logger.error(f"Test Gemini all models failed: {last_error}")
        raise HTTPException(
            status_code=500,
            detail=f"Gemini API test failed (tried {models_to_try}): {str(last_error)}",
        )

    # ── Serve built frontend (for production / HF Spaces) ────────────────────
    frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
    if frontend_dist.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dist)), name="static")
        logger.info(f"Serving static frontend from: {frontend_dist}")

    return app


app = create_app()


# ── Run directly ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    backend_dir = Path(__file__).parent
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(backend_dir / "app")],
        reload_excludes=["charts/*", "generated_reports/*", "*.png", "*.pdf", "*.html", "*.log"],
        log_level=settings.LOG_LEVEL.lower(),
    )
