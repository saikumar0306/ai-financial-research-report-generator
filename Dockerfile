# ──────────────────────────────────────────────────────────────────────
# Dockerfile — Bull AI Financial Report Generator
#
# Multi-stage build:
#   Stage 1 (builder): Build React frontend
#   Stage 2 (runtime): Python FastAPI + WeasyPrint + built frontend
# ──────────────────────────────────────────────────────────────────────

# ── Stage 1: Frontend build ────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --silent
COPY frontend/ .
RUN npm run build

# ── Stage 2: Backend runtime ───────────────────────────────────────────
FROM python:3.11-slim

# WeasyPrint system dependencies (GTK / Cairo / Pango)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libcairo-gobject2 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy built frontend into backend's static serving path
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create output directories
RUN mkdir -p ./backend/charts ./backend/generated_reports

WORKDIR /app/backend

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/backend

EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/api/health')"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
