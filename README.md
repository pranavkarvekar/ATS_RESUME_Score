# ATS Resume Analyzer v2

An intelligent resume screening system with hybrid scoring — combining rule-based skill matching, experience analysis, and LLM-powered contextual evaluation.

## Features

- 📄 **3-tier PDF extraction** — PyMuPDF → pdfplumber → Tesseract OCR fallback
- 🧠 **AI-powered parsing** — Groq LLM extracts structured data with 3-attempt retry + regex fallback
- ⚖️ **Weighted scoring** — Skill Match 35% + Experience 25% + Contextual AI Fit 40%
- 🔍 **Semantic skill matching** — 4-tier pipeline: exact → alias → cluster → embedding cosine similarity
- 💾 **Persistent storage** — SQLite with resume hash caching to avoid redundant LLM calls
- 📊 **Analytics dashboard** — score distributions, top missing skills, score trend over time
- 🔀 **Compare view** — side-by-side comparison of two candidates
- 🌙 **Dark/Light theme** — fully responsive UI

---

## Project Structure

```
ATS_Resume_score/
├── ats-v2/
│   ├── backend/
│   │   ├── config.py          # Centralized env var management
│   │   ├── main.py            # FastAPI app factory
│   │   ├── models/            # Pydantic schemas + SQLAlchemy DB models
│   │   ├── parsing/           # LLM parser, JSON sanitizer, regex fallback
│   │   ├── extraction/        # 3-tier PDF/DOCX extractor
│   │   ├── scoring/           # Skill match, experience, contextual AI scorer, embeddings
│   │   ├── routers/           # FastAPI route handlers
│   │   ├── db/                # SQLAlchemy async session + CRUD
│   │   ├── security/          # API key auth + rate limiter
│   │   └── tests/             # pytest test suite (61 tests)
│   └── frontend/
│       ├── index.html         # Analyze page
│       ├── pages/
│       │   ├── history.html   # Analysis history with search/filter
│       │   ├── detail.html    # Full analysis detail + feedback
│       │   ├── compare.html   # Side-by-side comparison
│       │   └── analytics.html # Aggregate dashboard with charts
│       ├── css/               # Design tokens + component styles
│       └── js/api.js          # Centralized API client
├── Dockerfile
├── docker-compose.yml
└── .env.production.example
```

---

## Quick Start (Local)

### 1. Prerequisites
- Python 3.12+
- A [Groq API key](https://console.groq.com) (free tier available)
- Tesseract OCR (for scanned PDF fallback): [Install guide](https://github.com/UB-Mannheim/tesseract/wiki)

### 2. Setup

```bash
# Clone the repo
git clone https://github.com/your-username/ATS_Resume_score.git
cd ATS_Resume_score/ats-v2/backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — add your GROQ_API_KEY
```

### 3. Run

```bash
# From ats-v2/backend/
python main.py
```

Open **http://localhost:8000** in your browser.

---

## Docker Deployment

```bash
# From the project root
cp .env.production.example .env
# Edit .env — set GROQ_API_KEY and API_KEY

docker compose up -d
```

The app will be available at **http://localhost:8000**.

The SQLite database and downloaded embedding model (~90MB, one-time download) are persisted in a Docker volume (`ats_data`).

---

## API Reference

Full interactive docs available at **http://localhost:8000/docs**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (public) |
| POST | `/api/v1/analyze` | Analyze a resume |
| GET | `/api/v1/history` | List past analyses |
| GET | `/api/v1/analyses/{id}` | Get analysis detail |
| GET | `/api/v1/compare?a={id}&b={id}` | Compare two analyses |
| POST | `/api/v1/feedback` | Submit recruiter feedback |
| GET | `/api/v1/analytics/summary` | Aggregate analytics |

All endpoints except `/health` require the `X-API-Key` header.

---

## Scoring System

| Component | Weight | Method |
|-----------|--------|--------|
| Skill Match | **35%** | 4-tier: exact → alias → cluster → embedding cosine similarity |
| Experience Longevity | **25%** | Logarithmic curve on total months |
| Contextual AI Fit | **40%** | Groq LLM evaluation of experience vs. JD |

---

## Running Tests

```bash
cd ats-v2/backend
python -m pytest tests/ -v
# 61 tests — all should pass
```

---

## Groq Models

This project uses the Groq API. Available models depend on your account tier. 
Currently configured: `groq/compound` (primary) + `qwen/qwen3.6-27b` (fallback).

Check available models: `GET https://api.groq.com/openai/v1/models`

---

## License

MIT
