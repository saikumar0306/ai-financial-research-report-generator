# Bull AI — Financial Research Report Generator

> **AI-powered equity research report generator** — Upload any financial document and get a professional Geojit-style PDF report in seconds.

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-blue?logo=react)](https://react.dev)
[![Gemini](https://img.shields.io/badge/Gemini_SDK-google--genai-orange?logo=google)](https://github.com/googleapis/python-genai)

---

## Features

- 📄 **Multi-format input** — PDF, TXT, CSV
- 🤖 **Gemini AI extraction** — Structured JSON from any document
- 📊 **Auto chart generation** — Revenue, EBITDA, Net Profit, Margin trends
- 📑 **Geojit-style report** — Professional equity research layout
- 🖨️ **PDF export** — WeasyPrint-powered production PDF
- 🚀 **HF Spaces ready** — Single Docker container deployment

---

## Project Structure

```
financial-report-generator/
├── backend/
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Settings / env vars
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── routers/
│   │   │   ├── upload.py          # POST /api/upload
│   │   │   ├── extract.py         # POST /api/extract
│   │   │   ├── generate.py        # POST /api/generate
│   │   │   └── files.py           # GET /api/download, /api/preview
│   │   ├── services/
│   │   │   ├── document_parser.py # PDF/CSV/TXT → text
│   │   │   ├── ai_extractor.py    # Gemini AI → JSON
│   │   │   ├── chart_generator.py # matplotlib charts
│   │   │   ├── report_builder.py  # Jinja2 HTML rendering
│   │   │   └── pdf_generator.py   # WeasyPrint → PDF
│   │   └── utils/
│   │       ├── logger.py
│   │       └── helpers.py
│   └── templates/
│       └── report_template.html   # Geojit-style report
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── UploadForm.jsx
│   │   │   ├── ProgressIndicator.jsx
│   │   │   ├── LoadingSpinner.jsx
│   │   │   └── ReportPreview.jsx
│   │   ├── pages/HomePage.jsx
│   │   ├── hooks/useReportGenerator.js
│   │   └── services/api.js
│   └── package.json
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- Node.js 18+
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

### 1. Clone and setup

```bash
git clone <your-repo-url>
cd financial-report-generator
```

### 2. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here
```

### 3. Start the backend

```bash
# From the backend/ directory
python main.py
# or
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/api/docs

### 4. Frontend setup

```bash
cd frontend
npm install
npm run dev
```

Open: http://localhost:5173

---

## Environment Variables

| Variable       | Required | Default             | Description                        |
|----------------|----------|---------------------|------------------------------------|
| GEMINI_API_KEY | ✅ Yes   | —                   | Google Gemini API key              |
| GEMINI_MODEL   | ❌ No    | gemini-1.5-flash    | Gemini model to use                |
| CORS_ORIGINS   | ❌ No    | localhost:5173,3000 | Allowed frontend origins           |
| CHARTS_DIR     | ❌ No    | charts              | Chart PNG output directory         |
| REPORTS_DIR    | ❌ No    | generated_reports   | PDF/HTML output directory          |
| LOG_LEVEL      | ❌ No    | INFO                | Logging level                      |

---

## API Reference

| Method | Endpoint                   | Description                          |
|--------|----------------------------|--------------------------------------|
| POST   | `/api/upload`              | Upload document → return text        |
| POST   | `/api/extract`             | Text → Gemini AI → JSON              |
| POST   | `/api/generate`            | JSON → charts + HTML + PDF           |
| GET    | `/api/download/{filename}` | Download generated report            |
| GET    | `/api/preview/{filename}`  | Preview report in browser            |
| GET    | `/api/health`              | Health check                         |

---

## WeasyPrint Setup (Windows)

WeasyPrint requires GTK system libraries. On Windows, use one of:

### Option A — Docker (recommended)
```bash
docker-compose up --build
# App available at http://localhost:8000
```

### Option B — GTK for Windows
Download and install [MSYS2](https://www.msys2.org/) then:
```bash
pacman -S mingw-w64-x86_64-gtk3
# Add C:\msys64\mingw64\bin to your PATH
```

### Option C — HTML fallback
If WeasyPrint fails, the app automatically saves `.html` instead of `.pdf`.
You can print it as PDF from your browser (Print → Save as PDF).

---

## Deploy to Hugging Face Spaces

1. Create a new Space → Docker SDK
2. Push this repository
3. Add `GEMINI_API_KEY` in Space Secrets
4. The Dockerfile handles everything (port 7860)

```bash
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/bull-ai
git push hf main
```

---

## Supported Document Types

| Format | Parser         | Tables | Notes                     |
|--------|----------------|--------|---------------------------|
| PDF    | PyMuPDF + pdfplumber | ✅ | Best results              |
| CSV    | pandas         | ✅     | Financial data tables     |
| TXT    | Plain text     | ❌     | Annual reports, filings   |

---

## License

License —  killada sai kuamr 

---

*Built with ❤️ using Google Gemini AI, FastAPI, React, and WeasyPrint.*
