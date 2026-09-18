# Architecture — ATS Resume Analyzer v2
## Application Flow, Folder Structure & Tech Stack

> **Document Version**: 1.0  
> **Last Updated**: 2026-09-05  
> **Prerequisite Reading**: [PRD.md](file:///d:/ATS_Resume_score/docs/PRD.md)  
> **Design Principle**: Local-first development, cloud-deployable with zero code changes.

---

## 1. System Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                              │
│                                                                      │
│   React SPA (Vite)                                                   │
│   ┌─────────┐  ┌─────────┐  ┌──────────┐  ┌──────────┐            │
│   │ Upload  │  │ Results │  │ History  │  │Analytics │            │
│   │  Page   │  │  View   │  │  Page    │  │Dashboard │            │
│   └────┬────┘  └────┬────┘  └────┬─────┘  └────┬─────┘            │
│        │            │            │              │                    │
│        └────────────┴────────────┴──────────────┘                    │
│                          │                                           │
│                   HTTP / REST API                                    │
└──────────────────────────┬───────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI + Uvicorn)                        │
│                                                                      │
│   ┌─────────────────────────────────────────────────────────────┐    │
│   │                      API Layer                               │    │
│   │   /api/v1/analyze   /api/v1/history   /api/v1/feedback      │    │
│   │   /api/v1/compare   /api/v1/analytics /health               │    │
│   └─────────────┬───────────────────────────────────────────────┘    │
│                 │                                                     │
│   ┌─────────────┴──────────────────────────────────────────────┐     │
│   │                  Processing Pipeline                        │     │
│   │                                                             │     │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │     │
│   │  │Extraction│  │ Security │  │   LLM    │  │ Scoring  │  │     │
│   │  │ Pipeline │→ │Sanitizer │→ │  Parser  │→ │  Engine  │  │     │
│   │  │(3-tier)  │  │(3-layer) │  │(3-retry) │  │(3-score) │  │     │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │     │
│   └────────────────────────────────────────────────────────────┘     │
│                 │                                                     │
│   ┌─────────────┴──────────────────────────────────────────────┐     │
│   │                   Data Layer                                │     │
│   │   SQLAlchemy ORM + Alembic Migrations                       │     │
│   │   SQLite (local) ←→ PostgreSQL (production)                 │     │
│   └─────────────────────────────────────────────────────────────┘     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              │    External Services    │
              │                         │
              │  Groq API (LLaMA 3.3)  │  ← LLM inference (free tier)
              │  ONNX Runtime (local)  │  ← Embedding similarity (local)
              │  Tesseract (local)     │  ← OCR engine (local)
              │  Poppler (local)       │  ← PDF rendering for OCR (local)
              └─────────────────────────┘
```

---

## 2. Application Flow — Complete Request Lifecycle

### 2.1 Analysis Request Flow

```
Step  Component           Action                                   Duration
────  ─────────────────   ──────────────────────────────────────   ────────
 1    Frontend            User drags PDF + types JD + skills        —
 2    Frontend            Client-side validation (type, size)       < 10ms
 3    Frontend            POST /api/v1/analyze (multipart)          —
 4    API Router          Validate: magic bytes, content-type       < 5ms
 5    API Router          Validate: file size, JD not empty         < 5ms
 6    Extraction          Tier 1 (PyMuPDF) ──┐                     ~200ms
 7    Extraction          Tier 2 (pdfplumber) ┘ concurrent          ~300ms
 8    Extraction          Compare results, two-column detection     < 5ms
 9    Extraction          [If needed] Tier 3 (OCR)                  ~2-5s
10    Security            Sanitize text (unicode + injection)       < 10ms
11    Security            Sanitize JD text                          < 5ms
12    LLM Parser          Attempt 1 → Groq API (temp=0.1)          ~1-3s
13    LLM Parser          sanitize_llm_json → Pydantic validate     < 10ms
14    LLM Parser          [If fail] Attempt 2–3 with correction     ~1-3s ea
15    LLM Parser          [If all fail] Regex fallback              < 50ms
16    Verifier            Cross-check fields vs raw text            < 20ms
17    Layout Check        Character ratio + contact presence        < 5ms
18    Scoring             ┌─ Skill match (deterministic)  ──┐      < 50ms
19    Scoring             │  Experience bracket (determ.)    │      < 5ms
20    Scoring             └─ Contextual LLM (async) ────────┘      ~1-3s
                          (18-20 run concurrently via asyncio.gather)
21    Aggregator          Sum scores, clamp, apply confidence       < 5ms
22    Database            Store AnalysisRecord + link to config     < 20ms
23    API Router          Return AnalysisResult JSON                —
24    Frontend            Animate score ring + render breakdown     ~500ms
```

**Total typical latency**: 3–6 seconds (text PDF) | 5–10 seconds (scanned PDF)

### 2.2 History & Feedback Flow

```
Frontend: GET /api/v1/history?page=1&limit=20
  → Backend: query AnalysisRecord table, paginated
  → Return list of analyses with scores + timestamps

Frontend: GET /api/v1/analyses/{id}
  → Backend: query single AnalysisRecord by UUID
  → Return full analysis detail with parsed resume + config version

Frontend: POST /api/v1/feedback
  → Body: { analysis_id, feedback_type, reason }
  → Backend: store RecruiterFeedback linked to analysis + config version

Frontend: GET /api/v1/analytics/summary
  → Backend: aggregate queries (avg scores, tier distribution, feedback stats)
  → Return summary metrics
```

---

## 3. Folder & File Structure

```
ats-resume-analyzer/
│
├── backend/                          ← Python FastAPI application
│   ├── main.py                       ← App factory: create FastAPI, attach routers, lifespan
│   │
│   ├── config.py                     ← All env vars, constants, settings (single source of truth)
│   │
│   ├── routers/                      ← API route handlers (thin — delegate to services)
│   │   ├── __init__.py
│   │   ├── analyze.py                ← POST /api/v1/analyze
│   │   ├── history.py                ← GET /api/v1/history, GET /api/v1/analyses/{id}
│   │   ├── feedback.py               ← POST /api/v1/feedback
│   │   ├── analytics.py              ← GET /api/v1/analytics/*
│   │   └── health.py                 ← GET /health
│   │
│   ├── services/                     ← Business logic (testable without HTTP)
│   │   ├── __init__.py
│   │   ├── analysis_service.py       ← Orchestrates: extract → parse → score → store
│   │   ├── feedback_service.py       ← Feedback CRUD
│   │   └── analytics_service.py      ← Aggregate queries
│   │
│   ├── extraction/                   ← PDF text extraction pipeline
│   │   ├── __init__.py
│   │   ├── pipeline.py               ← extract_text_pipeline() — tier orchestrator
│   │   ├── tier1_fitz.py             ← PyMuPDF extraction
│   │   ├── tier2_plumber.py          ← pdfplumber extraction
│   │   ├── tier3_ocr.py              ← Tesseract OCR extraction
│   │   └── docx_extractor.py         ← DOCX text extraction (ENHANCED)
│   │
│   ├── parsing/                      ← LLM parsing + validation
│   │   ├── __init__.py
│   │   ├── llm_parser.py             ← parse_resume_with_groq() — LLM calls + retry
│   │   ├── regex_fallback.py         ← _regex_fallback_extractor()
│   │   ├── json_sanitizer.py         ← sanitize_llm_json()
│   │   ├── verifier.py               ← verify_parsed_resume() — source cross-check
│   │   └── prompts.py                ← All system/user prompts (centralized)
│   │
│   ├── scoring/                      ← All scoring logic
│   │   ├── __init__.py
│   │   ├── skill_match.py            ← compute_semantic_skill_score()
│   │   ├── skill_normalization.py    ← normalize_string(), canonicalize()
│   │   ├── skill_aliases.py          ← _SKILL_ALIASES dict + reverse index
│   │   ├── skill_clusters.py         ← _SEMANTIC_CLUSTERS dict + reverse index
│   │   ├── embeddings.py             ← ONNX embedding similarity (ENHANCED)
│   │   ├── experience.py             ← compute_experience_longevity()
│   │   ├── contextual.py             ← _contextual_fit_score()
│   │   └── aggregator.py             ← Final score assembly + clamping
│   │
│   ├── security/                     ← Security & sanitization
│   │   ├── __init__.py
│   │   ├── sanitizer.py              ← sanitize_resume_text()
│   │   ├── injection_patterns.py     ← Regex patterns for prompt injection
│   │   ├── file_validator.py         ← Magic byte validation, size check
│   │   ├── auth.py                   ← API key middleware
│   │   └── rate_limiter.py           ← Rate limiting config
│   │
│   ├── models/                       ← Data models
│   │   ├── __init__.py
│   │   ├── schemas.py                ← Pydantic models (ParsedResume, AnalysisResult, etc.)
│   │   └── db_models.py              ← SQLAlchemy ORM models (AnalysisRecord, ScoringConfig, etc.)
│   │
│   ├── db/                           ← Database layer
│   │   ├── __init__.py
│   │   ├── database.py               ← Engine + session factory (async)
│   │   ├── crud.py                   ← CRUD operations
│   │   └── migrations/               ← Alembic migrations
│   │       ├── env.py
│   │       ├── alembic.ini
│   │       └── versions/
│   │
│   ├── tests/                        ← All tests
│   │   ├── __init__.py
│   │   ├── test_fairness.py          ← Fairness regression tests (from prototype)
│   │   ├── test_skill_matching.py    ← Normalization + alias + cluster tests
│   │   ├── test_security.py          ← Injection pattern tests
│   │   ├── test_extraction.py        ← Tier switching tests
│   │   ├── test_api.py               ← Integration tests (FastAPI TestClient)
│   │   └── fixtures/                 ← Test PDF files, sample data
│   │       ├── sample_resume.pdf
│   │       └── sample_jd.txt
│   │
│   ├── requirements.txt              ← Pinned Python dependencies
│   ├── Dockerfile                    ← Multi-stage production build
│   └── .env.example                  ← Template for environment variables
│
├── frontend/                         ← React SPA (Vite)
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html                    ← HTML entry point
│   │
│   ├── public/
│   │   └── favicon.svg
│   │
│   ├── src/
│   │   ├── main.jsx                  ← React entry point
│   │   ├── App.jsx                   ← Root component + routing
│   │   │
│   │   ├── api/                      ← API client layer
│   │   │   ├── client.js             ← Axios/fetch wrapper with base URL + auth header
│   │   │   ├── analyze.js            ← analyzeResume(), getAnalysis()
│   │   │   ├── history.js            ← getHistory(), getAnalysisDetail()
│   │   │   ├── feedback.js           ← submitFeedback()
│   │   │   └── analytics.js          ← getAnalyticsSummary()
│   │   │
│   │   ├── pages/                    ← Full-page components (one per route)
│   │   │   ├── AnalyzePage.jsx       ← Upload + JD form + results
│   │   │   ├── HistoryPage.jsx       ← Analysis history list
│   │   │   ├── DetailPage.jsx        ← Single analysis full breakdown
│   │   │   ├── ComparePage.jsx       ← Side-by-side candidate comparison
│   │   │   ├── AnalyticsPage.jsx     ← Aggregate stats dashboard
│   │   │   └── NotFoundPage.jsx      ← 404
│   │   │
│   │   ├── components/               ← Reusable UI components
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.jsx       ← Navigation sidebar
│   │   │   │   ├── Header.jsx        ← Top bar with search + status
│   │   │   │   └── PageWrapper.jsx   ← Page layout wrapper
│   │   │   │
│   │   │   ├── upload/
│   │   │   │   ├── DropZone.jsx      ← Drag-and-drop file upload
│   │   │   │   ├── FileInfo.jsx      ← Selected file name + size
│   │   │   │   └── AnalyzeForm.jsx   ← JD + skills + submit button
│   │   │   │
│   │   │   ├── results/
│   │   │   │   ├── ScoreRing.jsx     ← Animated SVG circular score
│   │   │   │   ├── ScoreBreakdown.jsx← 3-component horizontal bars
│   │   │   │   ├── SkillTags.jsx     ← Matched (green) + Missing (red) tags
│   │   │   │   ├── VerifiedSkills.jsx← Verified vs Unverified skill panel
│   │   │   │   ├── ExperienceTimeline.jsx ← Timeline with dots + connectors
│   │   │   │   ├── ProjectCards.jsx  ← Project name + tech stack + description
│   │   │   │   ├── Justification.jsx ← AI contextual paragraph
│   │   │   │   ├── MetadataChips.jsx ← Tier badge, processing time, config version
│   │   │   │   └── ReviewBanner.jsx  ← manual_review_recommended warning
│   │   │   │
│   │   │   ├── history/
│   │   │   │   ├── HistoryTable.jsx  ← Sortable/filterable table
│   │   │   │   └── HistoryFilters.jsx← Date range, score range, name search
│   │   │   │
│   │   │   ├── analytics/
│   │   │   │   ├── StatCard.jsx      ← Single metric card
│   │   │   │   ├── ScoreChart.jsx    ← Score distribution chart
│   │   │   │   ├── SkillGapHeatmap.jsx ← Missing skills heatmap
│   │   │   │   └── FeedbackChart.jsx ← Feedback distribution pie/bar
│   │   │   │
│   │   │   ├── feedback/
│   │   │   │   └── FeedbackBar.jsx   ← Accurate / Too High / Too Low / Inaccurate
│   │   │   │
│   │   │   └── common/
│   │   │       ├── Button.jsx
│   │   │       ├── Badge.jsx
│   │   │       ├── Toast.jsx
│   │   │       ├── Loader.jsx
│   │   │       ├── Modal.jsx
│   │   │       ├── Tooltip.jsx
│   │   │       └── EmptyState.jsx
│   │   │
│   │   ├── hooks/                    ← Custom React hooks
│   │   │   ├── useAnalysis.js        ← Analysis state management
│   │   │   ├── useHistory.js         ← History fetching + pagination
│   │   │   └── useTheme.js           ← Dark/light theme toggle
│   │   │
│   │   ├── utils/
│   │   │   ├── formatters.js         ← Score formatting, date formatting
│   │   │   ├── validators.js         ← Client-side file validation
│   │   │   └── constants.js          ← Tier labels, score ranges, colors
│   │   │
│   │   └── styles/
│   │       ├── globals.css           ← CSS reset + design tokens + base styles
│   │       ├── variables.css         ← CSS custom properties (colors, spacing, etc.)
│   │       └── components/           ← Per-component CSS modules (if needed)
│   │
│   └── .env.example                  ← VITE_API_BASE_URL
│
├── docs/                             ← Project documentation (this folder)
│   ├── PRD.md
│   ├── Architecture.md               ← This document
│   ├── Rules.md
│   ├── Phases.md
│   └── Design.md
│
├── docker-compose.yml                ← Orchestrate backend + frontend (+ Postgres for prod)
├── .gitignore
└── README.md                         ← Quick start guide
```

### 3.1 File Responsibility Rules

| Rule | Rationale |
|---|---|
| No file exceeds 300 lines | Prevents monolith formation |
| Routers are thin — max 50 lines per endpoint | Routers validate + delegate; logic lives in services |
| Services contain business logic | Testable without HTTP request context |
| One model file per concern | `schemas.py` = API shapes, `db_models.py` = DB tables |
| All prompts in `prompts.py` | Single location for every LLM prompt — easy to version |
| All constants in `config.py` | No hardcoded values scattered across files |
| Tests mirror source structure | `test_skill_matching.py` tests `scoring/skill_match.py` |

---

## 4. Tech Stack

### 4.1 Backend

| Layer | Technology | Version | Purpose | Why This |
|---|---|---|---|---|
| **Language** | Python | 3.12 | Core runtime | Best LLM/NLP ecosystem, FastAPI built for it |
| **Framework** | FastAPI | 0.115+ | REST API server | Async-native, Pydantic-integrated, auto Swagger docs |
| **ASGI Server** | Uvicorn | 0.32+ | Runs FastAPI | High-performance async server |
| **Validation** | Pydantic v2 | 2.10+ | Schema validation | Rust-compiled, strict mode, custom validators |
| **ORM** | SQLAlchemy 2.0 | 2.0+ | Database abstraction | Industry standard, async support, both SQLite + Postgres |
| **Migrations** | Alembic | 1.13+ | DB schema versioning | Works with SQLAlchemy, autogenerate migrations |
| **DB (local)** | SQLite | built-in | Development database | Zero config, file-based, comes with Python |
| **DB (prod)** | PostgreSQL | 15+ | Production database | ACID, concurrent writes, full SQL |
| **Async DB** | aiosqlite / asyncpg | latest | Async DB drivers | Non-blocking DB operations |
| **LLM Client** | openai SDK | 1.57+ | Groq API calls | Groq is OpenAI-compatible; one SDK for both |
| **LLM Provider** | Groq (free tier) | — | LLM inference | Free, fast (LPU), LLaMA 3.3 70B |
| **Embeddings** | ONNX Runtime | 1.17+ | Skill similarity | 50 MB vs 400 MB (PyTorch), local inference |
| **Embedding Model** | all-MiniLM-L6-v2 | ONNX export | Sentence embeddings | Light, accurate for short texts (skills) |
| **PDF Tier 1** | PyMuPDF (fitz) | 1.25+ | Fast text extraction | Fastest Python PDF reader |
| **PDF Tier 2** | pdfplumber | 0.11+ | Complex layouts | Tables + multi-column |
| **PDF Tier 3** | pytesseract + pdf2image | latest | OCR for scanned PDFs | Industry-standard OCR |
| **DOCX** | python-docx | 1.1+ | Word document support | Simple API for DOCX |
| **Rate Limit** | slowapi | 0.1+ | Request throttling | FastAPI-native, uses Starlette |
| **Logging** | Python logging | stdlib | Structured logs | No external dep needed |
| **Env Config** | python-dotenv | 1.0+ | Load .env file | Standard approach |

### 4.2 Frontend

| Layer | Technology | Version | Purpose | Why This |
|---|---|---|---|---|
| **Framework** | React | 18+ | UI library | Component-based, huge ecosystem, easy to hire for |
| **Build Tool** | Vite | 5+ | Dev server + bundler | Instant HMR, fast builds, zero-config start |
| **Routing** | React Router | 6+ | Client-side navigation | Standard for React SPAs |
| **HTTP Client** | Axios | 1.7+ | API calls | Interceptors for auth headers, better error handling than fetch |
| **Charts** | Recharts | 2.12+ | Data visualization | React-native charts, lightweight |
| **Icons** | Lucide React | latest | Icon library | Clean, consistent, tree-shakeable |
| **CSS** | Vanilla CSS + CSS Modules | — | Styling | Full control, no framework dependency, modular |
| **State** | React useState + useContext | built-in | Local state | No Redux overhead for this project size |
| **Notifications** | react-hot-toast | latest | Toast messages | Simple, beautiful, zero-config |
| **PDF Export** | html2pdf.js | latest | Generate PDF reports | Client-side PDF from HTML |

### 4.3 DevOps

| Tool | Purpose |
|---|---|
| **Docker** | Container for backend (Tesseract + Poppler baked in) |
| **Docker Compose** | Orchestrate backend + frontend + Postgres |
| **Git** | Version control |
| **pytest** | Test runner |
| **pytest-asyncio** | Async test support |

### 4.4 External Services

| Service | Tier | Cost | Purpose |
|---|---|---|---|
| **Groq API** | Free tier | $0 | LLM inference (LLaMA 3.3 70B) — 30 RPM, 6000 tokens/min |
| **Tesseract OCR** | System install | $0 | OCR engine — installed locally or in Docker |
| **Poppler** | System install | $0 | PDF page rendering for OCR — installed locally or in Docker |

---

## 5. Database Schema

### 5.1 Entity Relationship

```
┌─────────────────┐       ┌──────────────────┐       ┌───────────────────┐
│ ScoringConfig   │       │ AnalysisRecord   │       │RecruiterFeedback  │
├─────────────────┤       ├──────────────────┤       ├───────────────────┤
│ id (PK, UUID)   │◄──┐   │ id (PK, UUID)    │◄──┐   │ id (PK, UUID)     │
│ version_tag     │   │   │ candidate_name   │   │   │ analysis_id (FK)  │──► AnalysisRecord
│ skill_weight    │   │   │ resume_hash      │   │   │ config_id (FK)    │──► ScoringConfig
│ exp_weight      │   │   │ jd_hash          │   │   │ feedback_type     │
│ context_weight  │   │   │ total_score      │   │   │ reason            │
│ model_name      │   │   │ skill_score      │   │   │ created_at        │
│ prompt_version  │   └───│ config_id (FK)   │   │   └───────────────────┘
│ created_at      │       │ exp_score        │   │
│ is_active       │       │ ctx_score        │   │
└─────────────────┘       │ parsed_resume    │   │
                          │ raw_text_preview │   │
                          │ field_confidence │   │
                          │ verified_skills  │   │
                          │ unverified_skills│   │
                          │ extraction_tier  │   │
                          │ llm_attempts     │   │
                          │ used_fallback    │   │
                          │ difficult_layout │   │
                          │ manual_review    │   │
                          │ processing_ms    │   │
                          │ created_at       │   │
                          │ job_description  │   │
                          │ required_skills  │   │
                          │ matched_skills   │   │
                          │ missing_skills   │   │
                          │ justification    │   │
                          └──────────────────┘   │
                                                  │
                          ┌──────────────────┐    │
                          │ ResumeCache      │    │
                          ├──────────────────┤    │
                          │ resume_hash (PK) │    │
                          │ parsed_resume    │    │
                          │ field_confidence │    │
                          │ verified_skills  │    │
                          │ extraction_tier  │    │
                          │ created_at       │    │
                          │ expires_at       │    │
                          └──────────────────┘
```

### 5.2 Key Design Decisions

| Decision | Rationale |
|---|---|
| UUID primary keys | Globally unique, no auto-increment conflicts across instances |
| JSON columns for lists | `matched_skills`, `parsed_resume` stored as JSON — avoids complex joins for list data |
| `resume_hash` for dedup | SHA-256 of file bytes. Same resume → skip re-parsing, only re-score |
| `config_id` FK on every record | Every score is auditable: "this score was produced with these weights" |
| `ResumeCache` with TTL | Parsed resumes cached for 30 days. After that, re-parse (model may have improved) |
| `raw_text_preview` | First 500 chars of extracted text — for debugging, not full storage |

---

## 6. API Specification

### 6.1 Endpoints

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/v1/analyze` | API Key | Upload resume + JD → return analysis |
| `GET` | `/api/v1/history` | API Key | List past analyses (paginated, filterable) |
| `GET` | `/api/v1/analyses/{id}` | API Key | Get full analysis detail by UUID |
| `POST` | `/api/v1/feedback` | API Key | Submit recruiter feedback on an analysis |
| `GET` | `/api/v1/analytics/summary` | API Key | Get aggregate statistics |
| `GET` | `/api/v1/compare?ids=uuid1,uuid2` | API Key | Compare 2–4 analyses side by side |
| `GET` | `/health` | None | Health check (public) |
| `GET` | `/api/v1/config/current` | API Key | Get current scoring config version |

### 6.2 Request/Response Examples

**POST /api/v1/analyze**

Request (multipart/form-data):
```
resume:                    <PDF file binary>
job_description:           "We are looking for a Python developer..."
required_skills:           "Python, Docker, PostgreSQL, FastAPI"
experience_target_months:  36
```

Response (200 OK):
```json
{
  "id": "a1b2c3d4-e5f6-...",
  "candidate_name": "Rahul Sharma",
  "total_score": 72.5,
  "semantic_skill_match": 32.0,
  "experience_longevity": 26.25,
  "context_alignment": 14.25,
  "context_justification": "The candidate shows strong backend experience...",
  "total_experience_months": 9,
  "matched_skills": ["Python", "FastAPI"],
  "missing_skills": ["Docker", "PostgreSQL"],
  "extraction_tier_used": 1,
  "processing_time_ms": 3400,
  "llm_parse_attempts": 1,
  "used_regex_fallback": false,
  "difficult_layout_detected": false,
  "manual_review_recommended": false,
  "field_confidence": {
    "name": "verified",
    "skills": "partial",
    "experience[0]": "verified",
    "education": "verified"
  },
  "verified_skills": ["Python", "FastAPI", "Django"],
  "unverified_skills": ["AWS"],
  "unverified_fields": ["skills (unverified: AWS)"],
  "scoring_config_version": "v1.0",
  "parsed_resume": {
    "name": "Rahul Sharma",
    "skills": ["Python", "FastAPI", "Django", "AWS"],
    "experience": [...],
    "education": [...],
    "projects": [...],
    "certifications": [...]
  },
  "created_at": "2026-09-05T12:30:00Z"
}
```

---

## 7. Local Development Setup

### 7.1 Prerequisites

```
Python 3.12+
Node.js 18+ (with npm)
Tesseract OCR (system install)
Poppler (system install — Windows only, Linux has it by default)
```

### 7.2 Quick Start

```bash
# Clone
git clone <repo-url> ats-resume-analyzer
cd ats-resume-analyzer

# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # Add GROQ_API_KEY
python main.py                  # Runs on localhost:8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                     # Runs on localhost:5173
```

### 7.3 Environment Variables

```env
# === LLM ===
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_BASE_URL=https://api.groq.com/openai/v1

# === Database ===
DATABASE_URL=sqlite+aiosqlite:///./ats_data.db    # Local
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/ats  # Production

# === Security ===
API_KEY=your-secret-api-key-here
CORS_ORIGINS=http://localhost:5173

# === Limits ===
MAX_FILE_SIZE_MB=10
OCR_CHAR_THRESHOLD=150
EXPERIENCE_TARGET_MONTHS=36
RATE_LIMIT=30/minute

# === Paths (Windows only — Docker handles these automatically) ===
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
POPPLER_PATH=C:\poppler\Library\bin
```

### 7.4 Deployment (Docker Compose)

```yaml
# docker-compose.yml
version: '3.9'
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: ./backend/.env
    depends_on: [db]
    
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ats
      POSTGRES_USER: ats_user
      POSTGRES_PASSWORD: ats_pass
    volumes: ["pgdata:/var/lib/postgresql/data"]

volumes:
  pgdata:
```

---

## 8. Key Architecture Decisions (ADRs)

### ADR-1: Monorepo (backend + frontend in one repo)
**Decision**: Keep backend and frontend in the same Git repository.  
**Rationale**: Single developer project. Simpler CI. Shared documentation.  
**Trade-off**: Larger repo, but manageable at this scale.

### ADR-2: SQLite as default, PostgreSQL as option
**Decision**: Default to SQLite for local dev. Switch to PostgreSQL via env var for production.  
**Rationale**: Zero-config local setup. SQLAlchemy abstracts the difference.  
**Trade-off**: SQLite doesn't support concurrent writes well — acceptable for single-user local use.

### ADR-3: React SPA (not server-rendered)
**Decision**: Use React with Vite as a single-page application. No server-side rendering.  
**Rationale**: Dashboard UI doesn't need SEO. Faster development. Clean separation from backend.  
**Trade-off**: Initial page load slightly slower than SSR. Acceptable for internal tool.

### ADR-4: ONNX Runtime over PyTorch
**Decision**: Export embedding model to ONNX format and use ONNX Runtime instead of loading via PyTorch/sentence-transformers.  
**Rationale**: 50 MB RAM vs 400 MB. No PyTorch dependency. Faster cold-start.  
**Trade-off**: Must pre-export the model. Slightly more setup work once.

### ADR-5: No WebSocket — polling for analysis status
**Decision**: Use standard HTTP request/response. Frontend waits for the POST to complete (3–8 seconds). No WebSocket for real-time updates.  
**Rationale**: Single analysis takes < 10 seconds. WebSocket adds complexity for no real benefit.  
**Trade-off**: If analysis ever takes > 30 seconds (e.g., batch), this decision should be revisited.

### ADR-6: Vanilla CSS (no Tailwind, no CSS-in-JS)
**Decision**: Use CSS custom properties + CSS modules for styling.  
**Rationale**: Full control over design system. No framework dependency. Smaller bundle.  
**Trade-off**: More manual CSS writing. Acceptable for a design-focused project.
